"""Configurazione compatibile con la CLI e loader YAML della piattaforma."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"


class ConfigurationError(ValueError):
    """Configurazione assente o semanticamente non valida."""


def load_yaml_config(name: str) -> dict[str, Any]:
    """Carica un file da ``config/`` e restituisce una copia mutabile."""
    path = CONFIG_DIR / name
    if not path.exists():
        raise ConfigurationError(f"File di configurazione non trovato: {path}")
    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, dict):
        raise ConfigurationError(f"La radice di {name} deve essere una mappa YAML")
    return deepcopy(data)


def get_asset_config(symbol: str) -> dict[str, Any]:
    """Restituisce e valida la configurazione specifica dell'asset."""
    assets = load_yaml_config("assets.yml").get("assets", {})
    if symbol not in assets:
        raise ConfigurationError(f"Asset non configurato: {symbol}")
    cfg = deepcopy(assets[symbol])
    required = {"asset_class", "trades_24_7", "annualization_days", "primary_frequency"}
    missing = sorted(required - cfg.keys())
    if missing:
        raise ConfigurationError(f"{symbol}: campi mancanti: {', '.join(missing)}")
    if cfg["asset_class"] == "crypto" and cfg["annualization_days"] != 365:
        raise ConfigurationError(f"{symbol}: le crypto devono annualizzare su 365 giorni")
    return cfg


def resolve_asset_config(symbol: str) -> tuple[str, dict[str, Any]]:
    """Resolve ticker canonici e simboli provider (es. BTC-USDT/BTCUSDT)."""
    assets = load_yaml_config("assets.yml").get("assets", {})
    normalized = symbol.upper().replace("_", "-")
    for asset_key, values in assets.items():
        aliases = {
            asset_key.upper(),
            str(values.get("data_symbol", "")).upper(),
            str(values.get("derivatives_symbol", "")).upper(),
        }
        aliases.discard("")
        if normalized in aliases or normalized.replace("-", "") in {
            alias.replace("-", "") for alias in aliases
        }:
            return asset_key, get_asset_config(asset_key)
    raise ConfigurationError(f"Asset o simbolo provider non configurato: {symbol}")


def annualization_factor(symbol: str, frequency: str | None = None) -> int:
    """Numero di periodi annui coerente con asset e frequenza."""
    cfg = get_asset_config(symbol)
    frequency = frequency or cfg["primary_frequency"]
    if frequency.endswith("h"):
        hours = int(frequency[:-1])
        return int(cfg.get("annualization_hours", cfg["annualization_days"] * 24) / hours)
    if frequency.endswith("d"):
        days = int(frequency[:-1])
        return int(cfg["annualization_days"] / days)
    raise ConfigurationError(f"Frequenza non supportata: {frequency}")


def seasonal_periods(symbol: str, frequency: str | None = None) -> list[int]:
    cfg = get_asset_config(symbol)
    frequency = frequency or cfg["primary_frequency"]
    return [int(value) for value in cfg.get("seasonal_periods", {}).get(frequency, [])]

# ---------------------------------------------------------------------------
# ASSETS DA INGERIRE
# ---------------------------------------------------------------------------

ASSETS = {
    "stocks":      ["AAPL", "MSFT", "TSLA"],
    "crypto":      ["BTC-USD", "ETH-USD"],
    "forex":       ["EURUSD=X", "GBPUSD=X"],
    "commodities": ["GC=F", "CL=F"],
    "indices":     ["^GSPC", "^DJI", "^VIX"],
    "bonds":       ["^TNX", "^TYX"],
}

# ---------------------------------------------------------------------------
# FRED — Serie macroeconomiche
# ---------------------------------------------------------------------------

FRED_SERIES = {
    "GDPC1":    "Real GDP (Quarterly)",
    "CPIAUCSL": "CPI All Items",
    "T10YIE":   "10Y Breakeven Inflation",
    "FEDFUNDS": "Federal Funds Rate",
    "DFF":      "Daily Federal Funds Rate",
    "DGS2":     "2Y Treasury Yield",
    "DGS5":     "5Y Treasury Yield",
    "DGS10":    "10Y Treasury Yield",
    "DGS30":    "30Y Treasury Yield",
    "T10Y2Y":   "10Y-2Y Yield Spread",
    "T10Y3M":   "10Y-3M Yield Spread",
    "UNRATE":   "Unemployment Rate",
    "VIXCLS":   "CBOE VIX (Daily)",
    "DCOILWTICO": "WTI Crude Oil Price",
}

# ---------------------------------------------------------------------------
# DATE
# ---------------------------------------------------------------------------

INGESTION_START_DATE = "2018-01-01"   # storico minimo richiesto
PRIMARY_TICKER      = "BTC-USD"       # ticker usato di default nelle analisi
FORECAST_STEPS      = 20              # giorni da prevedere
LAG_DAYS            = 5               # feature lag

# ---------------------------------------------------------------------------
# DuckDB
# ---------------------------------------------------------------------------

DUCKDB_PATH    = "data/finance.duckdb"
RAW_DATASET    = "raw_finance"
DBT_DATASET    = "analytics"

# ---------------------------------------------------------------------------
# MONTE CARLO
# ---------------------------------------------------------------------------

MC_N_SIMULATIONS = 1000
MC_HORIZON_DAYS  = 365    # default crypto; sovrascritto dalla config asset
MC_CONFIDENCE    = 0.95   # livello per VaR / CVaR
