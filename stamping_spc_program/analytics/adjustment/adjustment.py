"""Adjustment: what followed a subgroup mean beyond two sigma (or beyond the printed limit on the paper presses), the
autocorrelation of subgroup means within a run and coil, and the variance in runs with an adjustment against runs
without, on characteristics an adjustment at the press acts on and on those it does not; and the same on the pilot
presses after the reaction plan."""
import numpy as np
import pandas as pd

from analytics.data import query
from analytics.stats import wilson

SEED = 20250105
BASELINE_YEAR = 2025
R5 = ["r1", "r2", "r3", "r4", "r5"]


def after_a_point_beyond_two_sigma(year=BASELINE_YEAR):
    """Points beyond two sigma (or the printed limit) before the redesign: an adjustment recorded at the point, and the
    next subgroup on the other side of the centre line by more than one sigma of the mean. Characteristics not adjusted
    at the press give the rate at which the second happens with no adjustment."""
    d = query("""
        select adjusted_at_the_press, entry_method,
               count(*) as points,
               count(*) filter (where adjustment_recorded) as adjustment_recorded,
               count(*) filter (where next_position_in_sigma is not null) as points_with_a_next_subgroup,
               count(*) filter (where next_position_in_sigma is not null and sign(next_position_in_sigma) = -sign(position_in_sigma) and abs(next_position_in_sigma) > 1) as next_on_the_other_side_beyond_one_sigma,
               count(*) filter (where adjustment_recorded and next_position_in_sigma is not null) as recorded_with_a_next_subgroup,
               count(*) filter (where adjustment_recorded and next_position_in_sigma is not null and sign(next_position_in_sigma) = -sign(position_in_sigma) and abs(next_position_in_sigma) > 1) as recorded_and_next_on_the_other_side
        from marts.mart_adjustment_points
        where sample_year = ? and not after_redesign and beyond_two_sigma_or_the_printed_limit and abs(position_in_sigma) < 12
        group by 1, 2 order by 1 desc, 2""", [year])
    for k, n, name in (("adjustment_recorded", "points", "recorded_share"), ("next_on_the_other_side_beyond_one_sigma", "points_with_a_next_subgroup", "other_side_share")):
        d[name] = d[k] / d[n]
        ci = [wilson(a, b) for a, b in zip(d[k], d[n])]
        d[name + "_low"], d[name + "_high"] = [c[0] for c in ci], [c[1] for c in ci]
    return d


GROUPS = ["beyond two sigma, adjustment recorded", "beyond two sigma, none recorded", "beyond two sigma, characteristics not adjusted at the press",
          "between one and two sigma", "between one and two sigma, characteristics not adjusted at the press"]


