-- calibration system export: burr check qualifications, typed. One row per export row.

select
    nullif(trim(qualification_id), '') as qualification_id,
    nullif(trim(operator_id), '') as operator_id,
    cast(nullif(trim("date"), '') as date) as "date",
    cast(nullif(trim(parts), '') as bigint) as parts,
    cast(nullif(trim(trials), '') as bigint) as trials,
    cast(nullif(trim(agreement_with_reference), '') as double) as agreement_with_reference,
    cast(nullif(trim(kappa), '') as double) as kappa,
    nullif(trim("result"), '') as "result",
    cast(nullif(trim(requalification_of), '') as date) as requalification_of,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'calibration__attribute_qualifications') }}
