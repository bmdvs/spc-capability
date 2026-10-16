-- The strokes a press makes against the strokes its run speed would give, by press, over every completed run that
-- started in the record: strokes made over run speed times the run's working clock time. Grain: one row per press.
--
-- Working clock time is the part of the run, from start of production to end, that falls inside the plant's working
-- day ({{ var('working_day_start_minute') // 60 }}:00 to {{ var('working_day_end_minute') // 60 }}:00) on days the press recorded a check. A run's whole clock time cannot be used:
-- runs of more than a shift span the hours the plant does not run.

with runs as (

    select run_id, press_id, strokes, run_speed_spm, production_start, actual_end
    from {{ ref('stg_erp__production_runs') }}
    where status = 'complete'
      and cast(production_start as date) between cast('{{ var("record_start") }}' as date) and cast('{{ var("record_end") }}' as date)

),

working_days as (

    select distinct x.press_id, cast(k.check_time as date) as working_day
    from {{ ref('int_run_checks') }} k
    join {{ ref('stg_erp__production_runs') }} x on x.run_id = k.run_id

),

run_days as (

    select r.*, cast(unnest(range(cast(r.production_start as date), cast(r.actual_end as date) + interval 1 day, interval 1 day)) as date) as day
    from runs r

),

worked as (

    select d.run_id, d.press_id, any_value(d.strokes) as strokes, any_value(d.run_speed_spm) as run_speed_spm,
           sum(greatest(0, date_diff('second',
               greatest(d.production_start, cast(d.day as timestamp) + interval {{ var('working_day_start_minute') }} minute),
               least(d.actual_end, cast(d.day as timestamp) + interval {{ var('working_day_end_minute') }} minute)))) / 60.0 as working_minutes
    from run_days d
    join working_days w on w.press_id = d.press_id and w.working_day = d.day
    group by 1, 2

)

select
    press_id,
    count(*) as runs,
    median(strokes / nullif(run_speed_spm * working_minutes, 0)) as realised_share_of_run_speed,
    sum(strokes) / sum(run_speed_spm * working_minutes) as realised_share_of_run_speed_pooled,
    {{ batch_id() }} as export_batch_id
from worked
where working_minutes > 0
group by 1
order by 1
