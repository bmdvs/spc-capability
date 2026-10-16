-- Observed signals on routine subgroups, by characteristic, period and the limit set's chart and baseline size, for
-- comparison with the false-alarm rate expected under the rules in force. Charts with a special cause are left out:
-- a subgroup is in scope when it is charted under limits in force (not provisional) and falls outside any sharpening
-- interval in which the chart carried an assignable cause. Signals are counted per subgroup; any rule covers every
-- chart of the characteristic (means or individuals, range, moving range). Grain: one row per
-- characteristic, press, period, chart and baseline size.

with special as (

    select distinct characteristic_id, die_id, sharpening_interval_no
    from {{ ref('int_alarm_dispositions') }}
    where assignable_cause

),

s as (

    select h.*, l.chart, l.subgroups_used as baseline_subgroups,
           sp.characteristic_id is null and not h.limits_provisional as in_scope
    from {{ ref('int_characteristic_history') }} h
    join {{ ref('mart_limit_sets') }} l on l.limit_set_id = h.limit_set_id
    left join special sp on sp.characteristic_id = h.characteristic_id and sp.die_id = h.die_id and sp.sharpening_interval_no = h.sharpening_interval_no
    where h.subgroup_type = 'routine' and h.in_record and h.subgroup_mean is not null

),

periods as (

    select 'record' as period, * from s
    union all
    select 'quarter' as period, * from s where in_quarter

)

select
    period, characteristic_id, min(part_id) as part_id, bool_or(family_part) as family_part, press_id, min(press_group) as press_group,
    min(characteristic_class) as characteristic_class, chart, baseline_subgroups,
    count(*) as routine_subgroups,
    count(*) filter (where in_scope) as subgroups_in_scope,
    count(*) filter (where in_scope and (alarm_rule_1 or pattern_flags is not null or alarm_rule_1_range or alarm_rule_1_moving_range)) as signals_any_rule,
    count(*) filter (where in_scope and (alarm_rule_1 or pattern_flags is not null)) as signals_centre_chart,
    count(*) filter (where in_scope and alarm_rule_1) as signals_rule_1,
    count(*) filter (where in_scope and pattern_flags is not null) as signals_rules_2_to_4,
    count(*) filter (where in_scope and pattern_flags like '%2%') as signals_rule_2,
    count(*) filter (where in_scope and pattern_flags like '%3%') as signals_rule_3,
    count(*) filter (where in_scope and pattern_flags like '%4%') as signals_rule_4,
    count(*) filter (where in_scope and alarm_rule_1_range) as signals_range,
    count(*) filter (where in_scope and alarm_rule_1_moving_range) as signals_moving_range,
    count(*) filter (where alarm_rule_1 or pattern_flags is not null or alarm_rule_1_range or alarm_rule_1_moving_range) as signals_any_rule_all_subgroups,
    {{ batch_id() }} as export_batch_id
from periods
group by period, characteristic_id, press_id, chart, baseline_subgroups
