{{
  config(
    materialized='table',
    tags=['intermediate', 'features']
  )
}}

-- Feature di lag sui rendimenti logaritmici (per modelli ML)
WITH base AS (
    SELECT
        symbol,
        asset_class,
        date,
        close,
        log_return,
        ma_20,
        ma_60,
        rolling_vol_20,
        rolling_vol_60
    FROM {{ ref('int_daily_returns') }}
)

SELECT
    symbol,
    asset_class,
    date,
    close,
    log_return,
    ma_20,
    ma_60,
    rolling_vol_20,
    rolling_vol_60,
    -- Lag 1–5 sui rendimenti
    LAG(log_return, 1) OVER (PARTITION BY symbol ORDER BY date) AS lag_1,
    LAG(log_return, 2) OVER (PARTITION BY symbol ORDER BY date) AS lag_2,
    LAG(log_return, 3) OVER (PARTITION BY symbol ORDER BY date) AS lag_3,
    LAG(log_return, 4) OVER (PARTITION BY symbol ORDER BY date) AS lag_4,
    LAG(log_return, 5) OVER (PARTITION BY symbol ORDER BY date) AS lag_5,
    -- Rendimento al quadrato (proxy varianza)
    POWER(log_return, 2) AS squared_return,
    -- Segno del rendimento (direction)
    CASE WHEN log_return > 0 THEN 1 ELSE 0 END AS direction_up
FROM base
