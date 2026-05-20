-- SPC software export: limit verifications, typed. One row per export row.

select
    nullif(trim(verification_id), '') as verification_id,
    nullif(trim(characteristic_id), '') as characteristic_id,
    nullif(trim(chart), '') as chart,
    nullif(trim(die_id), '') as die_id,
    nullif(trim(die_event), '') as die_event,
    cast(nullif(trim(event_date), '') as date) as event_date,
    cast(nullif(trim(verified_at), '') as timestamp) as verified_at,
    cast(nullif(trim(subgroups), '') as bigint) as subgroups,
    cast(nullif(trim(coil_changes), '') as bigint) as coil_changes,
    cast(nullif(trim(mean_offset_sigma), '') as double) as mean_offset_sigma,
    nullif(trim("result"), '') as "result",
    nullif(trim(limit_set_id), '') as limit_set_id,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'spc__limit_verifications') }}
