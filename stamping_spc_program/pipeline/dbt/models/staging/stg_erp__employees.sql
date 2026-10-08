-- ERP export: employees, typed. One row per export row.

select
    nullif(trim(employee_id), '') as employee_id,
    nullif(trim(role), '') as role,
    cast(nullif(trim(shift), '') as bigint) as shift,
    cast(nullif(trim(hire_date), '') as date) as hire_date,
    nullif(trim(status), '') as status,
    cast(nullif(trim(burr_check_qualification_date), '') as date) as burr_check_qualification_date,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'erp__employees') }}