def return_toward_centre(year=BASELINE_YEAR):
    """The position of the next subgroup as a share of the position of the point, by group of points, with the
    estimated share of points beyond two sigma that an adjustment followed (keyed entry). The points with no adjustment
    recorded are taken as a mix of points adjusted, returning as the recorded adjustments do, and points left alone,
    returning as a reference group does. The primary reference is the points beyond two sigma on characteristics not
    adjusted at the press; the points between one and two sigma on the adjusted characteristics are beside it.
    Intervals are a bootstrap over characteristics; an estimate outside 0 to 1 is returned as it falls."""
    d = query("""
        select characteristic_id, entry_method, adjusted_at_the_press,
               case when beyond_two_sigma_or_the_printed_limit and adjustment_recorded then 'beyond two sigma, adjustment recorded'
                    when beyond_two_sigma_or_the_printed_limit and adjusted_at_the_press then 'beyond two sigma, none recorded'
                    when beyond_two_sigma_or_the_printed_limit then 'beyond two sigma, characteristics not adjusted at the press'
                    when adjusted_at_the_press then 'between one and two sigma'
                    else 'between one and two sigma, characteristics not adjusted at the press' end as points_group,
               count(*) as points, sum(abs(position_in_sigma)) as position, sum(next_position_in_sigma * sign(position_in_sigma)) as next_position
        from marts.mart_adjustment_points
        where sample_year = ? and not after_redesign and next_position_in_sigma is not null and abs(position_in_sigma) < 12
          and (beyond_two_sigma_or_the_printed_limit or abs(position_in_sigma) between 1 and 2)
        group by 1, 2, 3, 4 order by 1, 2, 4""", [year])
    cols = ["points", "position", "next_position"]
    rows = []
    for m, (method, dm) in enumerate(sorted(d.groupby("entry_method"), key=lambda x: x[0])):
        for gi, name in enumerate(GROUPS):
            g = dm[dm["points_group"] == name]
            if g.empty:
                continue
            a = g[cols].values.astype(float); r = np.random.default_rng([SEED, 60, m, gi]); pick = r.integers(0, len(a), (2000, len(a)))
            b = a[pick, 2].sum(axis=1) / a[pick, 1].sum(axis=1)
            rows.append({"entry_method": method, "points_group": name, "points": int(a[:, 0].sum()), "characteristics": len(a), "mean_position_in_sigma": a[:, 1].sum() / a[:, 0].sum(),
                         "next_as_share_of_position": a[:, 2].sum() / a[:, 1].sum(), "low": float(np.percentile(b, 2.5)), "high": float(np.percentile(b, 97.5))})
    table = pd.DataFrame(rows)

    k = d[d["entry_method"] == "keyed"]

    def sums(frame, name):
        g = frame[frame["points_group"] == name]
        return g.set_index("characteristic_id")[cols].astype(float)

    rec, un = sums(k, GROUPS[0]), sums(k, GROUPS[1])
    adj_ids = np.array(sorted(set(rec.index) | set(un.index)))
    refs = (("points beyond two sigma on characteristics not adjusted at the press (primary)", sums(k, GROUPS[2]), False),
            ("points between one and two sigma on the adjusted characteristics (sensitivity)", sums(k, GROUPS[3]), True))

    def rate(rec_s, un_s, ref_s):
        s_rec, s_un, s_ref = (x[2] / x[1] for x in (rec_s, un_s, ref_s))
        share = (s_ref - s_un) / (s_ref - s_rec)
        adjustments = rec_s[0] + share * un_s[0]
        return share, adjustments / (rec_s[0] + un_s[0]), rec_s[0] / adjustments

    est = []
    for ri, (label, ref, same_characteristics) in enumerate(refs):
        r = np.random.default_rng([SEED, 70, ri]); boot = []
        adj_ids = np.array(sorted(set(rec.index) | set(un.index) | (set(ref.index) if same_characteristics else set())))
        R, U, F = rec.reindex(adj_ids).fillna(0).values, un.reindex(adj_ids).fillna(0).values, (ref.reindex(adj_ids).fillna(0).values if same_characteristics else ref.values)
        for _ in range(2000):
            pa = r.integers(0, len(adj_ids), len(adj_ids)); pf = pa if same_characteristics else r.integers(0, len(F), len(F))
            boot.append(rate(R[pa].sum(axis=0), U[pa].sum(axis=0), F[pf].sum(axis=0)))
        boot = np.array(boot); v = rate(R.sum(axis=0), U.sum(axis=0), F.sum(axis=0))
        for name, x, col in (("share of the points with none recorded that return as adjusted points do", v[0], 0), ("an adjustment followed a point beyond two sigma (estimated)", v[1], 1), ("of those adjustments, recorded (estimated)", v[2], 2)):
            est.append({"reference_for_a_point_left_alone": label, "measure": name, "estimate": x, "low": float(np.percentile(boot[:, col], 2.5)), "high": float(np.percentile(boot[:, col], 97.5)),
                        "reference_points": int(F[:, 0].sum()), "reference_characteristics": len(F)})
    return table, pd.DataFrame(est)


def _segments(year_filter):
    return query(f"""
        select characteristic_id, adjusted_at_the_press, run_id, coil_id, sample_time, subgroup_id, subgroup_mean
        from marts.mart_adjustment_points
        where coil_id is not null and {year_filter}
        order by characteristic_id, run_id, coil_id, sample_time, subgroup_id""")


def _lag1(d, min_len=6):
    """Lag-1 coefficient of the means less their run-and-coil segment mean, pooled over segments of at least min_len;
    returns the coefficient, the segment count and the per-characteristic sums for the interval."""
    rows = []
    for (cid, _, _), g in d.groupby(["characteristic_id", "run_id", "coil_id"], sort=False):
        if len(g) < min_len:
            continue
        x = g["subgroup_mean"].values - g["subgroup_mean"].values.mean()
        rows.append((cid, float((x[1:] * x[:-1]).sum()), float((x * x).sum())))
    t = pd.DataFrame(rows, columns=["characteristic_id", "num", "den"])
    return (t["num"].sum() / t["den"].sum() if len(t) else np.nan), len(t), t.groupby("characteristic_id")[["num", "den"]].sum()


def _interval(by_char, key):
    r = np.random.default_rng([SEED, key]); a = by_char.values
    if len(a) < 5:
        return (np.nan, np.nan)
    pick = r.integers(0, len(a), (2000, len(a)))
    b = a[pick, 0].sum(axis=1) / a[pick, 1].sum(axis=1)
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def autocorrelation():
    """Lag-1 autocorrelation of subgroup means within a run and coil: the baseline year before the redesign, and the
    pilot presses from April 2026, by whether the characteristic is adjusted at the press."""
    rows = []
    sets = (("2025, before the redesign", f"sample_year = {BASELINE_YEAR} and not after_redesign"),
            ("pilot presses, April to June 2026", "after_redesign and is_pilot_press and sample_time >= date '2026-04-01' and sample_time < date '2026-07-01'"))
    for i, (label, flt) in enumerate(sets):
        d = _segments(flt)
        for j, (cls, g) in enumerate((("adjusted at the press", d[d["adjusted_at_the_press"]]), ("not adjusted at the press", d[~d["adjusted_at_the_press"]]))):
            coef, n, by_char = _lag1(g); lo, hi = _interval(by_char, i * 10 + j)
            rows.append({"period": label, "characteristics": cls, "lag_1_autocorrelation": coef, "low": lo, "high": hi, "segments": n, "characteristics_n": len(by_char)})
    return pd.DataFrame(rows)


