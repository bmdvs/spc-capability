-- calibration system export: gauge studies, typed. One row per export row.

select
    nullif(trim(study_id), '') as study_id,
    nullif(trim(gauge_id), '') as gauge_id,
    nullif(trim(characteristic_id), '') as characteristic_id,
    cast(nullif(trim("date"), '') as date) as "date",
    nullif(trim("trigger"), '') as "trigger",
    nullif(trim(method), '') as method,
    cast(nullif(trim(operators), '') as bigint) as operators,
    cast(nullif(trim(parts), '') as bigint) as parts,
    cast(nullif(trim(trials), '') as bigint) as trials,
    cast(nullif(trim(pct_grr_of_tolerance), '') as double) as pct_grr_of_tolerance,
    cast(nullif(trim(ndc), '') as bigint) as ndc,
    nullif(trim(worksheet_file), '') as worksheet_file,
    cast(nullif(trim(restudy_due), '') as date) as restudy_due,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'calibration__gauge_studies') }}
