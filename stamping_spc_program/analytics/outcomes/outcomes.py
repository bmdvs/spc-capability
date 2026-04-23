"""Outcomes: the pilot presses from March to December 2025 against the same months of 2024 and 2023, the comparison
presses from February to August, and the rollout presses from September to December, on sorting, customer PPM, scrap
and rework, production capability, burr, alarm signals and the quality cost lines as booked."""
import numpy as np
import pandas as pd
from scipy import stats as st

from analytics.data import query
from analytics.stats import wilson

SEED = 20250109
SETS = ["pilot presses", "comparison presses", "rollout presses"]
FORMED, PUNCHED = ("formed height", "bend angle"), ("hole diameter", "hole-to-edge", "hole-to-hole")
MIN_SUBGROUPS = 60
R5 = ["r1", "r2", "r3", "r4", "r5"]


def rate_test(k1, e1, k2, e2):
    """Poisson rate test, exact: given the total count, the first count is binomial with the first exposure's share."""
    if k1 + k2 == 0:
        return np.nan
    return float(st.binomtest(int(k1), int(k1 + k2), e1 / (e1 + e2)).pvalue)


def poisson_interval(k):
    return (st.chi2.ppf(0.025, 2 * k) / 2 if k else 0.0), st.chi2.ppf(0.975, 2 * k + 2) / 2


def score_test(x1, n1, x2, n2):
    """Two-proportion score test with the Newcombe interval on the difference (second less first)."""
    p1, p2, p = x1 / n1, x2 / n2, (x1 + x2) / (n1 + n2)
    z = (p2 - p1) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)); l1, u1 = wilson(x1, n1); l2, u2 = wilson(x2, n2)
    d = p2 - p1
    return float(2 * st.norm.sf(abs(z))), d - np.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2), d + np.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)


def _outcomes():
    return query("select * from marts.mart_outcomes order by press_set, period_year")


def _against(d, press_set, year, col_k, col_e=None):
    """p of the 2025 count against the given year's on the set, exposure equal periods or the named column."""
    a = d[(d["press_set"] == press_set) & (d["period_year"] == year)].iloc[0]; b = d[(d["press_set"] == press_set) & (d["period_year"] == 2025)].iloc[0]
    return rate_test(a[col_k], a[col_e] if col_e else 1.0, b[col_k], b[col_e] if col_e else 1.0)


def sorting():
    """Sorting events and quantity by press set and year, with the Poisson rate test of 2025 against each earlier year."""
    d = _outcomes(); rows = []
    for s in SETS:
        for y in (2023, 2024, 2025):
            r = d[(d["press_set"] == s) & (d["period_year"] == y)].iloc[0]; lo, hi = poisson_interval(int(r.sorting_events))
            rows.append({"press_set": s, "months": r.months, "year": y, "sorting_events": int(r.sorting_events), "low": lo, "high": hi, "quantity_sorted": int(r.quantity_sorted),
                         "quantity_per_event_median": r.quantity_sorted_median, "largest": r.quantity_sorted_largest, "cost_booked": r.sorting_cost_booked, "cost_booked_or_estimated": r.sorting_cost_booked_or_estimated,
                         "p_2025_against_this_year": _against(d, s, y, "sorting_events") if y < 2025 else np.nan})
    return pd.DataFrame(rows)


