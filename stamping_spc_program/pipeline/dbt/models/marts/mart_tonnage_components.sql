-- Per-stroke tonnage components by run, on the runs whose strokes the historian keeps. Grain: one row per run. Each
-- production stroke's total is taken as a share of its part's mean over every kept run, less one, so runs of different
-- parts sit on one scale. The sums of squares split exactly: between runs (the run's mean level about its part's mean),
-- wear within the run (the regression of the total on production strokes since the run start) and stroke to stroke (the
-- rest). Shares are the sums over runs divided by the total sum of squares. A run needs two production strokes to have
-- a spread within it.

with s as (

    select s.run_id, s.press_id, s.stroke_no, s.total_kn, r.part_id
    from {{ ref('stg_press_monitor__strokes') }} s
    join {{ ref('stg_press_monitor__tonnage_windows') }} w using (run_id)
    join {{ ref('stg_erp__production_runs') }} r using (run_id)
    where s.stroke_ts >= w.run_start_monitor

),

p as (

    select *, row_number() over (partition by run_id order by stroke_no) as production_stroke_no, count(*) over (partition by run_id) as run_strokes from s
    qualify run_strokes >= 2

),

part_mean as (

    select part_id, avg(total_kn) as part_total_kn_mean from p group by 1

),

y as (

    select p.run_id, p.press_id, p.part_id, p.production_stroke_no, p.total_kn / m.part_total_kn_mean - 1 as y
    from p join part_mean m using (part_id)

),

r as (

    select run_id, min(press_id) as press_id, min(part_id) as part_id, count(*) as production_strokes,
           avg(y) as y_mean, sum(y * y) as ss_total, var_pop(y) * count(*) as ss_within_run,
           coalesce(regr_slope(y, production_stroke_no), 0) as slope, coalesce(regr_sxx(y, production_stroke_no), 0) as sxx
    from y group by 1

)

select r.run_id, r.press_id, r.part_id, r.production_strokes,
       1 + r.y_mean as run_mean_share_of_part_mean,
       r.ss_total,
       r.production_strokes * r.y_mean * r.y_mean as ss_between_runs,
       r.slope * r.slope * r.sxx as ss_wear_within_run,
       r.ss_within_run - r.slope * r.slope * r.sxx as ss_stroke_to_stroke,
       {{ batch_id() }} as export_batch_id
from r
order by r.run_id
