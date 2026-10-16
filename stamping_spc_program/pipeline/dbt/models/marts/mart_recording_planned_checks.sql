-- The routine checks the control plan calls for on each run, and whether one was recorded. Grain: one row per run and
-- planned check time. A planned check falls on the clock at the part's check frequency (the shortest among its variable
-- characteristics charted at the press), inside the working day, in a shift in which the press recorded a check, from
-- {{ var('planned_check_after_start_minutes') }} minutes after production started (and after the press starts the working day) to {{ var('planned_check_before_end_minutes') }} minutes before the run ended. It counts as recorded when the run carries a
-- routine check from {{ var('planned_check_early_minutes') }} minutes before it to {{ var('planned_check_late_minutes') }} minutes after. Runs shorter than {{ var('short_run_minutes') }} minutes from production start to end
-- carry no rows. The day shift ends and the night shift starts at {{ var('shift_change_minute') }} minutes after midnight.

with runs as (

    select r.run_id, r.press_id, r.press_group, r.part_id, r.production_start, r.actual_end
    from {{ ref('int_run_shots') }} r
    where r.production_start is not null and r.actual_end is not null
      and cast(r.production_start as date) >= cast('{{ var("record_start") }}' as date)
      and cast(r.actual_end as date) <= cast('{{ var("record_end") }}' as date)
      and date_diff('minute', r.production_start, r.actual_end) >= {{ var('short_run_minutes') }}

),

frequency as (

    select part_id, min(frequency_minutes) as frequency_minutes
    from {{ ref('stg_spc__characteristics') }}
    where data_type = 'variable' and chart_type <> 'none'
    group by 1

),

press_shifts as (

    select distinct press_id, cast(sample_time as date) as working_day,
           case when hour(sample_time) * 60 + minute(sample_time) < {{ var('shift_change_minute') }} then 'days' else 'nights' end as shift
    from {{ ref('int_characteristic_history') }}

),

marks as (

    select r.*, f.frequency_minutes,
           unnest(range(date_trunc('hour', r.production_start), r.actual_end + interval 1 hour, interval 30 minute)) as planned_time
    from runs r
    join frequency f using (part_id)

),

planned as (

    select m.*
    from marks m
    join press_shifts d on d.press_id = m.press_id and d.working_day = cast(m.planned_time as date)
        and d.shift = case when hour(m.planned_time) * 60 + minute(m.planned_time) < {{ var('shift_change_minute') }} then 'days' else 'nights' end
    where hour(m.planned_time) * 60 + minute(m.planned_time) >= {{ var('working_day_start_minute') }} + {{ var('planned_check_after_start_minutes') }}
      and hour(m.planned_time) * 60 + minute(m.planned_time) < {{ var('working_day_end_minute') }}
      and (hour(m.planned_time) * 60 + minute(m.planned_time)) % m.frequency_minutes = 0
      and m.planned_time >= m.production_start + interval {{ var('planned_check_after_start_minutes') }} minute
      and m.planned_time <= m.actual_end - interval {{ var('planned_check_before_end_minutes') }} minute

)

select
    p.run_id, p.press_id, p.press_group, p.part_id, p.frequency_minutes, p.planned_time,
    cast(p.planned_time as date) >= cast('{{ var("quarter_start") }}' as date) as in_quarter,
    case when hour(p.planned_time) * 60 + minute(p.planned_time) < {{ var('shift_change_minute') }} then 'days' else 'nights' end as shift,
    count(c.check_time) > 0 as recorded,
    {{ batch_id() }} as export_batch_id
from planned p
left join {{ ref('int_run_checks') }} c
    on c.run_id = p.run_id and c.routine_check
   and c.check_time >= p.planned_time - interval {{ var('planned_check_early_minutes') }} minute
   and c.check_time <= p.planned_time + interval {{ var('planned_check_late_minutes') }} minute
group by all
