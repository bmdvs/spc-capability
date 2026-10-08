-- ERP export: shipments, typed. One row per export row.

select
    nullif(trim(shipment_id), '') as shipment_id,
    nullif(trim(run_id), '') as run_id,
    nullif(trim(customer_id), '') as customer_id,
    cast(nullif(trim(quantity), '') as bigint) as quantity,
    cast(nullif(trim(ship_date), '') as date) as ship_date,
    nullif(trim(dock_audit_id), '') as dock_audit_id,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'erp__shipments') }}
