"""Per-stroke monitoring on the pilot presses from 1 April 2026: the autocorrelation of per-stroke tonnage, every stop by
the per-stroke charts with the toolmaker's finding, punch replacements by what led to them, the channel drop and the
strokes to the stop at punch breaks, the rise of the total before a worn punch was found, and the parts between a
nonconformance arising and its finding under the hourly check against the stop."""
import numpy as np
import pandas as pd
from scipy import stats as st

from analytics.data import query

MONITORING_FROM = "2026-04-01"
DESIGN_ARL_STROKES = 500_000          # the combined in-control average run length the charts were designed to, at least
STEP_SIGMA = 4.0                      # a channel share further than this from its level before the stop is part of the step
LEVEL_FROM, LEVEL_TO = 300, 21        # strokes before the stop that give a channel's level and spread before a step
RISE_LAST, RISE_EARLY_FROM, RISE_EARLY_TO = 200, 6500, 5500


def poisson_interval(k, exposure):
    lo = st.chi2.ppf(0.025, 2 * k) / 2 if k else 0.0
    return lo / exposure, st.chi2.ppf(0.975, 2 * k + 2) / 2 / exposure


def tonnage_by_press():
    """Lag-1 autocorrelation of the per-stroke total within a run, the first-order autoregressive coefficient on the
    first 500 production strokes, and the coefficient of variation, by press."""
    d = query("""
        select coalesce(press_id, 'pilot presses') as press_id, count(*) as runs, sum(production_strokes) as production_strokes, sum(setup_strokes) as setup_strokes_set_aside,
               median(lag_1_autocorrelation) as lag_1_autocorrelation_median, min(lag_1_autocorrelation) as lowest, max(lag_1_autocorrelation) as highest,
               median(baseline_lag_1_autocorrelation) as ar1_coefficient_first_500_median,
               quantile_cont(baseline_lag_1_autocorrelation, 0.1) as ar1_p10, quantile_cont(baseline_lag_1_autocorrelation, 0.9) as ar1_p90,
               median(total_kn_sd / total_kn_mean) as coefficient_of_variation_median
        from marts.mart_per_stroke_run_tonnage group by grouping sets ((press_id), ()) order by 1""")
    return d


def stops():
    """Every stop by the per-stroke charts: chart by finding, and by press."""
    d = query("select * from marts.mart_per_stroke_stops order by stopped_at, fault_event_id")
    by_chart = d.pivot_table(index="chart", columns="finding", values="fault_event_id", aggfunc="count", fill_value=0)
    by_chart["stops"] = by_chart.sum(axis=1); by_chart.loc["both charts"] = by_chart.sum(axis=0)
    by_press = d.pivot_table(index="press_id", columns="finding", values="fault_event_id", aggfunc="count", fill_value=0); by_press["stops"] = by_press.sum(axis=1)
    strokes = query("select press_id, sum(production_strokes) as production_strokes from marts.mart_per_stroke_run_tonnage group by 1 order by 1").set_index("press_id")["production_strokes"]
    rows = []
    for press in list(by_press.index) + ["pilot presses"]:
        k = int(by_press["nothing found"].sum() if press == "pilot presses" else by_press.loc[press, "nothing found"]); n = float(strokes.sum() if press == "pilot presses" else strokes[press])
        total = int(by_press["stops"].sum() if press == "pilot presses" else by_press.loc[press, "stops"]); lo, hi = poisson_interval(k, n / 1e6)
        rows.append({"press_id": press, "production_strokes": int(n), "stops": total, "stops_per_million_strokes": total / n * 1e6, "stops_with_nothing_found": k,
                     "nothing_found_per_million_strokes": k / n * 1e6, "low": lo, "high": hi, "strokes_per_stop_with_nothing_found": n / k if k else np.nan,
                     "design_false_signals_per_million_at_most": 1e6 / DESIGN_ARL_STROKES})
    return by_chart.reset_index(), by_press.reset_index(), pd.DataFrame(rows), d


