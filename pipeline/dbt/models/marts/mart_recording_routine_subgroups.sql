-- Routine subgroups with the time from the parts to the entry, for the recording analysis. Grain: one row per routine
-- subgroup in the record.

select
    h.subgroup_id, h.run_id, h.characteristic_id, h.press_id, h.press_group, h.entry_method, h.data_type,
    h.frequency_minutes, h.operator_id, e.shift as operator_shift, h.sample_time, h.recorded_at, h.minutes_to_entry,
    h.minutes_to_entry > {{ var('late_entry_minutes') }} as late_entry,
    case when hour(h.sample_time) * 60 + minute(h.sample_time) < {{ var('shift_change_minute') }} then 'days' else 'nights' end as shift,
    h.in_quarter,
    {{ batch_id() }} as export_batch_id
from {{ ref('int_characteristic_history') }} h
left join {{ ref('stg_erp__employees') }} e on e.employee_id = h.operator_id
where h.subgroup_type = 'routine' and h.in_record
