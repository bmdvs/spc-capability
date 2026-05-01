"""SPC Monthly Summary, December 2025: the page. Reads the summary tables, builds the figures and writes
docs/monthly_summary/spc_monthly_summary_2025_12.html and the table of every number in the text with the table it is read from."""
import pandas as pd

from analytics.monthly_summary import figures, monthly_summary
from analytics.reports.assessment import F0, FIGURE, P1, SECTION, TRACE, exhibit, num, pct, section, show, titled_table
from analytics.style import style as S

PILOT = ["PR-03", "PR-06", "PR-09"]
WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
LAB = {"month": "Dec 2025", "month_before": "Nov 2025", "twelve_months": "2025", "twelve_months_before": "2024"}
ORDER = list(LAB)


def word(n, src, cap=False):
    """A count written as a word, traced as the count."""
    w = WORDS[int(n)]; TRACE.append((SECTION[0], str(int(n)), src))
    return w.capitalize() if cap else w


def F1(v):
    return f"{v:.1f}"


def F2(v):
    return f"{v:.2f}"


def wide(d, index, values, fmt, periods=ORDER):
    """One row per index value, one column per period and value."""
    cols = {}
    for p in periods:
        g = d[d["period"] == p].set_index(index)
        for v, name in values:
            cols[f"{name}, {LAB[p]}"] = g[v].map(lambda x, f=fmt.get(v, str): "" if x != x else f(x))
    return pd.DataFrame(cols).fillna("").reset_index()


def split(w, names):
    w[list(names)] = w["key"].str.split(" | ", regex=False, expand=True)
    return w[list(names) + [c for c in w.columns if c not in ("key",) + tuple(names)]]


