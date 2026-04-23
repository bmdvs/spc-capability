-- Periods in which a gauge was past its calibration due date or out of service for calibration. Grain: one row per
-- calibration event with such a period.

select
    calibration_id,
    gauge_id,
    due as overdue_from,
    removed_from_service as out_of_service_from,
    done as back_in_service,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_calibration__calibrations') }}
where done is not null and (done > due or removed_from_service is not null)
