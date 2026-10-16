-- Every limit set in the record with its basis, the trigger that issued it, the verifications that held it and the
-- subgroups charted under it. A three-way set spanning fewer coil changes than the baseline rule asks is flagged.
-- Grain: one row per limit set.

select
    l.*,
    strftime(l.effective_from, '%Y-%m') as issued_month,
    (l.chart = 'three-way' and l.coil_changes_spanned < {{ var('three_way_baseline_coil_changes') }}) as below_coil_change_minimum
from {{ ref('int_limit_sets') }} l