def tables(t):
    """Every table of the summary as a display frame, keyed as in the layout."""
    T = {}
    al = t["alarms"]; ala = al[al["press_id"] == "all presses"].set_index("period")
    pl = t["planned_checks"]; pla = pl[(pl["press_id"] == "all presses") & (pl["shift"] == "both shifts")].set_index("period")
    fc = t["first_check_of_the_shift"]; fca = fc[fc["press_id"] == "all presses"].groupby("period")[["planned_checks", "recorded"]].sum(); fca["share"] = fca["recorded"] / fca["planned_checks"]
    en = t["entries_after_the_parts"]; ena = en[en["press_id"] == "all presses"].set_index(["period", "entry_method"])
    cp = t["capability_plant"].set_index("characteristic_class"); sh = t["sharpenings_against_the_due_count"].set_index("against_the_due_count"); bu = t["burr_over_the_limit"].set_index("period")
    pu = t["punch_replacements"].set_index("led_by"); lim = t["limits_recalculated_by_month"].set_index("month_start")["charts"]; stm = t["stops_in_the_month"]; st12 = t["stops_twelve_months"]; sbm = t["stops_by_month"].set_index("month_start")

    def per(fn):
        return [fn(p) for p in ORDER]

    def on_time(p):
        a, b = sh.loc["at or before the due count", p], sh.loc["after the due count", p]
        return f"{a / (a + b) * 100:.0f}% ({a} of {a + b})"
    head = [
        ["2", "Ppk, critical formed characteristics, median", "", "", f"{cp.loc['formed', 'ppk_median']:.2f} ({cp.loc['formed', 'characteristics']} characteristics)", f"{cp.loc['formed', 'ppk_median_twelve_months_before']:.2f} ({cp.loc['formed', 'characteristics_twelve_months_before']})"],
        ["2", "Ppk, critical punched characteristics, median", "", "", f"{cp.loc['punched', 'ppk_median']:.2f} ({cp.loc['punched', 'characteristics']})", f"{cp.loc['punched', 'ppk_median_twelve_months_before']:.2f} ({cp.loc['punched', 'characteristics_twelve_months_before']})"],
        ["2", "Critical characteristics with Ppk under 1.33", "", "", f"{cp['ppk_under_1_33'].sum()} of {cp['characteristics'].sum()}", f"{cp['ppk_under_1_33_twelve_months_before'].sum()} of {cp['characteristics_twelve_months_before'].sum()}"],
        ["3", "Alarm signals per 100 subgroups"] + per(lambda p: F1(ala.loc[p, "alarm_signals_per_100_subgroups"])),
        ["3", "Alarm signals with an adjustment recorded"] + per(lambda p: P1(ala.loc[p, "adjustment_share"])),
        ["3", "Alarm signals with an acknowledgement or adjustment"] + per(lambda p: P1(ala.loc[p, "acknowledgement_or_adjustment_share"])),
        ["3", "Alarm signals with nothing recorded"] + per(lambda p: F0(ala.loc[p, "with_nothing_recorded"])),
        ["4", "Planned checks recorded"] + per(lambda p: P1(pla.loc[p, "recorded_share"])),
        ["4", "First check of each shift recorded"] + per(lambda p: P1(fca.loc[p, "share"])),
        ["4", "Entries more than 20 minutes after the parts, gauge-connected"] + per(lambda p: P1(ena.loc[(p, "gauge-connected"), "share"]) if (p, "gauge-connected") in ena.index else ""),
        ["4", "Entries more than 20 minutes after the parts, keyed"] + per(lambda p: P1(ena.loc[(p, "keyed"), "share"])),
        ["5", "Charts recalculated", str(int(lim.iloc[-1])), str(int(lim.iloc[-2])), f"{int(lim.sum())} recalculations, February to December", "none (fixed limits from 3 February 2025)"],
        ["5", "Charts due for recalculation at 31 December", str(len(t["limits_due"])), "", "", ""],
        ["6", "Sharpenings at or before the due count"] + per(on_time),
        ["6", "Sharpening intervals with burr over the limit"] + per(lambda p: f"{bu.loc[p, 'intervals_with_burr_over_the_limit']} of {bu.loc[p, 'intervals_with_burr_gauge_subgroups']}"),
        ["6", "Per-stroke stops", str(int(stm["stops"].sum())), str(int(sbm["stops"].iloc[-2])), str(int(st12["stops"].sum())), "none (monitoring from 5 May 2025)"],
        ["6", "Per-stroke stops with nothing found", str(int(stm["nothing found"].sum())), str(int(sbm["nothing_found"].iloc[-2])), str(int(st12[st12["finding"] == "nothing found"]["stops"].sum())), ""],
        ["6", "Punch replacements"] + per(lambda p: str(int(pu[p].sum()))),
    ]
    T["C-1"] = pd.DataFrame(head, columns=["Section", "Measure"] + [LAB[p] for p in ORDER])
    T["C-3"] = t["capability_by_press"].rename(columns={"press_id": "Press", "characteristic_class": "Class", "characteristics": "Characteristics", "subgroups": "Subgroups", "ppk_median": "Ppk, median, 2025", "cpk_median": "Cpk, median, 2025", "ppk_under_1_33": "Ppk under 1.33",
                                                         "characteristics_twelve_months_before": "Characteristics, 2024", "ppk_median_twelve_months_before": "Ppk, median, 2024", "ppk_under_1_33_twelve_months_before": "Under 1.33, 2024"})
    T["C-4"] = t["capability_under_1_33"][["part_id", "characteristic_id", "characteristic_name", "press_id", "chart", "ppk", "cpk", "subgroups"]].rename(columns={"part_id": "Part", "characteristic_id": "Characteristic", "characteristic_name": "Name", "press_id": "Press", "chart": "Chart", "ppk": "Ppk", "cpk": "Cpk", "subgroups": "Subgroups"})
    T["C-5"] = wide(al, "press_id", [("variable_subgroups", "Subgroups"), ("alarm_signals_per_100_subgroups", "Alarm signals per 100"), ("adjustment_share", "With an adjustment"), ("acknowledgement_or_adjustment_share", "With an acknowledgement or adjustment")],
                    {"variable_subgroups": F0, "alarm_signals_per_100_subgroups": F1, "adjustment_share": P1, "acknowledgement_or_adjustment_share": P1}, ["month", "twelve_months", "twelve_months_before"]).rename(columns={"press_id": "Press"})
    dec = al[al["period"] == "month"]
    T["C-6"] = dec[["press_id", "alarm_signals", "with_nothing_recorded", "subgroups_with_a_pattern_shown", "rule_2", "rule_3", "rule_4"]].rename(columns={"press_id": "Press", "alarm_signals": "Alarm signals", "with_nothing_recorded": "With nothing recorded",
                                                                                                                                                       "subgroups_with_a_pattern_shown": "Subgroups with a pattern shown", "rule_2": "Rule 2", "rule_3": "Rule 3", "rule_4": "Rule 4"})
    T["C-7"] = t["alarms_with_nothing_recorded"].assign(sample_time=lambda x: x["sample_time"].map(lambda v: str(v)[:16]), critical=lambda x: x["critical"].map({True: "yes", False: ""})).rename(
        columns={"press_id": "Press", "part_id": "Part", "characteristic_id": "Characteristic", "characteristic_name": "Name", "sample_time": "Time", "subgroup_type": "Subgroup", "operator_id": "Operator", "rule": "Rule", "critical": "Critical"})
    three = ["month", "twelve_months", "twelve_months_before"]
    T["C-8"] = split(wide(pl.assign(key=pl["press_id"] + " | " + pl["shift"]), "key", [("planned_checks", "Planned"), ("recorded_share", "Recorded")], {"planned_checks": F0, "recorded_share": P1}, three), ("Press", "Shift"))
    T["C-9"] = split(wide(fc.assign(key=fc["press_id"] + " | " + fc["shift"]), "key", [("planned_checks", "Planned"), ("recorded_share", "Recorded")], {"planned_checks": F0, "recorded_share": P1}, three), ("Press", "Shift"))
    T["C-10"] = split(wide(en.assign(key=en["press_id"] + " | " + en["entry_method"]), "key", [("subgroups", "Subgroups"), ("share", "More than 20 minutes after")], {"subgroups": F0, "share": P1}, three), ("Press", "Entry"))
    T["C-11"] = t["limits_recalculated"].rename(columns={"press_id": "Press", "method": "Limits basis", "charts_recalculated": "Charts recalculated", "charts_with_first_limits_under_the_redesign": "Charts with first limits under the redesign", "dies": "Dies"})
    T["C-12"] = t["limits_status"].pivot_table(index=["press_id", "chart"], columns="status", values="charts", aggfunc="sum", fill_value=0).reset_index().rename(
        columns={"press_id": "Press", "chart": "Chart", "baseline not yet complete on the new edge": "Limits from before the last sharpening, baseline not yet complete", "set on the current edge": "Limits set on the current edge"})
    T["C-12"]["Due for recalculation"] = 0 if t["limits_due"].empty else T["C-12"].apply(lambda r: int(((t["limits_due"]["press_id"] == r["Press"]) & (t["limits_due"]["chart"] == r["Chart"])).sum()), axis=1)
    T["C-13"] = t["sharpenings_against_the_due_count"].rename(columns={"against_the_due_count": "Sharpening", **LAB})
    sm = t["sharpenings_in_the_month"]
    T["C-14"] = pd.DataFrame({"Sharpened": sm["sharpened"].map(lambda v: str(v)[:10]), "Press": sm["press_id"], "Die": sm["die_id"], "Shots in the interval": sm["shots_in_interval_logged"].map(F0),
                              "Due count (burr at 80% of the limit)": sm["shots_at_80pct_of_limit"].map(lambda v: "" if v != v else F0(v)), "Against the due count": sm["against_the_due_count"]})
    T["C-15"] = t["burr_over_the_limit"].assign(period=lambda x: x["period"].map(LAB)).rename(columns={"period": "Period", "intervals_with_burr_gauge_subgroups": "Sharpening intervals with burr gauge subgroups", "intervals_with_burr_over_the_limit": "With burr over the limit"})
    dd = t["dies_due"]
    T["C-16"] = pd.DataFrame({"Press": dd["press_id"], "Die": dd["die_id"], "Part": dd["part_id"], "Last sharpening": dd["last_sharpening"].map(lambda v: str(v)[:10]), "Shots since": dd["shots_since_sharpening"].map(F0), "Due count": dd["shots_at_80pct_of_limit"].map(F0),
                              "Shots to the due count": dd["shots_to_the_due_count"].map(F0), "Strokes a day in December": [F0(v) if run else "not run in December" for v, run in zip(dd["strokes_a_day"], dd["run_in_the_month"])],
                              "Days to the due count": ["past due" if s == "past due" else F1(v) for s, v in zip(dd["status"], dd["days_to_the_due_count"])]})
    T["C-17"] = stm.assign(is_pilot_press=lambda x: x["is_pilot_press"].map({True: "historian", False: "fault events"})).rename(columns={"press_id": "Press", "is_pilot_press": "Source", "nothing found": "Nothing found", "punch chipped and replaced": "Punch chipped and replaced",
                                                                                                                                    "punch worn and replaced": "Punch worn and replaced", "slug pulling cleared": "Slug pulling cleared", "stops": "Stops"})
    T["C-18"] = t["punch_replacements"].rename(columns={"led_by": "Punch replacement", **LAB})
    g = t["gauges_past_due_or_out_of_service"]; lost = set(t["gauges_not_active"]["gauge_id"])
    T["C-19"] = pd.DataFrame({"Gauge": g["gauge_id"], "Type": g["type"], "Location": g["location"], "Calibration due": g["due"].map(lambda v: str(v)[:10]), "Removed from service": g["removed_from_service"].map(lambda v: "" if v != v or v is pd.NaT else str(v)[:10]),
                              "Recorded as": g["gauge_id"].map(lambda v: "lost" if v in lost else "")})
    T["C-20"] = wide(t["subgroups_on_gauges"], "press_id", [("subgroups", "Subgroups"), ("on_a_gauge_past_due", "On a gauge past calibration due"), ("on_a_gauge_out_of_service", "On a gauge out of service"), ("on_a_gauge_past_due_or_out_of_service", "Past due or out of service")],
                     {k: F0 for k in ("subgroups", "on_a_gauge_past_due", "on_a_gauge_out_of_service", "on_a_gauge_past_due_or_out_of_service")}, ["month", "twelve_months"]).rename(columns={"press_id": "Press"})
    T["C-21"] = t["check_fixtures_by_grr"].rename(columns={"status": "Latest %GRR of tolerance", "check_fixtures": "Check fixtures"})
    fx = t["check_fixtures_at_10pct_or_more"]
    T["C-21b"] = pd.DataFrame({"Check fixture": fx["fixture_id"], "Part": fx["part_id"], "Press": fx["press_id"], "Study": fx["study_date"].map(lambda v: str(v)[:10]), "Trigger": fx["study_trigger"], "%GRR of tolerance": fx["pct_grr_of_tolerance"].map(F1), "ndc": fx["ndc"]})
    T["C-22"] = t["characteristics_on_a_gauge_with_no_study"].rename(columns={"press_id": "Press", "gauge_type": "Gauge type", "characteristics": "Characteristics", "critical_characteristics": "Critical", "gauges": "Gauges", "parts": "Parts"})
    T["C-23"] = wide(t["nonconformances_by_press"], "press_id", [("sorting_events", "Sorting events"), ("burr_nonconformances", "Burr nonconformances")], {"sorting_events": F0, "burr_nonconformances": F0}).rename(columns={"press_id": "Press"})
    b = t["burr_nonconformances"]
    T["C-24"] = pd.DataFrame({"Opened": b["opened"].map(lambda v: str(v)[:10]), "Press": b["press_id"], "Part": b["part_id"], "Die": b["die_id"], "Detected at": b["detected_at"], "Quantity": b["quantity_affected"].map(F0),
                              "Shots since sharpening over the stated interval": b["position_in_the_stated_interval"].map(lambda v: "" if v != v else F2(v)), "Over the due count": b["position_against_the_due_count"].map(lambda v: "" if v != v else F2(v))})
    return T


