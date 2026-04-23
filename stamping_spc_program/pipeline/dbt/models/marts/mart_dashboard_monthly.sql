-- The plant by month for the dashboard. Grain: one row per month of the record. Complaints are counted on the date
-- received and shipments on the ship date; scrap and rework are the accounting lines of the month; revenue is the
-- quantity produced on runs ended in the month at the part's price for the year.

with months as (

    select unnest(range(date '2023-01-01', date '2026-01-01', interval 1 month))::date as month_start

),

complaints as (
    select month_start::date as month_start, count(*) as complaints, sum(quantity) as pieces_rejected
    from {{ ref('mart_dashboard_complaints') }} where not duplicate_entry group by 1
),

shipments as (
    select date_trunc('month', ship_date)::date as month_start, sum(quantity) as pieces_shipped from {{ ref('stg_erp__shipments') }} group by 1
),

sorting as (
    select date_trunc('month', sort_started)::date as month_start, count(*) as sorting_events, sum(quantity_sorted) as quantity_sorted, sum(sorting_cost_booked_or_estimated) as sorting_cost_booked_or_estimated
    from {{ ref('mart_sorting_events') }} group by 1
),

booked as (
    select month_start::date as month_start, sum(amount) filter (where category = 'scrap') as scrap_booked, sum(amount) filter (where category = 'rework labor') as rework_labor_booked
    from {{ ref('mart_outcome_cost_lines') }} group by 1
),

revenue as (
    select date_trunc('month', r.actual_end)::date as month_start, sum(r.quantity_produced * c.price) as revenue, sum(r.quantity_produced) as pieces_produced, sum(r.quantity_scrapped) as pieces_scrapped
    from {{ ref('int_run_shots') }} r
    left join {{ ref('stg_accounting__contribution') }} c on c.part_id = r.part_id and c.year = least(greatest(year(r.production_start), 2023), 2025)
    where r.actual_end is not null group by 1
),

signals as (
    select date_trunc('month', sample_time)::date as month_start, count(*) as variable_subgroups, count(*) filter (where alarm_raised) as alarm_signals,
           count(*) filter (where alarm_raised and (acknowledgement_text is not null or adjustment_recorded)) as signals_with_an_action_recorded
    from {{ ref('int_characteristic_history') }} where data_type = 'variable' and subgroup_mean is not null group by 1
),

burr as (
    select date_trunc('month', opened)::date as month_start, count(*) as burr_nonconformances from {{ ref('mart_burr_nonconformances') }} where defect_code = 'burr' group by 1
)

select
    m.month_start, strftime(m.month_start, '%Y-%m') as period,
    coalesce(c.complaints, 0) as complaints, coalesce(c.pieces_rejected, 0) as pieces_rejected, s.pieces_shipped,
    coalesce(o.sorting_events, 0) as sorting_events, coalesce(o.quantity_sorted, 0) as quantity_sorted, coalesce(o.sorting_cost_booked_or_estimated, 0) as sorting_cost_booked_or_estimated,
    b.scrap_booked, b.rework_labor_booked, r.revenue, r.pieces_produced, r.pieces_scrapped,
    g.variable_subgroups, g.alarm_signals, g.signals_with_an_action_recorded,
    coalesce(u.burr_nonconformances, 0) as burr_nonconformances,
    {{ batch_id() }} as export_batch_id
from months m
left join complaints c using (month_start)
left join shipments s using (month_start)
left join sorting o using (month_start)
left join booked b using (month_start)
left join revenue r using (month_start)
left join signals g using (month_start)
left join burr u using (month_start)
order by 1
