-- QMS export: corrective actions, typed. One row per export row.

select
    nullif(trim(corrective_action_id), '') as corrective_action_id,
    nullif(trim(source), '') as source,
    cast(nullif(trim(opened), '') as date) as opened,
    nullif(trim(owner), '') as owner,
    nullif(trim(root_cause_text), '') as root_cause_text,
    nullif(trim(actions), '') as actions,
    nullif(trim(verification), '') as verification,
    cast(nullif(trim(closed), '') as date) as closed,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'qms__corrective_actions') }}
