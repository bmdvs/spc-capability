-- QMS export: nonconformances, typed. One row per export row.

select
    nullif(trim(ncr_id), '') as ncr_id,
    nullif(trim(run_id), '') as run_id,
    nullif(trim(characteristic_id), '') as characteristic_id,
    nullif(trim(defect_code), '') as defect_code,
    cast(nullif(trim(quantity_affected), '') as bigint) as quantity_affected,
    nullif(trim(detected_at), '') as detected_at,
    nullif(trim(cause_code), '') as cause_code,
    nullif(trim(cause_text), '') as cause_text,
    nullif(trim(disposition), '') as disposition,
    cast(nullif(trim(opened), '') as timestamp) as opened,
    cast(nullif(trim(closed), '') as timestamp) as closed,
    nullif(trim(corrective_action_id), '') as corrective_action_id,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'qms__nonconformances') }}
