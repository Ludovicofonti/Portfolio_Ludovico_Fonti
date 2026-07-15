select *
from {{ ref('stg_basis_metrics') }}
where index_price <= 0 or futures_price <= 0
   or abs(basis_rate) > 1
   or available_time > ingested_at
