-- The die maintenance log in order, with the sharpening interval each event falls in. Grain: one row per die event.
-- A sharpening interval runs from one sharpening (or rebuild) to the next on the same die; interval 0 is the part of
-- the record before the die's first logged sharpening or rebuild, whose start lies outside the export.

with events as (

    select
        die_event_id, die_id, "date" as event_date, "type" as event_type, stations_touched, shot_count, toolmaker, hours, notes, fault_event_id,
        ("type" in ('sharpening', 'rebuild')) as starts_interval
    from {{ ref('stg_die_room__die_events') }}

)

select
    e.*,
    (e.shot_count is not null and e.shot_count % 1000 = 0) as shot_count_rounded_to_thousand,
    sum(e.starts_interval::int) over (partition by e.die_id order by e.event_date, e.die_event_id rows between unbounded preceding and current row) as sharpening_interval_no,
    max(case when e.event_type = 'rebuild' then e.event_date end) over (partition by e.die_id order by e.event_date, e.die_event_id rows between unbounded preceding and current row) as last_rebuild_date,
    {{ batch_id() }} as export_batch_id
from events e
order by e.die_id, e.event_date, e.die_event_id
