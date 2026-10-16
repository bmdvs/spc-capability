-- calibration system export: fixture verifications, typed. One row per export row.

select
    nullif(trim(verification_id), '') as verification_id,
    nullif(trim(gauge_id), '') as gauge_id,
    cast(nullif(trim("date"), '') as date) as "date",
    cast(nullif(trim("time"), '') as timestamp) as "time",
    cast(nullif(trim(master_deviation_mm), '') as double) as master_deviation_mm,
    cast(nullif(trim(tolerance_mm), '') as double) as tolerance_mm,
    nullif(trim("result"), '') as "result",
    nullif(trim(verified_by), '') as verified_by,
    nullif(trim(action), '') as action,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'calibration__fixture_verifications') }}
