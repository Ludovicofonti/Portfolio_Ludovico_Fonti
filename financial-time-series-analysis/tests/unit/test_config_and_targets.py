import numpy as np
import pandas as pd

from config import annualization_factor, resolve_asset_config, seasonal_periods
from features.calendar import annualized_volatility
from features.targets import build_targets


def test_crypto_calendar_uses_365_days():
    assert annualization_factor("BTC-USD", "1d") == 365
    assert annualization_factor("BTC-USD", "1h") == 8760
    assert 7 in seasonal_periods("BTC-USD", "1d")


def test_provider_symbol_resolves_to_canonical_asset():
    key, config = resolve_asset_config("BTCUSDT")
    assert key == "BTC-USDT"
    assert config["asset_class"] == "crypto"


def test_annualized_volatility_respects_asset_calendar():
    returns = pd.Series([0.01, -0.01, 0.02, -0.02])
    assert np.isclose(annualized_volatility(returns, "BTC-USD", "1d"), returns.std() * np.sqrt(365))


def test_targets_are_future_and_tail_rows_are_missing():
    frame = pd.DataFrame({"close": [100.0, 110.0, 121.0, 100.0]})
    result = build_targets(frame, horizons=[2], neutral_threshold=0.001)
    assert np.isclose(result.loc[0, "target_return_2"], np.log(121 / 100))
    assert result.loc[0, "target_direction_2"] == 1
    assert pd.isna(result.loc[2, "target_direction_2"])
