-- The times at which parts were checked on each run: one row per run and distinct sample time, with what was
-- checked then. Grain: one row per run and check time.

select
    h.run_id,
    h.sample_time as check_time,
    count(*) as characteristics_checked,
    bool_or(h.subgroup_type = 'routine') as routine_check,
    bool_or(h.subgroup_type = 'first-piece') as first_piece_check,
    bool_or(h.subgroup_type = 'coil-change') as coil_change_check,
    bool_or(h.subgroup_type = 'last-piece') as last_piece_check,
    {{ batch_id() }} as export_batch_id
from {{ ref('int_characteristic_history') }} h
group by 1, 2
