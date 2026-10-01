-- Press monitor export: peak force per channel on every stroke the historian keeps (April to June 2026 on every press,
-- July 2025 to June 2026 on PR-03). One row per press and stroke. Read in place from the Parquet export, one file per press and month.

select
    press_id,
    run_id,
    stroke_no,
    stroke_ts,
    peak_kn_ch1,
    peak_kn_ch2,
    peak_kn_ch3,
    peak_kn_ch4,
    total_kn,
    strokes_per_minute
from read_parquet('{{ var("raw_dir") }}/press_monitor/strokes/*/*.parquet')
