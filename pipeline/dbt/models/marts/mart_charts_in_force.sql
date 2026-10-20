-- The charts in force at the status date: one row per characteristic with a chart, with the limit set in force and its
-- basis, the gauge with its latest study (for a hand gauge, the latest study of its type at its press) and calibration,
-- the check frequency and the reaction plan. A chart is in a baseline when its last routine subgroup in the record was charted under provisional limits; the baseline's progress is
-- the routine subgroups and coil changes since the provisional limits began, and the chart is past its trigger when that
-- progress meets the baseline rule with no new limit set issued. Formed characteristics carry the chart of coil-change
-- means with its last limits. Grain: one row per characteristic.

{% set status_end = "cast('" ~ var('status_date') ~ "' as timestamp) + interval 1 day" %}

with k as (

    select k.*, p.die_id, p.primary_press as press_id, pr.press_group, list_contains({{ var('family_parts') }}, k.part_id) as family_part
    from {{ ref('stg_spc__characteristics') }} k
    left join {{ ref('stg_erp__parts') }} p on p.part_id = k.part_id
    left join {{ ref('stg_erp__presses') }} pr on pr.press_id = p.primary_press
    where k.chart_type <> 'none'

),

ls as (

    select * from {{ ref('mart_limit_sets') }}
    where effective_from < {{ status_end }} and (effective_to is null or effective_to >= {{ status_end }})

),

routine as (

    select characteristic_id, sample_time, coil_id, limits_provisional,
           row_number() over (partition by characteristic_id order by sample_time desc, subgroup_id desc) as back
    from {{ ref('int_characteristic_history') }}
    where subgroup_type = 'routine' and subgroup_mean is not null and in_record

),

provisional_start as (

    select characteristic_id, max(sample_time) as last_in_force_at
    from routine where not limits_provisional
    group by 1

),

progress as (

    select r.characteristic_id,
           count(*) as baseline_subgroups_so_far,
           count(distinct r.coil_id) - 1 as baseline_coil_changes_so_far,
           min(r.sample_time) as provisional_from
    from routine r
    left join provisional_start s using (characteristic_id)
    where r.limits_provisional and (s.last_in_force_at is null or r.sample_time > s.last_in_force_at)
    group by 1

),

last_routine as (

    select characteristic_id, limits_provisional as in_baseline from routine where back = 1

),

studies as (

    select s.*, g."type" as gauge_type, g.location
    from {{ ref('stg_calibration__gauge_studies') }} s
    join {{ ref('stg_calibration__gauges') }} g using (gauge_id)
    where s."date" <= cast('{{ var("status_date") }}' as date)

),

own_study as (

    select gauge_id, "date" as study_date, pct_grr_of_tolerance, ndc, restudy_due, "trigger" as study_trigger
    from studies
    qualify row_number() over (partition by gauge_id order by "date" desc, study_id desc) = 1

),

family_study as (

    -- a hand gauge is covered by the latest study of its type at its press
    select gauge_type, location, "date" as study_date, pct_grr_of_tolerance, ndc, restudy_due, "trigger" as study_trigger
    from studies
    where "trigger" like '%hand gauge family%'
    qualify row_number() over (partition by gauge_type, location order by "date" desc, study_id desc) = 1

),

cal as (

    select gauge_id, max(done) filter (where done <= cast('{{ var("status_date") }}' as date)) as last_calibrated,
           min(due) filter (where done is null or done > cast('{{ var("status_date") }}' as date)) as calibration_due
    from {{ ref('stg_calibration__calibrations') }}
    group by 1

),

cc as (

    select characteristic_id, coil_change_centre, coil_change_ucl, coil_change_lcl, coils_on_record + 1 as coils_on_record
    from {{ ref('mart_coil_change_points') }}
    where charted_point
    qualify row_number() over (partition by characteristic_id order by sample_time desc, subgroup_id desc) = 1

),

plans as (

    select characteristic_id, string_agg(distinct signal, '; ' order by signal) as reaction_plan_signals, count(*) as reaction_plan_steps
    from {{ ref('stg_spc__reaction_plan_steps') }}
    group by 1

)

