-- Every alarm with the subgroup it was raised on, its disposition and the time to acknowledge and to close it.
-- Grain: one row per alarm (one alarm per chart and rule signalled on a subgroup).

select
    a.alarm_id,
    a.subgroup_id,
    h.characteristic_id,
    h.part_id,
    h.family_part,
    h.run_id,
    h.press_id,
    h.press_group,
    h.die_id,
    h.sharpening_interval_no,
    h.characteristic_type,
    h.characteristic_class,
    h.chart_type,
    h.subgroup_type,
    h.limit_set_id,
    h.limits_provisional,
    a.chart,
    a.rule,
    case when a.rule = 1 then 'rule 1' else 'rules 2 to 4' end as rule_group,
    a.raised_at,
    a.acknowledged_at,
    a.acknowledged_by,
    a.closed_at,
    date_diff('second', a.raised_at, a.acknowledged_at) / 60.0 as minutes_to_acknowledge,
    date_diff('second', a.raised_at, a.closed_at) / 60.0 as minutes_to_close,
    a.disposition,
    a.disposition = 'assignable cause found' as assignable_cause,
    a.cause_code,
    a.action,
    h.adjustment_recorded,
    h.in_record,
    h.in_quarter,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_spc__alarms') }} a
join {{ ref('int_characteristic_history') }} h on h.subgroup_id = a.subgroup_id
