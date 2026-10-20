"""Capability by characteristic, for the review quarter, for the record, and for each calendar quarter of the record
(period "2025 Q3" to "2026 Q2"). Grain: one row per critical variable
characteristic, and every flatness characteristic, per period with at least the minimum routine subgroups in the period.

Ppk on overall sigma from all readings, every class. Cpk by class:
- formed (three-way charts): between/within sigma, the within-subgroup sigma from the average range (R-bar / d2)
  combined with the between-subgroup sigma from the moving range of subgroup means (MR-bar / 1.128, less the within
  share of a subgroup mean, not below zero);
- hole diameter (tool-wear charts): sigma of the readings about the regression of subgroup means on shots since
  sharpening, on subgroups with the shot count known (none reported where fewer than 30 have it); Ppk carries the wear
  over the interval;
- hole position, length, width and flatness: pooled within-subgroup standard deviation.
One-sided characteristics (flatness) carry the upper index only. Intervals are 95%, by Bissell's approximation on the
number of readings for Ppk and on the number of subgroups for Cpk.
"""
import numpy as np
import pandas as pd

R5 = ["r1", "r2", "r3", "r4", "r5"]
D2_5 = 2.326
Z = 1.959964


def bissell(index, n):
    se = np.sqrt(1.0 / (9.0 * n) + index ** 2 / (2.0 * (n - 1)))
    return index - Z * se, index + Z * se


def model(dbt, session):
    dbt.config(materialized="table")
    min_n = int(dbt.config.get("capability_min_subgroups"))
    q0 = pd.Timestamp(dbt.config.get("quarter_start"))
    h = dbt.ref("int_characteristic_history").df()
    batch = h["export_batch_id"].iloc[0]
    h = h[h["in_record"] & (h["critical"] | (h["characteristic_class"] == "flatness")) & (h["data_type"] == "variable") & (h["subgroup_type"] == "routine") & h["subgroup_mean"].notna()
          & h["characteristic_class"].isin(["formed", "hole diameter", "hole position", "length and width", "flatness"])]
    h = h.sort_values(["characteristic_id", "sample_time", "subgroup_id"], kind="stable")
    rows = []
    quarters = [(f"{d.year} Q{(d.month - 1) // 3 + 1}", h[(h["sample_time"] >= d) & (h["sample_time"] < d + pd.DateOffset(months=3))]) for d in pd.date_range("2025-07-01", "2026-04-01", freq="3MS")]
    for period, sel in [("quarter", h[h["sample_time"] >= q0]), ("record", h)] + quarters:
        for cid, g in sel.groupby("characteristic_id", sort=True):
            if len(g) < min_n:
                continue
            f = g.iloc[0]; x = g[R5].values.astype(float); m = float(x.mean())
            so = float(x.std(ddof=1)); sw_pooled = float(np.sqrt(np.var(x, axis=1, ddof=1).mean()))
            usl, lsl = float(f.usl), (None if f.one_sided else float(f.lsl))
            cls = f.characteristic_class
            if cls == "formed":
                sw = float(g["subgroup_range"].mean()) / D2_5
                mr = np.abs(np.diff(g["subgroup_mean"].values.astype(float))).mean() / 1.128
                sb2 = max(mr ** 2 - sw ** 2 / 5, 0.0)
                s_short = float(np.sqrt(sw ** 2 + sb2)); definition = "between/within"
            elif cls == "hole diameter":
                k = g[g["shots_since_sharpening"].notna()]; definition = "residual about the wear regression"
                if len(k) >= 30:
                    xk = k[R5].values.astype(float); s = k["shots_since_sharpening"].values.astype(float)
                    b1, b0 = np.polyfit(s, xk.mean(1), 1)
                    s_short = float(np.std(xk - (b0 + b1 * s)[:, None], ddof=2))
                else:
                    s_short = np.nan
            else:
                s_short = sw_pooled; definition = "pooled within-subgroup"
            upper_p = (usl - m) / (3 * so); upper_k = (usl - m) / (3 * s_short)
            if lsl is None:
                ppk, cpk = upper_p, upper_k; pp = cp = np.nan
            else:
                ppk = min(upper_p, (m - lsl) / (3 * so)); cpk = min(upper_k, (m - lsl) / (3 * s_short))
                pp = (usl - lsl) / (6 * so); cp = (usl - lsl) / (6 * s_short)
            n_r, n_s = x.size, len(g)
            plo, phi = bissell(ppk, n_r); clo, chi = bissell(cpk, n_s)
            rows.append({"period": period, "characteristic_id": cid, "part_id": f.part_id, "family_part": bool(f.family_part), "press_id": f.press_id, "press_group": f.press_group,
                         "characteristic_name": f.characteristic_name, "characteristic_type": f.characteristic_type, "characteristic_class": cls, "chart_type": f.chart_type,
                         "one_sided": bool(f.one_sided), "index_reported": "Ppu and Cpu" if f.one_sided else "Ppk and Cpk", "cpk_definition": definition,
                         "subgroups": n_s, "readings": n_r, "mean": m, "usl": usl, "lsl": lsl, "sigma_overall": so, "sigma_short_term": s_short, "sigma_within_pooled": sw_pooled,
                         "pp": pp, "ppk": ppk, "ppk_low": plo, "ppk_high": phi, "cp": cp, "cpk": cpk, "cpk_low": clo, "cpk_high": chi, "cpk_less_ppk": cpk - ppk,
                         "under_1_33": bool(ppk < 1.33)})
    out = pd.DataFrame(rows)
    out["export_batch_id"] = batch
    return out
