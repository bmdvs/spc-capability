-- Subgroups recorded on a gauge away for calibration or past its due date, by press and month. Grain: one row per
-- press and month.

select
    press_id,
    any_value(press_group) as press_group,
    strftime(sample_time, '%Y-%m') as sample_month,
    bool_or(in_quarter) as in_quarter,
    count(*) as subgroups,
    count(*) filter (where gauge_out_of_service) as subgroups_on_gauge_away,
    count(*) filter (where gauge_past_due) as subgroups_on_gauge_past_due,
    {{ batch_id() }} as export_batch_id
from {{ ref('int_characteristic_history') }}
where in_record
group by press_id, strftime(sample_time, '%Y-%m')
