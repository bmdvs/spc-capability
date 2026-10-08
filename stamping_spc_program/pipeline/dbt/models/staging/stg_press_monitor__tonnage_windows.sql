-- Press monitor export: tonnage windows, typed. One row per export row.

select
    nullif(trim(press_id), '') as press_id,
    nullif(trim(run_id), '') as run_id,
    cast(nullif(trim(set_at), '') as timestamp) as set_at,
    nullif(trim(set_by), '') as set_by,
    cast(nullif(trim(total_high_kn), '') as bigint) as total_high_kn,
    cast(nullif(trim(total_low_kn), '') as bigint) as total_low_kn,
    cast(nullif(trim(ch1_high_kn), '') as bigint) as ch1_high_kn,
    cast(nullif(trim(ch1_low_kn), '') as bigint) as ch1_low_kn,
    cast(nullif(trim(ch2_high_kn), '') as bigint) as ch2_high_kn,
    cast(nullif(trim(ch2_low_kn), '') as bigint) as ch2_low_kn,
    cast(nullif(trim(ch3_high_kn), '') as double) as ch3_high_kn,
    cast(nullif(trim(ch3_low_kn), '') as double) as ch3_low_kn,
    cast(nullif(trim(ch4_high_kn), '') as double) as ch4_high_kn,
    cast(nullif(trim(ch4_low_kn), '') as double) as ch4_low_kn,
    cast(nullif(trim(run_start_monitor), '') as timestamp) as run_start_monitor,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'press_monitor__tonnage_windows') }}
