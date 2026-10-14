-- Each PPAP study on a critical characteristic with the production record that followed it: the twelve months after
-- the study, cut at the date the redesign reached the part's press and at the assessment date. Grain: one row per
-- study. A window shorter than six months is kept and marked; the capability comparison leaves it out.

with s as (

    select p.*, c."type" as characteristic_type, c.critical, c.nominal, c.usl, c.lsl, pt.primary_press as press_id, pr.redesign_date, pr.press_group
    from {{ ref('stg_qms__ppap_studies') }} p
    join {{ ref('stg_spc__characteristics') }} c on c.characteristic_id = p.characteristic_id
    join {{ ref('stg_erp__parts') }} pt on pt.part_id = c.part_id
    join {{ ref('int_press_redesign') }} pr on pr.press_id = pt.primary_press
    where c.critical and c.data_type = 'variable'

),

w as (

    select s.*,
        s."date" as window_start,
        least(s."date" + interval 12 month, cast(s.redesign_date as timestamp), cast('{{ var("assessment_date") }}' as timestamp) + interval 1 day) as window_end,
        lead(s."date") over (partition by s.characteristic_id order by s."date") as next_study_date
    from s

)

select
    w.study_id, w.characteristic_id, w.part_id, w.press_id, w.press_group, w.characteristic_type,
    case when w.characteristic_type in ('formed height', 'bend angle') then 'formed' else 'punched' end as characteristic_class,
    w.trigger, w.window_start as study_date, cast(w.window_end as date) as window_end,
    date_diff('day', w.window_start, cast(w.window_end as date)) / 30.4 as window_months,
    (date_diff('day', w.window_start, cast(w.window_end as date)) >= 182) as window_at_least_six_months,
    w.pieces, w.mean as filed_mean, w.sigma as filed_sigma, w.pp as filed_pp, w.ppk as filed_ppk,
    w.nominal, w.usl, w.lsl,
    {{ batch_id() }} as export_batch_id
from w
where (w.redesign_date is null or w.window_start < cast(w.redesign_date as date))
  and w.window_start <= cast('{{ var("assessment_date") }}' as date)
order by w.characteristic_id, w.window_start
