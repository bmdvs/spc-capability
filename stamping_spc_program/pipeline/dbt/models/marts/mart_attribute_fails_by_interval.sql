-- Attribute check fails across the sharpening interval. Grain: one row per check (burr against the limit sample, hole
-- diameter by pin) and fifth of the interval. Routine subgroups in the record with the shot count known; position is
-- shots since sharpening over the die's due shot count, and points past the due count go into the last fifth.

with a as (

    select case h.characteristic_type when 'burr height' then 'burr' else 'pin' end as attribute_check,
           least(floor(h.shots_since_sharpening / d.sharpening_due_count / 0.2), 4) + 1 as interval_fifth,
           h.shots_since_sharpening / d.sharpening_due_count as position,
           h.pieces, coalesce(h.attribute_count, 0) as fails
    from {{ ref('int_characteristic_history') }} h
    join {{ ref('stg_erp__dies') }} d using (die_id)
    where h.in_record and h.data_type = 'attribute' and h.subgroup_type = 'routine' and h.shots_since_sharpening is not null

)

select attribute_check, cast(interval_fifth as integer) as interval_fifth, count(*) as subgroups, sum(pieces) as pieces_checked, sum(fails) as fails,
       count(*) filter (where position > 1) as subgroups_past_due_count, {{ batch_id() }} as export_batch_id
from a
group by 1, 2
order by 1, 2