def variance_in_adjusted_runs(year=BASELINE_YEAR):
    """On characteristics adjusted at the press: the variance of all readings against the variance in the same
    characteristic's runs with no adjustment recorded and no point beyond two sigma (or the printed limit), and against
    its runs with no adjustment recorded. The per-characteristic values are returned beside the summary."""
    d = query("""
        with p as (
            select characteristic_id, run_id,
                   bool_or(adjustment_recorded or beyond_two_sigma_or_the_printed_limit) as adjustment_in_run,
                   bool_or(adjustment_recorded) as adjustment_recorded_in_run
            from marts.mart_adjustment_points where sample_year = ? and not after_redesign and adjusted_at_the_press group by 1, 2)
        select h.characteristic_id, p.adjustment_in_run, p.adjustment_recorded_in_run, h.r1, h.r2, h.r3, h.r4, h.r5
        from intermediate.int_characteristic_history h join p using (characteristic_id, run_id)
        where year(h.sample_time) = ? and not h.after_redesign and h.r1 is not null and h.implausible_readings = 0
        order by h.characteristic_id, h.sample_time, h.subgroup_id""", [year, year])
    out = {}; by_char = {}
    for name, col in (("no adjustment recorded and no point beyond two sigma", "adjustment_in_run"), ("no adjustment recorded", "adjustment_recorded_in_run")):
        inc = []; ids = []
        for cid, g in d.groupby("characteristic_id", sort=True):
            has = g[col].values.astype(bool)
            if has.sum() < 40 or (~has).sum() < 40:
                continue
            inc.append(g[R5].values.astype(float).var(ddof=1) / g[~has][R5].values.astype(float).var(ddof=1) - 1); ids.append(cid)
        inc = np.array(inc); r = np.random.default_rng([SEED, 50, len(out)]); by_char[name] = pd.DataFrame({"characteristic_id": ids, "added_variance": inc})
        b = np.median(inc[r.integers(0, len(inc), (2000, len(inc)))], axis=1)
        out[name] = {"comparison_runs": name, "characteristics": len(inc), "added_variance_median": float(np.median(inc)), "low": float(np.percentile(b, 2.5)), "high": float(np.percentile(b, 97.5)),
                     "characteristics_with_more_variance": int((inc > 0).sum())}
    return pd.DataFrame(out.values()), by_char["no adjustment recorded and no point beyond two sigma"]


def after_the_reaction_plan():
    """Pilot presses, April to June 2026: adjustments recorded, and what they followed."""
    return query("""
        select count(*) filter (where h.adjustment_recorded) as adjustments_recorded,
               count(*) filter (where h.adjustment_recorded and h.alarm_rule_1) as following_a_rule_1_alarm,
               count(*) filter (where h.adjustment_recorded and h.subgroup_type = 'coil-change' and not h.alarm_rule_1) as at_a_coil_change,
               count(*) filter (where h.adjustment_recorded and not h.alarm_rule_1 and h.subgroup_type <> 'coil-change') as following_neither,
               count(*) filter (where h.alarm_rule_1) as rule_1_alarms,
               count(*) filter (where h.alarm_rule_1 and h.adjustment_recorded) as rule_1_alarms_with_an_adjustment_recorded
        from intermediate.int_characteristic_history h
        where h.after_redesign and h.is_pilot_press and h.sample_time >= date '2026-04-01' and h.sample_time < date '2026-07-01'
          and h.data_type = 'variable' and h.characteristic_type not in ('burr height', 'flatness') and h.subgroup_mean is not null
          and h.characteristic_type in ('formed height', 'bend angle', 'hole-to-edge')""")


def compute():
    toward, estimate = return_toward_centre(); variance, by_characteristic = variance_in_adjusted_runs()
    return {"after_a_point": after_a_point_beyond_two_sigma(), "return_toward_centre": toward, "adjustment_estimate": estimate, "autocorrelation": autocorrelation(), "variance": variance, "variance_by_characteristic": by_characteristic, "after_the_reaction_plan": after_the_reaction_plan()}


if __name__ == "__main__":
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60)
    for name, table in compute().items():
        print(f"\n== {name}\n{table.round(4).to_string(index=False)}")
