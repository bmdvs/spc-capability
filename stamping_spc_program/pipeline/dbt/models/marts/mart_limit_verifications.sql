-- Verifications of limits held across a die event, completed in the record, with the die event they follow. A
-- sharpening counts as failed when any X-bar and R or tool-wear chart of the die fails its verification after it.
-- Grain: one row per verification.

with v as (

    select v.*, k.part_id, k."type" as characteristic_type, p.primary_press as press_id, pr.press_group,
           list_contains({{ var('family_parts') }}, k.part_id) as family_part
    from {{ ref('stg_spc__limit_verifications') }} v
    join {{ ref('stg_spc__characteristics') }} k using (characteristic_id)
    left join {{ ref('stg_erp__parts') }} p on p.part_id = k.part_id
    left join {{ ref('stg_erp__presses') }} pr on pr.press_id = p.primary_press

),

events as (

    select die_id, die_event, event_date,
           bool_or(result = 'failed') filter (where chart in ('X-bar and R', 'tool-wear')) as event_failed_on_xbar_r_or_tool_wear
    from v
    group by 1, 2, 3

)

select
    v.verification_id, v.characteristic_id, v.part_id, v.family_part, v.press_id, v.press_group, v.characteristic_type, v.chart,
    v.die_id, v.die_event, v.event_date, v.verified_at, v.subgroups, v.coil_changes, v.mean_offset_sigma, v.result, v.limit_set_id,
    cast(v.verified_at as date) >= cast('{{ var("quarter_start") }}' as date) as in_quarter,
    e.event_failed_on_xbar_r_or_tool_wear,
    {{ batch_id() }} as export_batch_id
from v
join events e using (die_id, die_event, event_date)
