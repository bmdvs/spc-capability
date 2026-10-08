{{ config(materialized='table') }}

-- Strokes by press and month on the presses whose monitor keeps per-minute summaries. Grain: one row per press and month.

select
    press_id, date_trunc('month', minute_start) as month_start, sum(stroke_count) as stroke_count, count(*) as minutes,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_press_monitor__stroke_minutes') }}
group by 1, 2
