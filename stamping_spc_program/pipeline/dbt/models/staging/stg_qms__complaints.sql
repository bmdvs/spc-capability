-- QMS export: complaints, typed. One row per export row.

select
    nullif(trim(complaint_id), '') as complaint_id,
    nullif(trim(customer_id), '') as customer_id,
    nullif(trim(part_id), '') as part_id,
    nullif(trim(run_ids), '') as run_ids,
    cast(nullif(trim(quantity), '') as bigint) as quantity,
    nullif(trim(quantity_basis), '') as quantity_basis,
    nullif(trim(defect_code), '') as defect_code,
    cast(nullif(trim(received), '') as date) as received,
    cast(nullif(trim(ppm_as_scored), '') as bigint) as ppm_as_scored,
    cast(nullif(trim(charge_back), '') as double) as charge_back,
    cast(nullif(trim(premium_freight), '') as double) as premium_freight,
    (containment_required = 'Y') as containment_required,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'qms__complaints') }}
