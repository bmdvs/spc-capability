-- QMS export: scorecards, typed. One row per export row.

select
    nullif(trim(customer_id), '') as customer_id,
    nullif(trim(period), '') as period,
    cast(nullif(trim(ppm), '') as bigint) as ppm,
    cast(nullif(trim(on_time_pct), '') as double) as on_time_pct,
    nullif(trim(rating), '') as rating,
    cast(nullif(trim(received_date), '') as date) as received_date,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'qms__scorecards') }}
