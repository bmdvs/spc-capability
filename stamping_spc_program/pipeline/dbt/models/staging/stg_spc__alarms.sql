-- SPC software export: alarms, typed. One row per export row.

select
    nullif(trim(alarm_id), '') as alarm_id,
    nullif(trim(subgroup_id), '') as subgroup_id,
    nullif(trim(rule), '') as rule,
    cast(nullif(trim(raised_at), '') as timestamp) as raised_at,
    cast(nullif(trim(acknowledged_at), '') as timestamp) as acknowledged_at,
    nullif(trim(acknowledged_by), '') as acknowledged_by,
    nullif(trim(text), '') as text,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'spc__alarms') }}
