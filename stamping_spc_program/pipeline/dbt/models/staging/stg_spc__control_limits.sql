-- SPC software export: control limits, typed. One row per export row.

select
    nullif(trim(limit_set_id), '') as limit_set_id,
    nullif(trim(characteristic_id), '') as characteristic_id,
    cast(nullif(trim(effective_from), '') as timestamp) as effective_from,
    cast(nullif(trim(effective_to), '') as timestamp) as effective_to,
    nullif(trim(method), '') as method,
    cast(nullif(trim(centre_line), '') as double) as centre_line,
    cast(nullif(trim(ucl_mean), '') as double) as ucl_mean,
    cast(nullif(trim(lcl_mean), '') as double) as lcl_mean,
    cast(nullif(trim(ucl_range), '') as double) as ucl_range,
    cast(nullif(trim(lcl_range), '') as double) as lcl_range,
    cast(nullif(trim(subgroups_used), '') as bigint) as subgroups_used,
    nullif(trim(set_by), '') as set_by,
    cast(nullif(trim(slope_per_100k_shots), '') as double) as slope_per_100k_shots,
    cast(nullif(trim(coil_changes_spanned), '') as bigint) as coil_changes_spanned,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'spc__control_limits') }}
