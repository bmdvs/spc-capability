{{ config(materialized='table') }}

-- The production strokes of the run on each pilot press up to the time the SPC boards are drawn for, with each
-- channel's share of the total. Grain: one row per press and stroke.

select
    s.press_id, s.run_id, s.stroke_no, s.stroke_ts, s.total_kn,
    s.peak_kn_ch1 / s.total_kn as share_ch1, s.peak_kn_ch2 / s.total_kn as share_ch2, s.peak_kn_ch3 / s.total_kn as share_ch3, s.peak_kn_ch4 / s.total_kn as share_ch4,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_press_monitor__strokes') }} s
join {{ ref('mart_board_current_run') }} r using (run_id)
join {{ ref('stg_press_monitor__tonnage_windows') }} w using (run_id)
where s.stroke_ts >= w.run_start_monitor and s.stroke_ts <= r.board_as_at
