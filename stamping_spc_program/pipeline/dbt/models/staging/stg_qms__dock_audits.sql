-- QMS export: dock audits, typed. One row per export row.

select
    nullif(trim(dock_audit_id), '') as dock_audit_id,
    nullif(trim(shipment_id), '') as shipment_id,
    cast(nullif(trim(audit_date), '') as date) as audit_date,
    cast(nullif(trim(lot_size), '') as bigint) as lot_size,
    nullif(trim(plan_code_letter), '') as plan_code_letter,
    cast(nullif(trim(sample_size), '') as bigint) as sample_size,
    cast(nullif(trim(defects_found), '') as bigint) as defects_found,
    nullif(trim(defect_codes), '') as defect_codes,
    nullif(trim(result), '') as result,
    nullif(trim(auditor), '') as auditor,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'qms__dock_audits') }}
