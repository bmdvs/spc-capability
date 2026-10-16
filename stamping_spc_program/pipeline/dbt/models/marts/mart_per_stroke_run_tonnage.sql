-- Per-stroke tonnage by run, on the runs whose strokes the historian keeps. Grain: one row per run. Production strokes
-- are those from the monitor's run start; strokes before it are setup and try-out. The lag-1 autocorrelation is of the
-- total peak force on consecutive production strokes; the first {{ var('tonnage_baseline_strokes') }} production strokes are the baseline the per-stroke
-- charts are set on; the largest standard deviation of a channel's share of the total over the baseline is given beside it.

with s as (

    select s.run_id, s.press_id, s.stroke_no, s.total_kn, s.stroke_ts >= w.run_start_monitor as production_stroke,
           s.peak_kn_ch1 / s.total_kn as share_ch1, s.peak_kn_ch2 / s.total_kn as share_ch2, s.peak_kn_ch3 / s.total_kn as share_ch3, s.peak_kn_ch4 / s.total_kn as share_ch4
    from {{ ref('stg_press_monitor__strokes') }} s
    join {{ ref('stg_press_monitor__tonnage_windows') }} w using (run_id)

),

p as (

    select run_id, press_id, stroke_no, total_kn, share_ch1, share_ch2, share_ch3, share_ch4,
           row_number() over (partition by run_id order by stroke_no) as production_stroke_no,
           lag(total_kn) over (partition by run_id order by stroke_no) as previous_total_kn
    from s
    where production_stroke

),

a as (

    select run_id, min(press_id) as press_id, count(*) as production_strokes,
           avg(total_kn) as total_kn_mean, stddev_samp(total_kn) as total_kn_sd,
           corr(total_kn, previous_total_kn) as lag_1_autocorrelation,
           avg(total_kn) filter (where production_stroke_no <= {{ var('tonnage_baseline_strokes') }}) as baseline_total_kn_mean,
           stddev_samp(total_kn) filter (where production_stroke_no <= {{ var('tonnage_baseline_strokes') }}) as baseline_total_kn_sd,
           corr(total_kn, previous_total_kn) filter (where production_stroke_no between 2 and {{ var('tonnage_baseline_strokes') }}) as baseline_lag_1_autocorrelation,
           greatest(stddev_samp(share_ch1) filter (where production_stroke_no <= {{ var('tonnage_baseline_strokes') }}),
                    coalesce(stddev_samp(share_ch2) filter (where production_stroke_no <= {{ var('tonnage_baseline_strokes') }}), 0),
                    coalesce(stddev_samp(share_ch3) filter (where production_stroke_no <= {{ var('tonnage_baseline_strokes') }}), 0),
                    coalesce(stddev_samp(share_ch4) filter (where production_stroke_no <= {{ var('tonnage_baseline_strokes') }}), 0)) as baseline_largest_channel_share_sd
    from p
    group by 1

),

setup as (

    select run_id, count(*) filter (where not production_stroke) as setup_strokes from s group by 1

),

stops as (

    select run_id, count(*) as per_stroke_stops
    from {{ ref('stg_press_monitor__fault_events') }}
    where input like '%signal'
    group by 1

)

select
    a.*, setup.setup_strokes, coalesce(stops.per_stroke_stops, 0) as per_stroke_stops,
    r.part_id, r.die_id, r.press_group, r.parts_per_stroke, r.run_speed_spm, r.production_start,
    cast(r.production_start as date) >= cast('{{ var("quarter_start") }}' as date) as in_quarter,
    {{ batch_id() }} as export_batch_id
from a
join setup using (run_id)
left join stops using (run_id)
left join {{ ref('int_run_shots') }} r using (run_id)
