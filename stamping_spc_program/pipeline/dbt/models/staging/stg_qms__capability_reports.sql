-- QMS export: capability reports, typed. One row per export row.

select
    nullif(trim(report_id), '') as report_id,
    nullif(trim(characteristic_id), '') as characteristic_id,
    cast(nullif(trim(run_date), '') as date) as run_date,
    nullif(trim(source), '') as source,
    cast(nullif(trim(pp), '') as double) as pp,
    cast(nullif(trim(ppk), '') as double) as ppk,
    cast(nullif(trim(cp), '') as double) as cp,
    cast(nullif(trim(cpk), '') as double) as cpk,
    nullif(trim(issued_to), '') as issued_to,
    cast(nullif(trim(issued_date), '') as date) as issued_date,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'qms__capability_reports') }}
