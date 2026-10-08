-- Each sorting event traced through its nonconformance to the run, the check before the finding, the die-protection
-- fault that bounds the sort where there is one, and the die work that followed. Grain: one row per sorting event.
--
-- A check is any recorded check on the run: routine, first-piece (which before the redesign includes the check at a
-- coil change), coil-change and last-piece. The check before is the last check before the finding, whether the
-- finding was made at a check or between checks; a check recorded within {{ var('finding_check_minutes') }} minutes
-- before the finding is the check at which it was found. The record before per-stroke monitoring does not hold the
-- stroke at which parts first went wrong, or the stroke of the finding. An interval of time is turned into parts two
-- ways: at the run's speed and parts per stroke, which is the most the press can have made, and at that figure times
-- the press's realised share of run speed. Where the die-protection log has a slug detection or part-out fault on the
-- run between the check before and the finding, and the quantity on the nonconformance is no more than the press can
-- have made since that fault (with {{ var('fault_bound_tolerance') * 100 }}% allowed), the sort is taken as bounded by
-- the fault; otherwise it is a sort back to the check before. Where the fault was logged within
-- {{ var('fault_at_check_minutes') }} minutes of the check before, the two bases give the same quantity and the sort is
-- shown as not distinguishable. Parts between two times are estimates, not counts.

with s as (

    select se.*, n.detected_at, n.cause_code, n.cause_text, n.defect_code, n.characteristic_id, n.opened as found_at, n.quantity_affected, n.disposition
    from {{ ref('stg_qms__sorting_events') }} se
    join {{ ref('stg_qms__nonconformances') }} n on n.ncr_id = se.ncr_id

),

r as (

    select x.run_id, x.press_id, x.die_id, x.part_id, x.production_start, x.actual_end, x.strokes, x.run_speed_spm, x.parts_per_stroke, x.standard_hours, x.labor_hours,
           x.run_speed_spm * x.parts_per_stroke as parts_per_minute_at_run_speed, sr.realised_share_of_run_speed
    from {{ ref('int_run_shots') }} x
    join {{ ref('int_press_stroke_rate') }} sr on sr.press_id = x.press_id

),

checks as (

    select
        s.sorting_event_id,
        max(c.check_time) filter (where c.check_time <= s.found_at and c.check_time >= s.found_at - interval {{ var('finding_check_minutes') }} minute) as found_at_check,
        max(c.check_time) filter (where c.check_time < s.found_at - interval {{ var('finding_check_minutes') }} minute) as check_before,
        arg_max(c.first_piece_check and not c.routine_check, c.check_time) filter (where c.check_time <= s.found_at and c.check_time >= s.found_at - interval {{ var('finding_check_minutes') }} minute) as found_at_a_first_piece_check
    from s
    left join {{ ref('int_run_checks') }} c on c.run_id = s.run_id
    group by 1

),

die_work as (

    select s.sorting_event_id,
           min(e.event_date) as die_event_date,
           arg_min(e.die_event_id, e.event_date) as die_event_id,
           arg_min(e.event_type, e.event_date) as die_event_type,
           arg_min(e.notes, e.event_date) as die_event_notes
    from s
    join r on r.run_id = s.run_id
    join {{ ref('int_die_event_timeline') }} e
        on e.die_id = r.die_id and e.event_type in ('punch replacement', 'repair')
       and e.event_date >= cast(s.found_at as date) and e.event_date <= cast(s.found_at as date) + {{ var('trace_days') }}
    group by 1

),

fault_rows as (

    select s.sorting_event_id, f.fault_event_id, f."input", f."timestamp" as fault_time,
           date_diff('second', coalesce(k.check_before, r.production_start), f."timestamp") / 60.0 as minutes_after_check_before,
           date_diff('second', f."timestamp", s.found_at) / 60.0 * r.parts_per_minute_at_run_speed as parts_from_fault_to_finding,
           s.quantity_affected
    from s
    join r on r.run_id = s.run_id
    join checks k on k.sorting_event_id = s.sorting_event_id
    join {{ ref('stg_press_monitor__fault_events') }} f
        on f.run_id = s.run_id and f."timestamp" > coalesce(k.check_before, r.production_start) and f."timestamp" <= s.found_at
    where f."input" in ('misfeed', 'part-out', 'strip position', 'slug detection')

),

