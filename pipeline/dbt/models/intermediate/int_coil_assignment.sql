-- The coil in force at each subgroup. Grain: one row per subgroup. Where the operator did not scan the coil it is
-- recovered when the run consumed one coil, or when the scanned subgroups on the run before and after it carry the
-- same coil; otherwise it stays unassigned.

with s as (

    select subgroup_id, run_id, sample_time, coil_id
    from {{ ref('stg_spc__subgroups') }}

),

neighbours as (

    select
        s.*,
        last_value(coil_id ignore nulls) over (partition by run_id order by sample_time, subgroup_id rows between unbounded preceding and current row) as coil_before,
        first_value(coil_id ignore nulls) over (partition by run_id order by sample_time, subgroup_id rows between current row and unbounded following) as coil_after
    from s

)

select
    n.subgroup_id,
    n.coil_id as coil_id_recorded,
    case
        when n.coil_id is not null then n.coil_id
        when r.coils_on_run = 1 then r.coils_consumed
        when n.coil_before = n.coil_after then n.coil_before
    end as coil_id,
    case
        when n.coil_id is not null then 'recorded'
        when r.coils_on_run = 1 then 'recovered: one coil on the run'
        when n.coil_before = n.coil_after then 'recovered: same coil scanned before and after'
        else 'unassigned'
    end as coil_assignment,
    {{ batch_id() }} as export_batch_id
from neighbours n
left join {{ ref('int_run_shots') }} r on r.run_id = n.run_id
