-- Readings against shots since the last sharpening, for the die wear analysis.
-- Grain: one row per subgroup of variable readings on a critical hole diameter or on burr height (the burr gauge in
-- the lab), with the die's shots since sharpening known and no reading set aside by the plausibility rule. The value
-- is the mean of the five readings. Burr height carries an upper limit only; its value is also given as a share of it.

with s as (

    select
        h.subgroup_id, h.characteristic_id, h.characteristic_type, h.part_id, h.die_id, h.press_id, h.is_pilot_press, h.after_redesign,
        h.sharpening_interval_no, h.sharpening_date, h.shots_since_sharpening, h.sample_time, h.subgroup_type, h.usl, h.lsl, h.tolerance_width,
        (h.r1 + h.r2 + h.r3 + h.r4 + h.r5) / 5 as reading_mean
    from {{ ref('int_characteristic_history') }} h
    where h.data_type = 'variable' and h.r5 is not null and h.implausible_readings = 0 and h.shots_since_sharpening is not null
      and ((h.characteristic_type = 'hole diameter' and h.critical) or h.characteristic_type = 'burr height')

)

select
    s.*,
    year(s.sample_time) as sample_year,
    case when s.characteristic_type = 'burr height' then s.reading_mean / s.usl end as share_of_limit,
    {{ batch_id() }} as export_batch_id
from s