faults as (

    select sorting_event_id,
           count(*) as die_protection_faults_in_the_window,
           string_agg(distinct "input", ', ' order by "input") as fault_inputs,
           arg_max(fault_event_id, fault_time) filter (where "input" in ('slug detection', 'part-out') and quantity_affected <= (1 + {{ var('fault_bound_tolerance') }}) * parts_from_fault_to_finding) as bounding_fault_event_id,
           max(fault_time) filter (where "input" in ('slug detection', 'part-out') and quantity_affected <= (1 + {{ var('fault_bound_tolerance') }}) * parts_from_fault_to_finding) as bounding_fault_time,
           arg_max(minutes_after_check_before, fault_time) filter (where "input" in ('slug detection', 'part-out') and quantity_affected <= (1 + {{ var('fault_bound_tolerance') }}) * parts_from_fault_to_finding) as bounding_fault_minutes_after_check_before,
           arg_max(parts_from_fault_to_finding, fault_time) filter (where "input" in ('slug detection', 'part-out') and quantity_affected <= (1 + {{ var('fault_bound_tolerance') }}) * parts_from_fault_to_finding) as parts_from_fault_to_finding
    from fault_rows
    group by 1

)

select
    s.sorting_event_id,
    s.ncr_id,
    s.run_id,
    r.press_id,
    pr.press_group,
    pr.is_pilot_press,
    r.die_id,
    r.part_id,
    s.started as sort_started,
    s.ended as sort_ended,
    s.sorted_at,
    s.detected_at,
    s.defect_code,
    s.cause_code,
    s.cause_text,
    s.found_at,
    k.found_at_check,
    (k.found_at_check is not null) as found_at_a_check,
    coalesce(k.found_at_a_first_piece_check, false) as found_at_a_first_piece_check,
    k.check_before,
    date_diff('second', coalesce(k.check_before, r.production_start), s.found_at) / 60.0 as minutes_from_check_before_to_finding,
    r.run_speed_spm,
    r.parts_per_stroke,
    date_diff('second', coalesce(k.check_before, r.production_start), s.found_at) / 60.0 * r.parts_per_minute_at_run_speed as parts_from_check_before_to_finding,
    date_diff('second', coalesce(k.check_before, r.production_start), s.found_at) / 60.0 * r.parts_per_minute_at_run_speed * r.realised_share_of_run_speed as parts_from_check_before_to_finding_at_the_realised_rate,
    s.quantity_affected,
    s.quantity_sorted,
    s.quantity_rejected,
    s.hours as sorting_hours_booked,
    s.cost as sorting_cost_booked,
    r.standard_hours as run_standard_hours,
    r.labor_hours as run_labor_hours,
    r.labor_hours - r.standard_hours as run_hours_above_standard,
    d.die_event_id,
    d.die_event_date,
    date_diff('day', cast(s.found_at as date), d.die_event_date) as days_from_finding_to_die_log,
    d.die_event_type,
    d.die_event_notes,
    coalesce(f.die_protection_faults_in_the_window, 0) as die_protection_faults_in_the_window,
    f.fault_inputs,
    f.bounding_fault_event_id,
    f.bounding_fault_time,
    f.parts_from_fault_to_finding,
    case
        when s.detected_at = 'customer' then 'customer complaint'
        when d.die_event_id is not null then 'die event between two checks'
        else 'press check, no die work logged within three days'
    end as traced_to,
    case
        when s.detected_at = 'customer' then 'sorted at the customer'
        when f.bounding_fault_event_id is not null and f.bounding_fault_minutes_after_check_before <= {{ var('fault_at_check_minutes') }} then 'fault logged at the check before; basis not distinguishable'
        when f.bounding_fault_event_id is not null then 'sorted from a logged die-protection fault'
        when s.sorted_at = 'in-house' then 'sorted back to the check before, in-house'
        else 'sorted back to the check before, sorting service'
    end as sort_basis,
    {{ batch_id() }} as export_batch_id
from s
join r on r.run_id = s.run_id
left join {{ ref('int_press_redesign') }} pr on pr.press_id = r.press_id
left join checks k on k.sorting_event_id = s.sorting_event_id
left join die_work d on d.sorting_event_id = s.sorting_event_id
left join faults f on f.sorting_event_id = s.sorting_event_id
order by s.started
