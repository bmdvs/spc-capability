-- Subgroup means in sequence on each run, with the next subgroup beside each, for the adjustment analysis.
-- Grain: one row per routine subgroup on a variable characteristic with limits in force and no reading set aside by
-- the plausibility rule. The position of a mean is in units of the chart's sigma of the mean as the limits in force
-- give it. A characteristic an adjustment at the press acts on is a formed height, a bend angle or a hole-to-edge
-- position (shut height, pressure pad and feed); hole diameters, hole-to-hole positions, lengths and widths are set by
-- the die and are not adjusted at the press.

with s as (

    select
        h.subgroup_id, h.characteristic_id, h.characteristic_type, h.run_id, h.press_id, h.press_group, h.is_pilot_press, h.after_redesign,
        h.coil_id, h.sample_time, h.entry_method, h.subgroup_mean, h.subgroup_range, h.centre_line, h.ucl_mean, h.lcl_mean,
        h.alarm_rule_1, h.alarm_raised, h.adjustment_recorded, h.acknowledgement_text,
        (h.characteristic_type in ('formed height', 'bend angle', 'hole-to-edge')) as adjusted_at_the_press,
        (h.subgroup_mean - h.centre_line) / nullif((h.ucl_mean - h.centre_line) / 3, 0) as position_in_sigma
    from {{ ref('int_characteristic_history') }} h
    where h.subgroup_type = 'routine' and h.data_type = 'variable' and h.characteristic_type not in ('burr height', 'flatness')
      and h.subgroup_mean is not null and h.limits_in_force and h.implausible_readings = 0

)

select
    s.*,
    year(s.sample_time) as sample_year,
    lead(s.position_in_sigma) over w as next_position_in_sigma,
    lead(s.adjustment_recorded) over w as next_adjustment_recorded,
    case when s.entry_method = 'paper transcription' then s.alarm_rule_1 else abs(s.position_in_sigma) > 2 end as beyond_two_sigma_or_the_printed_limit,
    {{ batch_id() }} as export_batch_id
from s
window w as (partition by s.characteristic_id, s.run_id order by s.sample_time, s.subgroup_id)
