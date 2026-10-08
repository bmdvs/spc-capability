-- First-piece parts measured on both systems: the CMM readings in the die log against the check fixture readings of
-- the same five parts in the SPC record. Grain: one row per first-piece approval with a matched subgroup.

select
    e.die_event_id,
    e."date" as event_date,
    e.die_id,
    e.cmm_characteristic_id as characteristic_id,
    c."type" as characteristic_type,
    c.critical,
    h.gauge_id,
    h.press_id,
    h.entry_method,
    h.after_redesign,
    (e.cmm_r1 + e.cmm_r2 + e.cmm_r3 + e.cmm_r4 + e.cmm_r5) / 5 as cmm_mean,
    (h.r1 + h.r2 + h.r3 + h.r4 + h.r5) / 5 as fixture_mean,
    (h.r1 + h.r2 + h.r3 + h.r4 + h.r5) / 5 - (e.cmm_r1 + e.cmm_r2 + e.cmm_r3 + e.cmm_r4 + e.cmm_r5) / 5 as fixture_less_cmm,
    h.implausible_readings,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_die_room__die_events') }} e
join {{ ref('int_characteristic_history') }} h on h.subgroup_id = e.cmm_subgroup_id
join {{ ref('stg_spc__characteristics') }} c on c.characteristic_id = e.cmm_characteristic_id
where e.cmm_subgroup_id is not null and h.r1 is not null
