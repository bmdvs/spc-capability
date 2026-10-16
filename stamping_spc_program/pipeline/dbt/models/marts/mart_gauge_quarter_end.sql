-- Calibration status of every gauge at each quarter end in the record: past its due date, away for calibration, and
-- whether it feeds a chart. Grain: one row per gauge and quarter end.

with quarter_ends as (

    select cast(unnest(range(cast('{{ var("record_start") }}' as date) + interval 3 month, cast('{{ var("record_end") }}' as date) + interval 2 day, interval 3 month)) as date) - 1 as quarter_end

),

feeding as (

    select distinct gauge_id from {{ ref('stg_spc__characteristics') }} where chart_type <> 'none'

),

status as (

    select q.quarter_end, c.gauge_id,
           bool_or(c.due <= q.quarter_end and (c.done is null or c.done > q.quarter_end)) as past_due,
           bool_or(c.removed_from_service <= q.quarter_end and (c.done is null or c.done > q.quarter_end)) as away_for_calibration
    from quarter_ends q
    cross join {{ ref('stg_calibration__calibrations') }} c
    group by 1, 2

)

select
    s.quarter_end, s.gauge_id, g."type" as gauge_type, g.location, g.status as gauge_status,
    s.past_due, s.away_for_calibration, f.gauge_id is not null as feeds_a_chart,
    {{ batch_id() }} as export_batch_id
from status s
join {{ ref('stg_calibration__gauges') }} g using (gauge_id)
left join feeding f using (gauge_id)
