"""Join point-in-time per dati macro e vintage."""

import pandas as pd


def macro_asof(market: pd.DataFrame, macro: pd.DataFrame, origin_column: str = "timestamp") -> pd.DataFrame:
    required = {"series_id", "value", "available_time"}
    if missing := required - set(macro.columns):
        raise ValueError(f"Campi macro mancanti: {sorted(missing)}")
    left = market.copy()
    left[origin_column] = pd.to_datetime(left[origin_column], utc=True)
    right = macro.copy()
    right["available_time"] = pd.to_datetime(right["available_time"], utc=True)
    wide = []
    for series_id, group in right.groupby("series_id"):
        joined = pd.merge_asof(
            left[[origin_column]].sort_values(origin_column),
            group[["available_time", "value"]].sort_values("available_time"),
            left_on=origin_column, right_on="available_time", direction="backward",
        )["value"].rename(str(series_id))
        wide.append(joined)
    return pd.concat([left.reset_index(drop=True), *wide], axis=1)