def punch_replacements():
    """Punch replacements on the dies run on the pilot presses, by what led to them: the months of per-stroke
    monitoring against the same months of the two years before."""
    return query(f"""
        with dies as (select distinct die_id from intermediate.int_run_shots where press_id in (select press_id from intermediate.int_press_redesign where is_pilot_press)
                      and production_start >= date '2024-01-01'),
        e as (select e.*, year(e.event_date) as event_year from intermediate.int_die_event_timeline e join dies using (die_id)
              where e.event_type = 'punch replacement' and month(e.event_date) between 4 and 6)
        select event_year, case when fault_event_id is not null then 'after a stop by the per-stroke charts'
                                when notes like '%sharpening%' then 'at a sharpening'
                                when notes like '%nonconforming%' then 'after nonconforming parts'
                                else notes end as led_by, count(*) as punch_replacements
        from e group by 1, 2 order by 1, 3 desc""")


def punch_breaks(stop_rows):
    """Stops at which the toolmaker found a chipped punch: the channel whose share stepped, the fall in its peak, and
    the strokes from the step to the stop."""
    rows = []
    for r in stop_rows[stop_rows["finding"] == "punch chipped and replaced"].itertuples():
        s = query("select * from marts.mart_per_stroke_stop_strokes where fault_event_id = ? and strokes_before_the_stop <= ? order by stroke_no", [r.fault_event_id, LEVEL_FROM])
        chans = [c for c in ("ch1", "ch2", "ch3", "ch4") if s[f"share_{c}"].notna().all()]
        before = s[s["strokes_before_the_stop"] >= LEVEL_TO]; best = None
        for c in chans:          # the channel that stepped is the one whose own peak fell furthest at the stop; the others' shares rise with it
            m, sd = before[f"share_{c}"].mean(), before[f"share_{c}"].std(ddof=1); z = (s[f"share_{c}"].values - m) / sd
            fall = 1 - s[f"peak_kn_{c}"].values[-1] / before[f"peak_kn_{c}"].mean()
            if best is None or fall > best[2]:
                best = (c, z, fall)
        c, z, _ = best; sign = np.sign(z[-1]); n = 0
        for v in z[::-1]:
            if v * sign > STEP_SIGMA:
                n += 1
            else:
                break
        peak_before = before[f"peak_kn_{c}"].mean(); peak_after = s[f"peak_kn_{c}"].values[-max(n, 1):].mean()
        rows.append({"fault_event_id": r.fault_event_id, "press_id": r.press_id, "run_id": r.run_id, "die_id": r.die_id, "chart": r.chart, "channel": c, "share_at_the_stop_in_sigma": float(z[-1]),
                     "channel_peak_before_kn": peak_before, "channel_peak_from_the_step_kn": peak_after, "fall_in_the_channel_peak": 1 - peak_after / peak_before,
                     "strokes_from_the_step_to_the_stop": n, "parts_per_stroke": r.parts_per_stroke})
    return pd.DataFrame(rows)


def rise_before_a_worn_punch(stop_rows):
    """Stops at which the toolmaker found a worn punch: the total over the last 200 strokes against the run's first 500
    production strokes and against the strokes 6,500 to 5,500 before the stop, where the run has them."""
    base = query("select run_id, baseline_total_kn_mean from marts.mart_per_stroke_run_tonnage").set_index("run_id")["baseline_total_kn_mean"]
    agg = query(f"""select fault_event_id, avg(total_kn) filter (where strokes_before_the_stop < {RISE_LAST}) as total_last,
                           avg(total_kn) filter (where strokes_before_the_stop between {RISE_EARLY_TO} and {RISE_EARLY_FROM}) as total_early,
                           count(*) filter (where strokes_before_the_stop between {RISE_EARLY_TO} and {RISE_EARLY_FROM}) as early_strokes
                    from marts.mart_per_stroke_stop_strokes group by 1""").set_index("fault_event_id")
    d = stop_rows[stop_rows["finding"].isin(["punch worn and replaced", "nothing found", "slug pulling cleared"])].copy()
    d["rise_against_the_first_500"] = [agg.loc[f, "total_last"] / base[r] - 1 for f, r in zip(d["fault_event_id"], d["run_id"])]
    d["rise_over_the_last_6000"] = [agg.loc[f, "total_last"] / agg.loc[f, "total_early"] - 1 if agg.loc[f, "early_strokes"] >= 900 else np.nan for f in d["fault_event_id"]]
    g = d.groupby(["finding", "chart"], as_index=False).agg(
        stops=("fault_event_id", "count"), rise_against_the_first_500_median=("rise_against_the_first_500", "median"),
        rise_p10=("rise_against_the_first_500", lambda x: x.quantile(0.1)), rise_p90=("rise_against_the_first_500", lambda x: x.quantile(0.9)),
        with_a_rise_of_3pct_or_more=("rise_against_the_first_500", lambda x: int((x >= 0.03).sum())),
        with_6000_strokes_before=("rise_over_the_last_6000", "count"), rise_over_the_last_6000_median=("rise_over_the_last_6000", "median"))
    return g, d[["fault_event_id", "press_id", "run_id", "chart", "finding", "rise_against_the_first_500", "rise_over_the_last_6000"]]


