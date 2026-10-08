-- SPC software export: weekly reviews, typed. One row per export row.

select
    nullif(trim(review_id), '') as review_id,
    nullif(trim(characteristic_id), '') as characteristic_id,
    cast(nullif(trim(week_start), '') as date) as week_start,
    cast(nullif(trim(subgroups), '') as bigint) as subgroups,
    cast(nullif(trim(patterns), '') as bigint) as patterns,
    cast(nullif(trim(rule_1_alarms), '') as bigint) as rule_1_alarms,
    nullif(trim(finding), '') as finding,
    nullif(trim(reviewed_by), '') as reviewed_by,
    cast(nullif(trim(reviewed_on), '') as date) as reviewed_on,
    nullif(trim(export_batch_id), '') as export_batch_id
from {{ source('raw', 'spc__weekly_reviews') }}
