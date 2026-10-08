-- The press monitor clock against the SPC terminal clock, by run: the monitor's run start less the start of production
-- on the terminal. Grain: one row per production run with a tonnage window record.

select
    w.run_id,
    w.press_id,
    r.production_start as run_start_terminal,
    w.run_start_monitor,
    date_diff('second', r.production_start, w.run_start_monitor) as monitor_offset_seconds,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_press_monitor__tonnage_windows') }} w
join {{ ref('stg_erp__production_runs') }} r on r.run_id = w.run_id
