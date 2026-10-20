-- SPC software export: characteristics, typed. One row per export row.

select
    nullif(trim(characteristic_id), '') as characteristic_id,
    nullif(trim(part_id), '') as part_id,
    nullif(trim(revision), '') as revision,
    nullif(trim(name), '') as name,
    nullif(trim("type"), '') as "type",
    cast(nullif(trim(nominal), '') as double) as nominal,
    cast(nullif(trim(usl), '') as double) as usl,
    cast(nullif(trim(lsl), '') as double) as lsl,
    nullif(trim(unit), '') as unit,
    (nullif(trim(critical), '') = 'Y') as critical,
    (nullif(trim(customer_designated), '') = 'Y') as customer_designated,
    nullif(trim(gauge_id), '') as gauge_id,
    cast(nullif(trim(subgroup_size), '') as bigint) as subgroup_size,
    cast(nullif(trim(coil_change_subgroup_size), '') as bigint) as coil_change_subgroup_size,
    cast(nullif(trim(frequency_minutes), '') as bigint) as frequency_minutes,
    nullif(trim(data_type), '') as data_type,
    nullif(trim(chart_type), '') as chart_type,
    nullif(trim("status"), '') as "status",
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'spc__characteristics') }}
