-- Readings against shots since the last sharpening, for the die wear analysis. Grain: one row per routine subgroup
-- on a variable hole diameter or on burr height (the lab burr gauge), with the die's shots since sharpening known.
-- The value is the subgroup mean; the lab burr readings carry no mean in the SPC software (burr height is not charted),
-- so their value is the mean of the five readings. Burr height carries an upper limit only, and its value is also given as
-- a share of it.

select
    h.subgroup_id, h.characteristic_id, h.characteristic_type, h.part_id, h.family_part, h.die_id, h.press_id, h.press_group,
    h.sharpening_interval_no, h.sharpening_date, h.shots_since_sharpening, h.sample_time, h.in_quarter, h.usl, h.lsl, h.tolerance_width,
    coalesce(h.subgroup_mean, (h.r1 + h.r2 + h.r3 + h.r4 + h.r5) / 5) as subgroup_mean, h.subgroup_range, h.limit_set_id, h.centre_line, h.ucl_mean, h.lcl_mean,
    case when h.characteristic_type = 'burr height' then (h.r1 + h.r2 + h.r3 + h.r4 + h.r5) / 5 / h.usl end as share_of_limit,
    {{ batch_id() }} as export_batch_id
from {{ ref('int_characteristic_history') }} h
where h.in_record and h.data_type = 'variable' and coalesce(h.subgroup_mean, h.r5) is not null and h.shots_since_sharpening is not null
  and h.subgroup_type = 'routine' and h.characteristic_class in ('hole diameter', 'burr height')
