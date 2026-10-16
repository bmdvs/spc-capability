-- Production runs with the press, the die's sharpening interval and the shots on the die since the sharpening at the
-- start of the run. Grain: one row per production run. A run belongs to the interval of the last sharpening or rebuild
-- dated on or before the day the run started; runs before the die's first logged sharpening carry interval 0 and no
-- shot count since sharpening, because the start of that interval lies outside the export.

with runs as (

    select r.*, cast(r.actual_start as date) as start_date
    from {{ ref('stg_erp__production_runs') }} r

),

placed as (

    select
        r.run_id,
        coalesce(max(i.sharpening_interval_no), 0) as sharpening_interval_no,
        max(i.interval_start) as interval_start
    from runs r
    left join {{ ref('int_sharpening_intervals') }} i
        on i.die_id = r.die_id and i.interval_start <= r.start_date
    group by 1

)

select
    r.run_id, r.part_id, r.die_id, r.press_id, pr.press_group, r.operator_shift_1, r.operator_shift_2,
    r.scheduled_start, r.actual_start, r.production_start, r.actual_end,
    r.quantity_ordered, r.quantity_produced, r.quantity_scrapped, r.strokes, r.run_speed_spm, r.coils_consumed, r.status,
    len(string_split(r.coils_consumed, ';')) as coils_on_run,
    d.parts_per_stroke,
    p.sharpening_interval_no,
    p.interval_start as sharpening_date,
    case when p.sharpening_interval_no > 0 then
        coalesce(sum(r.strokes) over (partition by r.die_id, p.sharpening_interval_no order by r.actual_start, r.run_id rows between unbounded preceding and 1 preceding), 0)
    end as shots_since_sharpening_at_start,
    {{ batch_id() }} as export_batch_id
from runs r
join placed p on p.run_id = r.run_id
left join {{ ref('stg_erp__dies') }} d on d.die_id = r.die_id
left join {{ ref('stg_erp__presses') }} pr on pr.press_id = r.press_id
order by r.run_id
