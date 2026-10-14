-- Press monitor export: peak force per channel on every stroke, pilot presses from 1 April 2026. One row per press and stroke.
-- Read in place from the Parquet export, one file per press and month.

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
