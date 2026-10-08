-- Limits as set: the limit sets the shop had in force on each characteristic, as its systems recorded them, with the
-- die's rebuilds and sharpenings since the set took effect. Grain: one row per limit set.

with sets as (

    select l.*, c.part_id, c."type" as characteristic_type, c.critical, p.die_id, p.primary_press as press_id
    from {{ ref('stg_spc__control_limits') }} l
    join {{ ref('stg_spc__characteristics') }} c on c.characteristic_id = l.characteristic_id
    join {{ ref('stg_erp__parts') }} p on p.part_id = c.part_id

),

die_work as (

    select
        s.limit_set_id,
        max(case when e.event_type = 'rebuild' and e.event_date <= cast(s.effective_from as date) + 7 then e.event_date end) as rebuild_on_or_before_set,
        count(*) filter (where e.event_type = 'sharpening' and e.event_date > cast(s.effective_from as date)
                         and e.event_date <= least(coalesce(cast(s.effective_to as date), date '{{ var("assessment_date") }}'), date '{{ var("assessment_date") }}')) as sharpenings_while_in_force_to_assessment,
        count(*) filter (where e.event_type = 'rebuild' and e.event_date > cast(s.effective_from as date) + 7
                         and e.event_date <= least(coalesce(cast(s.effective_to as date), date '{{ var("assessment_date") }}'), date '{{ var("assessment_date") }}')) as rebuilds_while_in_force_to_assessment
    from sets s
    left join {{ ref('int_die_event_timeline') }} e on e.die_id = s.die_id
    group by 1

)

select
    s.limit_set_id,
    s.characteristic_id,
    s.part_id,
    s.die_id,
    s.press_id,
    pr.press_group,
    s.characteristic_type,
    s.critical,
    s.method,
    s.effective_from,
    s.effective_to,
    (cast(s.effective_from as date) <= date '{{ var("assessment_date") }}'
        and (s.effective_to is null or cast(s.effective_to as date) > date '{{ var("assessment_date") }}')) as in_force_at_assessment,
    s.centre_line, s.ucl_mean, s.lcl_mean, s.ucl_range, s.lcl_range,
    s.subgroups_used,
    s.slope_per_100k_shots,
    s.coil_changes_spanned,
    s.set_by,
    w.rebuild_on_or_before_set,
    date_diff('day', cast(s.effective_from as date), date '{{ var("assessment_date") }}') / 30.4 as months_in_force_at_assessment,
    w.sharpenings_while_in_force_to_assessment,
    w.rebuilds_while_in_force_to_assessment,
    -- the first limits of a three-way chart at the redesign: the earliest baseline set on the characteristic, built on the record before it
    (s.method = 'baseline after sharpening' and s.coil_changes_spanned is not null
        and s.effective_from = min(case when s.method = 'baseline after sharpening' then s.effective_from end) over (partition by s.characteristic_id)) as first_limits_at_redesign,
    {{ batch_id() }} as export_batch_id
from sets s
left join die_work w on w.limit_set_id = s.limit_set_id
left join {{ ref('int_press_redesign') }} pr on pr.press_id = s.press_id
order by s.characteristic_id, s.effective_from
