-- Sorting events with their trace, the quantity sorted against the parts at risk, and the hours and cost as booked
-- and as estimated. Grain: one row per sorting event. Where in-house sorting carries no hours on the sorting labor
-- code, the estimate is the run's labor hours above standard; it is costed at the rate the booked in-house events
-- carry.

with t as (

    select * from {{ ref('int_sorting_event_trace') }}

),

rate as (

    select sum(sorting_cost_booked) / sum(sorting_hours_booked) as in_house_rate
    from t where sorted_at = 'in-house' and sorting_hours_booked is not null

)

select
    t.*,
    year(t.sort_started) as sort_year,
    t.quantity_sorted / nullif(t.parts_from_check_before_to_finding, 0) as sorted_over_parts_at_risk,
    t.quantity_affected / nullif(t.parts_from_check_before_to_finding, 0) as nonconformance_quantity_over_parts_since_the_check_before,
    (t.sorting_hours_booked is not null) as booked_to_the_sorting_labor_code,
    case when t.sorting_hours_booked is null and t.sorted_at = 'in-house' then greatest(t.run_hours_above_standard, 0) end as sorting_hours_estimated_from_run_hours,
    coalesce(t.sorting_hours_booked, case when t.sorted_at = 'in-house' then greatest(t.run_hours_above_standard, 0) end) as sorting_hours_booked_or_estimated,
    coalesce(t.sorting_cost_booked, case when t.sorted_at = 'in-house' then greatest(t.run_hours_above_standard, 0) * r.in_house_rate end) as sorting_cost_booked_or_estimated,
    r.in_house_rate
from t cross join rate r
order by t.sort_started
