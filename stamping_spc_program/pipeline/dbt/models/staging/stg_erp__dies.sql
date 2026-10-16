-- ERP export: dies, typed. One row per export row.

select
    nullif(trim(die_id), '') as die_id,
    nullif(trim(part_ids), '') as part_ids,
    cast(nullif(trim(stations), '') as bigint) as stations,
    cast(nullif(trim(parts_per_stroke), '') as bigint) as parts_per_stroke,
    cast(nullif(trim(build_date), '') as date) as build_date,
    cast(nullif(trim(last_rebuild_date), '') as date) as last_rebuild_date,
    cast(nullif(trim(shot_count), '') as bigint) as shot_count,
    cast(nullif(trim(sharpening_due_count), '') as bigint) as sharpening_due_count,
    nullif(trim("status"), '') as "status",
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'erp__dies') }}
