-- Every subgroup with what it was taken on and under: the run, press, die and sharpening interval, the characteristic
-- and its limits, the coil in force, the limits in force at entry, the alarms raised and the gauge's calibration
-- status that day. A gauge is out of service from the day it is removed for calibration to the day it is back, both
-- days counted, and past due from the day after its due date to the day it is removed or calibrated. Grain: one row per subgroup.
--
-- The plausibility rule is applied here. A keyed or transcribed reading more than
-- {{ var('implausible_tolerance_widths') }} tolerance widths from the characteristic's nominal cannot be a measurement
-- of the part; the rule uses the reading, the nominal and the tolerance and nothing else. Such readings stay in the
-- row as recorded and are counted in implausible_readings; analyses that set them aside filter on that column.

with s as (

    select * from {{ ref('stg_spc__subgroups') }}

),

c as (

    select
        characteristic_id, part_id, name as characteristic_name, "type" as characteristic_type, nominal, usl, lsl, unit,
        critical, customer_designated, gauge_id as gauge_id_planned, frequency_minutes, data_type, chart_type,
        usl - coalesce(lsl, 0) as tolerance_width
    from {{ ref('stg_spc__characteristics') }}

),

gauge_days as (

    select distinct s.subgroup_id,
        bool_or(g.out_of_service_from is not null and cast(s.sample_time as date) >= g.out_of_service_from and cast(s.sample_time as date) <= g.back_in_service) as gauge_out_of_service,
        bool_or(g.back_in_service > g.overdue_from and cast(s.sample_time as date) > g.overdue_from and cast(s.sample_time as date) <= coalesce(g.out_of_service_from, g.back_in_service)) as gauge_past_due
    from s
    join {{ ref('int_gauge_status') }} g
        on g.gauge_id = s.gauge_id
       and cast(s.sample_time as date) > least(g.overdue_from, coalesce(g.out_of_service_from, g.overdue_from))
       and cast(s.sample_time as date) <= g.back_in_service
    group by 1

),

flagged as (

    select
        s.subgroup_id,
        (case when abs(s.r1 - c.nominal) > {{ var('implausible_tolerance_widths') }} * c.tolerance_width then 1 else 0 end
         + case when abs(s.r2 - c.nominal) > {{ var('implausible_tolerance_widths') }} * c.tolerance_width then 1 else 0 end
         + case when abs(s.r3 - c.nominal) > {{ var('implausible_tolerance_widths') }} * c.tolerance_width then 1 else 0 end
         + case when abs(s.r4 - c.nominal) > {{ var('implausible_tolerance_widths') }} * c.tolerance_width then 1 else 0 end
         + case when abs(s.r5 - c.nominal) > {{ var('implausible_tolerance_widths') }} * c.tolerance_width then 1 else 0 end) as beyond
    from s
    join c on c.characteristic_id = s.characteristic_id
    where s.r1 is not null

)

select
    s.subgroup_id,
    s.characteristic_id,
    c.part_id,
    s.run_id,
    r.press_id,
    pr.press_group,
    r.die_id,
    r.sharpening_interval_no,
    r.sharpening_date,
    case when r.shots_since_sharpening_at_start is not null then
        r.shots_since_sharpening_at_start
        + r.strokes * least(greatest(date_diff('second', r.production_start, s.sample_time) / nullif(date_diff('second', r.production_start, r.actual_end), 0), 0), 1)
    end as shots_since_sharpening,
    c.characteristic_name,
    c.characteristic_type,
    c.data_type,
    c.critical,
    c.customer_designated,
    c.nominal, c.usl, c.lsl, c.tolerance_width, c.unit,
    c.frequency_minutes,
    s.subgroup_no,
    s.sample_time,
    s.recorded_at,
    date_diff('second', s.sample_time, s.recorded_at) / 60.0 as minutes_to_entry,
    s.operator_id,
    s.gauge_id,
    s.entry_method,
    s.subgroup_type,
    ca.coil_id,
    ca.coil_assignment,
    s.r1, s.r2, s.r3, s.r4, s.r5,
    s.attribute_count,
    s.mean as subgroup_mean,
    s."range" as subgroup_range,
    s.centre_line, s.ucl_mean, s.lcl_mean, s.ucl_range, s.lcl_range,
    (s.ucl_mean is not null) as limits_in_force,
    coalesce(s.alarm_flags like '%1%', false) as alarm_rule_1,
    coalesce(s.alarm_flags like '%2%', false) as alarm_rule_2,
    (s.alarm_flags is not null) as alarm_raised,
    s.pattern_flags,
    s.acknowledgement_text,
    coalesce(s.adjustment_flag, false) as adjustment_recorded,
    case when s.entry_method = 'gauge-connected' then 0 else coalesce(f.beyond, 0) end as implausible_readings,
    coalesce(g.gauge_out_of_service, false) as gauge_out_of_service,
    coalesce(g.gauge_past_due, false) as gauge_past_due,
    coalesce(gm.status = 'lost', false) as gauge_recorded_as_lost,
    (s.sample_time >= pr.redesign_date) as after_redesign,
    pr.is_pilot_press,
    {{ batch_id() }} as export_batch_id
from s
join c on c.characteristic_id = s.characteristic_id
left join {{ ref('int_run_shots') }} r on r.run_id = s.run_id
left join {{ ref('int_press_redesign') }} pr on pr.press_id = r.press_id
left join {{ ref('int_coil_assignment') }} ca on ca.subgroup_id = s.subgroup_id
left join flagged f on f.subgroup_id = s.subgroup_id
left join gauge_days g on g.subgroup_id = s.subgroup_id
left join {{ ref('stg_calibration__gauges') }} gm on gm.gauge_id = s.gauge_id
