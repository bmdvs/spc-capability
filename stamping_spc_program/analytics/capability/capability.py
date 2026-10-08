"""Subgrouping and capability: the PPAP study against the production record.

For every critical characteristic with a PPAP study in the record: the filed Ppk beside production Cpk and Ppk on the
check fixture over the months after the study, with intervals; the variance components (coil within characteristic,
subgroup within coil); the regression of formed level on the coil's thickness and hardness; the check fixture against
the CMM on matched first-piece parts; and the distribution of the bounded characteristics.
"""
import numpy as np
import pandas as pd
from scipy import stats

from analytics.data import query
from analytics.stats import anderson_darling_normal, cpk_interval, reml_nested, wilson

SEED = 20250102
R5 = ["r1", "r2", "r3", "r4", "r5"]
BOOT = 1000


def _readings():
    """Usable subgroups of every study window in the capability comparison, in a fixed order."""
    return query("""
        select w.study_id, h.subgroup_id, h.coil_id, h.sample_time, h.r1, h.r2, h.r3, h.r4, h.r5, h.subgroup_mean
        from marts.mart_capability_as_computed w
        join intermediate.int_characteristic_history h
            on h.characteristic_id = w.characteristic_id and h.sample_time >= w.study_date and h.sample_time < w.window_end
        where h.r1 is not null and h.implausible_readings = 0 and not h.after_redesign
        order by w.study_id, h.sample_time, h.subgroup_id""")


def _ppk_bootstrap(v, coil, usl, lsl, key):
    """Bootstrap interval for Ppk, resampling coils: readings from one coil move together."""
    r = np.random.default_rng([SEED, key])
    codes, inv = np.unique(coil, return_inverse=True)
    n = np.bincount(inv, minlength=len(codes)) * v.shape[1]
    s1 = np.bincount(inv, weights=v.sum(axis=1), minlength=len(codes)); s2 = np.bincount(inv, weights=(v ** 2).sum(axis=1), minlength=len(codes))
    pick = r.integers(0, len(codes), (BOOT, len(codes)))
    N = n[pick].sum(axis=1); A = s1[pick].sum(axis=1); B = s2[pick].sum(axis=1)
    m = A / N; sd = np.sqrt(np.maximum(B - N * m * m, 0) / (N - 1))
    ppk = np.minimum(usl - m, m - lsl) / (3 * sd)
    return float(np.percentile(ppk, 2.5)), float(np.percentile(ppk, 97.5))


def by_study():
    """One row per study: filed figures, production capability with intervals, and the variance components."""
    cap = query("select * from marts.mart_capability_as_computed order by study_id")
    lim = query("select study_id, usl, lsl from marts.mart_capability_study_windows").set_index("study_id")
    rd = _readings()
    rows = []
    for sid, g in rd.groupby("study_id", sort=True):
        c = cap[cap["study_id"] == sid].iloc[0]
        v = g[R5].values.astype(float)
        coil = g["coil_id"].fillna("unassigned").values
        usl, lsl = float(lim.loc[sid, "usl"]), float(lim.loc[sid, "lsl"])
        lo, hi = _ppk_bootstrap(v, coil, usl, lsl, int(sid.split("-")[1]) * 10000 + int(sid.split("-")[2]))
        clo, chi = cpk_interval(float(c["cpk"]), v.size)
        a = g[g["coil_id"].notna()]
        bc, bs, wi = reml_nested(a["subgroup_mean"].values, a["coil_id"].values, float(c["sigma_within"]))
        tot = bc + bs + wi
        rows.append({"study_id": sid, "characteristic_id": c["characteristic_id"], "characteristic_class": c["characteristic_class"], "characteristic_type": c["characteristic_type"],
                     "press_group": c["press_group"], "study_date": c["study_date"], "subgroups": int(c["subgroups"]), "readings": int(c["readings"]), "coils": int(a["coil_id"].nunique()),
                     "subgroups_set_aside": int(c["subgroups_set_aside"]), "subgroups_with_no_coil": int(g["coil_id"].isna().sum()),
                     "filed_ppk": float(c["filed_ppk"]), "cpk": float(c["cpk"]), "cpk_low": clo, "cpk_high": chi, "ppk": float(c["ppk"]), "ppk_low": lo, "ppk_high": hi,
                     "filed_less_production_ppk": float(c["filed_less_production_ppk"]),
                     "share_between_coils": bc / tot, "share_between_subgroups_within_coil": bs / tot, "share_within_subgroup": wi / tot,
                     "between_over_within_variance": (bc + bs) / wi})
    return pd.DataFrame(rows)


