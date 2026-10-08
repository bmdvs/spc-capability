-- Parts that pass between routine checks, by press and part, in the baseline year: from the run speed, the parts per
-- stroke and the check frequency in the control plan, with the interval between routine checks as recorded beside it.
-- Grain: one row per press and part with a run in the baseline year before the redesign.

with freq as (

    select part_id, min(frequency_minutes) as plan_frequency_minutes
    from {{ ref('stg_spc__characteristics') }}
    where data_type = 'variable' and "type" <> 'burr height'
    group by 1

),

gaps as (

    select c.run_id, date_diff('second', lag(c.check_time) over (partition by c.run_id order by c.check_time), c.check_time) / 60.0 as minutes_since_last_routine_check
    from {{ ref('int_run_checks') }} c
    where c.routine_check

),

run_gaps as (

    select run_id, median(minutes_since_last_routine_check) as median_minutes_between_routine_checks, count(*) + 1 as routine_checks
    from gaps where minutes_since_last_routine_check is not null
    group by 1

)

select
    r.press_id,
    pr.press_group,
    r.part_id,
    p.program,
    count(*) as runs,
    median(r.run_speed_spm) as strokes_per_minute,
    any_value(r.parts_per_stroke) as parts_per_stroke,
    any_value(f.plan_frequency_minutes) as plan_frequency_minutes,
    median(r.run_speed_spm) * any_value(r.parts_per_stroke) * any_value(f.plan_frequency_minutes) as parts_between_checks_by_plan,
    median(g.median_minutes_between_routine_checks) as minutes_between_routine_checks_recorded,
    median(r.run_speed_spm * r.parts_per_stroke * g.median_minutes_between_routine_checks) as parts_between_checks_recorded,
    any_value(sr.realised_share_of_run_speed) as realised_share_of_run_speed,
    median(r.run_speed_spm) * any_value(r.parts_per_stroke) * any_value(f.plan_frequency_minutes) * any_value(sr.realised_share_of_run_speed) as parts_between_checks_at_the_realised_rate,
    {{ batch_id() }} as export_batch_id
from {{ ref('int_run_shots') }} r
join {{ ref('int_press_redesign') }} pr on pr.press_id = r.press_id
join {{ ref('stg_erp__parts') }} p on p.part_id = r.part_id
join {{ ref('int_press_stroke_rate') }} sr on sr.press_id = r.press_id
left join freq f on f.part_id = r.part_id
left join run_gaps g on g.run_id = r.run_id
where year(r.production_start) = {{ var('baseline_year') }} and r.production_start < pr.redesign_date
group by 1, 2, 3, 4
order by 1, 3
