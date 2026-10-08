-- Complaints for the dashboard with the press of their run and the duplicate entries flagged. Grain: one row per complaint.
-- A complaint entered a second time for the same customer, part, run, quantity and defect code is a duplicate entry.

select
    c.complaint_id, c.customer_id, c.part_id, c.received, date_trunc('month', c.received) as month_start, c.quantity, c.defect_code, c.ppm_as_scored,
    r.press_id,
    row_number() over (partition by c.customer_id, c.part_id, c.run_ids, c.quantity, c.defect_code order by c.received, c.complaint_id) > 1 as duplicate_entry,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_qms__complaints') }} c
left join {{ ref('int_run_shots') }} r on r.run_id = split_part(c.run_ids, ';', 1)
