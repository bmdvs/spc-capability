{{ config(materialized='table') }}

-- The production strokes of the run shown on the PR-03 SPC terminal and press monitor screens, up to the time the
-- screens are drawn for, with each channel's peak and its share of the total. Grain: one row per stroke.

{% set screen_run = 'R26-00820' %}
{% set screen_as_at = '2026-05-13 12:04:00' %}

select
    s.press_id, s.run_id, s.stroke_no, s.stroke_ts, s.total_kn, s.strokes_per_minute,
    s.peak_kn_ch1, s.peak_kn_ch2, s.peak_kn_ch3, s.peak_kn_ch4,
    s.peak_kn_ch1 / s.total_kn as share_ch1, s.peak_kn_ch2 / s.total_kn as share_ch2, s.peak_kn_ch3 / s.total_kn as share_ch3, s.peak_kn_ch4 / s.total_kn as share_ch4,
    cast('{{ screen_as_at }}' as timestamp) as screen_as_at,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_press_monitor__strokes') }} s
join {{ ref('stg_press_monitor__tonnage_windows') }} w using (run_id)
where s.run_id = '{{ screen_run }}' and s.stroke_ts >= w.run_start_monitor and s.stroke_ts <= cast('{{ screen_as_at }}' as timestamp)
