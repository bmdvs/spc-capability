-- Quality cost lines as booked, with the press each can be traced to. Grain: one row per cost line. A line names a
-- press, or a run (traced to the run's press), or neither (plant level: inspection labor, calibration, gauge and
-- fixture repair).

select
    l.line_id, l.period, cast(l.period || '-01' as date) as month_start, l.category, l.source_record, l.amount, l.hours,
    coalesce(nullif(regexp_extract(l.source_record, 'PR-[0-9]{2}'), ''), r.press_id) as press_id,
    x.is_pilot_press,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_accounting__quality_cost_lines') }} l
left join {{ ref('int_run_shots') }} r on r.run_id = nullif(regexp_extract(l.source_record, 'R[0-9]{2}-[0-9]{5}'), '')
left join {{ ref('int_press_redesign') }} x on x.press_id = coalesce(nullif(regexp_extract(l.source_record, 'PR-[0-9]{2}'), ''), r.press_id)
