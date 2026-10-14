-- Production capability by critical characteristic over the twelve months to the dashboard's current month, with the
-- Ppk of the latest PPAP study beside. Grain: one row per critical variable characteristic with at least
-- {{ var('dashboard_min_subgroups') }} subgroups in the twelve months. Readings set aside by the plausibility rule are left out.

with h as (

    select characteristic_id, part_id, press_id, is_pilot_press, characteristic_type, usl, lsl, r1, r2, r3, r4, r5
    from {{ ref('int_characteristic_history') }}
    where critical and data_type = 'variable' and r5 is not null and implausible_readings = 0 and lsl is not null
      and sample_time >= date '2025-07-01' and sample_time < date '2026-07-01'

),

s as (

    select characteristic_id, any_value(part_id) as part_id, any_value(press_id) as press_id, any_value(is_pilot_press) as is_pilot_press, any_value(characteristic_type) as characteristic_type,
           any_value(usl) as usl, any_value(lsl) as lsl, count(*) as subgroups,
           avg((r1 + r2 + r3 + r4 + r5) / 5) as mean_reading,
           sqrt(avg(list_aggregate([r1, r2, r3, r4, r5], 'var_samp'))) as sigma_within,
           stddev_samp(reading) as sigma_overall_placeholder
    from (select *, unnest([r1, r2, r3, r4, r5]) as reading from h)
    group by 1

),

o as (

    select characteristic_id, stddev_samp(reading) as sigma_overall
    from (select characteristic_id, unnest([r1, r2, r3, r4, r5]) as reading from h)
    group by 1

),

ppap as (

    select characteristic_id, date as ppap_study_date, ppk as ppap_ppk
    from {{ ref('stg_qms__ppap_studies') }}
    qualify row_number() over (partition by characteristic_id order by date desc) = 1

)

select
    s.characteristic_id, s.part_id, s.press_id, s.is_pilot_press, s.characteristic_type,
    case when s.characteristic_type in ('formed height', 'bend angle') then 'formed' else 'punched' end as characteristic_class,
    s.subgroups / 5 as subgroups,
    least(s.usl - s.mean_reading, s.mean_reading - s.lsl) / (3 * s.sigma_within) as production_cpk,
    least(s.usl - s.mean_reading, s.mean_reading - s.lsl) / (3 * o.sigma_overall) as production_ppk,
    p.ppap_ppk, p.ppap_study_date,
    {{ batch_id() }} as export_batch_id
from s
join o using (characteristic_id)
left join ppap p using (characteristic_id)
where s.subgroups / 5 >= {{ var('dashboard_min_subgroups') }}