def ppm():
    """Customer PPM on the presses' parts: pieces rejected over pieces shipped, with a bootstrap interval over
    complaints and the Poisson rate test on complaint counts over shipped pieces."""
    d = _outcomes(); c = query("select press_set, period_year, quantity from marts.mart_outcome_complaints where not duplicate_entry order by press_set, period_year, complaint_id"); rows = []
    for i, s in enumerate(SETS):
        for y in (2023, 2024, 2025):
            r = d[(d["press_set"] == s) & (d["period_year"] == y)].iloc[0]; q = c[(c["press_set"] == s) & (c["period_year"] == y)]["quantity"].values.astype(float)
            g = np.random.default_rng([SEED, 20, i, y])
            tot = [g.choice(q, size=g.poisson(len(q)), replace=True).sum() for _ in range(2000)] if len(q) else [0.0]
            rows.append({"press_set": s, "months": r.months, "year": y, "complaints": int(r.complaints), "duplicate_entries_left_out": int(r.duplicate_complaint_entries), "pieces_rejected": int(r.pieces_rejected),
                         "pieces_shipped": int(r.pieces_shipped), "ppm": r.pieces_rejected / r.pieces_shipped * 1e6, "low": np.percentile(tot, 2.5) / r.pieces_shipped * 1e6, "high": np.percentile(tot, 97.5) / r.pieces_shipped * 1e6,
                         "complaints_per_million_shipped": r.complaints / r.pieces_shipped * 1e6, "p_2025_against_this_year": _against(d, s, y, "complaints", "pieces_shipped") if y < 2025 else np.nan})
    return pd.DataFrame(rows)


def scrap_and_rework():
    """Scrap and rework as booked as a share of revenue, and scrapped pieces over produced pieces with the score test."""
    d = _outcomes(); rows = []
    for s in SETS:
        b = d[(d["press_set"] == s) & (d["period_year"] == 2025)].iloc[0]
        for y in (2023, 2024, 2025):
            r = d[(d["press_set"] == s) & (d["period_year"] == y)].iloc[0]
            p, lo, hi = score_test(r.pieces_scrapped, r.pieces_produced, b.pieces_scrapped, b.pieces_produced) if y < 2025 else (np.nan, np.nan, np.nan)
            rows.append({"press_set": s, "months": r.months, "year": y, "scrap_booked": r.scrap_booked, "rework_labor_booked": r.rework_labor_booked, "revenue": r.revenue,
                         "scrap_and_rework_share_of_revenue": (r.scrap_booked + r.rework_labor_booked) / r.revenue, "pieces_scrapped": int(r.pieces_scrapped), "pieces_produced": int(r.pieces_produced),
                         "pieces_scrapped_share": r.pieces_scrapped / r.pieces_produced, "p_2025_against_this_year": p, "difference_low": lo, "difference_high": hi})
    return pd.DataFrame(rows)


def capability():
    """Production Cpk and Ppk on critical formed and punched characteristics by press set and year: the median over
    characteristics with at least 60 subgroups in the period, with a bootstrap interval over characteristics."""
    d = query(f"""
        select p.press_set, p.period_year, h.characteristic_id, h.characteristic_type, h.usl, h.lsl, h.r1, h.r2, h.r3, h.r4, h.r5
        from marts.mart_outcome_periods p join intermediate.int_characteristic_history h
          on h.is_pilot_press = p.is_pilot_press and h.sample_time >= p.period_start and h.sample_time < p.period_end
        where h.critical and h.data_type = 'variable' and h.r5 is not null and h.implausible_readings = 0 and h.lsl is not null
          and h.characteristic_type in {FORMED + PUNCHED}
        order by p.press_set, p.period_year, h.characteristic_id, h.sample_time, h.subgroup_id""")
    rows = []
    for (s, y, cid), g in d.groupby(["press_set", "period_year", "characteristic_id"], sort=True):
        if len(g) < MIN_SUBGROUPS:
            continue
        x = g[R5].values.astype(float); m = x.mean(); within = np.sqrt(x.var(axis=1, ddof=1).mean()); overall = x.std(ddof=1); near = min(g["usl"].iloc[0] - m, m - g["lsl"].iloc[0])
        rows.append({"press_set": s, "year": y, "characteristic_id": cid, "class": "formed" if g["characteristic_type"].iloc[0] in FORMED else "punched", "subgroups": len(g), "cpk": near / (3 * within), "ppk": near / (3 * overall)})
    c = pd.DataFrame(rows); out = []
    for i, ((s, cls, y), g) in enumerate(c.groupby(["press_set", "class", "year"], sort=True)):
        r = np.random.default_rng([SEED, 40, i]); pick = r.integers(0, len(g), (2000, len(g))); row = {"press_set": s, "characteristics_class": cls, "year": y, "characteristics": len(g), "subgroups": int(g["subgroups"].sum())}
        for k in ("ppk", "cpk"):
            v = g[k].values; b = np.median(v[pick], axis=1); row[k + "_median"] = float(np.median(v)); row[k + "_low"] = float(np.percentile(b, 2.5)); row[k + "_high"] = float(np.percentile(b, 97.5))
        row["characteristics_with_ppk_under_1_33"] = int((g["ppk"] < 1.33).sum()); out.append(row)
    return pd.DataFrame(out), c


