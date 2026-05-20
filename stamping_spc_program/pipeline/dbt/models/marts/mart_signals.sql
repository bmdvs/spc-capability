-- Every alarm raised in the record with its disposition, cause and times to acknowledge and close, and whether it fell
-- in a sharpening interval in which the chart carried an assignable cause. Grain: one row per alarm.

with special as (

    select distinct characteristic_id, die_id, sharpening_interval_no
    from {{ ref('int_alarm_dispositions') }}
    where assignable_cause

)

select
    a.*,
    s.characteristic_id is not null as interval_with_assignable_cause,
    strftime(a.raised_at, '%Y-%m') as raised_month
from {{ ref('int_alarm_dispositions') }} a
left join special s on s.characteristic_id = a.characteristic_id and s.die_id = a.die_id and s.sharpening_interval_no = a.sharpening_interval_no
where a.in_record
