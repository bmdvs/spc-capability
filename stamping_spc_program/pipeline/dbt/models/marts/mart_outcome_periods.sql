-- The periods of the outcome comparison. Grain: one row per press set, comparison and year. The pilot presses are
-- compared on March to December; the other presses on February to August (before the redesign reached them) and on
-- September to December (after it did).

select * from (values
    ('pilot presses', 'March to December', 2023, date '2023-03-01', date '2024-01-01', true),
    ('pilot presses', 'March to December', 2024, date '2024-03-01', date '2025-01-01', true),
    ('pilot presses', 'March to December', 2025, date '2025-03-01', date '2026-01-01', true),
    ('comparison presses', 'February to August', 2023, date '2023-02-01', date '2023-09-01', false),
    ('comparison presses', 'February to August', 2024, date '2024-02-01', date '2024-09-01', false),
    ('comparison presses', 'February to August', 2025, date '2025-02-01', date '2025-09-01', false),
    ('rollout presses', 'September to December', 2023, date '2023-09-01', date '2024-01-01', false),
    ('rollout presses', 'September to December', 2024, date '2024-09-01', date '2025-01-01', false),
    ('rollout presses', 'September to December', 2025, date '2025-09-01', date '2026-01-01', false)
) as t(press_set, months, period_year, period_start, period_end, is_pilot_press)
