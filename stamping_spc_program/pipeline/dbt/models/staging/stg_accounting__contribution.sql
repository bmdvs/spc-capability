-- Accounting export: contribution, typed. One row per export row.

select
    nullif(trim(part_id), '') as part_id,
    cast(nullif(trim(year), '') as bigint) as year,
    cast(nullif(trim(price), '') as double) as price,
    cast(nullif(trim(material_cost), '') as double) as material_cost,
    cast(nullif(trim(contribution_per_piece), '') as double) as contribution_per_piece,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'accounting__contribution') }}
