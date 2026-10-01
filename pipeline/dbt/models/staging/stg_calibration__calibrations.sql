-- calibration system export: calibrations, typed. One row per export row.

select
    nullif(trim(calibration_id), '') as calibration_id,
    nullif(trim(gauge_id), '') as gauge_id,
    cast(nullif(trim(due), '') as date) as due,
    cast(nullif(trim(done), '') as date) as done,
    cast(nullif(trim(removed_from_service), '') as date) as removed_from_service,
    nullif(trim("result"), '') as "result",
    cast(nullif(trim(as_found), '') as double) as as_found,
    cast(nullif(trim(as_left), '') as double) as as_left,
    nullif(trim(performed_by), '') as performed_by,
    nullif(trim(certificate), '') as certificate,
    nullif(trim(event_type), '') as event_type,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'calibration__calibrations') }}
