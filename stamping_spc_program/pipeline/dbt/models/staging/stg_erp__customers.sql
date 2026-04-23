-- ERP export: customers, typed. One row per export row.

select
    nullif(trim(customer_id), '') as customer_id,
    nullif(trim(customer_name), '') as customer_name,
    nullif(trim(program), '') as program,
    cast(nullif(trim(ppap_level), '') as bigint) as ppap_level,
    nullif(trim(scorecard_frequency), '') as scorecard_frequency,
    cast(nullif(trim(ppm_target), '') as double) as ppm_target,
    nullif(trim(status), '') as status,
    cast(nullif(trim(created_at), '') as date) as created_at,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'erp__customers') }}
