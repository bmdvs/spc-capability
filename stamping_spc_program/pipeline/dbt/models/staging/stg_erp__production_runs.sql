-- ERP export: production runs, typed. One row per export row.

select
    nullif(trim(run_id), '') as run_id,
    nullif(trim(part_id), '') as part_id,
    nullif(trim(revision), '') as revision,
    nullif(trim(die_id), '') as die_id,
    nullif(trim(press_id), '') as press_id,
    nullif(trim(operator_shift_1), '') as operator_shift_1,
    nullif(trim(operator_shift_2), '') as operator_shift_2,
    cast(nullif(trim(scheduled_start), '') as timestamp) as scheduled_start,
    cast(nullif(trim(actual_start), '') as timestamp) as actual_start,
    cast(nullif(trim(production_start), '') as timestamp) as production_start,
    cast(nullif(trim(actual_end), '') as timestamp) as actual_end,
    cast(nullif(trim(quantity_ordered), '') as double) as quantity_ordered,
    cast(nullif(trim(quantity_produced), '') as bigint) as quantity_produced,
    cast(nullif(trim(quantity_scrapped), '') as bigint) as quantity_scrapped,
    nullif(trim(coils_consumed), '') as coils_consumed,
    cast(nullif(trim(strokes), '') as bigint) as strokes,
    cast(nullif(trim(run_speed_spm), '') as bigint) as run_speed_spm,
    cast(nullif(trim(standard_hours), '') as double) as standard_hours,
    cast(nullif(trim(labor_hours), '') as double) as labor_hours,
    nullif(trim(status), '') as status,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'erp__production_runs') }}
