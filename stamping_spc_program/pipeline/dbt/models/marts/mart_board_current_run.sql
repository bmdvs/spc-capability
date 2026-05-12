-- The run on each pilot press at the time the SPC boards are drawn for ({{ var('board_as_at') }}, the end of the last
-- working day of the last complete week of June 2026). Grain: one row per pilot press.

with runs as (

    select r.*, row_number() over (partition by r.press_id order by r.production_start desc) as recency
    from {{ ref('int_run_shots') }} r
    join {{ ref('int_press_redesign') }} p using (press_id)
    where p.is_pilot_press and r.production_start <= cast('{{ var("board_as_at") }}' as timestamp)

),

checks as (

    select h.run_id,
           max(h.sample_time) filter (where h.subgroup_type = 'routine') as last_routine_check,
           min(h.sample_time) filter (where h.subgroup_type = 'first-piece') as first_piece_check,
           count(distinct h.characteristic_id) filter (where h.subgroup_type = 'first-piece') as first_piece_characteristics,
           count(*) filter (where h.subgroup_type = 'first-piece' and h.alarm_rule_1) as first_piece_rule_1_signals,
           max(h.sample_time) filter (where h.subgroup_type = 'coil-change') as last_coil_change_check,
           arg_max(h.coil_id, h.sample_time) filter (where h.coil_id is not null) as coil_in_force
    from {{ ref('int_characteristic_history') }} h
    where h.sample_time <= cast('{{ var("board_as_at") }}' as timestamp)
    group by 1

),

previous as (

    select r.press_id, r.run_id as previous_run_id, r.part_id as previous_part_id, r.actual_end as previous_run_ended
    from runs r
    where r.recency = 2

),

last_piece as (

    select h.run_id, max(h.sample_time) as last_piece_check, count(distinct h.characteristic_id) as last_piece_characteristics
    from {{ ref('int_characteristic_history') }} h
    where h.subgroup_type = 'last-piece'
    group by 1

)

select
    r.press_id, r.run_id, r.part_id, r.die_id, r.production_start, r.run_speed_spm, r.parts_per_stroke,
    cast('{{ var("board_as_at") }}' as timestamp) as board_as_at,
    c.last_routine_check, c.first_piece_check, c.first_piece_characteristics, c.first_piece_rule_1_signals, c.last_coil_change_check,
    c.coil_in_force, k.grade as coil_grade, k.nominal_thickness_mm, k.certificate_thickness_mm, k.certificate_hardness_hrb,
    p.previous_run_id, p.previous_part_id, p.previous_run_ended, l.last_piece_check as previous_run_last_piece_check, l.last_piece_characteristics as previous_run_last_piece_characteristics,
    t.baseline_total_kn_mean, t.baseline_total_kn_sd, t.baseline_lag_1_autocorrelation,
    {{ batch_id() }} as export_batch_id
from runs r
left join checks c using (run_id)
left join {{ ref('stg_erp__coils') }} k on k.coil_id = c.coil_in_force
left join previous p using (press_id)
left join last_piece l on l.run_id = p.previous_run_id
left join {{ ref('mart_per_stroke_run_tonnage') }} t using (run_id)
where r.recency = 1
