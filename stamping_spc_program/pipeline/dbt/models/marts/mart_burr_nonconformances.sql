-- Burr nonconformances with the die's position in its sharpening interval. Grain: one row per nonconformance with a
-- burr defect code. Shots since sharpening are at the end of the nonconformance's run; the die's sharpening interval is
-- the die room's practice as the die master records it.

select
    n.ncr_id, n.defect_code, n.detected_at, n.opened, year(n.opened) as opened_year, n.quantity_affected, n.disposition,
    n.run_id, r.part_id, r.die_id, r.press_id, r.sharpening_interval_no, r.sharpening_date,
    r.shots_since_sharpening_at_start + r.strokes as shots_since_sharpening_at_run_end,
    d.sharpening_interval_shots as sharpening_interval_practice,
    (r.shots_since_sharpening_at_start + r.strokes) <= d.sharpening_interval_shots as within_the_sharpening_interval,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_qms__nonconformances') }} n
left join {{ ref('int_run_shots') }} r on r.run_id = n.run_id
left join {{ ref('stg_erp__dies') }} d on d.die_id = r.die_id
where n.defect_code in ('burr', 'hole burr and size')
