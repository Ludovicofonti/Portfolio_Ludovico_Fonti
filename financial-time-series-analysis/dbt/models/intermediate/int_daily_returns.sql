{{
  config(
    materialized='table',
    tags=['intermediate', 'returns']
  )
}}

-- Calcolo dei rendimenti logaritmici e delle statistiche rolling
-- per ogni asset usando DuckDB window functions
WITH base AS (
    SELECT
        symbol,
        asset_class,
        date,
        close,
        LAG(close) OVER (PARTITION BY symbol ORDER BY date) AS prev_close
    FROM {{ ref('stg_prices') }}
),

returns AS (
    SELECT
        symbol,
        asset_class,
        date,
        close,
        prev_close,
        -- Rendimento logaritmico: ln(p_t / p_{t-1})
        CASE
            WHEN prev_close > 0 AND close > 0
            THEN LN(close / prev_close)
            ELSE NULL
        END AS log_return
    FROM base
    WHERE prev_close IS NOT NULL
),

with_rolling AS (
    SELECT
        symbol,
        asset_class,
        date,
        close,
        log_return,
        -- Medie mobili sul prezzo
        AVG(close) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS ma_20,
        AVG(close) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS ma_60,
        -- Volatilità rolling (std rendimenti × √252 → annualizzata)
        STDDEV(log_return) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) * SQRT(252) AS rolling_vol_20,
        STDDEV(log_return) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) * SQRT(252) AS rolling_vol_60,
        -- Rendimento cumulativo rispetto al primo giorno
        EXP(SUM(log_return) OVER (
            PARTITION BY symbol
            ORDER BY date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )) - 1 AS cumulative_return
    FROM returns
)

SELECT * FROM with_rolling
WHERE log_return IS NOT NULL
