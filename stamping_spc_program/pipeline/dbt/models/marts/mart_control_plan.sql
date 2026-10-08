-- The control plan as in force at the end of the record on the parts that run on the pilot presses. Grain: one row per
-- characteristic. Each characteristic carries its limit set in force at {{ var('control_plan_date') }} where it has one, the latest study on
-- its gauge or check fixture, the count of reaction plan steps, the check frequency in the characteristics master and
-- the frequency as recorded (the median minutes between consecutive routine subgroups on a run, March to December 2025).

with parts as (

    select p.part_id, p.revision, p.program, p.primary_press as press_id, p.die_id, p.material_grade, p.thickness_mm, p.parts_per_stroke, x.load_cell_channels
    from {{ ref('stg_erp__parts') }} p
    join {{ ref('int_press_redesign') }} x on x.press_id = p.primary_press
    where x.is_pilot_press

),

limits as (

    select *
    from {{ ref('mart_limits_as_set') }}
    where effective_from <= cast('{{ var("control_plan_date") }}' as date)
      and (effective_to is null or effective_to > cast('{{ var("control_plan_date") }}' as date))
    qualify row_number() over (partition by characteristic_id order by effective_from desc) = 1

),

studies as (

    select gauge_id, date as study_date, trigger as study_trigger, pct_grr_of_tolerance, ndc
    from {{ ref('stg_calibration__gauge_studies') }}
    where date <= cast('{{ var("control_plan_date") }}' as date)
    qualify row_number() over (partition by gauge_id order by date desc) = 1

),

steps as (

    select characteristic_id, count(*) as reaction_plan_steps
    from {{ ref('stg_spc__reaction_plan_steps') }}
    group by 1

),

gaps as (

    select characteristic_id, run_id,
           date_diff('minute', lag(sample_time) over (partition by characteristic_id, run_id order by sample_time), sample_time) as minutes_since_the_check_before
    from {{ ref('int_characteristic_history') }}
    where subgroup_type = 'routine' and after_redesign and sample_time >= date '2025-03-01' and sample_time < date '2026-01-01'

),

recorded as (

    select characteristic_id, median(minutes_since_the_check_before) as frequency_minutes_as_recorded, count(*) as checks_behind_the_frequency
    from gaps
    where minutes_since_the_check_before is not null and minutes_since_the_check_before <= 600
    group by 1

),

speed as (

    select part_id, median(run_speed_spm) as run_speed_spm
    from {{ ref('int_run_shots') }}
    where production_start >= date '2025-02-03'
    group by 1

)

select
    c.characteristic_id, c.part_id, p.revision, p.program, p.press_id, p.die_id, p.material_grade, p.thickness_mm, p.parts_per_stroke, p.load_cell_channels,
    c.name as characteristic_name, c.type as characteristic_type, c.critical, c.customer_designated, c.nominal, c.lsl, c.usl, c.unit,
    c.data_type, c.chart_type as chart_type_in_the_master, c.subgroup_size, c.frequency_minutes as frequency_minutes_in_the_master,
    r.frequency_minutes_as_recorded, r.checks_behind_the_frequency,
    s.run_speed_spm, s.run_speed_spm * p.parts_per_stroke * coalesce(r.frequency_minutes_as_recorded, c.frequency_minutes) as parts_between_checks_at_run_speed,
    c.gauge_id, g.type as gauge_type, t.study_date as gauge_study_date, t.study_trigger as gauge_study_trigger, t.pct_grr_of_tolerance, t.ndc,
    case
        when c.data_type = 'attribute' then 'attribute check'
        when l.method = 'tool-wear regression' then 'tool-wear chart'
        when l.characteristic_id is null then 'no limit set in force'
        when c.type in ('formed height', 'bend angle') then 'three-way chart'
        else 'X-bar and R'
    end as chart_in_force,
    l.limit_set_id, l.method as limits_basis, l.effective_from as limits_in_force_from, l.centre_line, l.lcl_mean, l.ucl_mean, l.ucl_range,
    l.subgroups_used, l.coil_changes_spanned, l.slope_per_100k_shots,
    coalesce(st.reaction_plan_steps, 0) as reaction_plan_steps,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_spc__characteristics') }} c
join parts p using (part_id)
left join limits l using (characteristic_id)
left join {{ ref('stg_calibration__gauges') }} g on g.gauge_id = c.gauge_id
left join studies t on t.gauge_id = c.gauge_id
left join steps st using (characteristic_id)
left join recorded r using (characteristic_id)
left join speed s using (part_id)
