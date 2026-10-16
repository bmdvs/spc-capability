-- QMS export: first-piece approvals, typed. One row per export row.

select
    nullif(trim(approval_id), '') as approval_id,
    nullif(trim(run_id), '') as run_id,
    cast(nullif(trim(first_piece_at), '') as timestamp) as first_piece_at,
    cast(nullif(trim(characteristics_measured), '') as bigint) as characteristics_measured,
    nullif(trim("result"), '') as "result",
    (nullif(trim(held), '') = 'Y') as held,
    nullif(trim(held_characteristic_id), '') as held_characteristic_id,
    cast(nullif(trim(released_at), '') as timestamp) as released_at,
    nullif(trim(released_by), '') as released_by,
    cast(nullif(trim(minutes_to_release), '') as double) as minutes_to_release,
    nullif(trim(action), '') as action,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'qms__first_piece_approvals') }}
