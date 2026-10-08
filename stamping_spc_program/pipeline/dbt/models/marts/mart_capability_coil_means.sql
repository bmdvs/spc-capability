-- Formed-characteristic level by coil, with the coil's certificate and receiving values, for the production window of
-- each study in the capability comparison. Grain: one row per study and coil with at least two usable subgroups.

select
    w.study_id,
    h.characteristic_id,
    h.characteristic_type,
    h.coil_id,
    count(*) as subgroups,
    avg(h.subgroup_mean) as coil_mean,
    c.supplier_id,
    c.nominal_thickness_mm,
    (c.certificate_thickness_mm - c.nominal_thickness_mm) / c.nominal_thickness_mm as certificate_thickness_deviation,
    ((c.receiving_thickness_1_mm + c.receiving_thickness_2_mm) / 2 - c.nominal_thickness_mm) / c.nominal_thickness_mm as receiving_thickness_deviation,
    c.certificate_hardness_hrb,
    c.receiving_hardness_hrb,
    {{ batch_id() }} as export_batch_id
from {{ ref('mart_capability_as_computed') }} w
join {{ ref('int_characteristic_history') }} h
    on h.characteristic_id = w.characteristic_id
   and h.sample_time >= w.study_date and h.sample_time < w.window_end
join {{ ref('stg_erp__coils') }} c on c.coil_id = h.coil_id
where w.characteristic_class = 'formed'
  and h.implausible_readings = 0 and h.subgroup_mean is not null and not h.after_redesign
group by all
having count(*) >= 2
