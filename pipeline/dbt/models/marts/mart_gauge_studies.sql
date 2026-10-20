-- Gauge studies on file, with the gauge's previous study and whether the study is the latest at the status date.
-- Grain: one row per study.

select
    s.study_id, s.gauge_id, g."type" as gauge_type, g.location, s.characteristic_id, k.part_id,
    list_contains({{ var('family_parts') }}, k.part_id) as family_part,
    s."date" as study_date, s."trigger" as study_trigger, s.method, s.operators, s.parts, s.trials, s.pct_grr_of_tolerance, s.ndc, s.restudy_due,
    case when s.pct_grr_of_tolerance < 10 then 'under 10%' when s.pct_grr_of_tolerance <= 30 then '10% to 30%' else 'over 30%' end as grr_band,
    lag(s.pct_grr_of_tolerance) over (partition by s.gauge_id order by s."date", s.study_id) as previous_pct_grr,
    lag(s."date") over (partition by s.gauge_id order by s."date", s.study_id) as previous_study_date,
    s."date" between cast('{{ var("quarter_start") }}' as date) and cast('{{ var("record_end") }}' as date) as in_quarter,
    row_number() over (partition by s.gauge_id order by s."date" desc, s.study_id desc) = 1 as latest_on_file,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_calibration__gauge_studies') }} s
join {{ ref('stg_calibration__gauges') }} g using (gauge_id)
left join {{ ref('stg_spc__characteristics') }} k using (characteristic_id)
where s."date" <= cast('{{ var("status_date") }}' as date)
