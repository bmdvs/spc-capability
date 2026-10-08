-- The routine checks the control plan calls for on each run, and whether one was recorded. Grain: one row per run and
-- planned check time. A planned check falls on the clock at the part's check frequency (the shortest frequency among
-- its characteristics in the characteristics master), inside the working day, on a day the press recorded a check,
-- from {{ var('planned_check_after_start_minutes') }} minutes after production started to {{ var('planned_check_before_end_minutes') }} minutes before the run ended. It counts as recorded when the run
-- carries a routine check from {{ var('planned_check_early_minutes') }} minutes before it to {{ var('planned_check_late_minutes') }} minutes after. Runs shorter than {{ var('short_run_minutes') }} minutes
-- from production start to end are in the short-run count of the recording analysis and carry no rows here. The
-- day shift ends and the night shift starts at {{ var('shift_change_minute') }} minutes after midnight.

with runs as (

    select r.run_id, r.press_id, r.part_id, r.production_start, r.actual_end, p.is_pilot_press,
           cast(r.production_start as date) >= p.redesign_date as after_redesign
    from {{ ref('int_run_shots') }} r
    join {{ ref('int_press_redesign') }} p using (press_id)
    where r.production_start is not null and r.actual_end is not null
      and date_diff('minute', r.production_start, r.actual_end) >= {{ var('short_run_minutes') }}

),

frequency as (

    select part_id, min(frequency_minutes) as frequency_minutes
    from {{ ref('stg_spc__characteristics') }}
    group by 1

),

press_days as (

    select distinct press_id, cast(sample_time as date) as working_day
    from {{ ref('int_characteristic_history') }}

),

marks as (

    select r.*, f.frequency_minutes,
           unnest(range(date_trunc('hour', r.production_start), r.actual_end + interval 1 hour, interval 1 hour)) as planned_time
    from runs r
    join frequency f using (part_id)

),

planned as (

    select m.*
    from marks m
    join press_days d on d.press_id = m.press_id and d.working_day = cast(m.planned_time as date)
    where hour(m.planned_time) * 60 >= {{ var('working_day_start_minute') }} and hour(m.planned_time) * 60 < {{ var('working_day_end_minute') }}
      and (hour(m.planned_time) * 60) % m.frequency_minutes = 0
      and m.planned_time >= m.production_start + interval {{ var('planned_check_after_start_minutes') }} minute
      and m.planned_time <= m.actual_end - interval {{ var('planned_check_before_end_minutes') }} minute

)

select
    p.run_id, p.press_id, p.part_id, p.is_pilot_press, p.after_redesign, p.frequency_minutes, p.planned_time,
    year(p.planned_time) as planned_year,
    case when hour(p.planned_time) * 60 + minute(p.planned_time) < {{ var('shift_change_minute') }} then 'days' else 'nights' end as shift,
    count(c.check_time) > 0 as recorded,
    {{ batch_id() }} as export_batch_id
from planned p
left join {{ ref('int_run_checks') }} c
    on c.run_id = p.run_id and c.routine_check
   and c.check_time >= p.planned_time - interval {{ var('planned_check_early_minutes') }} minute
   and c.check_time <= p.planned_time + interval {{ var('planned_check_late_minutes') }} minute
group by all
