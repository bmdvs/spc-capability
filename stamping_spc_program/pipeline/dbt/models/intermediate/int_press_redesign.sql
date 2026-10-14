-- The date the redesign took effect on each press, from the record: the earliest reaction plan step on a part whose
-- primary press it is. A press the redesign has not reached in the record has no date. Grain: one row per press.

with steps as (

    select p.primary_press as press_id, min(s.effective_from) as redesign_date
    from {{ ref('stg_spc__reaction_plan_steps') }} s
    join {{ ref('stg_spc__characteristics') }} c on c.characteristic_id = s.characteristic_id
    join {{ ref('stg_erp__parts') }} p on p.part_id = c.part_id
    group by 1

)

select
    pr.press_id,
    pr.press_group,
    pr.spc_entry_at_install,
    pr.load_cell_channels,
    s.redesign_date,
    coalesce(s.redesign_date = (select min(redesign_date) from steps), false) as is_pilot_press,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_erp__presses') }} pr
left join steps s on s.press_id = pr.press_id
order by pr.press_id