DEFINITIONS = ("<p>Periods are December 2025, November 2025, 2025 (the twelve months to December) and 2024 (the twelve months before), on all eleven presses. The redesign took effect on PR-03, PR-06 and PR-09 on 3 February 2025 and on the other eight presses on 2 September 2025, so 2025 spans both practices. "
               "An alarm signal is a subgroup on a variable characteristic with an alarm raised under the limits in force at entry; it has nothing recorded when it carries no acknowledgement text and no adjustment. A pattern is a subgroup shown on rules 2 to 4. "
               "A planned check falls on the clock at the part's check frequency between 06:00 and 23:00 on a day the press recorded a check, on runs of two hours or more, and is recorded when the run carries a routine check from 6 minutes before it to 31 minutes after; the first check of the shift is the 06:00 planned time on days and the 15:00 planned time on nights. "
               "Production Cpk and Ppk are on critical variable characteristics with 60 subgroups or more in the period: within-subgroup sigma pooled across subgroups, overall sigma from all readings, medians over characteristics. A single month does not carry 60 subgroups on most characteristics, so capability is stated for 2025 and 2024 only. "
               "A chart is recalculated when a new limit set takes effect on it in the month; a chart's first limits under the redesign are counted beside. A chart is due for recalculation when its limits in force predate the die's last sharpening and its baseline on the new edge is complete: 25 subgroups on an X-bar and R chart, 25 subgroups and six coil changes on a three-way chart. Tool-wear charts recalculate on a planned trigger and are not classed. "
               "The due count of a die is the shot count at which its burr line reaches 80% of the burr limit, counted from the last sharpening; a sharpening is at or before the due count when the logged shots of the run interval it ends are at or under it. A die is due in January when its shots to the due count, over its strokes per calendar day in December, come to 31 days or fewer. "
               "A sharpening interval has burr over the limit when a burr gauge subgroup mean in it is over the limit, on intervals with five burr gauge subgroups or more. Per-stroke stops are from the historian on PR-03, PR-06 and PR-09 and from the fault events on the other presses. "
               "A gauge is past calibration due at 31 December when its due date has passed with no calibration done. A subgroup is on a gauge past calibration due when the gauge's due date had passed on the subgroup's date with no calibration done by then, calibrations still open at 31 December included; out of service is as flagged in the SPC record. "
               "A gauge study is the latest on the check fixture, by the ANOVA method, %GRR of tolerance at 6 sigma. A burr nonconformance's position is the die's shots since sharpening at the end of its run over the stated sharpening interval, and over the due count. Customer PPM, scrap and rework, and cost lines are in the SPC Redesign and Results report.</p>")


