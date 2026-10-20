-- The coil-change subgroups on formed characteristics with the coil's certificate, and the points of the chart of
-- coil-change means: one point per coil, the first coil-change subgroup measured on it. coils_on_record is the number of
-- earlier points on the chart, which sets its limits (from 6 coils on all coils on record, from 20 on the previous 20).
-- Grain: one row per coil-change subgroup.

with cc as (

    select h.*,
           row_number() over (partition by h.characteristic_id, h.coil_id order by h.sample_time, h.subgroup_id) = 1 as charted_point
    from {{ ref('int_characteristic_history') }} h
    where h.subgroup_type = 'coil-change' and h.characteristic_class = 'formed' and h.subgroup_mean is not null

)

select
    cc.subgroup_id, cc.characteristic_id, cc.part_id, cc.family_part, cc.press_id, cc.run_id, cc.die_id, cc.characteristic_type, cc.characteristic_name,
    cc.nominal, cc.usl, cc.lsl, cc.tolerance_width, cc.sample_time, cc.in_quarter, cc.coil_id, cc.coil_assignment,
    cc.r1, cc.r2, cc.r3, cc.r4, cc.r5, cc.r6, cc.r7, cc.r8, cc.r9, cc.r10,
    cc.subgroup_mean, cc.subgroup_range, cc.subgroup_mean - cc.nominal as offset_from_nominal,
    cc.charted_point,
    case when cc.charted_point then
        count(*) filter (where cc.charted_point) over (partition by cc.characteristic_id order by cc.sample_time, cc.subgroup_id rows between unbounded preceding and 1 preceding)
    end as coils_on_record,
    cc.coil_change_centre, cc.coil_change_ucl, cc.coil_change_lcl,
    cc.alarm_rule_1_coil_change,
    cc.adjustment_recorded,
    k.certificate_thickness_mm, k.certificate_hardness_hrb, k.receiving_hardness_hrb, k.supplier_id, k.coil_lot,
    {{ batch_id() }} as export_batch_id
from cc
left join {{ ref('stg_erp__coils') }} k on k.coil_id = cc.coil_id
