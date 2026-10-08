-- Capability as reported: the figures the shop filed or its software printed, as the source computed them.
-- Grain: one row per PPAP study and one row per software capability summary.

select
    'PPAP study' as source,
    p.study_id as report_id,
    p.characteristic_id,
    c.part_id,
    c."type" as characteristic_type,
    c.critical,
    p."date" as report_date,
    p.trigger,
    p.pieces,
    p.measured_on,
    p.mean as reported_mean,
    p.sigma as reported_sigma,
    p.pp, p.ppk,
    cast(null as double) as cp, cast(null as double) as cpk,
    p.filed_to as issued_to,
    {{ batch_id() }} as export_batch_id
from {{ ref('stg_qms__ppap_studies') }} p
join {{ ref('stg_spc__characteristics') }} c on c.characteristic_id = p.characteristic_id

union all

select
    r.source,
    r.report_id,
    r.characteristic_id,
    c.part_id,
    c."type",
    c.critical,
    r.run_date,
    cast(null as varchar),
    cast(null as bigint),
    'check fixture or hand gauge, as keyed',
    cast(null as double), cast(null as double),
    r.pp, r.ppk, r.cp, r.cpk,
    r.issued_to,
    {{ batch_id() }}
from {{ ref('stg_qms__capability_reports') }} r
join {{ ref('stg_spc__characteristics') }} c on c.characteristic_id = r.characteristic_id
where r.source <> 'PPAP study'