select
    k.characteristic_id, k.part_id, k.family_part, k.die_id, k.press_id, k.press_group, k.name as characteristic_name, k."type" as characteristic_type,
    case
        when k."type" in ('formed height', 'bend angle') then 'formed'
        when k."type" = 'hole diameter' and k.data_type = 'variable' then 'hole diameter'
        when k."type" in ('hole-to-edge', 'hole-to-hole') then 'hole position'
        when k."type" in ('length', 'width') then 'length and width'
        when k."type" = 'flatness' then 'flatness'
        else 'attribute'
    end as characteristic_class,
    k.critical, k.chart_type, k.data_type, k.subgroup_size, k.coil_change_subgroup_size, k.frequency_minutes, k.usl, k.lsl, k.nominal, k.unit,
    ls.limit_set_id, ls.basis, ls.trigger as limits_trigger, ls.effective_from as limits_effective_from, ls.annotation as limits_annotation, ls.last_verified_at,
    ls.rules_in_force, ls.centre_line, ls.ucl_mean, ls.lcl_mean, ls.ucl_range, ls.ucl_moving_range, ls.sigma_of_means, ls.slope_per_100k_shots, ls.trigger_subgroups,
    ls.subgroups_used, ls.coil_changes_spanned,
    coalesce(lr.in_baseline, false) as in_baseline,
    case when coalesce(lr.in_baseline, false) then pg.provisional_from end as baseline_started,
    case when coalesce(lr.in_baseline, false) then pg.baseline_subgroups_so_far end as baseline_subgroups_so_far,
    case when coalesce(lr.in_baseline, false) then pg.baseline_coil_changes_so_far end as baseline_coil_changes_so_far,
    coalesce(lr.in_baseline, false)
        and pg.baseline_subgroups_so_far >= case when k.chart_type = 'tool-wear' then coalesce(ls.trigger_subgroups, {{ var('baseline_subgroups') }}) else {{ var('baseline_subgroups') }} end
        and (k.chart_type <> 'three-way (I-MR-R)' or pg.baseline_coil_changes_so_far >= {{ var('three_way_baseline_coil_changes') }}) as past_trigger,
    k.gauge_id, g."type" as gauge_type, g.resolution as gauge_resolution,
    coalesce(st.study_date, fs.study_date) as study_date,
    case when st.study_date is not null then 'this gauge' when fs.study_date is not null then 'gauge type at the press' end as study_basis,
    coalesce(st.study_trigger, fs.study_trigger) as study_trigger,
    coalesce(st.pct_grr_of_tolerance, fs.pct_grr_of_tolerance) as pct_grr_of_tolerance,
    coalesce(st.ndc, fs.ndc) as ndc,
    coalesce(st.restudy_due, fs.restudy_due) as restudy_due,
    coalesce(st.pct_grr_of_tolerance, fs.pct_grr_of_tolerance) >= 10 and coalesce(st.restudy_due, fs.restudy_due) is not null as restudy_scheduled,
    cal.last_calibrated, cal.calibration_due,
    cc.coil_change_centre, cc.coil_change_ucl, cc.coil_change_lcl, cc.coils_on_record as coil_change_chart_coils,
    pl.reaction_plan_signals, pl.reaction_plan_steps,
    {{ batch_id() }} as export_batch_id
from k
left join ls on ls.characteristic_id = k.characteristic_id
left join last_routine lr on lr.characteristic_id = k.characteristic_id
left join progress pg on pg.characteristic_id = k.characteristic_id
left join {{ ref('stg_calibration__gauges') }} g on g.gauge_id = k.gauge_id
left join own_study st on st.gauge_id = k.gauge_id
left join family_study fs on fs.gauge_type = g."type" and fs.location = g.location
left join cal on cal.gauge_id = k.gauge_id
left join cc on cc.characteristic_id = k.characteristic_id
left join plans pl on pl.characteristic_id = k.characteristic_id
