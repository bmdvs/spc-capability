-- Stops of the press by the per-stroke charts, on every press, with the toolmaker's finding, the die work logged
-- against the stop, and whether the historian keeps the strokes before it. Grain: one row per stop.

with kept as (

    select distinct run_id from {{ ref('stg_press_monitor__strokes') }}

)

select
    f.fault_event_id, f.press_id, pr.press_group, f.run_id, f."timestamp" as stopped_at, f.stroke_no as stop_stroke_no,
    case f.input when 'EWMA signal' then 'EWMA on the total' when 'channel share signal' then 'channel share' else 'both' end as chart,
    f.finding,
    case
        when f.finding = 'nothing found' then 'nothing found'
        when f.finding like 'punch chipped%' then 'chipped punch'
        when f.finding like 'punch worn%' then 'worn punch'
        when f.finding like 'slug%' then 'slug pulling'
        else f.finding
    end as finding_class,
    f.cleared_at, f.cleared_by, date_diff('second', f."timestamp", f.cleared_at) / 60.0 as minutes_stopped,
    f.die_event_id, e.event_type as die_event_type, e.stations_touched, e.notes as die_event_notes,
    r.part_id, r.die_id, r.parts_per_stroke, r.run_speed_spm, r.strokes as run_strokes,
    k.run_id is not null as strokes_kept,
    cast(f."timestamp" as date) between cast('{{ var("record_start") }}' as date) and cast('{{ var("record_end") }}' as date) as in_record,
    cast(f."timestamp" as date) between cast('{{ var("quarter_start") }}' as date) and cast('{{ var("record_end") }}' as date) as in_quarter,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_press_monitor__fault_events') }} f
left join {{ ref('stg_erp__presses') }} pr on pr.press_id = f.press_id
left join {{ ref('int_die_event_timeline') }} e on e.die_event_id = f.die_event_id
left join {{ ref('int_run_shots') }} r on r.run_id = f.run_id
left join kept k on k.run_id = f.run_id
where f.input like '%signal'
