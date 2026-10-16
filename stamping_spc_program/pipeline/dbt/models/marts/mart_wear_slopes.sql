-- Hole diameter wear by sharpening interval and by die: the slope of subgroup means on shots since sharpening, in mm
-- per 100,000 shots, on intervals with at least {{ var('wear_interval_min_subgroups') }} subgroups spanning at least {{ var('run_interval_min_shots') }} shots. A die's rate is the median of its
-- interval slopes, given with the number of intervals behind it. The press is the one the interval ran on (the first by
-- id where it ran on two). Grain: one row per characteristic and interval.

with intervals as (

    select characteristic_id, min(part_id) as part_id, bool_or(family_part) as family_part, die_id, min(press_id) as press_id, sharpening_interval_no,
           count(*) as subgroups, max(shots_since_sharpening) - min(shots_since_sharpening) as shot_span,
           regr_slope(subgroup_mean, shots_since_sharpening) * 100000 as slope_mm_per_100k_shots,
           regr_intercept(subgroup_mean, shots_since_sharpening) as intercept_mm
    from {{ ref('mart_wear_points') }}
    where characteristic_type = 'hole diameter'
    group by characteristic_id, die_id, sharpening_interval_no

),

qualifying as (

    select * from intervals
    where subgroups >= {{ var('wear_interval_min_subgroups') }} and shot_span >= {{ var('run_interval_min_shots') }}

)

select
    q.*,
    median(q.slope_mm_per_100k_shots) over (partition by q.characteristic_id) as characteristic_rate_mm_per_100k_shots,
    count(*) over (partition by q.characteristic_id) as qualifying_intervals,
    {{ batch_id() }} as export_batch_id
from qualifying q
