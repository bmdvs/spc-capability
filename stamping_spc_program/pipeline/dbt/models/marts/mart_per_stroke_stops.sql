-- Stops of the press by the per-stroke charts on the presses with every stroke kept, with the toolmaker's finding and
-- the die work logged against the stop. Grain: one row per stop.

select
    f.fault_event_id, f.press_id, f.run_id, f."timestamp" as stopped_at, f.stroke_no as stop_stroke_no,
    case when f.input = 'EWMA signal' then 'EWMA on the total' else 'channel share' end as chart,
    f.finding, f.cleared_at, f.cleared_by,
    f.die_event_id, e.event_type as die_event_type, e.stations_touched, e.notes as die_event_notes,
    r.part_id, r.die_id, r.parts_per_stroke,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_press_monitor__fault_events') }} f
join {{ ref('int_press_redesign') }} p using (press_id)
left join {{ ref('int_die_event_timeline') }} e on e.die_event_id = f.die_event_id
left join {{ ref('int_run_shots') }} r on r.run_id = f.run_id
where f.input in ('EWMA signal', 'channel share signal') and p.is_pilot_press
