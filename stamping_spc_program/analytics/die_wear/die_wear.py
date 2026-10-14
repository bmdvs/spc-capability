"""Die wear: hole diameter and burr height against shots since sharpening by die, the shot count at which burr reaches
80% of its limit against the die's sharpening interval, and the burr nonconformances of the baseline year by the die's
position in its interval."""
import numpy as np
import pandas as pd
from scipy import stats as st

from analytics.data import query

SEED = 20250106
BASELINE_YEAR = 2025
MIN_SUBGROUPS, MIN_SHOT_SPAN = 15, 60000      # an interval enters the hole diameter regression with at least these
MIN_BURR_SUBGROUPS = 30                        # a die enters the burr regression with at least this many lab subgroups


def hole_diameter_intervals(year=BASELINE_YEAR):
    """Hole diameter on shots since sharpening within each sharpening interval: slope and R-squared by interval."""
    d = query("""select characteristic_id, die_id, press_id, sharpening_interval_no, shots_since_sharpening / 1e5 as shots, reading_mean, tolerance_width
                 from marts.mart_wear_points where characteristic_type = 'hole diameter' and sample_year = ? and not after_redesign
                 order by characteristic_id, sharpening_interval_no, sample_time, subgroup_id""", [year])
    rows = []
    for (cid, die, press, no), g in d.groupby(["characteristic_id", "die_id", "press_id", "sharpening_interval_no"], sort=True):
        if len(g) < MIN_SUBGROUPS or (g["shots"].max() - g["shots"].min()) * 1e5 < MIN_SHOT_SPAN:
            continue
        lr = st.linregress(g["shots"].values, g["reading_mean"].values)
        rows.append({"characteristic_id": cid, "die_id": die, "press_id": press, "sharpening_interval_no": int(no), "subgroups": len(g), "slope_mm_per_100k_shots": lr.slope, "r_squared": lr.rvalue ** 2,
                     "shots_span": (g["shots"].max() - g["shots"].min()) * 1e5})
    return pd.DataFrame(rows), d


def hole_diameter_by_die(intervals, points):
    """By die: the slope common to its intervals (each interval with its own intercept), with its interval, the
    R-squared within intervals, and the growth over the die's sharpening interval against the tolerance."""
    practice = query("select die_id, sharpening_interval_shots from staging.stg_erp__dies").set_index("die_id")["sharpening_interval_shots"]
    keep = set(zip(intervals["characteristic_id"], intervals["sharpening_interval_no"])); rows = []
    for (cid, die), g in points.groupby(["characteristic_id", "die_id"], sort=True):
        g = g[[(cid, int(n)) in keep for n in g["sharpening_interval_no"]]]
        if g.empty:
            continue
        x = g["shots"].values - g.groupby("sharpening_interval_no")["shots"].transform("mean").values
        y = g["reading_mean"].values - g.groupby("sharpening_interval_no")["reading_mean"].transform("mean").values
        k = g["sharpening_interval_no"].nunique(); b = (x * y).sum() / (x * x).sum(); res = y - b * x; dof = len(g) - k - 1
        se = np.sqrt((res ** 2).sum() / dof / (x * x).sum()); t = st.t.ppf(0.975, dof); iv = intervals[intervals["characteristic_id"] == cid]
        rows.append({"die_id": die, "characteristic_id": cid, "intervals": k, "subgroups": len(g), "slope_mm_per_100k_shots": b, "slope_low": b - t * se, "slope_high": b + t * se,
                     "r_squared_within_intervals": 1 - (res ** 2).sum() / (y ** 2).sum(), "r_squared_by_interval_median": iv["r_squared"].median(),
                     "sharpening_interval_shots": int(practice[die]), "growth_over_the_interval_mm": b * practice[die] / 1e5, "growth_as_share_of_tolerance": b * practice[die] / 1e5 / g["tolerance_width"].iloc[0]})
    return pd.DataFrame(rows)


