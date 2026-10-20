-- die maintenance log export: die events, typed. One row per export row.

select
    nullif(trim(die_event_id), '') as die_event_id,
    nullif(trim(die_id), '') as die_id,
    cast(nullif(trim("date"), '') as date) as "date",
    nullif(trim("type"), '') as "type",
    nullif(trim(stations_touched), '') as stations_touched,
    cast(nullif(trim(shot_count), '') as bigint) as shot_count,
    cast(nullif(trim(corrected_shot_count), '') as bigint) as corrected_shot_count,
    cast(nullif(trim(corrected_at), '') as date) as corrected_at,
    nullif(trim(corrected_by), '') as corrected_by,
    nullif(trim(toolmaker), '') as toolmaker,
    cast(nullif(trim(hours), '') as double) as hours,
    nullif(trim(notes), '') as notes,
    nullif(trim(fault_event_id), '') as fault_event_id,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'die_room__die_events') }}
