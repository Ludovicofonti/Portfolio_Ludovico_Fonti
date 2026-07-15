{{
  config(
    materialized='view',
    tags=['staging', 'macro']
  )
}}

-- Stub: ritorna schema vuoto finché i dati FRED non vengono caricati.
-- Per abilitare: configurare la variabile d'ambiente FRED_API_KEY e
-- rieseguire pipelines/run_ingestion.py (senza --yahoo-only).
SELECT
    CAST(NULL AS VARCHAR) AS series_id,
    CAST(NULL AS VARCHAR) AS description,
    CAST(NULL AS DATE)    AS date,
    CAST(NULL AS DOUBLE)  AS value
WHERE 1=0
