-- Nonconformances with the run, press and die, the corrective action and its closure. Grain: one row per
-- nonconformance.

select
    n.ncr_id, n.run_id, r.press_id, r.press_group, r.part_id, r.die_id, n.characteristic_id, n.defect_code, n.quantity_affected, n.detected_at,
    n.cause_code, n.cause_text, n.disposition, n.opened, n.closed, date_diff('hour', n.opened, n.closed) / 24.0 as days_to_close,
    n.corrective_action_id, c.opened as corrective_action_opened, c.closed as corrective_action_closed, c.verification as corrective_action_verification,
    cast(n.opened as date) between cast('{{ var("quarter_start") }}' as date) and cast('{{ var("record_end") }}' as date) as in_quarter,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_qms__nonconformances') }} n
left join {{ ref('int_run_shots') }} r using (run_id)
left join {{ ref('stg_qms__corrective_actions') }} c on c.corrective_action_id = n.corrective_action_id