def _median_interval(x, key):
    r = np.random.default_rng([SEED, 77, key]); x = np.asarray(x, dtype=float)
    b = np.median(x[r.integers(0, len(x), (2000, len(x)))], axis=1)
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def capability_summary(t):
    """Filed Ppk against production Cpk and Ppk by characteristic class, medians with bootstrap intervals."""
    rows = []
    for i, (cls, g) in enumerate(list(t.groupby("characteristic_class", sort=True)) + [("all critical", t)]):
        row = {"characteristic_class": cls, "studies": len(g), "characteristics": g["characteristic_id"].nunique(), "subgroups": int(g["subgroups"].sum()), "readings": int(g["readings"].sum()),
               "subgroups_set_aside": int(g["subgroups_set_aside"].sum())}
        for j, col in enumerate(("filed_ppk", "cpk", "ppk", "filed_less_production_ppk", "share_between_coils", "share_between_subgroups_within_coil", "share_within_subgroup", "between_over_within_variance")):
            lo, hi = _median_interval(g[col].values, i * 10 + j)
            row[col] = float(g[col].median()); row[col + "_low"] = lo; row[col + "_high"] = hi
        k = int((g["filed_less_production_ppk"] >= 0.40).sum()); lo, hi = wilson(k, len(g))
        row.update({"studies_filed_at_least_0_40_above": k, "share_at_least_0_40_above": k / len(g), "share_0_40_low": lo, "share_0_40_high": hi})
        k = int((g["filed_less_production_ppk"].abs() <= 0.25).sum()); lo, hi = wilson(k, len(g))
        row.update({"studies_within_0_25": k, "share_within_0_25": k / len(g), "share_0_25_low": lo, "share_0_25_high": hi})
        rows.append(row)
    return pd.DataFrame(rows)


def punched_by_type(t):
    """Punched studies by characteristic type: filed against production Ppk, and how many sit well above or close."""
    g = t[t["characteristic_class"] == "punched"]
    out = g.groupby("characteristic_type").agg(studies=("study_id", "count"), characteristics=("characteristic_id", "nunique"), filed_ppk=("filed_ppk", "median"),
                                                 production_ppk=("ppk", "median"), production_cpk=("cpk", "median"), gap=("filed_less_production_ppk", "median"),
                                                 filed_at_least_0_40_above=("filed_less_production_ppk", lambda x: int((x >= 0.40).sum())),
                                                 within_0_25=("filed_less_production_ppk", lambda x: int((x.abs() <= 0.25).sum()))).reset_index()
    return out.sort_values("filed_at_least_0_40_above", ascending=False, kind="stable").reset_index(drop=True)


