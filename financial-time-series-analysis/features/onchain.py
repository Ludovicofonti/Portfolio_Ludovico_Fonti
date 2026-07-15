"""Validazione dello schema normalizzato on-chain."""

REQUIRED_COLUMNS = {
    "network", "asset", "metric_name", "metric_value", "observation_time",
    "available_time", "source", "ingested_at", "quality_flag",
}


def validate_onchain_schema(columns) -> None:
    missing = REQUIRED_COLUMNS - set(columns)
    if missing:
        raise ValueError(f"Schema on-chain incompleto: {sorted(missing)}")
