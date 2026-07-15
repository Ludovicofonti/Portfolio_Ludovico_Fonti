"""Feature spot causali per OHLCV e microstruttura aggregata."""

from __future__ import annotations

import numpy as np
import pandas as pd


def market_features(frame: pd.DataFrame, window: int = 24) -> pd.DataFrame:
    out = frame.sort_values("timestamp" if "timestamp" in frame else "open_time").copy()
    close = out["close"].astype(float)
    out["log_return"] = np.log(close).diff()
    out["simple_return"] = close.pct_change()
    out["high_low_range"] = (out["high"] - out["low"]) / close
    out["close_open_return"] = out["close"] / out["open"] - 1
    out[f"realized_volatility_{window}"] = np.sqrt(out["log_return"].shift(1).pow(2).rolling(window).sum())
    out[f"rolling_volatility_{window}"] = out["log_return"].shift(1).rolling(window).std()
    if "quote_volume" in out:
        qv = out["quote_volume"].replace(0, np.nan)
        out["quote_volume_change"] = qv.pct_change()
        out["amihud_illiquidity"] = out["simple_return"].abs() / qv
        out["volume_zscore"] = (qv - qv.shift(1).rolling(window).mean()) / qv.shift(1).rolling(window).std()
        if "taker_buy_quote_volume" in out:
            out["taker_buy_ratio"] = out["taker_buy_quote_volume"] / qv
    if "number_of_trades" in out:
        trades = out["number_of_trades"].replace(0, np.nan)
        out["trade_count_change"] = trades.pct_change()
        out["average_trade_size"] = out.get("base_volume", out.get("volume")) / trades
        out["trade_count_zscore"] = (trades - trades.shift(1).rolling(window).mean()) / trades.shift(1).rolling(window).std()
    if {"best_bid", "best_ask"}.issubset(out.columns):
        out["mid_price"] = (out["best_bid"] + out["best_ask"]) / 2
        out["spread"] = out["best_ask"] - out["best_bid"]
        out["spread_bps"] = out["spread"] / out["mid_price"] * 10_000
    if {"bid_depth_1pct", "ask_depth_1pct"}.issubset(out.columns):
        total = out["bid_depth_1pct"] + out["ask_depth_1pct"]
        out["order_book_imbalance"] = (out["bid_depth_1pct"] - out["ask_depth_1pct"]) / total.replace(0, np.nan)
    return out
