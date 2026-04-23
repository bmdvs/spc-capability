-- Die maintenance log export: die events, typed. One row per export row.

select
    nullif(trim(die_event_id), '') as die_event_id,
    nullif(trim(die_id), '') as die_id,
    cast(nullif(trim(date), '') as date) as date,
    nullif(trim(type), '') as type,
    nullif(trim(stations_touched), '') as stations_touched,
    cast(nullif(trim(shot_count), '') as bigint) as shot_count,
    nullif(trim(toolmaker), '') as toolmaker,
    cast(nullif(trim(hours), '') as double) as hours,
    nullif(trim(notes), '') as notes,
    nullif(trim(fault_event_id), '') as fault_event_id,
    nullif(trim(cmm_characteristic_id), '') as cmm_characteristic_id,
    nullif(trim(cmm_subgroup_id), '') as cmm_subgroup_id,
    cast(nullif(trim(cmm_r1), '') as double) as cmm_r1,
    cast(nullif(trim(cmm_r2), '') as double) as cmm_r2,
    cast(nullif(trim(cmm_r3), '') as double) as cmm_r3,
    cast(nullif(trim(cmm_r4), '') as double) as cmm_r4,
    cast(nullif(trim(cmm_r5), '') as double) as cmm_r5,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'die_room__die_events') }}
