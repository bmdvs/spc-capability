"""Capability as computed: for each PPAP study window on a critical characteristic, capability from the production
record on the check fixture. Grain: one row per study with a window of at least six months and 100 usable subgroups.

Within-subgroup sigma is the pooled standard deviation across subgroups; overall sigma is the standard deviation of
all readings. Subgroups with a reading set aside by the plausibility rule take no part; the count is carried.
"""
import numpy as np
import pandas as pd

R = ["r1", "r2", "r3", "r4", "r5"]


def model(dbt, session):
    dbt.config(materialized="table")
    w = dbt.ref("mart_capability_study_windows").df()
    w = w[w["window_at_least_six_months"]]
    h = dbt.ref("int_characteristic_history").df()
    h = h[h["characteristic_id"].isin(w["characteristic_id"].unique()) & h["r1"].notna() & ~h["after_redesign"].fillna(False)]
    h = h.sort_values(["characteristic_id", "sample_time", "subgroup_id"], kind="stable")
    by = {k: g for k, g in h.groupby("characteristic_id", sort=False)}
    rows = []
    for s in w.sort_values(["characteristic_id", "study_date"]).itertuples():
        g = by.get(s.characteristic_id)
        if g is None:
            continue
        g = g[(g["sample_time"] >= pd.Timestamp(s.study_date)) & (g["sample_time"] < pd.Timestamp(s.window_end))]
        set_aside = int((g["implausible_readings"] > 0).sum())
        g = g[g["implausible_readings"] == 0]
        if len(g) < 100:
            continue
        v = g[R].values.astype(float)
        sw = float(np.sqrt(v.var(axis=1, ddof=1).mean())); so = float(v.std(ddof=1)); m = float(v.mean())
        k = min(s.usl - m, m - s.lsl)
        rows.append({"study_id": s.study_id, "characteristic_id": s.characteristic_id, "characteristic_class": s.characteristic_class, "characteristic_type": s.characteristic_type,
                     "press_id": s.press_id, "press_group": s.press_group, "study_date": s.study_date, "window_end": s.window_end,
                     "subgroups": int(len(g)), "readings": int(v.size), "subgroups_set_aside": set_aside, "coils": int(g["coil_id"].nunique()),
                     "production_mean": m, "sigma_within": sw, "sigma_overall": so,
                     "cp": (s.usl - s.lsl) / (6 * sw), "cpk": k / (3 * sw), "pp": (s.usl - s.lsl) / (6 * so), "ppk": k / (3 * so),
                     "filed_pp": s.filed_pp, "filed_ppk": s.filed_ppk, "filed_mean": s.filed_mean, "filed_sigma": s.filed_sigma,
                     "filed_less_production_ppk": s.filed_ppk - k / (3 * so)})
    out = pd.DataFrame(rows)
    out["export_batch_id"] = h["export_batch_id"].iloc[0]
    return out
