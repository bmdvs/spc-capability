-- QMS export: sorting events, typed. One row per export row.

select
    nullif(trim(sorting_event_id), '') as sorting_event_id,
    nullif(trim(ncr_id), '') as ncr_id,
    nullif(trim(run_id), '') as run_id,
    cast(nullif(trim(quantity_sorted), '') as bigint) as quantity_sorted,
    cast(nullif(trim(quantity_rejected), '') as bigint) as quantity_rejected,
    cast(nullif(trim(hours), '') as double) as hours,
    nullif(trim(sorted_at), '') as sorted_at,
    cast(nullif(trim(started), '') as timestamp) as started,
    cast(nullif(trim(ended), '') as timestamp) as ended,
    cast(nullif(trim(cost), '') as double) as cost,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'qms__sorting_events') }}
