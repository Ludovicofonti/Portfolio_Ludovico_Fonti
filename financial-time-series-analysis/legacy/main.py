"""
legacy/main.py — Pipeline storica end-to-end della piattaforma di analisi finanziaria.

Flusso:
  1. Ingestion dlt  → DuckDB (yahoo + FRED)
  2. dbt run        → trasformazioni SQL (staging → intermediate → marts)
  3. Analisi statistica (stazionarietà, ACF/PACF, rolling, decomposizione)
  4. Modelli ARIMA, SARIMA, GARCH, EGARCH, TARCH, VAR, Prophet
  5. Backtesting walk-forward (ARIMA vs SARIMA)
  6. Simulazioni Monte Carlo GBM vs GARCH-MC

Uso:
    python main.py [--skip-ingestion] [--skip-dbt] [--ticker AAPL]
"""

import argparse
import os
import subprocess
import sys
import warnings

import duckdb
import numpy as np
import pandas as pd

from config import (
    ASSETS,
    DUCKDB_PATH,
    DBT_DATASET,
    PRIMARY_TICKER,
    FORECAST_STEPS,
    MC_N_SIMULATIONS,
    MC_HORIZON_DAYS,
    MC_CONFIDENCE,
    annualization_factor,
    seasonal_periods,
    ConfigurationError,
)
from report import generate_report
from report_business import generate_business_report

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_returns(symbol: str) -> pd.Series:
    """Carica i rendimenti logaritmici da DuckDB marts."""
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    df = con.execute(
        f"SELECT date, log_return FROM {DBT_DATASET}.fct_asset_returns "
        "WHERE symbol = ? ORDER BY date",
        [symbol],
    ).df()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["log_return"].dropna()


def load_prices(symbol: str) -> pd.Series:
    """Carica i prezzi di chiusura da DuckDB marts."""
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    df = con.execute(
        f"SELECT date, close FROM {DBT_DATASET}.fct_asset_returns "
        "WHERE symbol = ? ORDER BY date",
        [symbol],
    ).df()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"].dropna()


def load_risk_metrics() -> pd.DataFrame:
    """Carica la tabella di metriche di rischio da DuckDB."""
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    df = con.execute(f"SELECT * FROM {DBT_DATASET}.fct_risk_metrics").df()
    con.close()
    return df


def run_ingestion() -> None:
    print("\n" + "=" * 60)
    print("  FASE 1 — Ingestion dlt")
    print("=" * 60)
    subprocess.run(
        [sys.executable, "pipelines/run_ingestion.py", "--yahoo-only"],
        check=True,
    )


def run_dbt() -> None:
    print("\n" + "=" * 60)
    print("  FASE 2 — Trasformazioni dbt")
    print("=" * 60)
    dbt_dir = os.path.join(os.path.dirname(__file__), "dbt")
    env = {**os.environ, "DBT_PROFILES_DIR": dbt_dir}
    subprocess.run(
        ["dbt", "run", "--profiles-dir", dbt_dir, "--project-dir", dbt_dir],
        check=True,
        env=env,
    )
    subprocess.run(
        ["dbt", "test", "--profiles-dir", dbt_dir, "--project-dir", dbt_dir],
        check=True,
        env=env,
    )


# ---------------------------------------------------------------------------
# Pipeline principale
# ---------------------------------------------------------------------------

