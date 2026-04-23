-- ERP export: parts, typed. One row per export row.

select
    nullif(trim(part_id), '') as part_id,
    nullif(trim(customer_id), '') as customer_id,
    nullif(trim(program), '') as program,
    nullif(trim(revision), '') as revision,
    nullif(trim(die_id), '') as die_id,
    nullif(trim(material_grade), '') as material_grade,
    cast(nullif(trim(thickness_mm), '') as double) as thickness_mm,
    nullif(trim(press_group), '') as press_group,
    nullif(trim(primary_press), '') as primary_press,
    cast(nullif(trim(parts_per_stroke), '') as bigint) as parts_per_stroke,
    cast(nullif(trim(annual_volume), '') as bigint) as annual_volume,
    cast(nullif(trim(standard_run_quantity), '') as bigint) as standard_run_quantity,
    cast(nullif(trim(ppap_date), '') as date) as ppap_date,
    nullif(trim(family_code), '') as family_code,
    nullif(trim(status), '') as status,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'erp__parts') }}