def parts_before_the_finding(breaks):
    """Parts made between a nonconformance arising and its finding: sorting events found at the press on the pilot
    presses under the hourly check, and after per-stroke monitoring; and the strokes from the step to the stop at the
    punch breaks the charts stopped."""
    s = query(f"""
        select case when found_at < date '{MONITORING_FROM}' then 'before per-stroke monitoring, 2024 to 31 March 2026' else 'under per-stroke monitoring, from 1 April 2026' end as period,
               count(*) as sorting_events_found_at_the_press, median(parts_from_check_before_to_finding_at_the_realised_rate) as parts_since_the_check_before_median,
               median(quantity_sorted) as quantity_sorted_median, max(quantity_sorted) as quantity_sorted_largest, sum(quantity_sorted) as quantity_sorted_total
        from marts.mart_sorting_events where is_pilot_press and detected_at <> 'customer' group by 1 order by 1""")
    b = pd.DataFrame([{"punch_breaks_stopped_by_the_charts": len(breaks), "strokes_from_the_step_to_the_stop_median": breaks["strokes_from_the_step_to_the_stop"].median(),
                       "strokes_largest": breaks["strokes_from_the_step_to_the_stop"].max(), "stopped_within_3_strokes": int((breaks["strokes_from_the_step_to_the_stop"] <= 3).sum()),
                       "parts_from_the_step_to_the_stop_median": (breaks["strokes_from_the_step_to_the_stop"] * breaks["parts_per_stroke"]).median(),
                       "parts_largest": (breaks["strokes_from_the_step_to_the_stop"] * breaks["parts_per_stroke"]).max(),
                       "fall_in_the_channel_peak_median": breaks["fall_in_the_channel_peak"].median(), "fall_lowest": breaks["fall_in_the_channel_peak"].min(), "fall_highest": breaks["fall_in_the_channel_peak"].max()}])
    return s, b


def sorting_under_monitoring():
    """The sorting events found at the press on the pilot presses under per-stroke monitoring, as the QMS records them."""
    return query(f"""select sorting_event_id, press_id, found_at, defect_code, quantity_affected, quantity_sorted, quantity_rejected, sort_basis, die_event_notes
                     from marts.mart_sorting_events where is_pilot_press and detected_at <> 'customer' and found_at >= date '{MONITORING_FROM}' order by found_at""")


def compute():
    by_chart, by_press, rates, stop_rows = stops(); breaks = punch_breaks(stop_rows); rise, rise_rows = rise_before_a_worn_punch(stop_rows); sorts, break_summary = parts_before_the_finding(breaks)
    return {"tonnage_by_press": tonnage_by_press(), "stops_by_chart": by_chart, "stops_by_press": by_press, "stops_with_nothing_found": rates, "punch_replacements": punch_replacements(),
            "punch_breaks": breaks, "punch_break_summary": break_summary, "rise_before_the_stop": rise, "rise_rows": rise_rows, "sorting_before_and_under_monitoring": sorts, "sorting_under_monitoring": sorting_under_monitoring(), "stop_rows": stop_rows}


if __name__ == "__main__":
    pd.set_option("display.width", 320); pd.set_option("display.max_columns", 60); pd.set_option("display.max_colwidth", 60)
    for name, table in compute().items():
        if name in ("stop_rows", "rise_rows"):
            continue
        print(f"\n== {name}\n{table.round(4).to_string(index=False)}")
