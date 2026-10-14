-- The periods of the outcome comparison. Grain: one row per press set and year. The pilot presses and the other
-- presses, which the redesign has not reached in the record, are compared on April to June.

select * from (values
    ('pilot presses', 'April to June', 2024, date '2024-04-01', date '2024-07-01', true),
    ('pilot presses', 'April to June', 2025, date '2025-04-01', date '2025-07-01', true),
    ('pilot presses', 'April to June', 2026, date '2026-04-01', date '2026-07-01', true),
    ('comparison presses', 'April to June', 2024, date '2024-04-01', date '2024-07-01', false),
    ('comparison presses', 'April to June', 2025, date '2025-04-01', date '2025-07-01', false),
    ('comparison presses', 'April to June', 2026, date '2026-04-01', date '2026-07-01', false)
) as t(press_set, months, period_year, period_start, period_end, is_pilot_press)