def burr():
    """Burr nonconformances by where they were detected, and the sharpening intervals with a burr gauge subgroup over
    the limit before the sharpening (intervals with at least 5 burr gauge subgroups, by the period the interval ended in)."""
    d = _outcomes()[["press_set", "months", "period_year", "burr_nonconformances_at_the_press_check", "burr_nonconformances_at_the_dock_audit", "burr_nonconformances_at_the_customer"]]
    i = query("""
        with b as (select w.die_id, w.sharpening_interval_no, count(*) as subgroups, max(w.share_of_limit) as highest, bool_or(w.is_pilot_press) as on_a_pilot_press
                   from marts.mart_wear_points w where w.characteristic_type = 'burr height' group by 1, 2)
        select p.press_set, p.period_year, count(*) as intervals_with_burr_gauge_subgroups, count(*) filter (where b.highest > 1) as intervals_with_burr_over_the_limit
        from marts.mart_outcome_periods p join intermediate.int_sharpening_intervals s on s.interval_end >= p.period_start and s.interval_end < p.period_end
        join b on b.die_id = s.die_id and b.sharpening_interval_no = s.sharpening_interval_no and b.on_a_pilot_press = p.is_pilot_press
        where b.subgroups >= 5 group by 1, 2 order by 1, 2""")
    d = d.merge(i, on=["press_set", "period_year"], how="left")
    d["share_over_the_limit"] = d["intervals_with_burr_over_the_limit"] / d["intervals_with_burr_gauge_subgroups"]
    ci = [wilson(int(k), int(n)) for k, n in zip(d["intervals_with_burr_over_the_limit"], d["intervals_with_burr_gauge_subgroups"])]; d["low"], d["high"] = [c[0] for c in ci], [c[1] for c in ci]
    return d


def signals():
    """Alarm signals and recorded actions per 100 variable subgroups, with the pilot presses split by their entry before."""
    d = query("""
        select p.press_set, p.months, p.period_year, case when p.is_pilot_press then case when h.press_group = 'high_speed' then 'PR-03 (paper before)' else 'PR-06 and PR-09 (software before)' end else 'all' end as presses,
               count(*) as variable_subgroups, count(*) filter (where h.alarm_raised) as alarm_signals, count(*) filter (where h.alarm_rule_1) as rule_1_signals,
               count(*) filter (where h.alarm_raised and (h.acknowledgement_text is not null or h.adjustment_recorded)) as signals_with_an_acknowledgement_or_adjustment,
               count(*) filter (where h.alarm_raised and h.adjustment_recorded) as signals_with_an_adjustment_recorded,
               count(*) filter (where h.alarm_raised and h.acknowledgement_text is not null and lower(trim(h.acknowledgement_text)) not in ('ok', 'checked', 'adj', 'okay', 'chk')) as signals_with_a_text_beyond_ok_checked_adj
        from marts.mart_outcome_periods p join intermediate.int_characteristic_history h
          on h.is_pilot_press = p.is_pilot_press and h.sample_time >= p.period_start and h.sample_time < p.period_end
        where h.data_type = 'variable' and h.subgroup_mean is not null
        group by grouping sets ((1, 2, 3, 4), (1, 2, 3)) order by 1, 4, 3""")
    d["presses"] = d["presses"].fillna("all presses of the set")
    d = d[~((d["press_set"] != "pilot presses") & (d["presses"] == "all"))]
    d["alarm_signals_per_100_subgroups"] = d["alarm_signals"] / d["variable_subgroups"] * 100; d["rule_1_per_100_subgroups"] = d["rule_1_signals"] / d["variable_subgroups"] * 100
    d["acknowledgement_or_adjustment_share"] = d["signals_with_an_acknowledgement_or_adjustment"] / d["alarm_signals"]; d["adjustment_share"] = d["signals_with_an_adjustment_recorded"] / d["alarm_signals"]
    d["text_beyond_ok_checked_adj_share"] = d["signals_with_a_text_beyond_ok_checked_adj"] / d["alarm_signals"]
    return d


