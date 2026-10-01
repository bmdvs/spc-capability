-- SPC software export: reaction plan steps, typed. One row per export row.

select
    nullif(trim(characteristic_id), '') as characteristic_id,
    nullif(trim("signal"), '') as "signal",
    cast(nullif(trim("step"), '') as bigint) as "step",
    nullif(trim(action), '') as action,
    nullif(trim(owner), '') as owner,
    cast(nullif(trim(effective_from), '') as date) as effective_from,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'spc__reaction_plan_steps') }}
