-- SPC software export: alarms, typed. One row per export row.

select
    nullif(trim(alarm_id), '') as alarm_id,
    nullif(trim(subgroup_id), '') as subgroup_id,
    nullif(trim(chart), '') as chart,
    cast(nullif(trim("rule"), '') as bigint) as "rule",
    cast(nullif(trim(raised_at), '') as timestamp) as raised_at,
    cast(nullif(trim(acknowledged_at), '') as timestamp) as acknowledged_at,
    nullif(trim(acknowledged_by), '') as acknowledged_by,
    nullif(trim(disposition), '') as disposition,
    nullif(trim(cause_code), '') as cause_code,
    nullif(trim(action), '') as action,
    cast(nullif(trim(closed_at), '') as timestamp) as closed_at,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'spc__alarms') }}
