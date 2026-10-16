-- Every limit set in the record with its basis, the trigger that issued it and the verifications that held it, and
-- the subgroups charted under it. Grain: one row per limit set.

with cl as (

    select * from {{ ref('stg_spc__control_limits') }}

),

v as (

    select limit_set_id,
           count(*) as verifications,
           count(*) filter (where result = 'passed') as verifications_passed,
           count(*) filter (where result = 'failed') as verifications_failed,
           max(verified_at) filter (where result = 'passed') as last_verified_at
    from {{ ref('stg_spc__limit_verifications') }}
    group by 1

),

charted as (

    select limit_set_id,
           count(*) filter (where subgroup_type = 'routine') as routine_subgroups_charted,
           count(*) filter (where subgroup_type = 'routine' and limits_provisional) as routine_subgroups_provisional,
           min(sample_time) as first_subgroup_at,
           max(sample_time) as last_subgroup_at
    from {{ ref('int_characteristic_history') }}
    where limit_set_id is not null
    group by 1

)

select
    cl.limit_set_id,
    cl.characteristic_id,
    k.part_id,
    list_contains({{ var('family_parts') }}, k.part_id) as family_part,
    p.die_id,
    p.primary_press as press_id,
    k."type" as characteristic_type,
    case
        when k."type" in ('formed height', 'bend angle') then 'formed'
        when k."type" = 'hole diameter' then 'hole diameter'
        when k."type" in ('hole-to-edge', 'hole-to-hole') then 'hole position'
        when k."type" in ('length', 'width') then 'length and width'
        when k."type" = 'flatness' then 'flatness'
    end as characteristic_class,
    k.critical,
    cl.basis,
    case cl.basis when 'three-way baseline' then 'three-way' when 'tool-wear regression' then 'tool-wear' else 'X-bar and R' end as chart,
    cl.status,
    cl.rules_in_force,
    cl.effective_from,
    cl.effective_to,
    cast(cl.effective_from as date) between cast('{{ var("record_start") }}' as date) and cast('{{ var("record_end") }}' as date) as issued_in_record,
    cast(cl.effective_from as date) between cast('{{ var("quarter_start") }}' as date) and cast('{{ var("record_end") }}' as date) as issued_in_quarter,
    cl.reason,
    case
        when cl.reason like 'baseline in force from before%' then 'baseline before the record'
        when cl.reason like 'baseline after the verification following%' then 'failed verification'
        when cl.reason like 'baseline after the die rebuild%' then 'rebuild'
        when cl.reason like 'baseline after the die forming-station repair%' or cl.reason like 'baseline after the die repair%' then 'repair'
        when cl.reason like 'tool-wear line re-fitted%' then 'tool-wear re-fit'
        when cl.reason = 'annual review' then 'annual review'
        when cl.reason like 'baseline after the move%' then 'chart change'
    end as trigger,
    cl.annotation,
    cl.centre_line, cl.ucl_mean, cl.lcl_mean, cl.ucl_range, cl.lcl_range, cl.ucl_moving_range, cl.sigma_individuals,
    case when cl.basis = 'three-way baseline' then cl.sigma_individuals else (cl.ucl_mean - cl.centre_line) / 3 end as sigma_of_means,
    cl.slope_per_100k_shots,
    cl.subgroups_used,
    cl.coil_changes_spanned,
    cl.trigger_subgroups,
    cl.set_by,
    coalesce(v.verifications, 0) as verifications,
    coalesce(v.verifications_passed, 0) as verifications_passed,
    coalesce(v.verifications_failed, 0) as verifications_failed,
    v.last_verified_at,
    coalesce(c.routine_subgroups_charted, 0) as routine_subgroups_charted,
    coalesce(c.routine_subgroups_provisional, 0) as routine_subgroups_provisional,
    c.first_subgroup_at,
    c.last_subgroup_at,
    {{ batch_id() }} as export_batch_id
from cl
join {{ ref('stg_spc__characteristics') }} k on k.characteristic_id = cl.characteristic_id
left join {{ ref('stg_erp__parts') }} p on p.part_id = k.part_id
left join v on v.limit_set_id = cl.limit_set_id
left join charted c on c.limit_set_id = cl.limit_set_id
