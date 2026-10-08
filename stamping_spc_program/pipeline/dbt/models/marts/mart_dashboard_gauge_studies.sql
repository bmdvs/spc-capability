-- Gauge study status by check fixture: the latest study on each fixture and the PPAP study where the record has one.
-- Grain: one row per check fixture.

with latest as (
    select gauge_id, date as study_date, trigger as study_trigger, pct_grr_of_tolerance, ndc
    from {{ ref('stg_calibration__gauge_studies') }}
    qualify row_number() over (partition by gauge_id order by date desc) = 1
),

counts as (
    select gauge_id, count(*) as studies_in_the_record, min(date) as first_study_date from {{ ref('stg_calibration__gauge_studies') }} group by 1
),

parts as (
    select c.gauge_id, any_value(c.part_id) as part_id, any_value(p.primary_press) as press_id
    from {{ ref('stg_spc__characteristics') }} c join {{ ref('stg_erp__parts') }} p using (part_id) group by 1
)

select
    g.gauge_id as fixture_id, x.part_id, x.press_id, l.study_date, l.study_trigger, l.pct_grr_of_tolerance, l.ndc, k.studies_in_the_record, k.first_study_date,
    case when l.pct_grr_of_tolerance is null then 'no study' when l.pct_grr_of_tolerance < 10 then 'under 10%' when l.pct_grr_of_tolerance <= 30 then '10% to 30%' else 'over 30%' end as status,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_calibration__gauges') }} g
left join latest l using (gauge_id)
left join counts k using (gauge_id)
left join parts x using (gauge_id)
where g.type = 'check fixture'