def coil_regression():
    """Formed heights: the coil mean on the coil's thickness and hardness, from the certificate and from receiving."""
    d = query("""select m.*, c.nominal, c.usl - c.lsl as tolerance from marts.mart_capability_coil_means m join staging.stg_spc__characteristics c using (characteristic_id)
                 where m.characteristic_type = 'formed height' order by m.study_id, m.coil_id""")
    rows = []
    for sid, g in d.groupby("study_id", sort=True):
        g = g.dropna(subset=["certificate_thickness_deviation", "certificate_hardness_hrb", "receiving_thickness_deviation", "receiving_hardness_hrb"])
        if len(g) < 12:
            continue
        y = g["coil_mean"].values; tol = float(g["tolerance"].iloc[0])
        out = {"study_id": sid, "characteristic_id": g["characteristic_id"].iloc[0], "coils": len(g), "subgroups_a_coil": float(g["subgroups"].mean()), "tolerance_mm": tol,
               "sd_of_coil_means_mm": float(y.std(ddof=1))}
        for name, tcol, hcol in (("certificate", "certificate_thickness_deviation", "certificate_hardness_hrb"), ("receiving", "receiving_thickness_deviation", "receiving_hardness_hrb")):
            X = np.column_stack([np.ones(len(g)), g[tcol].values * 100, g[hcol].values - g[hcol].values.mean()])
            beta, res, *_ = np.linalg.lstsq(X, y, rcond=None)
            e = y - X @ beta; dof = len(g) - 3; s2 = float(e @ e) / dof
            cov = s2 * np.linalg.inv(X.T @ X); se = np.sqrt(np.diag(cov)); tq = stats.t.ppf(0.975, dof)
            r2 = 1 - float(e @ e) / float(((y - y.mean()) ** 2).sum())
            out.update({f"{name}_mm_per_pct_thickness": beta[1], f"{name}_thickness_low": beta[1] - tq * se[1], f"{name}_thickness_high": beta[1] + tq * se[1],
                        f"{name}_thickness_p": float(2 * stats.t.sf(abs(beta[1] / se[1]), dof)),
                        f"{name}_mm_per_hrb": beta[2], f"{name}_hardness_p": float(2 * stats.t.sf(abs(beta[2] / se[2]), dof)), f"{name}_r_squared": r2,
                        f"{name}_intercept": beta[0], f"{name}_hardness_centre": float(g[hcol].values.mean()),
                        f"{name}_residual_sd_mm": float(np.sqrt(s2)), f"{name}_residual_sd_share_of_tolerance": float(np.sqrt(s2)) / tol})
        rows.append(out)
    t = pd.DataFrame(rows)
    summary = pd.DataFrame([{"characteristics": t["characteristic_id"].nunique(), "study_windows": len(t), "coils_median": float(t["coils"].median()),
                             "subgroups_a_coil_median": float(t["subgroups_a_coil"].median()),
                             "sd_of_coil_means_mm_median": float(t["sd_of_coil_means_mm"].median()), "sd_of_coil_means_share_of_tolerance_median": float((t["sd_of_coil_means_mm"] / t["tolerance_mm"]).median()),
                             "certificate_residual_sd_mm_median": float(t["certificate_residual_sd_mm"].median()), "receiving_residual_sd_mm_median": float(t["receiving_residual_sd_mm"].median()),
                             "certificate_residual_sd_share_of_tolerance_median": float(t["certificate_residual_sd_share_of_tolerance"].median()),
                             "receiving_residual_sd_share_of_tolerance_median": float(t["receiving_residual_sd_share_of_tolerance"].median()),
                             "certificate_r_squared_median": float(t["certificate_r_squared"].median()), "receiving_r_squared_median": float(t["receiving_r_squared"].median()),
                             "certificate_thickness_slope_significant": int((t["certificate_thickness_p"] < 0.05).sum()), "receiving_thickness_slope_significant": int((t["receiving_thickness_p"] < 0.05).sum()),
                             "certificate_hardness_slope_significant": int((t["certificate_hardness_p"] < 0.05).sum()),
                             "abs_mm_per_pct_thickness_median": float(t["certificate_mm_per_pct_thickness"].abs().median())}])
    return t, summary


