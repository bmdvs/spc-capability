-- Sorting events and alarm signals by press and month for the dashboard. Grain: one row per press and month.

with months as (
    select p.press_id, p.press_group, p.is_pilot_press, unnest(range(date '2024-01-01', date '2026-07-01', interval 1 month))::date as month_start
    from {{ ref('int_press_redesign') }} p
),

sorting as (
    select press_id, date_trunc('month', sort_started)::date as month_start, count(*) as sorting_events, sum(quantity_sorted) as quantity_sorted
    from {{ ref('mart_sorting_events') }} group by 1, 2
),

signals as (
    select press_id, date_trunc('month', sample_time)::date as month_start, count(*) as variable_subgroups, count(*) filter (where alarm_raised) as alarm_signals,
           count(*) filter (where alarm_raised and (acknowledgement_text is not null or adjustment_recorded)) as signals_with_an_action_recorded
    from {{ ref('int_characteristic_history') }} where data_type = 'variable' and subgroup_mean is not null group by 1, 2
)

select
    m.press_id, m.press_group, m.is_pilot_press, m.month_start, strftime(m.month_start, '%Y-%m') as period,
    coalesce(s.sorting_events, 0) as sorting_events, coalesce(s.quantity_sorted, 0) as quantity_sorted,
    g.variable_subgroups, g.alarm_signals, g.signals_with_an_action_recorded,
    {{ batch_id() }} as export_batch_id
from months m
left join sorting s using (press_id, month_start)
left join signals g using (press_id, month_start)
