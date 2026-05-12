-- Outcome counts by press set and period. Grain: one row per press set, comparison and year. A complaint and a
-- shipment belong to the press of their run (the first run where a complaint names several); complaints are counted on
-- the date received and shipments on the ship date. Scrap and rework are the accounting lines booked to the press in
-- the months of the period; revenue is the quantity produced on runs ended in the period at the part's price for the year.

with p as (select * from {{ ref('mart_outcome_periods') }}),

presses as (select press_id, is_pilot_press from {{ ref('int_press_redesign') }}),

runs as (
    select r.run_id, r.press_id, r.part_id, r.actual_end, r.quantity_produced, r.quantity_scrapped, x.is_pilot_press,
           r.quantity_produced * c.price as revenue
    from {{ ref('int_run_shots') }} r
    join presses x using (press_id)
    left join {{ ref('stg_accounting__contribution') }} c
        on c.part_id = r.part_id and c.year = least(greatest(year(r.production_start), 2024), 2026)
),

sorting as (
    select p.press_set, p.period_year, count(*) as sorting_events, median(s.quantity_sorted) as quantity_sorted_median, sum(s.quantity_sorted) as quantity_sorted,
           max(s.quantity_sorted) as quantity_sorted_largest, sum(s.sorting_cost_booked) as sorting_cost_booked, sum(s.sorting_cost_booked_or_estimated) as sorting_cost_booked_or_estimated
    from p join {{ ref('mart_sorting_events') }} s
        on s.is_pilot_press = p.is_pilot_press and s.sort_started >= p.period_start and s.sort_started < p.period_end
    group by 1, 2
),

complaints as (
    select press_set, period_year, count(*) filter (where not duplicate_entry) as complaints, sum(quantity) filter (where not duplicate_entry) as pieces_rejected,
           count(*) filter (where duplicate_entry) as duplicate_complaint_entries,
           sum(charge_back) filter (where not duplicate_entry) as charge_backs, sum(premium_freight) filter (where not duplicate_entry) as premium_freight
    from {{ ref('mart_outcome_complaints') }}
    group by 1, 2
),

shipments as (
    select p.press_set, p.period_year, sum(s.quantity) as pieces_shipped
    from p join {{ ref('stg_erp__shipments') }} s on s.ship_date >= p.period_start and s.ship_date < p.period_end
    join runs r on r.run_id = s.run_id and r.is_pilot_press = p.is_pilot_press
    group by 1, 2
),

production as (
    select p.press_set, p.period_year, count(*) as runs_ended, sum(r.quantity_produced) as pieces_produced, sum(r.quantity_scrapped) as pieces_scrapped, sum(r.revenue) as revenue
    from p join runs r on r.is_pilot_press = p.is_pilot_press and r.actual_end >= p.period_start and r.actual_end < p.period_end
    group by 1, 2
),

lines as (
    select l.category, l.amount, cast(l.period || '-01' as date) as month_start, regexp_extract(l.source_record, 'PR-[0-9]{2}') as press_id
    from {{ ref('stg_accounting__quality_cost_lines') }} l
    where l.category in ('scrap', 'rework labor')
),

booked as (
    select p.press_set, p.period_year, sum(l.amount) filter (where l.category = 'scrap') as scrap_booked, sum(l.amount) filter (where l.category = 'rework labor') as rework_labor_booked
    from p join lines l on l.month_start >= p.period_start and l.month_start < p.period_end
    join presses x on x.press_id = l.press_id and x.is_pilot_press = p.is_pilot_press
    group by 1, 2
),

signals as (
    select p.press_set, p.period_year, count(*) as variable_subgroups, count(*) filter (where h.alarm_raised) as alarm_signals,
           count(*) filter (where h.alarm_rule_1) as rule_1_signals,
           count(*) filter (where h.alarm_raised and (h.acknowledgement_text is not null or h.adjustment_recorded)) as signals_with_an_action_recorded
    from p join {{ ref('int_characteristic_history') }} h
        on h.is_pilot_press = p.is_pilot_press and h.sample_time >= p.period_start and h.sample_time < p.period_end
    where h.data_type = 'variable' and h.subgroup_mean is not null
    group by 1, 2
),

burr as (
    select p.press_set, p.period_year, count(*) filter (where n.detected_at = 'press check') as burr_nonconformances_at_the_press_check,
           count(*) filter (where n.detected_at = 'dock audit') as burr_nonconformances_at_the_dock_audit,
           count(*) filter (where n.detected_at = 'customer') as burr_nonconformances_at_the_customer
    from p join {{ ref('mart_burr_nonconformances') }} n on n.opened >= p.period_start and n.opened < p.period_end and n.defect_code = 'burr'
    join presses x on x.press_id = n.press_id and x.is_pilot_press = p.is_pilot_press
    group by 1, 2
)

select
    p.press_set, p.months, p.period_year, p.period_start, p.period_end,
    coalesce(sorting.sorting_events, 0) as sorting_events, sorting.quantity_sorted_median, coalesce(sorting.quantity_sorted, 0) as quantity_sorted, sorting.quantity_sorted_largest,
    coalesce(sorting.sorting_cost_booked, 0) as sorting_cost_booked, coalesce(sorting.sorting_cost_booked_or_estimated, 0) as sorting_cost_booked_or_estimated,
    coalesce(complaints.complaints, 0) as complaints, coalesce(complaints.pieces_rejected, 0) as pieces_rejected, coalesce(complaints.duplicate_complaint_entries, 0) as duplicate_complaint_entries, shipments.pieces_shipped,
    coalesce(complaints.charge_backs, 0) as charge_backs, coalesce(complaints.premium_freight, 0) as premium_freight,
    production.runs_ended, production.pieces_produced, production.pieces_scrapped, production.revenue, booked.scrap_booked, booked.rework_labor_booked,
    signals.variable_subgroups, signals.alarm_signals, signals.rule_1_signals, signals.signals_with_an_action_recorded,
    coalesce(burr.burr_nonconformances_at_the_press_check, 0) as burr_nonconformances_at_the_press_check,
    coalesce(burr.burr_nonconformances_at_the_dock_audit, 0) as burr_nonconformances_at_the_dock_audit,
    coalesce(burr.burr_nonconformances_at_the_customer, 0) as burr_nonconformances_at_the_customer,
    {{ batch_id() }} as export_batch_id
from p
left join sorting using (press_set, period_year)
left join complaints using (press_set, period_year)
left join shipments using (press_set, period_year)
left join production using (press_set, period_year)
left join booked using (press_set, period_year)
left join signals using (press_set, period_year)
left join burr using (press_set, period_year)
order by 1, 3
