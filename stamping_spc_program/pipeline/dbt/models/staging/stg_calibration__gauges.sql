-- Calibration system export: gauges, typed. One row per export row.

select
    nullif(trim(gauge_id), '') as gauge_id,
    nullif(trim(type), '') as type,
    nullif(trim(range), '') as range,
    cast(nullif(trim(resolution), '') as double) as resolution,
    nullif(trim(location), '') as location,
    cast(nullif(trim(interval_months), '') as bigint) as interval_months,
    nullif(trim(status), '') as status,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'calibration__gauges') }}
