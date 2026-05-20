-- Burr check qualifications by operator, with the latest qualification at the status date flagged. Grain: one row
-- per qualification study.

select
    q.qualification_id, q.operator_id, e.shift, q."date" as study_date, q.parts, q.trials, q.agreement_with_reference, q.kappa, q.result, q.requalification_of,
    q."date" >= cast('{{ var("quarter_start") }}' as date) as in_quarter,
    row_number() over (partition by q.operator_id order by q."date" desc, q.qualification_id desc) = 1 as latest,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_calibration__attribute_qualifications') }} q
left join {{ ref('stg_erp__employees') }} e on e.employee_id = q.operator_id
