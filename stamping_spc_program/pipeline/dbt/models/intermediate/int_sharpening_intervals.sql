-- Sharpening intervals by die: from one sharpening or rebuild to the next. Grain: one row per die and interval.
-- The interval open at the end of the export has no end date. Logged shots are the die's shot count at the next
-- sharpening less its count at this one, on the corrected counts. An interval of under {{ var('run_interval_min_shots') }} logged shots is
-- flagged as not a run interval.

with starts as (

    select die_id, sharpening_interval_no, event_date as interval_start, event_type as started_by, shot_count as shot_count_at_start, die_event_id, notes
    from {{ ref('int_die_event_timeline') }}
    where starts_interval

)

select
    s.die_id,
    s.sharpening_interval_no,
    s.interval_start,
    lead(s.interval_start) over w as interval_end,
    s.started_by,
    lead(s.started_by) over w as ended_by,
    s.shot_count_at_start,
    lead(s.shot_count_at_start) over w - s.shot_count_at_start as shots_in_interval_logged,
    lead(s.notes) over w as notes_at_end,
    s.die_event_id as starting_die_event_id,
    coalesce(lead(s.shot_count_at_start) over w - s.shot_count_at_start >= {{ var('run_interval_min_shots') }}, true) as is_run_interval,
    {{ batch_id() }} as export_batch_id
from starts s
window w as (partition by s.die_id order by s.sharpening_interval_no)
order by s.die_id, s.sharpening_interval_no
