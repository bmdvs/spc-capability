"""Phase I baselines completed in the record, with their screening and the normality of the baseline means.
Grain: one row per baseline limit set.

Normality is the Anderson-Darling statistic on the baseline subgroup means against the normal, with its 5% critical
value. Flatness is bounded at zero and is tested after a Box-Cox transformation.
"""
import numpy as np
import pandas as pd
from scipy import stats


def model(dbt, session):
    dbt.config(materialized="table")
    b = dbt.ref("mart_phase1_baseline_subgroups").df()
    ls = dbt.ref("mart_limit_sets").df().set_index("limit_set_id")
    batch = b["export_batch_id"].iloc[0]
    rows = []
    for sid, g in b.groupby("limit_set_id", sort=True):
        s = ls.loc[sid]; x = g["subgroup_mean"].values.astype(float)
        bounded = s.characteristic_type == "flatness"
        y = stats.boxcox(x)[0] if bounded and (x > 0).all() and len(x) > 2 else x
        ad = stats.anderson(y, dist="norm") if len(y) >= 8 else None
        crit = float(ad.critical_values[list(ad.significance_level).index(5.0)]) if ad is not None else np.nan
        rows.append({"limit_set_id": sid, "characteristic_id": s.characteristic_id, "part_id": s.part_id, "family_part": bool(s.family_part), "press_id": s.press_id,
                     "characteristic_type": s.characteristic_type, "characteristic_class": s.characteristic_class, "chart": s.chart, "trigger": s.trigger,
                     "effective_from": s.effective_from, "subgroups_used": int(s.subgroups_used), "subgroups_found": int(len(g)),
                     "coil_changes_spanned": s.coil_changes_spanned, "coil_changes_in_subgroups": int(g["coil_change_before"].sum()),
                     "screened_subgroups": int(g["screened"].sum()), "transformation": "Box-Cox" if bounded else "none",
                     "anderson_darling": float(ad.statistic) if ad is not None else np.nan, "anderson_darling_critical_5pct": crit,
                     "normal_at_5pct": bool(ad.statistic < crit) if ad is not None else None})
    out = pd.DataFrame(rows)
    out["coil_changes_spanned"] = out["coil_changes_spanned"].astype("Int64")
    out["export_batch_id"] = batch
    return out
