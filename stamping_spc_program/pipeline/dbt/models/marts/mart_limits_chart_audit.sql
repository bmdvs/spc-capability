-- The chart audit for the baseline year: every variable characteristic charted, how its limits were set and when,
-- what they signalled and what limits from the stable baseline signal on the same subgroups. Grain: one row per
-- characteristic with at least one subgroup in the baseline year.

with charted as (

    select
        h.characteristic_id,
        any_value(h.part_id) as part_id,
        any_value(h.characteristic_name) as characteristic_name,
        any_value(h.characteristic_type) as characteristic_type,
        bool_or(h.critical) as critical,
        mode(h.press_id) as press_id,
        mode(h.entry_method) as entry_method,
        any_value(h.frequency_minutes) as frequency_minutes,
        count(*) as subgroups,
        count(*) filter (where h.implausible_readings > 0) as subgroups_with_a_reading_set_aside,
        count(*) filter (where h.limits_in_force) as subgroups_with_limits_in_force,
        count(*) filter (where h.alarm_rule_1) as signals_as_set_rule_1,
        count(*) filter (where h.alarm_raised) as signals_as_set_any_rule,
        count(*) filter (where h.alarm_raised and (h.acknowledgement_text is not null or h.adjustment_recorded)) as signals_with_action_recorded,
        count(*) filter (where h.gauge_past_due) as subgroups_on_a_gauge_past_due
    from {{ ref('int_characteristic_history') }} h
    where year(h.sample_time) = {{ var('baseline_year') }}
      and h.data_type = 'variable' and h.characteristic_type <> 'burr height'
      and h.subgroup_mean is not null and not h.after_redesign
    group by 1

),

set_ as (

    select characteristic_id, method, effective_from, subgroups_used, rebuild_on_or_before_set, months_in_force_at_assessment,
           sharpenings_while_in_force_to_assessment, set_by
    from {{ ref('mart_limits_as_set') }}
    where in_force_at_assessment

),

compared as (

    select
        characteristic_id,
        count(*) as subgroups_compared,
        count(*) filter (where signal_as_computed_rule_1) as signals_as_computed_rule_1,
        count(*) filter (where signal_as_computed_rule_1 and signal_as_set_rule_1) as signals_by_both,
        count(*) filter (where signal_as_set_rule_1) as signals_as_set_rule_1_compared
    from {{ ref('mart_limits_subgroup_flags') }}
    group by 1

),

baselines as (

    select characteristic_id,
           count(*) filter (where baseline_to is not null) as intervals_with_computed_limits,
           count(*) filter (where baseline_basis = 'stable on rules 1 to 4') as baselines_stable_on_rules_1_to_4,
           count(*) filter (where baseline_basis = 'stable on rule 1 only') as baselines_stable_on_rule_1_only,
           count(*) filter (where baseline_basis = 'not stable') as baselines_not_stable,
           count(*) filter (where baseline_to is null) as intervals_too_short
    from {{ ref('mart_limits_as_computed') }}
    group by 1

)

select
    c.characteristic_id, c.part_id, c.characteristic_name, c.characteristic_type, c.critical, c.press_id, pr.press_group,
    c.entry_method, c.frequency_minutes,
    s.method as limits_as_set_method,
    s.effective_from as limits_as_set_from,
    s.subgroups_used as limits_as_set_subgroups_used,
    s.rebuild_on_or_before_set,
    s.months_in_force_at_assessment,
    s.sharpenings_while_in_force_to_assessment,
    c.subgroups, c.subgroups_with_a_reading_set_aside, c.subgroups_with_limits_in_force,
    c.signals_as_set_rule_1, c.signals_as_set_any_rule, c.signals_with_action_recorded, c.subgroups_on_a_gauge_past_due,
    b.intervals_with_computed_limits, b.baselines_stable_on_rules_1_to_4, b.baselines_stable_on_rule_1_only, b.baselines_not_stable, b.intervals_too_short,
    k.subgroups_compared, k.signals_as_computed_rule_1, k.signals_by_both, k.signals_as_set_rule_1_compared,
    {{ batch_id() }} as export_batch_id
from charted c
left join set_ s on s.characteristic_id = c.characteristic_id
left join compared k on k.characteristic_id = c.characteristic_id
left join baselines b on b.characteristic_id = c.characteristic_id
left join {{ ref('int_press_redesign') }} pr on pr.press_id = c.press_id
order by c.characteristic_id