def burr_by_die(through_year=BASELINE_YEAR):
    """Burr height on the burr gauge, as a share of its limit, on shots since sharpening by die, on the record before
    the redesign through the baseline year; the shot count at which the fitted line reaches 80% and 100% of the limit,
    with a bootstrap interval over subgroups, against the die's sharpening interval."""
    d = query("""select w.die_id, w.shots_since_sharpening as shots, w.share_of_limit, w.sharpening_interval_no, w.sample_year
                 from marts.mart_wear_points w
                 where w.characteristic_type = 'burr height' and not w.after_redesign and w.sample_year <= ?
                 order by w.die_id, w.sample_time, w.subgroup_id""", [through_year])
    dies = query("select die_id, sharpening_interval_shots from staging.stg_erp__dies order by die_id").set_index("die_id")["sharpening_interval_shots"]
    logged = query("""select die_id, median(shots_in_interval_logged) as logged_median, count(shots_in_interval_logged) as intervals_logged
                      from intermediate.int_sharpening_intervals where interval_end is not null and is_run_interval and year(interval_end) <= ? group by 1""", [through_year]).set_index("die_id")
    rows = []
    for i, (die, g) in enumerate(d.groupby("die_id", sort=True)):
        if len(g) < MIN_BURR_SUBGROUPS:
            rows.append({"die_id": die, "subgroups": len(g), "fitted": False}); continue
        x, y = g["shots"].values, g["share_of_limit"].values; lr = st.linregress(x, y)
        r = np.random.default_rng([SEED, 10, i]); pick = r.integers(0, len(x), (1000, len(x))); xb, yb = x[pick], y[pick]
        xm, ym = xb.mean(axis=1, keepdims=True), yb.mean(axis=1, keepdims=True); sb = ((xb - xm) * (yb - ym)).sum(axis=1) / ((xb - xm) ** 2).sum(axis=1); ib = ym[:, 0] - sb * xm[:, 0]
        s80b = np.where(sb > 0, (0.8 - ib) / np.where(sb > 0, sb, 1), np.inf)
        s80 = (0.8 - lr.intercept) / lr.slope if lr.slope > 0 else np.nan; s100 = (1.0 - lr.intercept) / lr.slope if lr.slope > 0 else np.nan
        rows.append({"die_id": die, "subgroups": len(g), "fitted": True, "slope_share_of_limit_per_100k_shots": lr.slope * 1e5, "share_of_limit_at_sharpening": lr.intercept, "r_squared": lr.rvalue ** 2,
                     "shots_at_80pct_of_limit": s80, "low": float(np.percentile(s80b, 2.5)), "high": float(np.percentile(s80b, 97.5)), "shots_at_the_limit": s100,
                     "sharpening_interval_shots": int(dies[die]), "logged_interval_median": logged["logged_median"].get(die, np.nan),
                     "share_of_limit_at_the_sharpening_interval": lr.intercept + lr.slope * dies[die]})
    t = pd.DataFrame(rows); f = t[t["fitted"]].copy()
    f["interval_longer_than_80pct_count"] = f["sharpening_interval_shots"] > f["shots_at_80pct_of_limit"]
    f["interval_longer_than_the_upper_bound"] = f["sharpening_interval_shots"] > f["high"]
    f["interval_longer_than_the_count_at_the_limit"] = f["sharpening_interval_shots"] > f["shots_at_the_limit"]
    summary = pd.DataFrame([{"dies_with_burr_readings": len(t), "dies_fitted": len(f), "dies_with_a_rising_line": int((f["slope_share_of_limit_per_100k_shots"] > 0).sum()),
                             "interval_longer_than_the_80pct_count": int(f["interval_longer_than_80pct_count"].sum()),
                             "the_same_beyond_the_upper_bound_of_the_count": int(f["interval_longer_than_the_upper_bound"].sum()),
                             "interval_longer_than_the_count_at_the_limit": int(f["interval_longer_than_the_count_at_the_limit"].sum()),
                             "r_squared_median": f["r_squared"].median(), "shots_at_80pct_median": f["shots_at_80pct_of_limit"].median(), "sharpening_interval_median": f["sharpening_interval_shots"].median(),
                             "ratio_of_interval_to_80pct_count_median": (f["sharpening_interval_shots"] / f["shots_at_80pct_of_limit"]).median()}])
    return f.drop(columns=["fitted"]), summary


def burr_over_the_limit_by_interval(year=BASELINE_YEAR):
    """Run intervals ending in the year: those with a burr gauge subgroup over the limit before the sharpening."""
    return query("""
        with i as (select die_id, sharpening_interval_no, shots_in_interval_logged from intermediate.int_sharpening_intervals where year(interval_end) = ? and is_run_interval),
             b as (select die_id, sharpening_interval_no, count(*) as subgroups, max(share_of_limit) as highest_share_of_limit, max(shots_since_sharpening) as last_reading_at_shots
                   from marts.mart_wear_points where characteristic_type = 'burr height' group by 1, 2)
        select count(*) as intervals_ending_in_the_year, count(b.subgroups) as with_a_burr_gauge_subgroup,
               count(*) filter (where b.highest_share_of_limit > 1) as with_a_subgroup_mean_over_the_limit,
               count(*) filter (where b.highest_share_of_limit > 0.8) as with_a_subgroup_mean_over_80pct_of_the_limit,
               median(b.subgroups) as subgroups_per_interval_median
        from i left join b using (die_id, sharpening_interval_no)""", [year])


