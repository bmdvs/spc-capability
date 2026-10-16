"""The incoming coil effect on formed characteristics against the coil certificate. Grain: one row per formed
characteristic with at least 20 coil-change subgroups in the record.

Coil-change subgroup means (10 pieces, before centring) regressed on the certificate thickness and hardness of the
coil. The residual sigma about the fit and the sigma of the coil means are each net of the within share of a
10-piece mean, and stated as a share of the tolerance.
"""
import numpy as np
import pandas as pd

R10 = [f"r{i}" for i in range(1, 11)]


def model(dbt, session):
    dbt.config(materialized="table")
    p = dbt.ref("mart_coil_change_points").df()
    batch = p["export_batch_id"].iloc[0]
    rows = []
    for cid, g in p[p["certificate_thickness_mm"].notna() & p["certificate_hardness_hrb"].notna()].groupby("characteristic_id", sort=True):
        if len(g) < 20:
            continue
        f = g.iloc[0]
        X = np.column_stack([np.ones(len(g)), g["certificate_thickness_mm"], g["certificate_hardness_hrb"]]); y = g["subgroup_mean"].values.astype(float)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ beta
        w10 = float(np.nanmean(np.nanvar(g[R10].values.astype(float), axis=1, ddof=1)))
        tol = float(f.tolerance_width)
        rows.append({"characteristic_id": cid, "part_id": f.part_id, "family_part": bool(f.family_part), "press_id": f.press_id, "characteristic_type": f.characteristic_type,
                     "coil_change_subgroups": int(len(g)), "coils": int(g["coil_id"].nunique()), "intercept": float(beta[0]), "per_mm_thickness": float(beta[1]),
                     "per_hrb": float(beta[2]), "r_squared": 1 - float(e.var()) / float(y.var()),
                     "residual_sigma_share_of_tolerance": float(np.sqrt(max(e.var(ddof=3) - w10 / 10, 0))) / tol,
                     "coil_means_sigma_share_of_tolerance": float(np.sqrt(max(y.var(ddof=1) - w10 / 10, 0))) / tol})
    out = pd.DataFrame(rows)
    out["export_batch_id"] = batch
    return out
