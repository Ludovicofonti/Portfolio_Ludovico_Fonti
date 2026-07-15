"""Pipeline quantitativa crypto end-to-end, configurabile e point-in-time."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

from config import (
    DUCKDB_PATH,
    annualization_factor,
    load_yaml_config,
    resolve_asset_config,
)
from evaluation.forecast_tests import diebold_mariano_hac
from evaluation.calibration import expected_calibration_error
from evaluation.metrics import (
    classification_metrics,
    pinball_loss,
    qlike,
    regression_metrics,
)
from evaluation.risk_backtesting import (
    conditional_coverage_test,
    expected_shortfall_backtest,
)
from evaluation.stability import fold_stability, grouped_performance
from evaluation.walk_forward import WalkForwardConfig, temporal_splits, walk_forward_evaluate
from experiments.artifacts import save_artifacts
from experiments.metadata import dataset_hash, git_commit
from experiments.registry import ExperimentRegistry
from features.leakage_checks import assert_available_at_origin, assert_sorted_time, assert_target_absent
from models.regimes import classify_regimes
from models.risk.extreme_value import fit_peaks_over_threshold
from reporting.business_report import promotion_decision, render_business_summary
from reporting.charts import save_diagnostic_charts
from reporting.technical_report import render_technical_report
from strategy.execution import cost_sensitivity
from strategy.signals import return_to_position
from strategy.transaction_costs import TransactionCostModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURES = (
    "return_1",
    "high_low_range",
    "close_open_return",
    "taker_buy_ratio",
    "funding_rate",
    "funding_zscore",
    "open_interest_change",
    "open_interest_zscore",
    "spread_bps",
    "order_book_imbalance",
    "depth_1pct",
    "long_short_ratio",
    "long_short_zscore",
    "buy_sell_ratio",
    "buy_sell_zscore",
    "basis_rate",
    "basis_zscore",
    "basis_change",
    "onchain_active_addresses",
    "onchain_transaction_count",
    "onchain_hash_rate",
    "onchain_market_cap_usd",
    "onchain_current_supply",
)


@dataclass(frozen=True)
class ResearchOptions:
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    horizon: int = 1
    model: str = "auto"
    task: str = "return"
    database: str = DUCKDB_PATH
    reports_dir: str = "reports"
    artifacts_dir: str = "reports/artifacts"


TASK_MODELS = {
    "return": "ridge_return",
    "direction": "ridge_direction",
    "volatility": "garch_student_t_1_1",
    "tail": "ridge_tail",
}

MODEL_TASKS = {
    "ridge_return": "return",
    "arima_return": "return",
    "sarima_return": "return",
    "ridge_direction": "direction",
    "garch_student_t_1_1": "volatility",
    "ridge_tail": "tail",
}


def _target_column(options: ResearchOptions) -> str:
    if options.task not in TASK_MODELS:
        raise ValueError(f"Task non supportato: {options.task}")
    if options.task in {"volatility", "tail"}:
        if options.horizon != 24:
            raise ValueError(f"Il task {options.task} richiede --horizon 24")
        return "target_volatility_24" if options.task == "volatility" else "target_tail_return_24"
    prefix = "target_return" if options.task == "return" else "target_direction"
    return f"{prefix}_{options.horizon}"


def _resolved_model(options: ResearchOptions) -> str:
    return TASK_MODELS[options.task] if options.model == "auto" else options.model


def load_model_dataset(options: ResearchOptions) -> pd.DataFrame:
    target = _target_column(options)
    with duckdb.connect(str(PROJECT_ROOT / options.database), read_only=True) as connection:
        columns = {
            row[0] for row in connection.execute(
                "describe analytics.fct_model_dataset"
            ).fetchall()
        }
        if target not in columns:
            raise ValueError(f"Target non disponibile nel mart: {target}")
        frame = connection.execute(
            f"""
            select *
            from analytics.fct_model_dataset
            where symbol = ? and interval = ? and {target} is not null
              and quality_flag = 'valid'
            order by forecast_origin
            """,
            [options.symbol, options.interval],
        ).df()
    if frame.empty:
        raise ValueError(
            f"Nessun dato in analytics.fct_model_dataset per {options.symbol}/{options.interval}"
        )
    frame["forecast_origin"] = pd.to_datetime(frame["forecast_origin"], utc=True)
    frame["available_time"] = pd.to_datetime(frame["available_time"], utc=True)
    frame = frame.set_index("forecast_origin", drop=False)
    assert_sorted_time(frame.reset_index(drop=True), "forecast_origin")
    assert_available_at_origin(frame, frame["forecast_origin"])
    return frame


def _walk_forward_config(horizon: int, interval: str) -> WalkForwardConfig:
    raw = load_yaml_config("backtesting.yml")["walk_forward"]
    allowed = set(WalkForwardConfig.__dataclass_fields__)
    values = {key: value for key, value in raw.items() if key in allowed}
    for field in ("initial_train_size", "test_size", "step_size"):
        override = raw.get(f"{field}_by_frequency", {}).get(interval)
        if override is not None:
            values[field] = int(override)
    values["gap_size"] = max(int(values.get("gap_size", 0)), horizon)
    return WalkForwardConfig(**values)


def _ridge_predictor(alpha: float):
    def fit_predict(x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame):
        train = x_train.replace([np.inf, -np.inf], np.nan)
        test = x_test.replace([np.inf, -np.inf], np.nan)
        active = [
            column for column in train
            if train[column].notna().mean() >= 0.80 and train[column].nunique(dropna=True) > 1
        ]
        if not active:
            return np.repeat(float(y_train.mean()), len(test))
        train = train[active]
        test = test[active]
        medians = train.median().fillna(0.0)
        train = train.fillna(medians)
        test = test.fillna(medians)
        means = train.mean()
        scales = train.std(ddof=0).replace(0, 1.0).fillna(1.0)
        train_values = np.clip(((train - means) / scales).to_numpy(float), -8.0, 8.0)
        test_values = np.clip(((test - means) / scales).to_numpy(float), -8.0, 8.0)
        design = np.column_stack([np.ones(len(train_values)), train_values])
        penalty = np.eye(design.shape[1]) * alpha
        penalty[0, 0] = 0.0
        coefficients = np.linalg.pinv(design.T @ design + penalty) @ design.T @ y_train.to_numpy(float)
        return np.column_stack([np.ones(len(test_values)), test_values]) @ coefficients

    return fit_predict


def _time_series_predictor(model_name: str, hyperparameters: dict):
    def fit_predict(x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame):
        import warnings

        clean = y_train.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
        if model_name == "arima_return":
            from statsmodels.tsa.arima.model import ARIMA

            order = tuple(hyperparameters.get("order", (1, 0, 1)))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fitted = ARIMA(clean, order=order).fit()
            return np.asarray(fitted.forecast(steps=len(x_test)), dtype=float)
        if model_name == "sarima_return":
            from statsmodels.tsa.statespace.sarimax import SARIMAX

            order = tuple(hyperparameters.get("order", (1, 0, 1)))
            seasonal = tuple(hyperparameters.get("seasonal_order", (1, 0, 1, 24)))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fitted = SARIMAX(
                    clean,
                    order=order,
                    seasonal_order=seasonal,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False)
            return np.asarray(fitted.forecast(steps=len(x_test)), dtype=float)
        if model_name == "garch_student_t_1_1":
            from arch import arch_model

            returns = x_train["return_1"].replace([np.inf, -np.inf], np.nan).dropna() * 100
            fitted = arch_model(
                returns,
                vol="GARCH",
                p=int(hyperparameters.get("p", 1)),
                q=int(hyperparameters.get("q", 1)),
                dist=str(hyperparameters.get("distribution", "t")),
                rescale=False,
            ).fit(disp="off")
            forecast = fitted.forecast(horizon=len(x_test), reindex=False)
            return np.sqrt(np.maximum(forecast.variance.values[-1], 1e-12)) / 100
        raise ValueError(f"Predictor time-series non supportato: {model_name}")

    return fit_predict


def _model_predictor(model_name: str, model_config: dict, task: str):
    hyperparameters = model_config.get("hyperparameters", {})
    if model_name in {"arima_return", "sarima_return", "garch_student_t_1_1"}:
        return _time_series_predictor(model_name, hyperparameters)
    alpha = float(hyperparameters.get("ridge_alpha", 1.0))
    ridge = _ridge_predictor(alpha)
    if task != "direction":
        return ridge

    def probability_predictor(x_train, y_train, x_test):
        return np.clip(ridge(x_train, y_train, x_test), 1e-6, 1 - 1e-6)

    return probability_predictor


def _baseline_results(features, target, config, task: str):
    if task == "direction":
        factories = {
            "neutral_probability": lambda _x, _y, test: np.repeat(0.5, len(test)),
            "historical_prevalence": lambda _x, train, test: np.repeat(float(train.mean()), len(test)),
            "last_direction": lambda _x, train, test: np.repeat(float(train.iloc[-1]), len(test)),
        }
    elif task == "volatility":
        factories = {
            "historical_mean_volatility": lambda _x, train, test: np.repeat(float(train.mean()), len(test)),
            "last_volatility": lambda _x, train, test: np.repeat(float(train.iloc[-1]), len(test)),
            "ewma_volatility": lambda x, _y, test: np.repeat(
                float(x["return_1"].ewm(span=24).std().iloc[-1]), len(test)
            ),
        }
    elif task == "tail":
        factories = {
            "historical_mean": lambda _x, train, test: np.repeat(float(train.mean()), len(test)),
            "historical_tail_quantile": lambda _x, train, test: np.repeat(float(train.quantile(0.05)), len(test)),
            "last_observed_return": lambda _x, train, test: np.repeat(float(train.iloc[-1]), len(test)),
        }
    else:
        factories = {
            "zero_return": lambda _x, _y, test: np.zeros(len(test)),
            "historical_mean": lambda _x, train, test: np.repeat(float(train.mean()), len(test)),
            "last_observed_return": lambda _x, train, test: np.repeat(float(train.iloc[-1]), len(test)),
        }
    return {
        name: walk_forward_evaluate(features, target, predictor, config)
        for name, predictor in factories.items()
    }


def _rolling_risk_forecasts(frame: pd.DataFrame, result: pd.DataFrame, confidence: float):
    var_values, es_values = [], []
    for origin in pd.to_datetime(result["date"], utc=True):
        history = frame.loc[:origin, "return_1"].replace([np.inf, -np.inf], np.nan).dropna().tail(500)
        if len(history) < 100:
            var_values.append(np.nan)
            es_values.append(np.nan)
            continue
        var = float(history.quantile(1 - confidence))
        tail = history[history <= var]
        var_values.append(var)
        es_values.append(float(tail.mean()) if len(tail) else var)
    return np.asarray(var_values), np.asarray(es_values)


def _direction_diagnostics(target: pd.Series, predictions: pd.DataFrame, config: WalkForwardConfig):
    probabilities = []
    for train_idx, test_idx in temporal_splits(len(target), config):
        scale = max(float(target.iloc[train_idx].std(ddof=1)), 1e-12)
        fold = predictions[predictions["fold"] == len(probabilities)]
        probabilities.append(stats.norm.cdf(fold["forecast"].to_numpy(float) / scale))
    probability = np.concatenate(probabilities)
    actual = (predictions["actual"].to_numpy(float) > 0).astype(int)
    metrics = classification_metrics(actual, probability)
    metrics["expected_calibration_error"] = expected_calibration_error(actual, probability)
    return metrics


def _task_metrics(task: str, actual, forecast, quantile: float = 0.05) -> dict:
    if task == "direction":
        metrics = classification_metrics(actual, forecast)
        metrics["expected_calibration_error"] = expected_calibration_error(actual, forecast)
        return metrics
    metrics = regression_metrics(actual, forecast)
    if task == "volatility":
        metrics["qlike"] = qlike(
            np.square(np.asarray(actual, dtype=float)),
            np.square(np.maximum(np.asarray(forecast, dtype=float), 1e-12)),
        )
    elif task == "tail":
        metrics[f"pinball_loss_{int(quantile * 100):02d}"] = pinball_loss(
            actual, forecast, quantile
        )
    return metrics


def _json_hash(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_research(options: ResearchOptions) -> dict:
    asset_key, asset = resolve_asset_config(options.symbol)
    model_name = _resolved_model(options)
    if MODEL_TASKS.get(model_name) != options.task:
        raise ValueError(
            f"Il modello {model_name} non è compatibile con il task {options.task}"
        )
    model_config = load_yaml_config("models.yml")["models"].get(model_name)
    if not model_config:
        raise ValueError(f"Modello non configurato: {model_name}")
    frame = load_model_dataset(options)
    target_column = _target_column(options)
    feature_columns = [name for name in DEFAULT_FEATURES if name in frame and not frame[name].isna().all()]
    if not feature_columns:
        raise ValueError("Nessuna feature numerica utilizzabile")
    assert_target_absent(feature_columns, [name for name in frame if name.startswith("target_")])
    features = frame[feature_columns].astype(float)
    target = frame[target_column].astype(float)
    config = _walk_forward_config(options.horizon, options.interval)
    minimum = config.initial_train_size + config.gap_size + config.test_size
    if len(frame) < minimum:
        raise ValueError(f"Servono almeno {minimum} righe per il walk-forward; disponibili: {len(frame)}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    registry = ExperimentRegistry(PROJECT_ROOT / "data" / "experiments.duckdb")
    registry.register({
        "run_id": run_id,
        "git_commit": git_commit(PROJECT_ROOT),
        "data_start": frame.index.min(),
        "data_end": frame.index.max(),
        "data_version": dataset_hash(frame),
        "asset": asset_key,
        "frequency": options.interval,
        "target": target_column,
        "horizon": options.horizon,
        "model_name": model_name,
        "hyperparameters": model_config.get("hyperparameters", {}),
        "feature_set": feature_columns,
        "cost_scenario": "base",
        "random_seed": load_yaml_config("backtesting.yml")["walk_forward"].get("random_seed", 42),
        "primary_metric": model_config.get("primary_metric", "mae"),
        "status": "started",
    })

    try:
        predictions = walk_forward_evaluate(
            features, target, _model_predictor(model_name, model_config, options.task), config
        )
        if predictions.empty:
            raise ValueError("Il walk-forward non ha prodotto fold")
        baselines = _baseline_results(features, target, config, options.task)
        quantile = float(model_config.get("hyperparameters", {}).get("quantile", 0.05))
        model_metrics = _task_metrics(
            options.task, predictions["actual"], predictions["forecast"], quantile
        )
        baseline_metrics = {
            name: _task_metrics(options.task, result["actual"], result["forecast"], quantile)
            for name, result in baselines.items()
        }
        primary_metric = str(model_config.get("primary_metric", "mae"))
        if primary_metric not in model_metrics:
            raise ValueError(f"Metrica primaria non prodotta: {primary_metric}")
        best_baseline = min(
            baseline_metrics, key=lambda name: baseline_metrics[name][primary_metric]
        )
        best_baseline_result = baselines[best_baseline]
        best_baseline_metric = baseline_metrics[best_baseline][primary_metric]
        dm_test = diebold_mariano_hac(
            best_baseline_result,
            predictions,
            label_a=best_baseline,
            label_b=model_name,
            loss="absolute",
            horizon=options.horizon,
        )

        per_fold = predictions.groupby("fold").apply(
            lambda group: float(np.mean(np.abs(group["actual"] - group["forecast"]))),
            include_groups=False,
        )
        baseline_fold = best_baseline_result.groupby("fold").apply(
            lambda group: float(np.mean(np.abs(group["actual"] - group["forecast"]))),
            include_groups=False,
        )
        stability = fold_stability((baseline_fold - per_fold).reindex(per_fold.index))
        residuals = predictions["actual"] - predictions["forecast"]
        actual_scale = float(predictions["actual"].std(ddof=1))
        residual_bias_score = max(
            0.0, 1.0 - abs(float(residuals.mean())) / max(actual_scale, 1e-12)
        )
        if options.task == "return":
            direction = _direction_diagnostics(target, predictions, config)
        elif options.task == "direction":
            direction = model_metrics
        else:
            direction = {"status": "not_applicable", "task": options.task}
        calibration_error = direction.get("expected_calibration_error", 0.0)
        calibration_score = max(0.0, 1.0 - float(calibration_error))
        residuals_valid = bool(np.isfinite(residuals).all() and residual_bias_score >= 0.5)

        venue = "binance_perpetual" if asset.get("market") == "perpetual" else "binance_spot"
        cost_model = TransactionCostModel.from_config(venue)
        expected_cost = (
            cost_model.taker_fee_bps
            + cost_model.default_spread_bps / 2
            + cost_model.minimum_slippage_bps
        ) / 10_000
        prediction_index = pd.to_datetime(predictions["date"], utc=True)
        if options.task == "return":
            raw_positions = return_to_position(predictions["forecast"], expected_cost)
        elif options.task == "direction":
            probability = predictions["forecast"].to_numpy(float)
            raw_positions = np.where(probability >= 0.55, 1.0, np.where(probability <= 0.45, -1.0, 0.0))
        else:
            raw_positions = np.zeros(len(predictions))
        positions = pd.Series(raw_positions, index=prediction_index)
        strategy_target = f"target_return_{options.horizon}"
        realized_values = (
            frame[strategy_target].reindex(prediction_index).to_numpy(float)
            if strategy_target in frame
            else np.zeros(len(predictions))
        )
        realized = pd.Series(realized_values, index=prediction_index)
        cost_analysis = cost_sensitivity(
            realized,
            positions,
            cost_model,
            periods_per_year=annualization_factor(asset_key, options.interval),
            execution_lag=0,
        )
        base_pnl = cost_analysis["base"]["pnl"]
        base_metrics = cost_analysis["base"]["metrics"]

        regimes = classify_regimes(
            frame["return_1"].astype(float),
            frame["close"].astype(float),
        )
        base_pnl["regime"] = regimes["volatility_regime"].reindex(base_pnl.index)
        base_pnl["year"] = base_pnl.index.year
        base_pnl["asset"] = asset_key
        grouped = grouped_performance(base_pnl)

        confidence = float(load_yaml_config("backtesting.yml")["promotion"]["confidence_level"])
        var_forecast, es_forecast = _rolling_risk_forecasts(frame, predictions, confidence)
        risk_actual = frame["return_1"].reindex(prediction_index).to_numpy(float)
        try:
            evt = fit_peaks_over_threshold(risk_actual, confidence=0.99)
        except ValueError as exc:
            evt = {"status": "not_available", "reason": str(exc)}
        risk = {
            "conditional_coverage": conditional_coverage_test(
                risk_actual, var_forecast, confidence
            ),
            "expected_shortfall": expected_shortfall_backtest(
                risk_actual, var_forecast, es_forecast
            ),
            "evt_pot": evt,
        }

        promotion_cfg = load_yaml_config("backtesting.yml")["promotion"]
        decision = promotion_decision(
            model_metric=model_metrics[primary_metric],
            baseline_metric=best_baseline_metric,
            higher_is_better=False,
            net_return=base_metrics["cumulative_net_return"],
            stability_score=float(stability.get("stability_score", 0.0)),
            calibration_score=calibration_score,
            minimum_stability=float(promotion_cfg["minimum_stability_score"]),
            minimum_calibration=float(promotion_cfg["minimum_calibration_score"]),
            residuals_valid=residuals_valid,
            require_positive_after_costs=options.task in {"return", "direction"},
        )
        cost_metrics = {
            name: values["metrics"]
            for name, values in cost_analysis.items()
            if isinstance(values, dict) and "metrics" in values
        }
        configuration = {
            "options": asdict(options),
            "walk_forward": asdict(config),
            "model": model_config,
            "asset": asset,
            "features": feature_columns,
            "feature_coverage": {
                column: float(frame[column].replace([np.inf, -np.inf], np.nan).notna().mean())
                for column in feature_columns
            },
            "expected_cost_return": expected_cost,
        }
        summary = {
            "run_id": run_id,
            "asset": asset_key,
            "symbol": options.symbol,
            "interval": options.interval,
            "horizon": options.horizon,
            "task": options.task,
            "target": target_column,
            "model": model_name,
            "primary_metric": primary_metric,
            "observations": len(frame),
            "forecast_observations": len(predictions),
            "data_start": frame.index.min(),
            "data_as_of": frame.index.max(),
            "data_version": dataset_hash(frame),
            "configuration_hash": _json_hash(configuration),
            "model_metrics": model_metrics,
            "baseline_metrics": baseline_metrics,
            "best_baseline": best_baseline,
            "dm_test": dm_test,
            "stability": stability,
            "calibration_score": calibration_score,
            "residual_bias_score": residual_bias_score,
            "direction_metrics": direction,
            "cost_metrics": cost_metrics,
            "risk": risk,
            "performance_by_group": grouped,
            "promotion": decision,
        }

        artifact_target = PROJECT_ROOT / options.artifacts_dir / run_id
        summary["charts"] = save_diagnostic_charts(
            artifact_target,
            predictions=predictions,
            pnl=base_pnl,
            var_forecast=var_forecast,
        )
        artifact_path = save_artifacts(
            artifact_target,
            configuration=configuration,
            metrics=summary,
            predictions=predictions,
            residuals=residuals,
        )
        reports = _write_reports(options, summary, configuration, feature_columns)
        summary["artifact_path"] = str(artifact_path)
        summary["reports"] = reports
        registry.update_status(
            run_id,
            "completed",
            primary_metric_value=model_metrics[primary_metric],
            baseline_metric_value=best_baseline_metric,
            net_sharpe=base_metrics["sharpe_ratio"],
            max_drawdown=base_metrics["maximum_drawdown"],
            artifact_path=str(artifact_path),
        )
        return summary
    except Exception:
        registry.update_status(run_id, "failed")
        raise


def _write_reports(options, summary, configuration, feature_columns):
    reports_dir = PROJECT_ROOT / options.reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = f"{options.symbol}_{options.interval}_{options.task}_h{options.horizon}_{timestamp}"
    charts = {}
    for name, path in summary.get("charts", {}).items():
        chart_path = Path(path)
        try:
            charts[name] = chart_path.resolve().relative_to(reports_dir.resolve()).as_posix()
        except ValueError:
            charts[name] = chart_path.as_posix()
    context = {
        "Data lineage": {
            "source": "Binance API → dlt/raw_finance → dbt/analytics.fct_model_dataset",
            "data_version": summary["data_version"],
            "configuration_hash": summary["configuration_hash"],
            "data_as_of": summary["data_as_of"],
        },
        "Qualità e freshness dei dati": {
            "observations": summary["observations"],
            "forecast_observations": summary["forecast_observations"],
            "point_in_time_check": "pass",
        },
        "Descrizione del target": {
            "task": options.task,
            "column": summary["target"],
            "horizon_periods": options.horizon,
            "forecast_origin": "chiusura candela, con sole feature disponibili a quel timestamp",
        },
        "Feature disponibili al forecast origin": {
            "candidates": feature_columns,
            "coverage": configuration.get(
                "feature_coverage", {column: None for column in feature_columns}
            ),
            "fold_admission_rule": "copertura training >= 80%; imputazione e scaling fittati nel fold",
        },
        "Baseline": summary["baseline_metrics"],
        "Configurazione walk-forward": configuration["walk_forward"],
        "Risultati per fold": summary["stability"],
        "Significatività del confronto": {
            "diebold_mariano": summary["dm_test"],
            "direction_metrics": summary["direction_metrics"],
        },
        "Performance per regime": summary["performance_by_group"],
        "Performance dopo i costi": summary["cost_metrics"],
        "VaR backtesting": summary["risk"]["conditional_coverage"],
        "Expected Shortfall": {
            "rolling_backtest": summary["risk"]["expected_shortfall"],
            "evt_pot": summary["risk"]["evt_pot"],
        },
        "Sensitivity analysis": summary["cost_metrics"],
        "Grafici e artefatti": charts,
        "Limiti": [
            "Il modello è sperimentale e non implica eseguibilità futura.",
            "Order book e dati derivati possono avere copertura più corta dell'OHLCV.",
            "La simulazione non modella market impact istituzionale.",
        ],
        "Condizioni di rifiuto del modello": summary["promotion"],
    }
    technical_path = reports_dir / f"REPORT_TECHNICAL_{suffix}.md"
    technical_path.write_text(render_technical_report(context), encoding="utf-8")
    paths = {"technical": str(technical_path)}
    business_context = {
        "run_id": summary["run_id"],
        "asset": summary["asset"],
        "symbol": summary["symbol"],
        "task": summary["task"],
        "target": summary["target"],
        "model": summary["model"],
        "horizon": summary["horizon"],
        "data_start": summary["data_start"],
        "data_as_of": summary["data_as_of"],
        "observations": summary["observations"],
        "forecast_observations": summary["forecast_observations"],
        "primary_metric": summary["primary_metric"],
        "baseline_comparison": {
            "model": summary["model_metrics"],
            "best_baseline_name": summary["best_baseline"],
            "best_baseline": summary["baseline_metrics"][summary["best_baseline"]],
            "diebold_mariano": summary["dm_test"],
        },
        "net_performance": summary["cost_metrics"]["base"],
        "regime": summary["performance_by_group"].get("regime", {}),
        "cost_impact": summary["cost_metrics"],
        "risk_threshold": summary["risk"],
        "charts": charts,
    }
    business_path = reports_dir / f"REPORT_BUSINESS_{suffix}.md"
    business_path.write_text(
        render_business_summary(business_context, summary["promotion"]),
        encoding="utf-8",
    )
    paths["business"] = str(business_path)
    return paths


def platform_status(database: str = DUCKDB_PATH) -> dict:
    db_path = PROJECT_ROOT / database
    status = {"database": str(db_path), "exists": db_path.exists(), "tables": {}}
    if not db_path.exists():
        return status
    with duckdb.connect(str(db_path), read_only=True) as connection:
        tables = connection.execute(
            """
            select table_schema, table_name
            from information_schema.tables
            where table_schema in ('raw_finance', 'analytics')
            order by 1, 2
            """
        ).fetchall()
        for schema, table in tables:
            count = connection.execute(f'select count(*) from "{schema}"."{table}"').fetchone()[0]
            status["tables"][f"{schema}.{table}"] = int(count)
        if "analytics.fct_model_dataset" in status["tables"]:
            records = connection.execute(
                """
                with model_data as (
                  select symbol, interval, count(*) as rows, max(forecast_origin) as data_as_of
                  from analytics.fct_model_dataset group by 1, 2
                ),
                feature_data as (
                  select symbol, interval, max(close_time) as feature_data_as_of
                  from (
                    select symbol, interval, close_time from analytics.fct_crypto_features_hourly
                    union all
                    select symbol, interval, close_time from analytics.fct_crypto_features_daily
                  )
                  group by 1, 2
                )
                select m.*, f.feature_data_as_of
                from model_data m left join feature_data f using (symbol, interval)
                order by symbol, interval
                """
            ).df().to_dict("records")
            expected_delay = float(
                load_yaml_config("data_sources.yml")["sources"]["binance_spot"]
                .get("expected_delay_seconds", 120)
            ) / 3600
            now = pd.Timestamp.now(tz="UTC")
            for record in records:
                as_of = pd.Timestamp(record["feature_data_as_of"])
                as_of = as_of.tz_localize("UTC") if as_of.tzinfo is None else as_of.tz_convert("UTC")
                interval = str(record["interval"])
                interval_hours = int(interval[:-1]) * (24 if interval.endswith("d") else 1)
                record["freshness_hours"] = float((now - as_of).total_seconds() / 3600)
                record["stale"] = record["freshness_hours"] > interval_hours * 2 + expected_delay
            status["model_dataset"] = records
    reports_root = PROJECT_ROOT / "reports"
    technical_reports = list(reports_root.glob("REPORT_TECHNICAL_*.md"))
    business_reports = list(reports_root.glob("REPORT_BUSINESS_*.md"))
    latest_technical = (
        max(technical_reports, key=lambda path: path.stat().st_mtime)
        if technical_reports else None
    )
    latest_business = (
        max(business_reports, key=lambda path: path.stat().st_mtime)
        if business_reports else None
    )
    status["latest_technical_report"] = str(latest_technical) if latest_technical else None
    status["latest_business_report"] = str(latest_business) if latest_business else None
    return status


def regenerate_report(run_id: str | None = None, artifacts_dir: str = "reports/artifacts") -> dict:
    root = PROJECT_ROOT / artifacts_dir
    candidates = [root / run_id] if run_id else sorted(path for path in root.glob("*") if path.is_dir())
    if not candidates or not candidates[-1].exists():
        raise ValueError("Nessuna run disponibile per rigenerare il report")
    run_path = candidates[-1]
    configuration = json.loads((run_path / "configuration.json").read_text(encoding="utf-8"))
    summary = json.loads((run_path / "metrics.json").read_text(encoding="utf-8"))
    options = ResearchOptions(**configuration["options"])
    return _write_reports(options, summary, configuration, configuration["features"])