def build():
    TRACE.clear(); FIGURE[0] = 0
    t = monthly_summary.compute(); f = figures.build(t); T = tables(t); body = []
    al = t["alarms"]; ala = al[al["press_id"] == "all presses"].set_index("period"); alp = al[(al["period"] == "month") & (al["press_id"] != "all presses")].set_index("press_id")
    pl = t["planned_checks"]; pla = pl[pl["press_id"] == "all presses"].set_index(["period", "shift"]); fc = t["first_check_of_the_shift"]; fca = fc[fc["press_id"] == "all presses"].set_index(["period", "shift"])
    en = t["entries_after_the_parts"]; ena = en[en["press_id"] == "all presses"].set_index(["period", "entry_method"]); cp = t["capability_plant"].set_index("characteristic_class"); u = t["capability_under_1_33"]
    sh = t["sharpenings_against_the_due_count"].set_index("against_the_due_count"); bu = t["burr_over_the_limit"].set_index("period"); nc = t["nonconformances_by_press"]; nca = nc[nc["press_id"] == "all presses"].set_index("period")
    dd = t["dies_due"]; past = dd[dd["status"] == "past due"]; g = t["gauges_past_due_or_out_of_service"]; lr = t["limits_recalculated"]; lra = lr[lr["press_id"] == "all presses"].set_index("method")
    M, B, Y, Y0 = "month", "month_before", "twelve_months", "twelve_months_before"
    on, late = int(sh.loc["at or before the due count", M]), int(sh.loc["after the due count", M]); on0, late0 = int(sh.loc["at or before the due count", Y0]), int(sh.loc["after the due count", Y0])
    under, total = int(cp["ppk_under_1_33"].sum()), int(cp["characteristics"].sum())

    # -- 1. Summary ----------------------------------------------------------
    body.append(section("summary", "1. Summary"))
    assert nca.loc[M, "sorting_events"] == 0 and nca.loc[M, "burr_nonconformances"] == 0 and bu.loc[M, "intervals_with_burr_over_the_limit"] == 0 and len(al[al["period"] == M]) == 12
    body.append(f"<p>In December the SPC program ran at the level set by the redesign on all eleven presses. Alarm signals were {num(ala.loc[M, 'alarm_signals_per_100_subgroups'], 'alarms.alarm_signals_per_100_subgroups, December', '{:.1f}')} per 100 subgroups against "
                f"{num(ala.loc[Y0, 'alarm_signals_per_100_subgroups'], 'alarms.alarm_signals_per_100_subgroups, 2024', '{:.1f}')} in 2024, with an acknowledgement or adjustment on {pct(ala.loc[M, 'acknowledgement_or_adjustment_share'], 'alarms.acknowledgement_or_adjustment_share, December')}. "
                f"{pct(pla.loc[(M, 'both shifts'), 'recorded_share'], 'planned_checks.recorded_share, December', 1)} of planned checks were recorded, against {pct(pla.loc[(Y0, 'both shifts'), 'recorded_share'], 'planned_checks.recorded_share, 2024', 1)}.</p>")
    body.append(f"<p>Die wear held at the sharpening count. {num(on, 'sharpenings_against_the_due_count: at or before, December')} of {num(on + late, 'sharpenings_against_the_due_count: with a burr line, December')} December sharpenings came at or before the die's due count, against "
                f"{num(on0, 'sharpenings_against_the_due_count: at or before, 2024')} of {num(on0 + late0, 'sharpenings_against_the_due_count: with a burr line, 2024')} in 2024. No sharpening interval ended with burr over the limit, and there were no burr nonconformances or sorting events.</p>")
    body.append(f"<p>Four items remain open at month end. {num(under, 'capability_plant.ppk_under_1_33, 2025')} of {num(total, 'capability_plant.characteristics, 2025')} critical characteristics have production Ppk under 1.33 over 2025. "
                f"{word(len(past), 'dies_due: past due', True)} dies are past their due count. {word(int(g['past_due'].sum()), 'gauges_past_due_or_out_of_service: past due', True)} gauges are past calibration due. "
                f"Keyed entries made more than 20 minutes after the parts remain at {pct(ena.loc[(M, 'keyed'), 'share'], 'entries_after_the_parts.share, keyed, December', 1)}.</p>")
    body.append(titled_table("SPC measures, December 2025", S.table(T["C-1"])))
    body.append(exhibit(f["headline"], "Headline measures by month, 2025", "Each panel is one measure on all presses by month, January to December 2025, with December marked and labelled. The dashed lines are the dates the redesign took effect: 3 February on the pilot presses and 2 September on the other eight."))

    # -- 2. Capability -------------------------------------------------------
    body.append(section("capability", "2. Capability on critical characteristics"))
    formed = u[u["characteristic_class"] == "formed"]
    assert (u["cpk"] > u["ppk"]).all()
    body.append(f"<p>Production capability on critical formed characteristics rose to a median Ppk of {num(cp.loc['formed', 'ppk_median'], 'capability_plant.ppk_median, formed 2025', '{:.2f}')} over 2025, against {num(cp.loc['formed', 'ppk_median_twelve_months_before'], 'capability_plant.ppk_median, formed 2024', '{:.2f}')} in 2024, "
                f"and critical characteristics under 1.33 fell from {num(cp['ppk_under_1_33_twelve_months_before'].sum(), 'capability_plant.ppk_under_1_33, 2024')} to {num(under, 'capability_plant.ppk_under_1_33, 2025')} of {num(total, 'capability_plant.characteristics, 2025')}. "
                f"Of the {num(under, 'capability_under_1_33: rows')}, {num(len(formed), 'capability_under_1_33: formed')} are formed heights or bend angles, and {num(int(formed['press_id'].isin(PILOT).sum()), 'capability_under_1_33: formed, on PR-03, PR-06 and PR-09')} of those are on PR-03, PR-06 and PR-09. "
                f"Cpk is higher than Ppk on all {num(under, 'capability_under_1_33: rows')}, with a median of {num(u['cpk'].median(), 'capability_under_1_33.cpk, median', '{:.2f}')} against {num(u['ppk'].median(), 'capability_under_1_33.ppk, median', '{:.2f}')}, so the shortfall is variation between subgroups, not within them.</p>")
    body.append(titled_table("Critical characteristics with production Ppk under 1.33, 2025", S.table(T["C-4"], {"Ppk": F2, "Cpk": F2})))

    # -- 3. Alarms and reaction ----------------------------------------------
    body.append(section("alarms", "3. Alarms and reaction"))
    a = ala.loc[M]; lo, hi = alp["alarm_signals_per_100_subgroups"].idxmin(), alp["alarm_signals_per_100_subgroups"].idxmax(); n0 = t["alarms_with_nothing_recorded"]
    assert (n0["rule"] == "rule 1").all() and (n0["subgroup_type"] == "routine").all()
    body.append(f"<p>Alarm signals held at {num(a.alarm_signals_per_100_subgroups, 'alarms.alarm_signals_per_100_subgroups, December', '{:.1f}')} per 100 subgroups in December, and all but {num(a.with_nothing_recorded, 'alarms.with_nothing_recorded, December')} of {num(a.alarm_signals, 'alarms.alarm_signals, December')} carry an acknowledgement or adjustment. "
                f"Rates run from {num(alp.loc[lo, 'alarm_signals_per_100_subgroups'], 'alarms.alarm_signals_per_100_subgroups, lowest press, December', '{:.1f}')} per 100 on {lo} to {num(alp.loc[hi, 'alarm_signals_per_100_subgroups'], 'alarms.alarm_signals_per_100_subgroups, highest press, December', '{:.1f}')} on {hi}, "
                f"and an adjustment is recorded on {pct(a.adjustment_share, 'alarms.adjustment_share, December')} of alarms. The {word(len(n0), 'alarms_with_nothing_recorded: rows')} alarms with nothing recorded are rule 1 alarms on routine subgroups across {word(n0['press_id'].nunique(), 'alarms_with_nothing_recorded: presses')} presses, "
                f"{word(int(n0['critical'].sum()), 'alarms_with_nothing_recorded: critical')} of them on critical characteristics. Rules 2 to 4 showed a pattern on {num(a.subgroups_with_a_pattern_shown, 'alarms.subgroups_with_a_pattern_shown, December')} of {num(a.variable_subgroups, 'alarms.variable_subgroups, December')} subgroups, "
                f"{num(a.rule_4, 'alarms.rule_4, December')} of them on rule 4.</p>")
    body.append(exhibit(f["alarms"], "Alarm signals per 100 subgroups by press, December 2025 against 2024"))
    body.append(titled_table("December alarms with nothing recorded", S.table(T["C-7"])))

    # -- 4. Checks and recording ---------------------------------------------
    body.append(section("checks", "4. Checks and recording"))
    assert fca.loc[(M, "nights"), "recorded"] == fca.loc[(M, "nights"), "planned_checks"]
    body.append(f"<p>Planned checks recorded held at {pct(pla.loc[(M, 'both shifts'), 'recorded_share'], 'planned_checks.recorded_share, December', 1)} in December, against {pct(pla.loc[(Y0, 'both shifts'), 'recorded_share'], 'planned_checks.recorded_share, 2024', 1)} in 2024, with nights at "
                f"{pct(pla.loc[(M, 'nights'), 'recorded_share'], 'planned_checks.recorded_share, nights, December', 1)} against {pct(pla.loc[(Y0, 'nights'), 'recorded_share'], 'planned_checks.recorded_share, nights, 2024', 1)}. The first check of the shift was recorded on "
                f"{pct(fca.loc[(M, 'days'), 'recorded_share'], 'first_check_of_the_shift.recorded_share, days, December', 1)} of day shifts and on every night shift, against {pct(fca.loc[(Y0, 'days'), 'recorded_share'], 'first_check_of_the_shift.recorded_share, days, 2024', 1)} and "
                f"{pct(fca.loc[(Y0, 'nights'), 'recorded_share'], 'first_check_of_the_shift.recorded_share, nights, 2024', 1)} in 2024. Late entry now depends on how the reading reaches the software. In December {pct(ena.loc[(M, 'gauge-connected'), 'share'], 'entries_after_the_parts.share, gauge-connected, December', 1)} of gauge-connected entries were made more than 20 minutes after the parts, "
                f"against {pct(ena.loc[(M, 'keyed'), 'share'], 'entries_after_the_parts.share, keyed, December', 1)} of the {num(ena.loc[(M, 'keyed'), 'subgroups'], 'entries_after_the_parts.subgroups, keyed, December')} keyed entries, unchanged from {pct(ena.loc[(Y0, 'keyed'), 'share'], 'entries_after_the_parts.share, keyed, 2024', 1)} in 2024.</p>")
    body.append(exhibit(f["checks"], "Planned checks recorded by press and shift, December 2025 against 2024"))

    # -- 5. Limits -----------------------------------------------------------
    body.append(section("limits", "5. Limits"))
    st = t["limits_status"].groupby("status")["charts"].sum(); first = int(lra["charts_with_first_limits_under_the_redesign"].sum()); firsts = lr[(lr["press_id"] != "all presses") & (lr["charts_with_first_limits_under_the_redesign"] > 0)]
    assert t["limits_due"].empty and not firsts["press_id"].isin(PILOT).any()
    body.append(f"<p>No chart was due for recalculation at 31 December. {num(lra['charts_recalculated'].sum(), 'limits_recalculated.charts_recalculated, December')} charts were recalculated in December: {num(lra.loc['baseline after sharpening', 'charts_recalculated'], 'limits_recalculated.charts_recalculated, baseline after sharpening')} on a baseline after sharpening and "
                f"{num(lra.loc['tool-wear regression', 'charts_recalculated'], 'limits_recalculated.charts_recalculated, tool-wear regression')} tool-wear charts. {num(first, 'limits_recalculated.charts_with_first_limits_under_the_redesign, December')} charts on the other eight presses received their first limits under the redesign. "
                f"The {num(st['baseline not yet complete on the new edge'], 'limits_status: limits from before the last sharpening, baseline not yet complete')} charts with limits from before the die's last sharpening are all still collecting their baseline on the new edge.</p>")
    body.append(titled_table("Charts recalculated in December", S.table(T["C-11"])))

    # -- 6. Die wear and per-stroke monitoring -------------------------------
    body.append(section("wear", "6. Die wear and per-stroke monitoring"))
    sm = t["sharpenings_in_the_month"]; lt = sm[sm["against_the_due_count"] == "after the due count"].assign(over=lambda x: x["shots_in_interval_logged"] / x["shots_at_80pct_of_limit"] - 1).sort_values("over", ascending=False)
    running = past[past["run_in_the_month"]]; stm = t["stops_in_the_month"]; pu = t["punch_replacements"].set_index("led_by")
    assert len(lt) == 2 and len(running) == 2 and int(pu[M].sum()) == int(pu.loc["after a stop by the per-stroke charts", M])
    body.append(f"<p>Sharpening at the due count held in December: {num(on, 'sharpenings_against_the_due_count: at or before, December')} of {num(on + late, 'sharpenings_against_the_due_count: with a burr line, December')} sharpenings with a burr line came at or before the die's due count, against "
                f"{num(on0, 'sharpenings_against_the_due_count: at or before, 2024')} of {num(on0 + late0, 'sharpenings_against_the_due_count: with a burr line, 2024')} in 2024. The two late sharpenings were {lt.iloc[0]['die_id']} on {lt.iloc[0]['press_id']}, {pct(lt.iloc[0]['over'], 'sharpenings_in_the_month: shots over the due count, first')} past its count, and "
                f"{lt.iloc[1]['die_id']} on {lt.iloc[1]['press_id']}, {pct(lt.iloc[1]['over'], 'sharpenings_in_the_month: shots over the due count, second')} past. {word(len(past), 'dies_due: past due', True)} dies are past their due count at month end, {word(len(past) - len(running), 'dies_due: past due and not run in December')} of them not run in December. "
                f"{running.iloc[0]['die_id']} on {running.iloc[0]['press_id']} and {running.iloc[1]['die_id']} on {running.iloc[1]['press_id']} are running past their count and are the two to pull first. {word(len(dd) - len(past), 'dies_due: due in January', True)} more dies come due in January at December's shot rate.</p>")
    body.append(f"<p>The per-stroke charts stopped presses {num(stm['stops'].sum(), 'stops_in_the_month.stops')} times in December: {num(stm['punch worn and replaced'].sum() + stm['punch chipped and replaced'].sum(), 'stops_in_the_month: punch worn and punch chipped')} for a worn or chipped punch, "
                f"{num(stm['slug pulling cleared'].sum(), 'stops_in_the_month.slug pulling cleared')} for slug pulling and {num(stm['nothing found'].sum(), 'stops_in_the_month.nothing found')} with nothing found. All {num(pu[M].sum(), 'punch_replacements, December')} punch replacements in the month followed a stop.</p>")
    body.append(exhibit(f["sharpenings"], "Sharpenings against the due count by month, 2025", "Each column is the sharpenings in the month on dies with a burr line, with the count at or before the due count over the total above it. The dashed lines are the dates the redesign took effect."))
    body.append(titled_table("Dies past their due count, or due in January 2026 at December's shot rate", S.table(T["C-16"])))
    body.append(titled_table("Per-stroke stops in December by press and finding", S.table(T["C-17"])))

    # -- 7. Measurement systems ----------------------------------------------
    body.append(section("measurement", "7. Measurement systems"))
    fx = g[g["type"] == "check fixture"]; ot = g[g["type"] != "check fixture"]; lost = t["gauges_not_active"].merge(g, on="gauge_id").iloc[0]; sg = t["subgroups_on_gauges"].set_index(["period", "press_id"]); cf = t["check_fixtures_by_grr"].set_index("status")["check_fixtures"]
    ns = t["characteristics_on_a_gauge_with_no_study"]; nsa = ns[ns["press_id"] == "all presses"].set_index("gauge_type"); since = pd.Timestamp(lost["due"])
    assert "over 30%" not in cf.index and int(nsa["critical_characteristics"].sum()) == int(nsa.loc["indicator", "critical_characteristics"]) and lost["status"] == "lost"
    body.append(f"<p>Calibration is the open measurement item. {word(len(g), 'gauges_past_due_or_out_of_service: past due', True)} gauges were past calibration due at 31 December: {word(len(fx), 'gauges_past_due_or_out_of_service: check fixtures')} check fixtures, {word(int(fx['out_of_service'].sum()), 'gauges_past_due_or_out_of_service: check fixtures out of service')} of them removed from service, and "
                f"{word(len(ot), 'gauges_past_due_or_out_of_service: other gauges')} gauges, {word(int(ot['out_of_service'].sum()), 'gauges_past_due_or_out_of_service: other gauges out of service')} of them removed from service. {num(sg.loc[(M, 'all presses'), 'on_a_gauge_past_due_or_out_of_service'], 'subgroups_on_gauges.on_a_gauge_past_due_or_out_of_service, December')} subgroups in December were measured on a gauge past due or out of service. "
                f"{lost['gauge_id']} on {lost['location_x'].replace('press ', '')} is recorded as lost and has been past due since {since.strftime('%B %Y')}. All {num(cf.sum(), 'check_fixtures_by_grr: check fixtures')} check fixtures are under 30% of tolerance on their latest study, {num(cf['under 10%'], 'check_fixtures_by_grr: under 10%')} of them under 10%. "
                f"{num(nsa['characteristics'].sum(), 'characteristics_on_a_gauge_with_no_study.characteristics')} variable characteristics are measured on a gauge with no study. {num(nsa['critical_characteristics'].sum(), 'characteristics_on_a_gauge_with_no_study.critical_characteristics')} of them are critical, all on indicators, and these are the studies to schedule first.</p>")
    body.append(titled_table("Gauges past calibration due at 31 December 2025", S.table(T["C-19"])))

    # -- 8. Nonconformances --------------------------------------------------
    body.append(section("nonconformances", "8. SPC-related nonconformances"))
    b = t["burr_nonconformances"]; wd = b[b["position_against_the_due_count"].notna()]; rec = b[b["opened"] >= "2025-09-02"]; last = pd.Timestamp(rec["opened"].max())
    assert nca.loc[Y, "sorting_events"] == nca.loc[Y0, "sorting_events"] and not rec["press_id"].isin(PILOT).any()
    body.append(f"<p>December had no sorting events and no burr nonconformances. Over 2025 sorting events held at {num(nca.loc[Y, 'sorting_events'], 'nonconformances_by_press.sorting_events, 2025')} and burr nonconformances were {num(nca.loc[Y, 'burr_nonconformances'], 'nonconformances_by_press.burr_nonconformances, 2025')}, against "
                f"{num(nca.loc[Y0, 'burr_nonconformances'], 'nonconformances_by_press.burr_nonconformances, 2024')} in 2024. Burr nonconformances still follow late sharpening: {num(int((wd['position_against_the_due_count'] > 1).sum()), 'burr_nonconformances: past the due count')} of the {num(len(wd), 'burr_nonconformances: with a due count')} with a due count fell on runs past it. "
                f"{word(len(rec), 'burr_nonconformances: opened from 2 September 2025', True)} have occurred since 2 September, all on the other eight presses, the last on {last.day} {last.strftime('%B')}.</p>")
    n_body = FIGURE[0]

    # -- Appendix ------------------------------------------------------------
    SECTION[0] = "Appendix"
    ax = ['<h2 id="appendix">Appendix</h2>', "<h3>Definitions</h3>", DEFINITIONS]
    plan = [("Section 2. Capability on critical characteristics", [("C-3", "Production Ppk and Cpk by press, critical characteristics", {"Ppk, median, 2025": F2, "Cpk, median, 2025": F2, "Ppk, median, 2024": F2, "Subgroups": F0, "Characteristics": F0, "Ppk under 1.33": F0, "Characteristics, 2024": F0, "Under 1.33, 2024": F0})]),
            ("Section 3. Alarms and reaction", [("C-5", "Alarm signals by press", None), ("C-6", "December: alarms with nothing recorded and patterns shown, by press", None)]),
            ("Section 4. Checks and recording", [("C-8", "Planned checks recorded by press and shift", None), ("C-9", "The first check of each shift", None), ("C-10", "Entries made more than 20 minutes after the parts, by press and entry", None)]),
            ("Section 5. Limits", [("C-12", "Charts by recalculation status at 31 December", None)]),
            ("Section 6. Die wear and per-stroke monitoring", [("C-13", "Sharpenings against the due count", None), ("C-14", "Sharpenings in December", None), ("C-15", "Sharpening intervals with burr over the limit", None), ("C-18", "Punch replacements by cause", None)]),
            ("Section 7. Measurement systems", [("C-20", "Subgroups on a gauge past calibration due or out of service", None), ("C-21", "Check fixtures by latest %GRR of tolerance", None), ("C-21b", "Check fixtures at 10% of tolerance or more on the latest study", None), ("C-22", "Variable characteristics measured on a gauge with no study", None)]),
            ("Section 8. SPC-related nonconformances", [("C-23", "Sorting events and burr nonconformances by press", None), ("C-24", "Burr nonconformances of 2025 with the die's position in its sharpening interval", None)])]
    for heading, items in plan:
        ax.append(f"<h3>{heading}</h3>")
        for key, title, fmt in items:
            ax.append(titled_table(title, S.table(T[key], fmt)))
            TRACE.append(("Appendix", f"table: {title}", "monthly summary tables"))
    for key, src in (("C-1", "alarms, planned_checks, first_check_of_the_shift, entries_after_the_parts, capability_plant, limits, sharpenings, burr, stops, punch_replacements"), ("C-4", "capability_under_1_33"), ("C-7", "alarms_with_nothing_recorded"), ("C-11", "limits_recalculated"), ("C-16", "dies_due"), ("C-17", "stops_in_the_month"), ("C-19", "gauges_past_due_or_out_of_service")):
        TRACE.append(("Body tables", f"table: {key}", src))

    toc = [("summary", "1. Summary"), ("capability", "2. Capability on critical characteristics"), ("alarms", "3. Alarms and reaction"), ("checks", "4. Checks and recording"), ("limits", "5. Limits"), ("wear", "6. Die wear and per-stroke monitoring"),
           ("measurement", "7. Measurement systems"), ("nonconformances", "8. SPC-related nonconformances"), ("appendix", "Appendix")]
    content = "\n".join(body + ax).replace('<table class="data">', '<div style="overflow-x:auto"><table class="data">').replace("</table>", "</table></div>")          # a wide table scrolls inside the text column
    html = S.report_shell("SPC Monthly Summary, December 2025", "", "", content, toc)
    out = S.DOCS / "monthly_summary"; out.mkdir(parents=True, exist_ok=True)
    (out / "spc_monthly_summary_2025_12.html").write_text(html, encoding="utf8", newline="\n")
    return html, pd.DataFrame(list(TRACE), columns=["section", "value_as_printed", "read_from"]), n_body, t


if __name__ == "__main__":
    html, trace, n_body, _ = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "monthly_summary_numbers.csv", index=False, lineterminator="\n")
    print(len(html), len(trace), n_body)
