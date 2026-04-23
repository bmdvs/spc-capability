-- QMS export: ppap studies, typed. One row per export row.

select
    nullif(trim(study_id), '') as study_id,
    nullif(trim(characteristic_id), '') as characteristic_id,
    nullif(trim(part_id), '') as part_id,
    cast(nullif(trim(date), '') as date) as date,
    nullif(trim(trigger), '') as trigger,
    cast(nullif(trim(pieces), '') as bigint) as pieces,
    cast(nullif(trim(mean), '') as double) as mean,
    cast(nullif(trim(sigma), '') as double) as sigma,
    cast(nullif(trim(pp), '') as double) as pp,
    cast(nullif(trim(ppk), '') as double) as ppk,
    nullif(trim(measured_on), '') as measured_on,
    nullif(trim(filed_to), '') as filed_to,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'qms__ppap_studies') }}
