-- press monitor export: fault events, typed. One row per export row.

select
    nullif(trim(fault_event_id), '') as fault_event_id,
    nullif(trim(press_id), '') as press_id,
    nullif(trim(run_id), '') as run_id,
    cast(nullif(trim("timestamp"), '') as timestamp) as "timestamp",
    nullif(trim(input), '') as input,
    cast(nullif(trim(stroke_no), '') as bigint) as stroke_no,
    cast(nullif(trim(cleared_at), '') as timestamp) as cleared_at,
    nullif(trim(cleared_by), '') as cleared_by,
    nullif(trim(finding), '') as finding,
    nullif(trim(die_event_id), '') as die_event_id,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'press_monitor__fault_events') }}
