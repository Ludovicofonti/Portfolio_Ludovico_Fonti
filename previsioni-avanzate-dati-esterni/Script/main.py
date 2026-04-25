"""
Previsioni Avanzate con Integrazione di Dati Esterni
=====================================================
Pipeline di forecasting multi-variato per dati di vendita, arricchita con
covariate meteo e macroeconomiche. Utilizza un TSMixer custom con attivazione
Mish e regressione quantilica per generare previsioni probabilistiche.

Pipeline:
    1. Data Integration  — merge vendite, meteo, indicatori economici
    2. TimeSeries         — creazione serie target e covariate con Darts
    3. Model Training     — TSMixer custom con quantile regression
    4. Forecasting        — previsioni probabilistiche multi-step
    5. Hyperparameter Opt — tuning multi-obiettivo con Optuna (opzionale)
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from datetime import date
from pathlib import Path

from darts import TimeSeries
from darts.dataprocessing.transformers import Scaler, StaticCovariatesTransformer
from darts.metrics import rmse, mae
from darts.models.forecasting.tsmixer_model import TSMixerModel, _TSMixerModule
from darts.utils.likelihood_models import QuantileRegression
from pytorch_lightning.callbacks import EarlyStopping
from sklearn.model_selection import train_test_split

try:
    import optuna
    from optuna.samplers import NSGAIIISampler

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False


# =============================================================================
# 1. CUSTOM TSMIXER — Mish Activation
# =============================================================================


class _CustomTSMixerModule(_TSMixerModule):
    """Modulo TSMixer con attivazione Mish per un gradient flow più regolare."""

    def __init__(self, activation="Mish", **kwargs):
        super().__init__(activation="ReLU", **kwargs)

        if activation == "Mish":
            self.activation_fn = nn.Mish()
            if hasattr(self, "model"):
                for block in self.model:
                    block.ff.activation = self.activation_fn


class CustomTSMixerModel(TSMixerModel):
    """Variante TSMixer con attivazione Mish e parametri esposti."""

    def __init__(
        self,
        *,
        output_chunk_shift=0,
        use_reversible_instance_norm=False,
        hidden_size=128,
        ff_size=256,
        num_blocks=3,
        dropout=0.1,
        normalize_before=False,
        use_static_covariates=False,
        **kwargs,
    ):
        self.use_reversible_instance_norm = use_reversible_instance_norm
        self.hidden_size = hidden_size
        self.ff_size = ff_size
        self.num_blocks = num_blocks
        self.dropout = dropout
        self.normalize_before = normalize_before
        self.use_static_covariates = use_static_covariates
        super().__init__(output_chunk_shift=output_chunk_shift, **kwargs)

    def _create_model(self, train_sample):
        x, y, static_cov, future_cov, past_cov, _ = train_sample
        return _CustomTSMixerModule(
            input_dim=y.shape[1],
            output_dim=y.shape[1],
            past_cov_dim=past_cov.shape[1] if past_cov is not None else 0,
            future_cov_dim=future_cov.shape[1] if future_cov is not None else 0,
            static_cov_dim=static_cov.shape[1] if static_cov is not None else 0,
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            nr_params=self.likelihood.num_parameters if self.likelihood else 1,
            hidden_size=self.hidden_size,
            ff_size=self.ff_size,
            num_blocks=self.num_blocks,
            dropout=self.dropout,
            activation="Mish",
            norm_type=self.norm_type,
            use_reversible_instance_norm=self.use_reversible_instance_norm,
            normalize_before=self.normalize_before,
        )


# =============================================================================
# 2. DATA LOADING & INTEGRATION
# =============================================================================


def load_and_merge_data(
    data_dir: Path,
    date_range: tuple[str, str] = ("2023-01-01", "2023-09-27"),
) -> pd.DataFrame:
    """Carica e unisce i dataset vendite, meteo e indicatori economici."""
    sales = pd.read_csv(data_dir / "syeewdataset.csv")
    weather = pd.read_csv(data_dir / "weather.csv")
    economy = pd.read_csv(data_dir / "economia.csv")

    economy["data"] = pd.to_datetime(economy["data"], errors="coerce")

    merged = pd.merge(
        sales, weather,
        left_on=["Date", "Cap"], right_on=["date", "zip"],
        how="inner",
    )
    merged["Date"] = pd.to_datetime(merged["Date"])

    merged["year"] = merged["Date"].dt.year
    merged["month"] = merged["Date"].dt.month
    economy["year"] = economy["data"].dt.year
    economy["month"] = economy["data"].dt.month

    df = pd.merge(merged, economy, on=["year", "month"], how="left")

    df = df[[
        "Date", "idMatrice", "idCat", "Netto", "Qta", "Dim", "Lav", "Cap",
        "TipoAttivita", "TipoCalc", "temp", "humidity", "precipitation",
        "Prezzi", "fiducia",
    ]]
    df = df[df["Date"].between(*date_range)]

    return df


# =============================================================================
# 3. TIME SERIES CREATION & PREPROCESSING
# =============================================================================

TARGET_COLS = ["Netto", "Qta", "Dim", "Lav"]
COVARIATE_COLS = ["temp", "precipitation", "fiducia"]


def create_time_series(
    df: pd.DataFrame,
) -> tuple[list[TimeSeries], list[TimeSeries]]:
    """Crea serie target e covariate passate dal DataFrame unificato."""
    target_series = TimeSeries.from_group_dataframe(
        df,
        time_col="Date",
        group_cols=["idMatrice", "idCat"],
        static_cols=["TipoAttivita", "Cap", "TipoCalc"],
        value_cols=TARGET_COLS,
        drop_group_cols=["idCat"],
        fill_missing_dates=True,
        freq="D",
    )

    past_covariates = TimeSeries.from_group_dataframe(
        df,
        time_col="Date",
        group_cols=["idMatrice", "idCat"],
        static_cols=["Cap"],
        value_cols=COVARIATE_COLS,
        drop_group_cols=["idCat", "idMatrice"],
        fill_missing_dates=False,
        freq="D",
    )

    for i in range(len(past_covariates)):
        past_covariates[i] = past_covariates[i].add_holidays("IT")

    return target_series, past_covariates


def scale_series(
    target_series: list[TimeSeries],
    past_covariates: list[TimeSeries],
) -> tuple[list[TimeSeries], list[TimeSeries], Scaler]:
    """Scala serie target, covariate e covariate statiche. Ritorna lo scaler target."""
    target_scaler = Scaler()
    target_series = target_scaler.fit_transform(target_series)

    cov_scaler = Scaler()
    past_covariates = cov_scaler.fit_transform(past_covariates)

    static_scaler = StaticCovariatesTransformer()
    target_series = static_scaler.fit_transform(target_series)

    return target_series, past_covariates, target_scaler


# =============================================================================
# 4. MODEL CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    "input_chunk_length": 64,
    "output_chunk_length": 32,
    "output_chunk_shift": 0,
    "batch_size": 1024,
    "hidden_size": 32,
    "ff_size": 16,
    "num_blocks": 4,
    "dropout": 0.075,
    "use_reversible_instance_norm": True,
    "normalize_before": True,
    "use_static_covariates": True,
    "optimizer_cls": torch.optim.RMSprop,
    "optimizer_kwargs": {"lr": 2e-4},
    "lr_scheduler_cls": torch.optim.lr_scheduler.ExponentialLR,
    "lr_scheduler_kwargs": {"gamma": 0.999},
    "likelihood": QuantileRegression(),
    "save_checkpoints": True,
    "force_reset": True,
    "random_state": 42,
    "add_encoders": {
        "cyclic": {
            "future": ["month", "quarter", "dayofweek", "dayofyear", "weekofyear"],
            "past": ["month", "quarter", "dayofweek", "dayofyear", "weekofyear"],
        },
        "datetime_attribute": {
            "future": ["month", "quarter", "dayofweek", "dayofyear", "weekofyear"],
            "past": ["month", "quarter", "dayofweek", "dayofyear", "weekofyear"],
        },
        "position": {"past": ["relative"], "future": ["relative"]},
        "transformer": Scaler(),
    },
}


def _get_trainer_kwargs(max_epochs: int = 300) -> dict:
    """Restituisce i kwargs per PyTorch Lightning trainer."""
    return {
        "gradient_clip_val": 1,
        "max_epochs": max_epochs,
        "accelerator": "cuda",
        "callbacks": [
            EarlyStopping(
                monitor="train_loss", patience=20, min_delta=1e-5, mode="min"
            )
        ],
    }


def build_model(**overrides) -> CustomTSMixerModel:
    """Costruisce un CustomTSMixerModel con configurazione di default + override."""
    config = {**DEFAULT_CONFIG, "pl_trainer_kwargs": _get_trainer_kwargs()}
    config.update(overrides)
    return CustomTSMixerModel(**config)


# =============================================================================
# 5. TRAINING & PREDICTION
# =============================================================================


def train_model(
    model: CustomTSMixerModel,
    target_series: list[TimeSeries],
    past_covariates: list[TimeSeries],
    test_size: float = 0.4,
) -> CustomTSMixerModel:
    """Addestra il modello su un train/test split."""
    torch.cuda.empty_cache()
    torch.set_float32_matmul_precision("high")

    train_target, _ = train_test_split(target_series, test_size=test_size)
    train_cov, _ = train_test_split(past_covariates, test_size=test_size)

    model.fit(series=train_target, past_covariates=train_cov)
    return model


def predict(
    model: CustomTSMixerModel,
    df: pd.DataFrame,
    n: int = 64,
    num_samples: int = 150,
) -> pd.DataFrame:
    """Genera previsioni probabilistiche aggregate per mese, per ogni gruppo."""
    results = []

    for (id_matrice, id_cat), group in df.groupby(["idMatrice", "idCat"]):
        target, covariates = create_time_series(group)
        target, covariates, scaler = scale_series(target, covariates)

        pred_scaled = model.predict(
            series=target[0],
            past_covariates=covariates[0],
            n=n,
            num_samples=num_samples,
            mc_dropout=True,
        )

        forecast_df = scaler.inverse_transform(pred_scaled).quantile_df()
        forecast_df = forecast_df.resample("ME").sum()
        forecast_df["idMatrice"] = id_matrice
        forecast_df["idCat"] = id_cat
        results.append(forecast_df)

    return pd.concat(results).reset_index()


# =============================================================================
# 6. HYPERPARAMETER OPTIMIZATION (Optuna)
# =============================================================================

SEARCH_SPACE = {
    "hidden_size": [8, 16, 32, 64, 128, 256],
    "batch_size": [32, 64, 128, 256, 512, 1024],
    "num_blocks": [2, 4, 8, 16, 32],
    "dropout": [0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35],
    "ff_size": [2, 4, 8, 16, 32],
}


def optimize_hyperparameters(
    target_series: list[TimeSeries],
    past_covariates: list[TimeSeries],
    n_trials: int = 100,
) -> "optuna.Study":
    """Ricerca multi-obiettivo degli iperparametri con Optuna (NSGA-III)."""
    if not OPTUNA_AVAILABLE:
        raise ImportError(
            "Optuna è necessario per l'ottimizzazione degli iperparametri."
        )

    train_target, _ = train_test_split(target_series, test_size=0.4)
    train_cov, _ = train_test_split(past_covariates, test_size=0.4)

    def objective(trial: "optuna.Trial") -> tuple[float, float]:
        torch.cuda.empty_cache()

        config = {
            param: trial.suggest_categorical(param, values)
            for param, values in SEARCH_SPACE.items()
        }

        model = build_model(**config)
        model.fit(series=train_target, past_covariates=train_cov)

        rmse_scores, mae_scores = [], []
        for ts, cov in zip(target_series, past_covariates):
            preds = model.predict(
                series=ts, past_covariates=cov,
                n=64, num_samples=150, mc_dropout=True,
            )
            rmse_scores.append(rmse(preds, ts))
            mae_scores.append(mae(preds, ts))

        return float(np.mean(rmse_scores)), float(np.mean(mae_scores))

    study = optuna.create_study(
        storage="sqlite:///optuna_study.db",
        study_name=f"TSMixer_{date.today():%Y%m%d}",
        sampler=NSGAIIISampler(),
        load_if_exists=True,
        directions=["minimize", "minimize"],
    )
    study.optimize(objective, n_trials=n_trials, n_jobs=1, show_progress_bar=True)

    return study


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    DATA_DIR = Path(__file__).parent

    # 1. Caricamento e merge dati
    print("Caricamento e merge dati...")
    df = load_and_merge_data(DATA_DIR)
    print(f"  Dataset: {df.shape[0]} righe, {df.shape[1]} colonne")

    # 2. Creazione TimeSeries
    print("Creazione TimeSeries...")
    target_series, past_covariates = create_time_series(df)
    target_series, past_covariates, target_scaler = scale_series(
        target_series, past_covariates
    )
    print(f"  {len(target_series)} serie target, {len(past_covariates)} covariate")

    # 3. Training
    print("Training modello...")
    model = build_model()
    model = train_model(model, target_series, past_covariates)
    print("  Training completato.")

    # 4. Previsioni (decommentare per generare)
    # predictions = predict(model, df)
    # print(predictions)

    # 5. Ottimizzazione iperparametri (decommentare per eseguire)
    # study = optimize_hyperparameters(target_series, past_covariates, n_trials=50)
    # print(study.best_trials)
