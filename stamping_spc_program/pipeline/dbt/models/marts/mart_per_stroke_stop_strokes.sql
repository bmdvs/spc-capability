{{ config(materialized='table') }}

-- The strokes before each stop by the per-stroke charts: the {{ var('stop_lookback_strokes') }} strokes up to and including the stop, with each
-- channel's share of the total. Grain: one row per stop and stroke. strokes_before_the_stop is 0 on the stroke of the stop.

select
    t.fault_event_id, s.run_id, s.press_id, s.stroke_no, t.stop_stroke_no - s.stroke_no as strokes_before_the_stop,
    s.total_kn, s.peak_kn_ch1, s.peak_kn_ch2, s.peak_kn_ch3, s.peak_kn_ch4,
    s.peak_kn_ch1 / s.total_kn as share_ch1, s.peak_kn_ch2 / s.total_kn as share_ch2, s.peak_kn_ch3 / s.total_kn as share_ch3, s.peak_kn_ch4 / s.total_kn as share_ch4,
    {{ batch_id() }} as export_batch_id
from {{ ref('mart_per_stroke_stops') }} t
join {{ ref('stg_press_monitor__strokes') }} s
    on s.run_id = t.run_id and s.stroke_no between t.stop_stroke_no - {{ var('stop_lookback_strokes') }} and t.stop_stroke_no
