-- Punch replacements in the die log, with what led to each: the per-stroke chart that stopped the press and the
-- condition the toolmaker found. Grain: one row per punch replacement.

select
    e.die_event_id, e.die_id, e.event_date, e.stations_touched, e.toolmaker, e.hours, e.notes, e.fault_event_id,
    case when e.notes like '%chipped%' then 'chipped' when e.notes like '%worn%' then 'worn' end as punch_condition,
    case
        when e.notes like '%(EWMA)%' then 'EWMA on the total'
        when e.notes like '%(channel share)%' then 'channel share'
        when e.notes like '%(both)%' then 'both'
        else 'other'
    end as led_by,
    s.press_id, s.press_group, s.run_id, s.stopped_at,
    e.event_date between cast('{{ var("quarter_start") }}' as date) and cast('{{ var("record_end") }}' as date) as in_quarter,
    {{ batch_id() }} as export_batch_id
from {{ ref('int_die_event_timeline') }} e
left join {{ ref('mart_per_stroke_stops') }} s on s.fault_event_id = e.fault_event_id
where e.event_type = 'punch replacement'