def cost_lines():
    """Quality cost lines as booked by category, press set and year, with the sorting estimate beside; the categories
    booked at plant level are given for the calendar months of each comparison."""
    d = query("""
        select p.press_set, p.months, p.period_year, l.category, sum(l.amount) as amount_booked, count(*) as lines
        from marts.mart_outcome_periods p join marts.mart_outcome_cost_lines l on l.month_start >= p.period_start and l.month_start < p.period_end and l.is_pilot_press = p.is_pilot_press
        group by 1, 2, 3, 4 order by 1, 4, 3""")
    plant = query("""
        select p.months, p.period_year, l.category, sum(l.amount) as amount_booked
        from (select distinct months, period_year, period_start, period_end from marts.mart_outcome_periods) p
        join marts.mart_outcome_cost_lines l on l.month_start >= p.period_start and l.month_start < p.period_end and l.press_id is null
        group by 1, 2, 3 order by 1, 3, 2""")
    t = d.pivot_table(index=["press_set", "category"], columns="period_year", values="amount_booked", aggfunc="sum", fill_value=0).reset_index()
    o = _outcomes(); est = o.assign(category="sorting, booked or estimated from run hours").pivot_table(index=["press_set", "category"], columns="period_year", values="sorting_cost_booked_or_estimated", aggfunc="sum").reset_index()
    return pd.concat([t, est], ignore_index=True).sort_values(["press_set", "category"]), plant.pivot_table(index=["months", "category"], columns="period_year", values="amount_booked", aggfunc="sum", fill_value=0).reset_index()


def redesign_by_class(as_at="2025-12-31"):
    """The limits in force on the pilot presses at the end of the record, by characteristic class and the method the
    limit set records, with the check frequency in the characteristics master."""
    return query("""
        select case when l.characteristic_type in ('formed height', 'bend angle') then 'formed height and bend angle'
                    when l.characteristic_type = 'hole diameter' then 'hole diameter'
                    when l.characteristic_type in ('burr height', 'flatness') then 'burr height and flatness' else 'hole position, length and width' end as characteristic_class,
               l.method as limits_basis, count(distinct l.characteristic_id) as characteristics, count(distinct l.characteristic_id) filter (where l.critical) as critical_characteristics,
               median(l.subgroups_used) as subgroups_used_median, median(l.coil_changes_spanned) as coil_changes_spanned_median, min(c.frequency_minutes) as check_frequency_minutes_in_the_master
        from marts.mart_limits_as_set l join staging.stg_spc__characteristics c using (characteristic_id)
        where l.press_id in (select press_id from intermediate.int_press_redesign where is_pilot_press)
          and l.effective_from <= cast(? as date) and (l.effective_to is null or l.effective_to > cast(? as date))
        group by 1, 2 order by 1, 2""", [as_at, as_at])


def reaction_plan():
    """The reaction plan steps as the SPC software holds them, with the characteristics each applies to."""
    return query("""select signal, step, action, owner, count(distinct characteristic_id) as characteristics, min(effective_from) as first_in_force
                    from staging.stg_spc__reaction_plan_steps group by 1, 2, 3, 4 order by 1, 2""")


