-- Complaints with the press set and period each falls in. Grain: one row per complaint, press set and period.
-- A complaint entered a second time for the same customer, part, run, quantity and defect code is a duplicate entry;
-- the first received is kept and the later one is flagged and left out of the counts.

with c as (

    select c.*, row_number() over (partition by c.customer_id, c.part_id, c.run_ids, c.quantity, c.defect_code order by c.received, c.complaint_id) > 1 as duplicate_entry
    from {{ ref('stg_qms__complaints') }} c

)

select
    p.press_set, p.months, p.period_year, c.complaint_id, c.customer_id, c.part_id, c.run_ids, c.received, c.quantity, c.defect_code, c.ppm_as_scored,
    c.charge_back, c.premium_freight, c.duplicate_entry,
    {{ batch_id() }} as export_batch_id
from {{ ref('mart_outcome_periods') }} p
join c on c.received >= p.period_start and c.received < p.period_end
join {{ ref('int_run_shots') }} r on r.run_id = split_part(c.run_ids, ';', 1)
join {{ ref('int_press_redesign') }} x on x.press_id = r.press_id and x.is_pilot_press = p.is_pilot_press
