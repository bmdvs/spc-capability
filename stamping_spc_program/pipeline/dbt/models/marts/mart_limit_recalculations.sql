-- New limit sets issued in the record, by month, trigger and chart. Grain: one row per month, trigger and chart.

select
    issued_month,
    trigger,
    chart,
    count(*) as limit_sets,
    count(*) filter (where issued_in_quarter) as limit_sets_in_quarter,
    count(*) filter (where family_part) as family_limit_sets,
    count(distinct characteristic_id) as characteristics,
    {{ batch_id() }} as export_batch_id
from {{ ref('mart_limit_sets') }}
where issued_in_record
group by 1, 2, 3
order by 1, 2, 3
