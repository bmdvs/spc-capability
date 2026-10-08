-- Each subgroup of the baseline year on a variable characteristic, with the signal the shop's limits raised at entry
-- and the signal limits computed from the stable baseline after the sharpening would raise. Grain: one row per
-- subgroup taken after the baseline window of its sharpening interval, before the redesign, with no reading set aside
-- by the plausibility rule.

select
    h.subgroup_id,
    h.characteristic_id,
    h.part_id,
    h.press_id,
    h.press_group,
    h.die_id,
    h.sharpening_interval_no,
    h.characteristic_type,
    h.critical,
    h.entry_method,
    case h.entry_method when 'keyed' then 'rolling 25 at entry' when 'paper transcription' then 'PPAP study' end as limits_as_set_method,
    h.subgroup_type,
    h.sample_time,
    h.subgroup_mean,
    h.subgroup_range,
    h.limits_in_force,
    h.ucl_mean as ucl_mean_as_set,
    h.lcl_mean as lcl_mean_as_set,
    h.ucl_range as ucl_range_as_set,
    b.ucl_mean as ucl_mean_as_computed,
    b.lcl_mean as lcl_mean_as_computed,
    b.ucl_range as ucl_range_as_computed,
    b.baseline_basis,
    h.alarm_rule_1 as signal_as_set_rule_1,
    h.alarm_raised as signal_as_set_any_rule,
    (h.subgroup_mean > b.ucl_mean or h.subgroup_mean < b.lcl_mean or h.subgroup_range > b.ucl_range) as signal_as_computed_rule_1,
    (h.acknowledgement_text is not null or h.adjustment_recorded) as action_recorded,
    h.adjustment_recorded,
    {{ batch_id() }} as export_batch_id
from {{ ref('int_characteristic_history') }} h
join {{ ref('mart_limits_as_computed') }} b
    on b.characteristic_id = h.characteristic_id
   and b.sharpening_interval_no = h.sharpening_interval_no
   and b.baseline_to is not null
where year(h.sample_time) = {{ var('baseline_year') }}
  and not h.after_redesign
  and h.subgroup_mean is not null
  and h.implausible_readings = 0
  and h.sample_time > b.baseline_to
