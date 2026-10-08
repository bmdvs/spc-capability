-- ERP export: coils, typed. One row per export row.

select
    nullif(trim(coil_id), '') as coil_id,
    nullif(trim(supplier_id), '') as supplier_id,
    nullif(trim(coil_lot), '') as coil_lot,
    nullif(trim(grade), '') as grade,
    cast(nullif(trim(nominal_thickness_mm), '') as double) as nominal_thickness_mm,
    cast(nullif(trim(width_mm), '') as double) as width_mm,
    cast(nullif(trim(weight_kg), '') as bigint) as weight_kg,
    cast(nullif(trim(certificate_thickness_mm), '') as double) as certificate_thickness_mm,
    cast(nullif(trim(received_date), '') as date) as received_date,
    cast(nullif(trim(certificate_hardness_hrb), '') as double) as certificate_hardness_hrb,
    cast(nullif(trim(certificate_yield_mpa), '') as bigint) as certificate_yield_mpa,
    cast(nullif(trim(receiving_thickness_1_mm), '') as double) as receiving_thickness_1_mm,
    cast(nullif(trim(receiving_thickness_2_mm), '') as double) as receiving_thickness_2_mm,
    cast(nullif(trim(receiving_hardness_hrb), '') as double) as receiving_hardness_hrb,
    nullif(trim(status), '') as status,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'erp__coils') }}
