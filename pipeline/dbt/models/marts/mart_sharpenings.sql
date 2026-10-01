-- Sharpenings in the record against the die's due count: the logged shots over the interval the sharpening closes
-- (on the corrected counts), the share of the due count, the reason logged with a late sharpening, and the burr
-- height reached on the lab gauge in the interval as a share of its limit. Grain: one row per sharpening that closes
-- an interval with a logged start.

with burr as (

    select die_id, sharpening_interval_no, max(share_of_limit) as burr_peak_share_of_limit, count(*) as burr_subgroups
    from {{ ref('mart_wear_points') }}
    where characteristic_type = 'burr height'
    group by 1, 2

),

die_press as (

    select die_id, min(primary_press) as press_id from {{ ref('stg_erp__parts') }} group by 1

)

select
    i.die_id, dp.press_id, pr.press_group,
    i.sharpening_interval_no, i.interval_start, i.interval_end as sharpened_on, i.started_by, i.shots_in_interval_logged, i.is_run_interval,
    d.sharpening_due_count,
    i.shots_in_interval_logged / d.sharpening_due_count as share_of_due_count,
    i.shots_in_interval_logged > d.sharpening_due_count as late,
    case when i.shots_in_interval_logged > d.sharpening_due_count then i.notes_at_end end as late_reason,
    e.shot_count_corrected,
    b.burr_peak_share_of_limit, b.burr_subgroups,
    coalesce(b.burr_peak_share_of_limit > 1, false) as burr_over_limit,
    i.interval_end >= cast('{{ var("quarter_start") }}' as date) as in_quarter,
    {{ batch_id() }} as export_batch_id
from {{ ref('int_sharpening_intervals') }} i
join {{ ref('stg_erp__dies') }} d using (die_id)
left join die_press dp using (die_id)
left join {{ ref('stg_erp__presses') }} pr on pr.press_id = dp.press_id
left join {{ ref('int_die_event_timeline') }} e on e.die_id = i.die_id and e.sharpening_interval_no = i.sharpening_interval_no + 1 and e.starts_interval
left join burr b on b.die_id = i.die_id and b.sharpening_interval_no = i.sharpening_interval_no
where i.ended_by = 'sharpening' and i.interval_end between cast('{{ var("record_start") }}' as date) and cast('{{ var("record_end") }}' as date)
