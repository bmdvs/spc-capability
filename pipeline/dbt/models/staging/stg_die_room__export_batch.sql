-- die maintenance log export: export batch, typed. One row per export row.

select
    nullif(trim(export_batch_id), '') as export_batch_id,
    nullif(trim(system), '') as system,
    cast(nullif(trim(exported_at), '') as timestamp) as exported_at,
    cast(nullif(trim(window_start), '') as date) as window_start,
    cast(nullif(trim(window_end), '') as date) as window_end,
    cast(nullif(trim(status_as_at), '') as date) as status_as_at
from {{ source('raw', 'die_room__export_batch') }}
