-- Every subgroup with what it was taken on and under: the run, press, die and sharpening interval, the characteristic
-- and its class, the coil in force, the limit set in force at entry, the rules signalled and the gauge's calibration
-- status that day. A gauge is out of service from the day it is removed for calibration to the day it is back, both
-- days counted, and past due from the day after its due date to the day it is removed or calibrated. Grain: one row per subgroup.
--
-- The alarm flags carry one token per rule signalled: 1 to 4 on the means or individuals chart, "1 range",
-- "1 moving range" and "1 coil-change" on those charts.

with s as (

    select * from {{ ref('stg_spc__subgroups') }}

),

c as (

    select
        characteristic_id, part_id, name as characteristic_name, "type" as characteristic_type, nominal, usl, lsl, unit,
        critical, customer_designated, gauge_id as gauge_id_planned, subgroup_size, coil_change_subgroup_size, frequency_minutes, data_type, chart_type,
        case
            when "type" in ('formed height', 'bend angle') then 'formed'
            when "type" = 'hole diameter' and data_type = 'variable' then 'hole diameter'
            when "type" in ('hole-to-edge', 'hole-to-hole') then 'hole position'
            when "type" in ('length', 'width') then 'length and width'
            when "type" = 'flatness' then 'flatness'
            when "type" = 'burr height' and data_type = 'variable' then 'burr height'
            else 'attribute'
        end as characteristic_class,
        usl - coalesce(lsl, 0) as tolerance_width,
        lsl is null as one_sided
    from {{ ref('stg_spc__characteristics') }}

),

gauge_days as (

    select s.subgroup_id,
        bool_or(g.out_of_service_from is not null and cast(s.sample_time as date) >= g.out_of_service_from and (g.back_in_service is null or cast(s.sample_time as date) <= g.back_in_service)) as gauge_out_of_service,
        bool_or(g.back_in_service > g.overdue_from and cast(s.sample_time as date) > g.overdue_from and cast(s.sample_time as date) <= coalesce(g.out_of_service_from, g.back_in_service)) as gauge_past_due
    from s
    join {{ ref('int_gauge_status') }} g
        on g.gauge_id = s.gauge_id
       and cast(s.sample_time as date) > least(g.overdue_from, coalesce(g.out_of_service_from, g.overdue_from))
       and (g.back_in_service is null or cast(s.sample_time as date) <= g.back_in_service)
    group by 1

),

flags as (

    select subgroup_id, alarm_flags,
           trim(replace(replace(replace(coalesce(alarm_flags, ''), '1 moving range', ''), '1 range', ''), '1 coil-change', '')) as centre_chart_flags
    from s

)

select
    s.subgroup_id,
    s.characteristic_id,
    c.part_id,
    p.family_code,
    list_contains({{ var('family_parts') }}, c.part_id) as family_part,
    s.run_id,
    r.press_id,
    r.press_group,
    r.die_id,
    r.sharpening_interval_no,
    r.sharpening_date,
    case when r.shots_since_sharpening_at_start is not null then
        r.shots_since_sharpening_at_start
        + r.strokes * least(greatest(date_diff('second', r.production_start, s.sample_time) / nullif(date_diff('second', r.production_start, r.actual_end), 0), 0), 1)
    end as shots_since_sharpening,
    c.characteristic_name,
    c.characteristic_type,
    c.characteristic_class,
    c.chart_type,
    c.data_type,
    c.critical,
    c.customer_designated,
    c.nominal, c.usl, c.lsl, c.one_sided, c.tolerance_width, c.unit,
    c.frequency_minutes,
    s.subgroup_no,
    s.sample_time,
    s.recorded_at,
    date_diff('second', s.sample_time, s.recorded_at) / 60.0 as minutes_to_entry,
    cast(s.sample_time as date) between cast('{{ var("record_start") }}' as date) and cast('{{ var("record_end") }}' as date) as in_record,
    cast(s.sample_time as date) between cast('{{ var("quarter_start") }}' as date) and cast('{{ var("record_end") }}' as date) as in_quarter,
    s.operator_id,
    s.gauge_id,
    s.entry_method,
    s.subgroup_type,
    s.pieces,
    ca.coil_id,
    ca.coil_assignment,
    s.r1, s.r2, s.r3, s.r4, s.r5, s.r6, s.r7, s.r8, s.r9, s.r10,
    s.attribute_count,
    s.mean as subgroup_mean,
    s."range" as subgroup_range,
    s.limit_set_id,
    s.limit_status,
    s.limit_status = 'provisional, baseline in progress' as limits_provisional,
    s.centre_line, s.ucl_mean, s.lcl_mean, s.ucl_range, s.lcl_range, s.ucl_moving_range,
    s.coil_change_centre, s.coil_change_ucl, s.coil_change_lcl,
    s.alarm_flags,
    regexp_matches(f.centre_chart_flags, '(^|\s)1(\s|$)') as alarm_rule_1,
    coalesce(s.alarm_flags like '%1 range%', false) as alarm_rule_1_range,
    coalesce(s.alarm_flags like '%1 moving range%', false) as alarm_rule_1_moving_range,
    coalesce(s.alarm_flags like '%1 coil-change%', false) as alarm_rule_1_coil_change,
    nullif(array_to_string(regexp_extract_all(f.centre_chart_flags, '[234]'), ' '), '') as pattern_flags,
    (s.alarm_flags is not null) as alarm_raised,
    coalesce(s.adjustment_flag, false) as adjustment_recorded,
    coalesce(g.gauge_out_of_service, false) as gauge_out_of_service,
    coalesce(g.gauge_past_due, false) as gauge_past_due,
    {{ batch_id() }} as export_batch_id
from s
join c on c.characteristic_id = s.characteristic_id
left join {{ ref('stg_erp__parts') }} p on p.part_id = c.part_id
left join {{ ref('int_run_shots') }} r on r.run_id = s.run_id
left join {{ ref('int_coil_assignment') }} ca on ca.subgroup_id = s.subgroup_id
left join flags f on f.subgroup_id = s.subgroup_id
left join gauge_days g on g.subgroup_id = s.subgroup_id
