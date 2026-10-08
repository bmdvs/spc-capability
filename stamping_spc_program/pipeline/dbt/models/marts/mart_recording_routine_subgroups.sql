-- Routine subgroups with the time each carries, for the recording analysis. Grain: one row per routine subgroup.
-- The stamped time is the time the entry method puts on the subgroup: the entry time on keyed and gauge-connected
-- subgroups, the time noted on the chart form on paper (the entry time there is the transcription).

select
    h.subgroup_id, h.run_id, h.characteristic_id, h.press_id, h.press_group, h.is_pilot_press, h.after_redesign, h.entry_method, h.data_type,
    h.frequency_minutes, h.operator_id, e.shift as operator_shift, h.sample_time, h.recorded_at,
    case when h.entry_method = 'paper transcription' then h.sample_time else h.recorded_at end as stamped_time,
    case when h.entry_method = 'paper transcription' then null else h.minutes_to_entry end as minutes_to_entry,
    year(h.sample_time) as sample_year,
    {{ batch_id() }} as export_batch_id
from {{ ref('int_characteristic_history') }} h
left join {{ ref('stg_erp__employees') }} e on e.employee_id = h.operator_id
where h.subgroup_type = 'routine'