def rule_1_by_month():
    """Rule 1 alarms per 100 subgroups by month on the pilot presses' formed characteristics, March to December 2025."""
    d = query("""select date_trunc('month', sample_time) as month_start, count(*) as subgroups, count(*) filter (where alarm_rule_1) as rule_1_alarms
                 from intermediate.int_characteristic_history
                 where is_pilot_press and after_redesign and data_type = 'variable' and subgroup_mean is not null and characteristic_type in ('formed height', 'bend angle')
                   and sample_time >= date '2025-03-01' and sample_time < date '2026-01-01' group by 1 order by 1""")
    d["rule_1_per_100_subgroups"] = d["rule_1_alarms"] / d["subgroups"] * 100
    return d


def pilot_complaints_by_month():
    """Complaints received by month on the pilot presses' parts, duplicate entries left out."""
    return query("""
        with c as (select c.*, row_number() over (partition by c.customer_id, c.part_id, c.run_ids, c.quantity, c.defect_code order by c.received, c.complaint_id) > 1 as duplicate_entry
                   from staging.stg_qms__complaints c)
        select date_trunc('month', c.received) as month_start, count(*) as complaints
        from c join intermediate.int_run_shots r on r.run_id = split_part(c.run_ids, ';', 1) join intermediate.int_press_redesign x using (press_id)
        where x.is_pilot_press and not c.duplicate_entry and c.received >= date '2023-01-01' and c.received < date '2026-01-01' group by 1 order by 1""")


def sharpening_at_the_count():
    """Sharpenings logged as made at the count from the burr regression, by whether the die runs on a pilot press."""
    return query("""
        with d as (select die_id, bool_or(press_id in (select press_id from intermediate.int_press_redesign where is_pilot_press)) as on_a_pilot_press
                   from intermediate.int_run_shots where production_start >= date '2025-01-01' group by 1)
        select case when d.on_a_pilot_press then 'pilot presses' else 'other presses' end as dies_on, count(*) as sharpenings_at_the_count, min(e.event_date) as first_logged
        from intermediate.int_die_event_timeline e join d using (die_id)
        where e.event_type = 'sharpening' and e.notes like '%burr regression%' group by 1 order by 1 desc""")


def pilot_sorting_starts(year=2025):
    """Sorting events on the pilot presses in March to December of the year, by whether they started before per-stroke monitoring."""
    return query("""select count(*) as sorting_events, count(*) filter (where sort_started < date '2025-05-05') as started_before_per_stroke_monitoring,
                           count(*) filter (where month(sort_started) = 3) as started_in_march
                    from marts.mart_sorting_events where is_pilot_press and sort_started >= make_date(?, 3, 1) and sort_started < make_date(? + 1, 1, 1)""", [year, year])


def compute():
    cap, by_characteristic = capability(); lines, plant = cost_lines()
    return {"sorting": sorting(), "ppm": ppm(), "scrap_and_rework": scrap_and_rework(), "capability": cap, "capability_by_characteristic": by_characteristic, "burr": burr(), "signals": signals(),
            "cost_lines": lines, "cost_lines_plant_level": plant, "redesign_by_class": redesign_by_class(), "reaction_plan": reaction_plan(), "rule_1_by_month": rule_1_by_month(), "pilot_complaints_by_month": pilot_complaints_by_month(), "sharpening_at_the_count": sharpening_at_the_count(), "pilot_sorting_starts": pilot_sorting_starts()}


if __name__ == "__main__":
    pd.set_option("display.width", 340); pd.set_option("display.max_columns", 60); pd.set_option("display.max_colwidth", 50)
    for name, table in compute().items():
        if name == "capability_by_characteristic":
            continue
        print(f"\n== {name}\n{table.round(4).to_string(index=False)}")
