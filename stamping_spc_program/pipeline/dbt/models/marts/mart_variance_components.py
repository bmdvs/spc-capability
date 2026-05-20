"""Variance components by characteristic over the record. Grain: one row per variable characteristic on a chart with
at least the minimum routine subgroups in the record.

Routine subgroups, nested by method of moments: within subgroup (pooled variance of the readings), between
subgroups within a run and coil, between coils within a sharpening interval, between intervals. Shares are of the sum.
On formed characteristics the incoming coil effect is measured on the coil-change subgroups (10 pieces, taken before
centring): the variance of their means less the within share of a 10-piece mean, as a share of that plus within.
On hole diameters the wear trend is the variance of the fitted values of the regression of subgroup means on shots
since sharpening (subgroups with the shot count known), as a share of the variance of all readings.
Lag-1 autocorrelation is of subgroup means less their run-and-coil mean, pooled over segments of six or more.
"""
import numpy as np
import pandas as pd

R5 = ["r1", "r2", "r3", "r4", "r5"]
R10 = [f"r{i}" for i in range(1, 11)]


def nested(g, sw2):
    seg = g.groupby(["run_id", "coil_id"])["subgroup_mean"]
    v_in_coil = float(np.nanmean(seg.var(ddof=1)))
    sub = max(v_in_coil - sw2 / 5, 0.0)
    coil_means = seg.mean(); n_c = float(seg.size().mean())
    interval = g.groupby(["run_id", "coil_id"])["interval_key"].first()
    v_coil = float(coil_means.groupby(interval).var(ddof=1).mean()) if coil_means.size > 3 else np.nan
    coil = max(v_coil - (sub + sw2 / 5) / n_c, 0.0) if v_coil == v_coil else 0.0
    iv = g.groupby("interval_key")["subgroup_mean"].mean()
    v_int = float(iv.var(ddof=1)) if len(iv) > 2 else 0.0
    inter = max(v_int - (coil + (sub + sw2 / 5) / n_c) / max(len(g) / max(len(iv), 1) / n_c, 1), 0.0)
    return sub, coil, inter, int(coil_means.size), int(len(iv))


def lag1(g):
    num = den = 0.0; n = 0
    for _, s in g.groupby(["run_id", "coil_id"], sort=False):
        if len(s) < 6:
            continue
        d = s["subgroup_mean"].values - s["subgroup_mean"].values.mean()
        num += float((d[1:] * d[:-1]).sum()); den += float((d * d).sum()); n += 1
    return (num / den if den > 0 else np.nan), n


def model(dbt, session):
    dbt.config(materialized="table")
    min_n = int(dbt.config.get("components_min_subgroups") or 60)
    h = dbt.ref("int_characteristic_history").df()
    batch = h["export_batch_id"].iloc[0]
    h = h[h["in_record"] & (h["data_type"] == "variable") & h["subgroup_mean"].notna()
          & h["characteristic_class"].isin(["formed", "hole diameter", "hole position", "length and width", "flatness"])]
    h = h.sort_values(["characteristic_id", "sample_time", "subgroup_id"], kind="stable")
    h["interval_key"] = h["die_id"] + "/" + h["sharpening_interval_no"].astype(str)
    gauges = dbt.ref("stg_spc__characteristics").df().set_index("characteristic_id")["gauge_id"]
    rows = []
    for cid, g in h.groupby("characteristic_id", sort=True):
        r = g[g["subgroup_type"] == "routine"]
        if len(r) < min_n:
            continue
        first = r.iloc[0]
        sw2 = float(np.nanmean(np.nanvar(r[R5].values.astype(float), axis=1, ddof=1)))
        sub, coil, inter, coils, intervals = nested(r, sw2)
        tot = sw2 + sub + coil + inter
        row = {"characteristic_id": cid, "part_id": first.part_id, "family_part": bool(first.family_part), "press_id": first.press_id, "press_group": first.press_group,
               "die_id": first.die_id, "characteristic_name": first.characteristic_name, "characteristic_type": first.characteristic_type,
               "characteristic_class": first.characteristic_class, "chart_type": first.chart_type, "critical": bool(first.critical), "gauge_id": gauges.get(cid),
               "tolerance_width": float(first.tolerance_width), "routine_subgroups": int(len(r)), "coils": coils, "intervals": intervals,
               "sigma_within": float(np.sqrt(sw2)), "sigma_total": float(np.sqrt(tot)),
               "share_within": sw2 / tot, "share_between_subgroups_in_coil": sub / tot, "share_between_coils": coil / tot, "share_between_intervals": inter / tot}
        a, nseg = lag1(r)
        row["lag_1_autocorrelation_within_coil"] = a; row["lag_1_segments"] = nseg
        cc = g[g["subgroup_type"] == "coil-change"]
        if first.characteristic_class == "formed" and len(cc) >= 15:
            w10 = float(np.nanmean(np.nanvar(cc[R10].values.astype(float), axis=1, ddof=1)))
            comp = max(float(cc["subgroup_mean"].var(ddof=1)) - w10 / 10, 0.0)
            row["coil_change_subgroups"] = int(len(cc)); row["incoming_coil_share"] = comp / (comp + w10)
        if first.characteristic_class == "hole diameter":
            k = r[r["shots_since_sharpening"].notna()]
            if len(k) > 30:
                x = k[R5].values.astype(float); s = k["shots_since_sharpening"].values.astype(float)
                b1, b0 = np.polyfit(s, x.mean(1), 1)
                allv = float(np.var(x.ravel(), ddof=1))
                row["trend_share"] = float(np.var(b0 + b1 * s, ddof=1)) / allv
                row["trend_within_share"] = float(np.mean(np.var(x, axis=1, ddof=1))) / allv
                row["trend_subgroups"] = int(len(k))
        rows.append(row)
    out = pd.DataFrame(rows)
    for c in ("coil_change_subgroups", "incoming_coil_share", "trend_share", "trend_within_share", "trend_subgroups"):
        if c not in out:
            out[c] = np.nan
    for c in ("coil_change_subgroups", "trend_subgroups"):
        out[c] = out[c].astype("Int64")
    out["export_batch_id"] = batch
    return out
