-- Press monitor export: the historian's per-minute summaries on the rollout presses from 2 September 2025. One row per press and minute.
-- Read in place from the Parquet export, one file per press.

select
    press_id,
    run_id,
    cast("minute" as timestamp) as minute_start,
    stroke_count,
    mean_total_kn,
    max_total_kn,
    min_total_kn,
    mean_kn_ch1,
    mean_kn_ch2,
    mean_kn_ch3,
    mean_kn_ch4,
    strokes_per_minute,
    export_batch_id
from read_parquet('{{ var("raw_dir") }}/press_monitor/stroke_minutes/*.parquet')