def fixture_against_cmm():
    """Matched first-piece parts: the check fixture reading less the CMM reading, by period and for the rebuilt fixtures."""
    d = query("""
        select m.*, (m.gauge_id in (select gauge_id from staging.stg_calibration__gauge_studies where worksheet_file like '%rebuilt%')) as fixture_rebuilt,
               (select min("date") from staging.stg_calibration__gauge_studies s where s.gauge_id = m.gauge_id and s.worksheet_file like '%rebuilt%') as rebuilt_on
        from marts.mart_capability_cmm_matched m where m.implausible_readings = 0 order by m.die_event_id""")
    d["group"] = np.where(d["fixture_rebuilt"] & (pd.to_datetime(d["event_date"]) >= pd.to_datetime(d["rebuilt_on"])), "rebuilt fixtures, after the rebuild",
                          np.where(d["after_redesign"], "other fixtures, after the redesign", "all fixtures, before the redesign"))
    rows = []
    for name, g in list(d.groupby("group", sort=True)) + [("all matched parts", d)]:
        x = g["fixture_less_cmm"].values
        if len(x) < 2:
            rows.append({"group": name, "matched_first_pieces": len(x), "fixtures": g["gauge_id"].nunique(), "mean_difference_mm": float(x.mean()) if len(x) else np.nan}); continue
        se = x.std(ddof=1) / np.sqrt(len(x)); tq = stats.t.ppf(0.975, len(x) - 1)
        rows.append({"group": name, "matched_first_pieces": len(x), "fixtures": g["gauge_id"].nunique(), "mean_difference_mm": float(x.mean()), "low": float(x.mean() - tq * se), "high": float(x.mean() + tq * se),
                     "sd_mm": float(x.std(ddof=1)), "p_value": float(stats.ttest_1samp(x, 0).pvalue)})
    return pd.DataFrame(rows), d


def bounded_characteristics(year=2024):
    """Burr height (lab readings) and flatness in the baseline year: the normal fit, the Box-Cox fit, and the upper
    capability index on the readings as recorded by the percentile method, with the normal and Box-Cox results beside."""
    d = query(f"""
        select h.characteristic_id, h.characteristic_type, h.usl, h.r1, h.r2, h.r3, h.r4, h.r5
        from intermediate.int_characteristic_history h
        where year(h.sample_time) = {year} and not h.after_redesign and h.r1 is not null and h.implausible_readings = 0
          and h.characteristic_type in ('burr height', 'flatness') and h.data_type = 'variable'
        order by h.characteristic_id, h.sample_time, h.subgroup_id""")
    rows = []
    for cid, g in d.groupby("characteristic_id", sort=True):
        x = g[R5].values.astype(float).ravel(); x = x[x > 0]
        if len(x) < 250:
            continue
        usl = float(g["usl"].iloc[0])
        a, pv = anderson_darling_normal(x)
        y, lam = stats.boxcox(x); ab, pb = anderson_darling_normal(y)
        med, hi = np.percentile(x, 50), np.percentile(x, 99.865)
        yu = stats.boxcox(np.array([usl]), lam)[0]
        rows.append({"characteristic_id": cid, "characteristic_type": g["characteristic_type"].iloc[0], "readings": len(x), "ad_normal": a, "p_normal": pv, "box_cox_lambda": float(lam),
                     "ad_after_box_cox": ab, "p_after_box_cox": pb, "ppu_normal": (usl - x.mean()) / (3 * x.std(ddof=1)), "ppu_percentile": (usl - med) / (hi - med),
                     "ppu_box_cox": (yu - y.mean()) / (3 * y.std(ddof=1)), "share_above_usl": float((x > usl).mean())})
    t = pd.DataFrame(rows)
    summary = t.groupby("characteristic_type").agg(characteristics=("characteristic_id", "count"), readings=("readings", "sum"), normal_fit_rejected=("p_normal", lambda p: int((p < 0.05).sum())),
                                                    box_cox_fit_rejected=("p_after_box_cox", lambda p: int((p < 0.05).sum())), box_cox_lambda_median=("box_cox_lambda", "median"),
                                                    ppu_normal_median=("ppu_normal", "median"), ppu_percentile_median=("ppu_percentile", "median"), ppu_box_cox_median=("ppu_box_cox", "median"),
                                                    readings_above_usl=("share_above_usl", "mean")).reset_index()
    return t, summary


def compute():
    studies = by_study()
    reg, reg_summary = coil_regression()
    cmm, cmm_rows = fixture_against_cmm()
    bounded, bounded_summary = bounded_characteristics()
    return {"by_study": studies, "capability_summary": capability_summary(studies), "punched_by_type": punched_by_type(studies), "coil_regression": reg, "coil_regression_summary": reg_summary,
            "fixture_against_cmm": cmm, "fixture_against_cmm_parts": cmm_rows, "bounded": bounded, "bounded_summary": bounded_summary}


if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)
    for name, table in compute().items():
        print(f"\n== {name}\n{table.head(12).to_string(index=False)}")
