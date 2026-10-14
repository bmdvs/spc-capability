"""Limits as computed: for each variable characteristic and sharpening interval with subgroups in the baseline year,
X-bar and R limits from a stable baseline of 25 subgroups after the sharpening. Grain: one row per characteristic
and sharpening interval.

The baseline is the first window of 25 consecutive subgroups, moving in steps of five from the sharpening, that shows
no Western Electric rule 1 to 4 signal on the means and no point above the range limit, against its own limits. Where
no such window exists the first window clean on rule 1 is used, and failing that the first 25; the basis is recorded.
Subgroups with a reading set aside by the plausibility rule take no part. Intervals with fewer than 40 usable
subgroups before the redesign carry no computed limits. Lab burr readings are not included.
"""
import numpy as np
import pandas as pd

XBAR_FACTOR, RANGE_FACTOR = 0.577, 2.114          # X-bar and R constants for subgroups of five


def we_rules(z):
    """Western Electric rules 1 to 4 on standardised means: True at each point that completes a signal."""
    n = len(z); out = np.zeros(n, dtype=bool)
    for i in range(n):
        if abs(z[i]) > 3:
            out[i] = True
        w = z[max(0, i - 2):i + 1]
        if (z[i] > 2 and (w > 2).sum() >= 2) or (z[i] < -2 and (w < -2).sum() >= 2):
            out[i] = True
        w = z[max(0, i - 4):i + 1]
        if (z[i] > 1 and (w > 1).sum() >= 4) or (z[i] < -1 and (w < -1).sum() >= 4):
            out[i] = True
        if i >= 7:
            w = z[i - 7:i + 1]
            if (w > 0).all() or (w < 0).all():
                out[i] = True
    return out


def model(dbt, session):
    dbt.config(materialized="table")
    year = int(dbt.config.get("baseline_year", 2025))
    size = 25
    h = dbt.ref("int_characteristic_history").df()
    h = h[(h["data_type"] == "variable") & (h["characteristic_type"] != "burr height") & h["subgroup_mean"].notna() & ~h["after_redesign"].fillna(False)
          & (h["implausible_readings"] == 0) & (h["sharpening_interval_no"] > 0)]
    h = h.sort_values(["characteristic_id", "sharpening_interval_no", "sample_time", "subgroup_id"], kind="stable")
    rows = []
    for (cid, ino), g in h.groupby(["characteristic_id", "sharpening_interval_no"], sort=True):
        t = g["sample_time"].values
        if not (pd.DatetimeIndex(t).year == year).any():
            continue
        base = {"characteristic_id": cid, "sharpening_interval_no": int(ino), "die_id": g["die_id"].iloc[0], "press_id": g["press_id"].iloc[0], "sharpening_date": g["sharpening_date"].iloc[0],
                "usable_subgroups": int(len(g))}
        if len(g) < 40:
            rows.append({**base, "baseline_basis": "fewer than 40 usable subgroups"})
            continue
        m = g["subgroup_mean"].values.astype(float); r = g["subgroup_range"].values.astype(float)
        pick = None; first_r1 = None
        for s0 in range(0, min(len(g) - 30, 50), 5):
            bm, br = m[s0:s0 + size].mean(), r[s0:s0 + size].mean()
            if br <= 0:
                continue
            z = (m[s0:s0 + size] - bm) / (XBAR_FACTOR * br / 3)
            r_ok = (r[s0:s0 + size] <= RANGE_FACTOR * br).all()
            if r_ok and not we_rules(z).any():
                pick = (s0, "stable on rules 1 to 4"); break
            if first_r1 is None and r_ok and (np.abs(z) <= 3).all():
                first_r1 = (s0, "stable on rule 1 only")
        if pick is None:
            pick = first_r1 or (0, "not stable")
        s0, basis = pick
        bm, br = float(m[s0:s0 + size].mean()), float(r[s0:s0 + size].mean())
        rows.append({**base, "baseline_basis": basis, "baseline_offset_subgroups": int(s0), "baseline_from": t[s0], "baseline_to": t[s0 + size - 1], "baseline_subgroups": size,
                     "centre_line": bm, "mean_range": br, "ucl_mean": bm + XBAR_FACTOR * br, "lcl_mean": bm - XBAR_FACTOR * br, "ucl_range": RANGE_FACTOR * br, "lcl_range": 0.0,
                     "sigma_within": br / 2.326, "sigma_of_means_in_baseline": float(m[s0:s0 + size].std(ddof=1))})
    out = pd.DataFrame(rows)
    out["export_batch_id"] = h["export_batch_id"].iloc[0]
    return out
