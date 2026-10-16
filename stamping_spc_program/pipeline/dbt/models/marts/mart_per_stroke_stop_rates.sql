-- Per-stroke stops against the strokes made, by press and period: stops by finding, and stops with nothing found per
-- million strokes. Strokes are the run strokes of production runs that started in the period. Grain: one row per
-- press and period.

with runs as (

    select run_id, press_id, press_group, strokes,
           cast(production_start as date) >= cast('{{ var("quarter_start") }}' as date) as in_quarter
    from {{ ref('int_run_shots') }}
    where cast(production_start as date) between cast('{{ var("record_start") }}' as date) and cast('{{ var("record_end") }}' as date)

),

periods as (

    select 'record' as period, * from runs
    union all
    select 'quarter', * from runs where in_quarter

),

strokes as (

    select period, press_id, any_value(press_group) as press_group, count(*) as runs, sum(strokes) as strokes from periods group by 1, 2

),

stops as (

    select p.period, s.press_id,
           count(*) as stops,
           count(*) filter (where s.finding_class = 'nothing found') as stops_nothing_found,
           count(*) filter (where s.finding_class = 'chipped punch') as stops_chipped_punch,
           count(*) filter (where s.finding_class = 'worn punch') as stops_worn_punch,
           count(*) filter (where s.finding_class = 'slug pulling') as stops_slug_pulling
    from {{ ref('mart_per_stroke_stops') }} s
    join periods p on p.run_id = s.run_id
    group by 1, 2

)

select
    t.period, t.press_id, t.press_group, t.runs, t.strokes,
    coalesce(s.stops, 0) as stops, coalesce(s.stops_nothing_found, 0) as stops_nothing_found, coalesce(s.stops_chipped_punch, 0) as stops_chipped_punch,
    coalesce(s.stops_worn_punch, 0) as stops_worn_punch, coalesce(s.stops_slug_pulling, 0) as stops_slug_pulling,
    coalesce(s.stops_nothing_found, 0) / (t.strokes / 1e6) as stops_nothing_found_per_million_strokes,
    {{ batch_id() }} as export_batch_id
from strokes t
left join stops s using (period, press_id)
