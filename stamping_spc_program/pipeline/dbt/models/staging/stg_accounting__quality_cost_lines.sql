-- Accounting export: quality cost lines, typed. One row per export row.

select
    nullif(trim(line_id), '') as line_id,
    nullif(trim(period), '') as period,
    nullif(trim(category), '') as category,
    nullif(trim(source_record), '') as source_record,
    cast(nullif(trim(amount), '') as double) as amount,
    cast(nullif(trim(hours), '') as double) as hours,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'accounting__quality_cost_lines') }}