def main(ticker: str, skip_ingestion: bool, skip_dbt: bool) -> None:

    # ──────────────────────────────────────────────────────────
    # FASE 1 — Ingestion
    # ──────────────────────────────────────────────────────────
    if not skip_ingestion:
        run_ingestion()
    else:
        print("\n  [SKIP] Ingestion")

    # ──────────────────────────────────────────────────────────
    # FASE 2 — dbt
    # ──────────────────────────────────────────────────────────
    if not skip_dbt:
        run_dbt()
    else:
        print("\n  [SKIP] dbt")

    # ──────────────────────────────────────────────────────────
    # CARICAMENTO DATI
    # ──────────────────────────────────────────────────────────
    print(f"\n  Caricamento dati per {ticker}...")
    returns = load_returns(ticker)
    prices  = load_prices(ticker)
    S0 = float(prices.iloc[-1])
    try:
        periods_per_year = annualization_factor(ticker, "1d")
        configured_periods = seasonal_periods(ticker, "1d")
    except ConfigurationError:
        periods_per_year = 365 if ticker in ASSETS.get("crypto", []) else 252
        configured_periods = [7] if periods_per_year == 365 else [5]
    print(f"  Osservazioni rendimenti: {len(returns)}")
    print(f"  Prezzo corrente ({ticker}): {S0:.2f}")

    # ──────────────────────────────────────────────────────────
    # FASE 3 — Analisi statistica
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  FASE 3 — Analisi statistica")
    print("=" * 60)
    from analysis import (
        run_stationarity_tests, plot_acf_pacf,
        plot_rolling_statistics, decompose_series,
    )
    from analysis.stationarity import test_adf, test_kpss
    run_stationarity_tests(prices,   label=f"Prezzo — {ticker}")
    run_stationarity_tests(returns,  label=f"Rendimenti Log — {ticker}")
    adf_prices  = test_adf(prices)
    kpss_prices = test_kpss(prices)
    adf_returns = test_adf(returns)
    kpss_returns = test_kpss(returns)
    plot_acf_pacf(returns, lags=40,  title=f"Rendimenti Log — {ticker}")
    plot_rolling_statistics(returns, windows=[20, 60], title=f"Rendimenti Log — {ticker}")
    decompose_series(prices, period=configured_periods[0], title=f"Prezzo — {ticker}")

    # ──────────────────────────────────────────────────────────
    # FASE 4 — Modelli
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  FASE 4 — Modelli")
    print("=" * 60)

    from models.arima import fit_arima, plot_arima_forecast
    from models.sarima import fit_sarima, plot_sarima_forecast
    from models.garch import fit_garch, compare_volatility_models, plot_garch_volatility
    from models.var_model import build_returns_matrix, fit_var, granger_causality_matrix
    from models.prophet_model import fit_prophet, plot_prophet

    # ARIMA
    print("\n  --- ARIMA ---")
    arima_res = fit_arima(returns, order=None, steps_ahead=FORECAST_STEPS)
    plot_arima_forecast(returns, arima_res, ticker=ticker)

    # SARIMA
    print("\n  --- SARIMA ---")
    sarima_res = fit_sarima(returns, seasonal_order=(1, 0, 1, configured_periods[0]), steps_ahead=FORECAST_STEPS)
    plot_sarima_forecast(returns, sarima_res, ticker=ticker)

    # GARCH family
    print("\n  --- Confronto Modelli Volatilità ---")
    vol_comparison = compare_volatility_models(returns, steps_ahead=FORECAST_STEPS, periods_per_year=periods_per_year)
    garch_res = fit_garch(returns, steps_ahead=FORECAST_STEPS, periods_per_year=periods_per_year)
    plot_garch_volatility(returns, garch_res, ticker=ticker)

    # VAR (multi-asset: stocks + crypto)
    print("\n  --- VAR Multi-asset ---")
    try:
        var_symbols = ["AAPL", "BTC-USD", "^GSPC"]
        returns_wide = build_returns_matrix(var_symbols, db_path=DUCKDB_PATH)
        if not returns_wide.empty:
            var_res = fit_var(returns_wide, maxlags=5, steps_ahead=FORECAST_STEPS)
            granger_causality_matrix(returns_wide, maxlag=3)
        else:
            print("  [SKIP] Dati insufficienti per VAR")
    except Exception as e:
        print(f"  [SKIP] VAR: {e}")

    # Prophet (sui prezzi, non sui rendimenti)
    print("\n  --- Prophet ---")
    try:
        prophet_res = fit_prophet(prices, steps_ahead=FORECAST_STEPS)
        plot_prophet(prophet_res, ticker=ticker)
    except Exception as e:
        print(f"  [SKIP] Prophet: {e}")

    # ──────────────────────────────────────────────────────────
    # FASE 5 — Backtesting
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  FASE 5 — Backtesting walk-forward")
    print("=" * 60)
    from models.backtesting import (
        walk_forward_validation, compute_metrics, plot_backtest,
    )
    from models.validation import (
        naive_forecast_validation,
        diebold_mariano_hac,
        summarize_model_validation,
        var_backtest,
    )
    from models.arima import fit_arima as _arima_fn
    from models.sarima import fit_sarima as _sarima_fn

    def arima_model_fn(train: pd.Series, steps: int) -> np.ndarray:
        r = _arima_fn(train, order=arima_res["order"], steps_ahead=steps)
        return r["forecast"].values

    def sarima_model_fn(train: pd.Series, steps: int) -> np.ndarray:
        r = _sarima_fn(train, order=sarima_res["order"],
                       seasonal_order=sarima_res["seasonal_order"], steps_ahead=steps)
        return r["forecast"].values

    min_train = min(500, len(returns) // 2)
    bt_arima  = walk_forward_validation(arima_model_fn,  returns, train_window=min_train, test_window=20, step=20)
    bt_sarima = walk_forward_validation(sarima_model_fn, returns, train_window=min_train, test_window=20, step=20)

    print("\n  Metriche ARIMA:")
    metrics_arima  = compute_metrics(bt_arima)
    print("\n  Metriche SARIMA:")
    metrics_sarima = compute_metrics(bt_sarima)
    baseline_bt = naive_forecast_validation(returns, train_window=min_train, test_window=20, step=20)
    metrics_baselines = {}
    for baseline_name, baseline_df in baseline_bt.items():
        print(f"\n  Metriche Baseline — {baseline_name}:")
        metrics_baselines[baseline_name] = compute_metrics(baseline_df)

    validation_backtests = {
        "ARIMA": bt_arima,
        "SARIMA": bt_sarima,
        **baseline_bt,
    }
    direction_tests = summarize_model_validation(validation_backtests)

    if not bt_arima.empty and not bt_sarima.empty:
        dm_result = diebold_mariano_hac(bt_arima, bt_sarima, "ARIMA", "SARIMA", horizon=20)
        dm_vs_baseline = {
            name: diebold_mariano_hac(bt_arima, df, "ARIMA", name, horizon=20)
            for name, df in baseline_bt.items()
            if not df.empty
        }
        plot_backtest(bt_arima,  title=f"Backtest ARIMA — {ticker}")
        plot_backtest(bt_sarima, title=f"Backtest SARIMA — {ticker}")
    else:
        dm_result = {}
        dm_vs_baseline = {}

    # ──────────────────────────────────────────────────────────
    # FASE 5B — Strategia dopo costi e sensitivity analysis
    # Il forecast prodotto a t viene eseguito da t+1 dal motore di execution.
    # ──────────────────────────────────────────────────────────
    from strategy.execution import cost_sensitivity
    from strategy.transaction_costs import TransactionCostModel

    if not bt_arima.empty:
        bt_index = pd.DatetimeIndex(bt_arima["date"])
        realized_oos = pd.Series(bt_arima["actual"].to_numpy(), index=bt_index)
        forecast_positions = pd.Series(np.sign(bt_arima["forecast"].to_numpy()), index=bt_index)
        if ticker in ASSETS.get("crypto", []):
            transaction_cost_model = TransactionCostModel.from_config("binance_spot")
        else:
            transaction_cost_model = TransactionCostModel(
                taker_fee_bps=5, minimum_slippage_bps=2, default_spread_bps=5
            )
        cost_analysis = cost_sensitivity(
            realized_oos, forecast_positions, transaction_cost_model,
            periods_per_year=periods_per_year,
        )
        strategy_metrics = {
            name: result["metrics"] for name, result in cost_analysis.items()
            if isinstance(result, dict) and "metrics" in result
        }
        strategy_metrics["economically_useful"] = cost_analysis["economically_useful"]
    else:
        cost_analysis = {}
        strategy_metrics = {"economically_useful": False}

    # ──────────────────────────────────────────────────────────
    # FASE 6 — Monte Carlo
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  FASE 6 — Simulazioni Monte Carlo")
    print("=" * 60)
    from models.montecarlo import simulate_gbm, compute_var_cvar, plot_gbm
    from models.montecarlo_garch import compare_mc_vs_garch_mc, simulate_garch_mc

    mu    = float(returns.mean() * periods_per_year)
    sigma = float(returns.std() * np.sqrt(periods_per_year))
    print(f"  GBM params: mu={mu:.4f}  sigma={sigma:.4f}")
    paths = simulate_gbm(S0, mu, sigma, T=MC_HORIZON_DAYS, n_sims=MC_N_SIMULATIONS)
    var_stats = compute_var_cvar(paths, S0, confidence=MC_CONFIDENCE)
    var_backtest_hist = var_backtest(returns, returns.quantile(1 - MC_CONFIDENCE), confidence=MC_CONFIDENCE)
    print(f"\n  VaR {MC_CONFIDENCE*100:.0f}%  = {var_stats['VaR']*100:.2f}%")
    print(f"  CVaR {MC_CONFIDENCE*100:.0f}% = {var_stats['CVaR']*100:.2f}%")
    plot_gbm(paths, ticker=ticker, confidence=MC_CONFIDENCE)
    compare_mc_vs_garch_mc(returns, S0, T=MC_HORIZON_DAYS, n_sims=MC_N_SIMULATIONS,
                            confidence=MC_CONFIDENCE)
    # GARCH-MC VaR per il report
    try:
        garch_mc_paths = simulate_garch_mc(returns, S0, T=MC_HORIZON_DAYS,
                                           n_sims=MC_N_SIMULATIONS)
        garch_mc_stats = compute_var_cvar(garch_mc_paths, S0, confidence=MC_CONFIDENCE)
    except Exception:
        garch_mc_stats = {}

    # ──────────────────────────────────────────────────────────
    # RIEPILOGO
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  RIEPILOGO FINALE")
    print("=" * 60)
    try:
        risk = load_risk_metrics()
        row = risk[risk["symbol"] == ticker]
        if not row.empty:
            r = row.iloc[0]
            print(f"  Ticker              : {ticker}")
            print(f"  Rendimento atteso   : {r.get('expected_annual_return_pct', 'N/A')}%")
            print(f"  Volatilità annua    : {r.get('vol_annual_pct', 'N/A')}%")
            print(f"  Sharpe ratio        : {r.get('sharpe_ratio', 'N/A')}")
            print(f"  VaR storico 95% 1g  : {r.get('var_95_daily_pct', 'N/A')}%")
            print(f"  CVaR storico 95% 1g : {r.get('cvar_95_daily_pct', 'N/A')}%")
    except Exception:
        pass
    print(f"\n  ARIMA{arima_res['order']}  AIC={arima_res['aic']:.2f}")
    print(f"  SARIMA{sarima_res['order']}×{sarima_res['seasonal_order']}")
    print(f"  GARCH VaR MC ({MC_HORIZON_DAYS}g): {var_stats['VaR']*100:.2f}%")
    print("=" * 60 + "\n")

    # ──────────────────────────────────────────────────────────
    # REPORT NARRATIVO
    # ──────────────────────────────────────────────────────────
    import scipy.stats as _scipy_stats
    risk_row_dict = None
    try:
        risk = load_risk_metrics()
        row = risk[risk["symbol"] == ticker]
        if not row.empty:
            risk_row_dict = row.iloc[0].to_dict()
    except Exception:
        pass

    report_ctx = {
        # Metadati
        "ticker":          ticker,
        "start_date":      returns.index[0].strftime("%Y-%m-%d"),
        "end_date":        returns.index[-1].strftime("%Y-%m-%d"),
        "n_obs":           len(returns),
        "S0":              S0,
        "forecast_steps":  FORECAST_STEPS,
        "mc_horizon":      MC_HORIZON_DAYS,
        "mc_sims":         MC_N_SIMULATIONS,
        "mc_confidence":   MC_CONFIDENCE,
        "periods_per_year": periods_per_year,
        # Statistiche descrittive
        "mu_annual":           mu,
        "sigma_annual":        sigma,
        "mean_return_daily":   float(returns.mean()),
        "std_return_daily":    float(returns.std()),
        "skewness":            float(returns.skew()),
        "kurtosis":            float(returns.kurt()),
        # Stazionarietà
        "adf_prices":   adf_prices,
        "kpss_prices":  kpss_prices,
        "adf_returns":  adf_returns,
        "kpss_returns": kpss_returns,
        # Modelli
        "arima":            arima_res,
        "sarima":           sarima_res,
        "vol_comparison":   vol_comparison,
        "garch":            garch_res,
        # Backtesting
        "backtest_arima":  metrics_arima,
        "backtest_sarima": metrics_sarima,
        "backtest_baselines": metrics_baselines,
        "direction_tests": direction_tests,
        "dm_test":         dm_result,
        "dm_vs_baseline":  dm_vs_baseline,
        "strategy_after_costs": strategy_metrics,
        # Monte Carlo
        "mc_gbm":   var_stats,
        "mc_garch": garch_mc_stats,
        "var_backtest": var_backtest_hist,
        # Risk metrics
        "risk_metrics": risk_row_dict,
    }
    generate_report(report_ctx)

    # ──────────────────────────────────────────────────────────
    # REPORT BUSINESS
    # ──────────────────────────────────────────────────────────
    arima_fc_series = arima_res.get("forecast")
    sarima_fc_series = sarima_res.get("forecast")
    garch_fc_vol = garch_res.get("forecast_vol")

    report_ctx["arima_fc_mean"]         = float(arima_fc_series.mean()) if arima_fc_series is not None else None
    report_ctx["sarima_fc_mean"]        = float(sarima_fc_series.mean()) if sarima_fc_series is not None else None
    report_ctx["garch_forecast_vol_pct"] = float(garch_fc_vol.mean() * 100) if garch_fc_vol is not None else None

    # Promotion gate: una previsione resta tecnica se non batte baseline,
    # non è positiva dopo costi o presenta diagnostiche non valide.
    from reporting.business_report import promotion_decision
    baseline_mae = metrics_baselines.get("Zero Return", {}).get("MAE", float("inf"))
    base_net = strategy_metrics.get("base", {}).get("cumulative_net_return", -1.0)
    fold_pnl = (
        cost_analysis.get("base", {}).get("pnl", pd.DataFrame()).get("net_pnl", pd.Series(dtype=float))
    )
    stability_score = float((fold_pnl.groupby(bt_arima["window"].to_numpy()).sum() > 0).mean()) if len(fold_pnl) else 0.0
    residual_checks = arima_res.get("diagnostics", {}).get("ljung_box", {})
    residuals_valid = all(item.get("white_noise", False) for item in residual_checks.values()) if residual_checks else False
    report_ctx["promotion"] = promotion_decision(
        model_metric=metrics_arima.get("MAE", float("inf")), baseline_metric=baseline_mae,
        higher_is_better=False, net_return=base_net, stability_score=stability_score,
        calibration_score=1.0, residuals_valid=residuals_valid,
    )

    generate_business_report(report_ctx, paths_final=paths[-1])

    # Registro e artefatti locali della run.
    try:
        from experiments.artifacts import save_artifacts
        from experiments.metadata import dataset_hash, git_commit
        from experiments.registry import ExperimentRegistry
        from datetime import datetime as _datetime

        run_id = _datetime.utcnow().strftime("%Y%m%dT%H%M%S") + "_" + ticker.replace("-", "_").replace("^", "")
        artifact_path = save_artifacts(
            os.path.join("reports", "artifacts", run_id),
            configuration={"ticker": ticker, "periods_per_year": periods_per_year,
                           "forecast_steps": FORECAST_STEPS, "seed": 42},
            metrics={"arima": metrics_arima, "sarima": metrics_sarima,
                     "baselines": metrics_baselines, "strategy": strategy_metrics,
                     "promotion": report_ctx["promotion"]},
            predictions=bt_arima,
            residuals=pd.Series(arima_res.get("residuals", [])),
        )
        ExperimentRegistry().register({
            "run_id": run_id, "git_commit": git_commit(),
            "data_start": returns.index.min(), "data_end": returns.index.max(),
            "data_version": dataset_hash(returns.to_frame("log_return")),
            "asset": ticker, "frequency": "1d", "target": "future_log_return",
            "horizon": 1, "model_name": "ARIMA", "hyperparameters": {"order": arima_res["order"]},
            "feature_set": ["lagged_returns"], "cost_scenario": "base", "random_seed": 42,
            "primary_metric": "mae", "primary_metric_value": metrics_arima.get("MAE"),
            "baseline_metric_value": baseline_mae,
            "net_sharpe": strategy_metrics.get("base", {}).get("sharpe_ratio"),
            "max_drawdown": strategy_metrics.get("base", {}).get("maximum_drawdown"),
            "status": "promoted" if report_ctx["promotion"]["promoted"] else "rejected",
            "artifact_path": str(artifact_path),
        })
    except Exception as exc:
        print(f"  [WARN] Experiment tracking non riuscito: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Financial Time Series Analysis Platform")
    parser.add_argument("--skip-ingestion", action="store_true",
                        help="Salta il download dei dati (usa DuckDB già popolato)")
    parser.add_argument("--skip-dbt", action="store_true",
                        help="Salta le trasformazioni dbt (usa le mart già calcolate)")
    parser.add_argument("--ticker", default=PRIMARY_TICKER,
                        help=f"Ticker da analizzare (default: {PRIMARY_TICKER})")
    args = parser.parse_args()
    main(ticker=args.ticker, skip_ingestion=args.skip_ingestion, skip_dbt=args.skip_dbt)
