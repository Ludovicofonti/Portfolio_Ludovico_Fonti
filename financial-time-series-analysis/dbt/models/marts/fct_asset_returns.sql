{{
  config(
    materialized='table',
    tags=['marts', 'returns']
  )
}}

-- Fact table principale: rendimenti giornalieri multi-asset
-- con tutte le feature calcolate, pronta per i modelli Python
SELECT
    symbol,
    asset_class,
    date,
    close,
    log_return,
    squared_return,
    direction_up,
    ma_20,
    ma_60,
    rolling_vol_20,
    rolling_vol_60,
    lag_1,
    lag_2,
    lag_3,
    lag_4,
    lag_5
FROM {{ ref('int_lagged_features') }}
WHERE lag_5 IS NOT NULL   -- rimuove le prime 5 righe per ogni asset
ORDER BY symbol, date
