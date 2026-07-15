"""Modello configurabile di commissioni, spread, slippage e funding."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from config import load_yaml_config


@dataclass(frozen=True)
class TransactionCostModel:
    maker_fee_bps: float = 0.0
    taker_fee_bps: float = 0.0
    minimum_slippage_bps: float = 0.0
    default_spread_bps: float = 0.0
    include_funding: bool = False
    volatility_coefficient: float = 0.0
    size_coefficient: float = 0.0

    @classmethod
    def from_config(cls, venue: str = "binance_spot") -> "TransactionCostModel":
        config = load_yaml_config("costs.yml")
        values = config["venues"][venue]
        slippage = config.get("slippage", {})
        return cls(
            maker_fee_bps=float(values.get("maker_fee_bps", 0)),
            taker_fee_bps=float(values.get("taker_fee_bps", 0)),
            minimum_slippage_bps=float(values.get("minimum_slippage_bps", 0)),
            default_spread_bps=float(values.get("default_spread_bps", 0)),
            include_funding=bool(values.get("include_funding", False)),
            volatility_coefficient=float(slippage.get("volatility_coefficient", 0)),
            size_coefficient=float(slippage.get("size_coefficient", 0)),
        )

    def scenario(self, name: str) -> "TransactionCostModel":
        multipliers = load_yaml_config("costs.yml")["cost_scenarios"][name]
        return replace(
            self,
            maker_fee_bps=self.maker_fee_bps * multipliers["fee_multiplier"],
            taker_fee_bps=self.taker_fee_bps * multipliers["fee_multiplier"],
            default_spread_bps=self.default_spread_bps * multipliers["spread_multiplier"],
            minimum_slippage_bps=self.minimum_slippage_bps * multipliers["slippage_multiplier"],
        )

    def slippage_bps(self, volatility=0.0, position_size=0.0, regime_multiplier=1.0):
        return np.maximum(
            self.minimum_slippage_bps,
            (self.minimum_slippage_bps + self.volatility_coefficient * np.asarray(volatility) * 10_000
             + self.size_coefficient * np.abs(np.asarray(position_size))) * regime_multiplier,
        )
