-- ERP export: scrap transactions, typed. One row per export row.

select
    nullif(trim(transaction_id), '') as transaction_id,
    nullif(trim(run_id), '') as run_id,
    cast(nullif(trim(quantity), '') as bigint) as quantity,
    nullif(trim(reason_code), '') as reason_code,
    cast(nullif(trim(date), '') as date) as date,
    cast(nullif(trim(cost), '') as double) as cost,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'erp__scrap_transactions') }}
