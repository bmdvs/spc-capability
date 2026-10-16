-- First-piece approvals at run start, with the run's press and part, the characteristic that held a held first piece
-- and the time to release. Grain: one row per approval.

select
    a.approval_id, a.run_id, r.press_id, r.press_group, r.part_id, r.die_id,
    list_contains({{ var('family_parts') }}, r.part_id) as family_part,
    a.first_piece_at, a.characteristics_measured, a.result, a.held, a.held_characteristic_id, k."type" as held_characteristic_type,
    a.released_at, a.released_by, a.minutes_to_release, a.action,
    cast(a.first_piece_at as date) between cast('{{ var("record_start") }}' as date) and cast('{{ var("record_end") }}' as date) as in_record,
    cast(a.first_piece_at as date) between cast('{{ var("quarter_start") }}' as date) and cast('{{ var("record_end") }}' as date) as in_quarter,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_qms__first_piece_approvals') }} a
left join {{ ref('int_run_shots') }} r using (run_id)
left join {{ ref('stg_spc__characteristics') }} k on k.characteristic_id = a.held_characteristic_id
