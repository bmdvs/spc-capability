-- The chart design parameters the program runs on, as the quality engineering design file states them. Grain: one row
-- per parameter.

select
    parameter,
    value,
    unit,
    description,
    {{ batch_id() }} as export_batch_id
from {{ ref('chart_design') }}
