{{
  config(
    materialized='table',
    tags=['marts', 'risk']
  )
}}

-- Metriche di rischio per asset: Sharpe ratio, VaR storico, CVaR, max drawdown
WITH returns AS (
    SELECT
        symbol,
        asset_class,
        log_return,
        close,
        date
    FROM {{ ref('int_daily_returns') }}
),

stats AS (
    SELECT
        symbol,
        asset_class,
        MIN(date)                           AS first_date,
        MAX(date)                           AS last_date,
        COUNT(*)                            AS n_obs,
        AVG(log_return)                     AS mean_daily_return,
        STDDEV(log_return)                  AS std_daily_return,
        -- Sharpe annualizzato (risk-free rate ≈ 0 per semplicità)
        CASE
            WHEN STDDEV(log_return) > 0
            THEN (AVG(log_return) * 252) / (STDDEV(log_return) * SQRT(252))
            ELSE NULL
        END                                 AS sharpe_ratio_annual,
        -- VaR storico al 95% (percentile 5° dei rendimenti giornalieri)
        PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY log_return) AS var_95_daily,
        -- Volatilità annualizzata
        STDDEV(log_return) * SQRT(252)      AS vol_annual
    FROM returns
    GROUP BY symbol, asset_class
),

-- CVaR calcolato in CTE separata per evitare aggregato annidato
cvar AS (
    SELECT
        r.symbol,
        AVG(r.log_return) AS cvar_95_daily
    FROM returns r
    INNER JOIN stats s ON r.symbol = s.symbol
    WHERE r.log_return <= s.var_95_daily
    GROUP BY r.symbol
)

SELECT
    s.symbol,
    s.asset_class,
    s.first_date,
    s.last_date,
    s.n_obs,
    ROUND(s.mean_daily_return * 252 * 100, 2)  AS expected_annual_return_pct,
    ROUND(s.vol_annual * 100, 2)               AS vol_annual_pct,
    ROUND(s.sharpe_ratio_annual, 3)            AS sharpe_ratio,
    ROUND(s.var_95_daily * 100, 3)             AS var_95_daily_pct,
    ROUND(c.cvar_95_daily * 100, 3)            AS cvar_95_daily_pct
FROM stats s
LEFT JOIN cvar c ON s.symbol = c.symbol
ORDER BY s.sharpe_ratio_annual DESC NULLS LAST
