-- ERP export: presses, typed. One row per export row.

select
    nullif(trim(press_id), '') as press_id,
    cast(nullif(trim(tonnage), '') as bigint) as tonnage,
    nullif(trim(bed_size_mm), '') as bed_size_mm,
    cast(nullif(trim(speed_min_spm), '') as bigint) as speed_min_spm,
    cast(nullif(trim(speed_max_spm), '') as bigint) as speed_max_spm,
    cast(nullif(trim(load_cell_channels), '') as bigint) as load_cell_channels,
    nullif(trim(press_group), '') as press_group,
    nullif(trim(shift_pattern), '') as shift_pattern,
    nullif(trim(spc_entry_at_install), '') as spc_entry_at_install,
    cast(nullif(trim(spc_software_from), '') as date) as spc_software_from,
    nullif(trim(tonnage_monitor), '') as tonnage_monitor,
    nullif(trim(status), '') as status,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'erp__presses') }}
