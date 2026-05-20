-- Daily master-part verifications of the check fixtures, with the deviation as a share of the verification
-- tolerance. Grain: one row per verification.

select
    v.verification_id, v.gauge_id, v."date" as verification_date, v."time" as verified_at, v.master_deviation_mm, v.tolerance_mm,
    abs(v.master_deviation_mm) / v.tolerance_mm as share_of_tolerance,
    v.result, v.verified_by, v.action,
    v."date" >= cast('{{ var("quarter_start") }}' as date) as in_quarter,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_calibration__fixture_verifications') }} v
