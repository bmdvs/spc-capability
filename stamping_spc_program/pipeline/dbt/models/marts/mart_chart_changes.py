"""The chart changes made in the record, with the evidence behind each. Grain: one row per change.

- A tool-wear chart's recalculation trigger shortened: the date of the first limit set issued on the shorter trigger,
  with the trigger before and after.
- A characteristic moved from X-bar and R to a three-way chart: the date its coil-change reaction step took effect,
  and its between-coil share of the total variance of routine readings over the record before the move, by the nested
  method of moments used for the variance components.
"""
import numpy as np
import pandas as pd

R5 = ["r1", "r2", "r3", "r4", "r5"]


def coil_share_of_total(g):
    sw2 = float(np.nanmean(np.nanvar(g[R5].values.astype(float), axis=1, ddof=1)))
    seg = g.groupby(["run_id", "coil_id"])["subgroup_mean"]
    sub = max(float(np.nanmean(seg.var(ddof=1))) - sw2 / 5, 0.0)
    coil_means = seg.mean(); n_c = float(seg.size().mean())
    coil = max(float(coil_means.var(ddof=1)) - (sub + sw2 / 5) / n_c, 0.0)
    return coil / (coil + sub + sw2), int(coil_means.size), int(len(g))


def model(dbt, session):
    dbt.config(materialized="table")
    ls = dbt.ref("mart_limit_sets").df()
    k = dbt.ref("stg_spc__characteristics").df()
    parts = dbt.ref("stg_erp__parts").df().set_index("part_id")
    rp = dbt.ref("stg_spc__reaction_plan_steps").df()
    h = dbt.ref("int_characteristic_history").df()
    batch = h["export_batch_id"].iloc[0]
    rows = []
    tw = ls[ls["chart"] == "tool-wear"].sort_values(["characteristic_id", "effective_from"])
    for cid, g in tw.groupby("characteristic_id", sort=True):
        t = g["trigger_subgroups"].astype("Int64")
        change = g[(t != t.shift()) & t.shift().notna()]
        for _, r in change.iterrows():
            before = int(t.shift().loc[r.name])
            rows.append({"characteristic_id": cid, "part_id": r.part_id, "press_id": r.press_id, "die_id": r.die_id, "change": "tool-wear trigger shortened" if r.trigger_subgroups < before else "tool-wear trigger lengthened",
                         "changed_on": pd.Timestamp(r.effective_from).normalize(), "from_value": float(before), "to_value": float(r.trigger_subgroups), "unit": "subgroups",
                         "evidence": "between-coil share of total variance before the change", "evidence_value": np.nan, "evidence_coils": None, "evidence_subgroups": None})
    moved = k[k["chart_type"].str.startswith("three-way") & ~k["type"].isin(["formed height", "bend angle"])]
    for _, c in moved.iterrows():
        steps = rp[(rp["characteristic_id"] == c.characteristic_id) & (rp["signal"] == "coil change")]
        on = pd.Timestamp(steps["effective_from"].min())
        g = h[(h["characteristic_id"] == c.characteristic_id) & (h["subgroup_type"] == "routine") & h["subgroup_mean"].notna() & (h["sample_time"] < on) & h["in_record"]]
        share, coils, n = coil_share_of_total(g)
        rows.append({"characteristic_id": c.characteristic_id, "part_id": c.part_id, "press_id": parts.at[c.part_id, "primary_press"], "die_id": parts.at[c.part_id, "die_id"],
                     "change": "moved from X-bar and R to three-way", "changed_on": on, "from_value": np.nan, "to_value": np.nan, "unit": None,
                     "evidence": "between-coil share of total variance before the change", "evidence_value": share, "evidence_coils": coils, "evidence_subgroups": n})
    out = pd.DataFrame(rows)
    out["evidence_coils"] = out["evidence_coils"].astype("Int64"); out["evidence_subgroups"] = out["evidence_subgroups"].astype("Int64")
    out["export_batch_id"] = batch
    return out
