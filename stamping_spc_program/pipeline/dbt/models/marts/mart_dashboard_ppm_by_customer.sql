-- Customer PPM by month, with the customer's scorecard figure beside where the customer issues one. Grain: one row per
-- customer and month with a shipment. A quarterly scorecard figure is carried on each month of its quarter.

with shipped as (
    select customer_id, date_trunc('month', ship_date)::date as month_start, sum(quantity) as pieces_shipped from {{ ref('stg_erp__shipments') }} group by 1, 2
),

rejected as (
    select customer_id, month_start::date as month_start, count(*) as complaints, sum(quantity) as pieces_rejected
    from {{ ref('mart_dashboard_complaints') }} where not duplicate_entry group by 1, 2
),

cards as (
    select customer_id, period, ppm as scorecard_ppm from {{ ref('stg_qms__scorecards') }}
)

select
    s.customer_id, k.program, k.scorecard_frequency, k.ppm_target, s.month_start, strftime(s.month_start, '%Y-%m') as period,
    s.pieces_shipped, coalesce(r.complaints, 0) as complaints, coalesce(r.pieces_rejected, 0) as pieces_rejected,
    coalesce(m.scorecard_ppm, q.scorecard_ppm) as scorecard_ppm,
    {{ batch_id() }} as export_batch_id
from shipped s
join {{ ref('stg_erp__customers') }} k using (customer_id)
left join rejected r using (customer_id, month_start)
left join cards m on m.customer_id = s.customer_id and m.period = strftime(s.month_start, '%Y-%m')
left join cards q on q.customer_id = s.customer_id and q.period = strftime(s.month_start, '%Y') || 'Q' || cast(quarter(s.month_start) as varchar)
where s.month_start >= date '2024-01-01' and s.month_start < date '2026-07-01'