def burr_nonconformances(by_die, year=BASELINE_YEAR):
    """Burr nonconformances opened in the year by where they were detected, the die's position in its sharpening
    interval at the end of the run, and its position against the die's 80% shot count."""
    n = query("select * from marts.mart_burr_nonconformances where opened_year = ? order by ncr_id", [year])
    s80 = by_die.set_index("die_id")["shots_at_80pct_of_limit"]
    n["shots_at_80pct_of_limit"] = n["die_id"].map(s80)
    n["past_the_80pct_count"] = np.where(n["shots_at_80pct_of_limit"].notna() & n["shots_since_sharpening_at_run_end"].notna(), n["shots_since_sharpening_at_run_end"] > n["shots_at_80pct_of_limit"], np.nan)
    n["share_of_the_interval"] = n["shots_since_sharpening_at_run_end"] / n["sharpening_interval_practice"]
    g = n.groupby(["defect_code", "detected_at"], as_index=False).agg(
        nonconformances=("ncr_id", "count"), quantity_affected=("quantity_affected", "sum"), with_shots_since_sharpening=("shots_since_sharpening_at_run_end", "count"),
        within_the_sharpening_interval=("within_the_sharpening_interval", lambda x: int((x == True).sum())), past_the_sharpening_interval=("within_the_sharpening_interval", lambda x: int((x == False).sum())),
        past_the_80pct_count=("past_the_80pct_count", lambda x: int((x == 1).sum())), before_the_80pct_count=("past_the_80pct_count", lambda x: int((x == 0).sum())),
        share_of_the_interval_median=("share_of_the_interval", "median"))
    return g, n


def intervals_as_logged(year=BASELINE_YEAR):
    """Run intervals ending in the year: logged shots over the die's stated interval, with the count of logged intervals
    left out as not run intervals (under 20,000 shots: a sharpening followed by a rebuild, or an entry with no shots
    between it and the one beside it)."""
    return query("""select count(*) filter (where i.is_run_interval) as intervals_with_shot_counts, count(*) as logged_intervals, count(*) filter (where not i.is_run_interval) as left_out_as_not_run_intervals,
                           median(i.shots_in_interval_logged / d.sharpening_interval_shots) filter (where i.is_run_interval) as logged_over_stated_median,
                           quantile_cont(i.shots_in_interval_logged / d.sharpening_interval_shots, 0.25) filter (where i.is_run_interval) as lower_quartile,
                           quantile_cont(i.shots_in_interval_logged / d.sharpening_interval_shots, 0.75) filter (where i.is_run_interval) as upper_quartile,
                           avg((i.shots_in_interval_logged > d.sharpening_interval_shots)::int) filter (where i.is_run_interval) as share_longer_than_stated
                    from intermediate.int_sharpening_intervals i join staging.stg_erp__dies d using (die_id)
                    where year(i.interval_end) = ? and i.shots_in_interval_logged is not null""", [year])


def runs_past_the_interval(nc_rows, year=BASELINE_YEAR):
    """Runs of the year that ended with the die past its stated sharpening interval, beside the burr nonconformances."""
    r = query("""select count(*) as runs_with_shots_known, count(*) filter (where (r.shots_since_sharpening_at_start + r.strokes) > d.sharpening_interval_shots) as runs_ended_past_the_interval
                 from intermediate.int_run_shots r join staging.stg_erp__dies d using (die_id)
                 where r.shots_since_sharpening_at_start is not null and year(r.actual_start) = ?""", [year])
    b = nc_rows[(nc_rows["defect_code"] == "burr") & nc_rows["shots_since_sharpening_at_run_end"].notna()]
    r["burr_nonconformances_with_shots_known"] = len(b); r["burr_nonconformances_past_the_interval"] = int((b["within_the_sharpening_interval"] == False).sum())
    r["position_median_lowest_by_detection"] = b.groupby("detected_at")["share_of_the_interval"].median().min(); r["position_median_highest_by_detection"] = b.groupby("detected_at")["share_of_the_interval"].median().max()
    r["share_of_runs_past"] = r["runs_ended_past_the_interval"] / r["runs_with_shots_known"]
    return r


def compute():
    intervals, points = hole_diameter_intervals(); by_die, summary = burr_by_die(); ncs, nc_rows = burr_nonconformances(by_die)
    hd = hole_diameter_by_die(intervals, points)
    hole_summary = pd.DataFrame([{"dies": hd["die_id"].nunique(), "intervals": len(intervals), "subgroups": int(intervals["subgroups"].sum()), "r_squared_by_interval_median": intervals["r_squared"].median(),
                                  "r_squared_p10": intervals["r_squared"].quantile(0.1), "r_squared_p90": intervals["r_squared"].quantile(0.9), "slope_by_interval_median": intervals["slope_mm_per_100k_shots"].median(),
                                  "slope_by_die_lowest": hd["slope_mm_per_100k_shots"].min(), "slope_by_die_highest": hd["slope_mm_per_100k_shots"].max(), "growth_as_share_of_tolerance_median": hd["growth_as_share_of_tolerance"].median(),
                                  "growth_as_share_of_tolerance_highest": hd["growth_as_share_of_tolerance"].max()}])
    return {"hole_diameter_summary": hole_summary, "hole_diameter_by_die": hd, "hole_diameter_intervals": intervals, "burr_summary": summary, "burr_by_die": by_die,
            "burr_over_the_limit_by_interval": burr_over_the_limit_by_interval(), "burr_nonconformances": ncs, "burr_nonconformance_rows": nc_rows, "intervals_as_logged": intervals_as_logged(), "runs_past_the_interval": runs_past_the_interval(nc_rows)}


if __name__ == "__main__":
    pd.set_option("display.width", 320); pd.set_option("display.max_columns", 60)
    for name, table in compute().items():
        print(f"\n== {name}\n{table.head(30).round(4).to_string(index=False)}")
