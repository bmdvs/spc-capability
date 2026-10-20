-- The subgroups of each Phase I baseline completed in the record: the routine subgroups the set was computed from,
-- the last ones on the chart up to the time the set was issued. A subgroup is screened when its mean (individual on a
-- three-way chart) or range falls beyond the limits the baseline gives. Tool-wear regressions are not baselines of
-- this kind and are left out. Grain: one row per limit set and subgroup.

with sets as (

    select limit_set_id, characteristic_id, chart, effective_from, subgroups_used, centre_line, ucl_mean, lcl_mean, ucl_range, ucl_moving_range
    from {{ ref('mart_limit_sets') }}
    where issued_in_record and chart in ('X-bar and R', 'three-way')

),

ranked as (

    select s.limit_set_id, s.chart, s.subgroups_used, s.centre_line, s.ucl_mean, s.lcl_mean, s.ucl_range, s.ucl_moving_range,
           h.subgroup_id, h.characteristic_id, h.sample_time, h.coil_id, h.subgroup_mean, h.subgroup_range, h.run_id,
           row_number() over (partition by s.limit_set_id order by h.sample_time desc, h.subgroup_id desc) as back
    from sets s
    join {{ ref('int_characteristic_history') }} h
        on h.characteristic_id = s.characteristic_id and h.subgroup_type = 'routine' and h.subgroup_mean is not null and h.sample_time <= s.effective_from

),

kept as (

    select *, row_number() over (partition by limit_set_id order by sample_time, subgroup_id) as baseline_subgroup_no
    from ranked
    where back <= subgroups_used

)

select
    k.limit_set_id, k.characteristic_id, k.chart, k.baseline_subgroup_no, k.subgroup_id, k.run_id, k.sample_time, k.coil_id,
    k.coil_id is distinct from lag(k.coil_id) over (partition by k.limit_set_id order by k.baseline_subgroup_no) and k.baseline_subgroup_no > 1 as coil_change_before,
    k.subgroup_mean, k.subgroup_range,
    abs(k.subgroup_mean - lag(k.subgroup_mean) over (partition by k.limit_set_id order by k.baseline_subgroup_no)) as moving_range,
    k.centre_line, k.ucl_mean, k.lcl_mean, k.ucl_range, k.ucl_moving_range,
    (k.subgroup_mean > k.ucl_mean or k.subgroup_mean < k.lcl_mean or k.subgroup_range > k.ucl_range) as screened,
    {{ batch_id() }} as export_batch_id
from kept k
