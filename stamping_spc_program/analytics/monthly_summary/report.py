"""SPC Monthly Summary, June 2026: the page. Reads the summary tables, builds the figures and writes
docs/monthly_summary/spc_monthly_summary_2026_06.html and the table of every number in the text with the table it is read from."""
import pandas as pd

from analytics.monthly_summary import figures, monthly_summary
from analytics.reports.assessment import F0, FIGURE, P1, SECTION, TRACE, exhibit, num, pct, section, show, titled_table
from analytics.style import style as S

PILOT = ["PR-03", "PR-06", "PR-09"]
PAPER = ["PR-01", "PR-02", "PR-04"]
MEDIUM = ["PR-05", "PR-07", "PR-08", "PR-10", "PR-11"]
GROUP_ROWS = (("Pilot presses", PILOT), ("High-speed presses on paper", PAPER), ("Medium presses not in the pilot", MEDIUM))
WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
LAB = {"month": "Jun 2026", "month_before": "May 2026", "twelve_months": "Jan to Jun 2026", "twelve_months_before": "2025"}
ORDER = list(LAB)


def word(n, src, cap=False):
    """A count written as a word, traced as the count."""
    w = WORDS[int(n)]; TRACE.append((SECTION[0], str(int(n)), src, ""))
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


def with_groups(d, keys, sums, ratios):
    """The frame with one row per press group under the by-press rows: counts summed, shares recomputed from them."""
    rows = []
    for name, presses in GROUP_ROWS:
        g = d[d["press_id"].isin(presses)].groupby(list(keys), sort=False)[list(sums)].sum().reset_index(); g["press_id"] = name
        for col, (top, bottom, scale) in ratios.items():
            g[col] = g[top] / g[bottom] * scale
        rows.append(g)
    return pd.concat([d] + rows, ignore_index=True)


def tables(t):
    """Every table of the summary as a display frame, keyed as in the layout."""
    T = {}
    al = with_groups(t["alarms"], ["period"], ["variable_subgroups", "alarm_signals", "with_an_adjustment_recorded", "with_an_acknowledgement_or_adjustment", "with_nothing_recorded", "subgroups_with_a_pattern_shown", "rule_2", "rule_3", "rule_4"],
                     {"alarm_signals_per_100_subgroups": ("alarm_signals", "variable_subgroups", 100), "adjustment_share": ("with_an_adjustment_recorded", "alarm_signals", 1), "acknowledgement_or_adjustment_share": ("with_an_acknowledgement_or_adjustment", "alarm_signals", 1)}); ala = al[al["press_id"] == "all presses"].set_index("period")
    pl = with_groups(t["planned_checks"], ["period", "shift"], ["planned_checks", "recorded"], {"recorded_share": ("recorded", "planned_checks", 1)}); pla = pl[(pl["press_id"] == "all presses") & (pl["shift"] == "both shifts")].set_index("period")
    fc = with_groups(t["first_check_of_the_shift"], ["period", "shift"], ["planned_checks", "recorded"], {"recorded_share": ("recorded", "planned_checks", 1)}); fca = fc[fc["press_id"] == "all presses"].groupby("period")[["planned_checks", "recorded"]].sum(); fca["share"] = fca["recorded"] / fca["planned_checks"]
    en = with_groups(t["entries_after_the_parts"], ["period", "entry_method"], ["subgroups", "entered_more_than_20_minutes_after"], {"share": ("entered_more_than_20_minutes_after", "subgroups", 1)}); ena = en[en["press_id"] == "all presses"].set_index(["period", "entry_method"])
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
        ["5", "Charts recalculated", str(int(lim.iloc[-1])), str(int(lim.iloc[-2])), f"{int(lim.sum())} recalculations, February to June", "none (before the redesign)"],
        ["5", "Charts due for recalculation at 30 June", str(len(t["limits_due"])), "", "", ""],
        ["6", "Sharpenings at or before the due count"] + per(on_time),
        ["6", "Sharpening intervals with burr over the limit"] + per(lambda p: f"{bu.loc[p, 'intervals_with_burr_over_the_limit']} of {bu.loc[p, 'intervals_with_burr_gauge_subgroups']}"),
        ["6", "Per-stroke stops", str(int(stm["stops"].sum())), str(int(sbm["stops"].iloc[-2])), str(int(st12["stops"].sum())), "none (monitoring from 1 April 2026)"],
        ["6", "Per-stroke stops with nothing found", str(int(stm["nothing found"].sum())), str(int(sbm["nothing_found"].iloc[-2])), str(int(st12[st12["finding"] == "nothing found"]["stops"].sum())), ""],
        ["6", "Punch replacements"] + per(lambda p: str(int(pu[p].sum()))),
    ]
    T["C-1"] = pd.DataFrame(head, columns=["Section", "Measure"] + [LAB[p] for p in ORDER])
    T["C-3"] = t["capability_by_press"].rename(columns={"press_id": "Press", "characteristic_class": "Class", "characteristics": "Characteristics", "subgroups": "Subgroups", "ppk_median": "Ppk, median, Jan to Jun 2026", "cpk_median": "Cpk, median, Jan to Jun 2026", "ppk_under_1_33": "Ppk under 1.33",
                                                         "characteristics_twelve_months_before": "Characteristics, 2025", "ppk_median_twelve_months_before": "Ppk, median, 2025", "ppk_under_1_33_twelve_months_before": "Under 1.33, 2025"})
    T["C-4"] = t["capability_under_1_33"][["part_id", "characteristic_id", "characteristic_name", "press_id", "chart", "ppk", "cpk", "subgroups"]].rename(columns={"part_id": "Part", "characteristic_id": "Characteristic", "characteristic_name": "Name", "press_id": "Press", "chart": "Chart", "ppk": "Ppk", "cpk": "Cpk", "subgroups": "Subgroups"})
    T["C-5"] = wide(al, "press_id", [("variable_subgroups", "Subgroups"), ("alarm_signals_per_100_subgroups", "Alarm signals per 100"), ("adjustment_share", "With an adjustment"), ("acknowledgement_or_adjustment_share", "With an acknowledgement or adjustment")],
                    {"variable_subgroups": F0, "alarm_signals_per_100_subgroups": F1, "adjustment_share": P1, "acknowledgement_or_adjustment_share": P1}, ["month", "twelve_months", "twelve_months_before"]).rename(columns={"press_id": "Press"})
    dec = al[al["period"] == "month"]
    T["C-6"] = dec[["press_id", "alarm_signals", "with_nothing_recorded", "subgroups_with_a_pattern_shown", "rule_2", "rule_3", "rule_4"]].rename(columns={"press_id": "Press", "alarm_signals": "Alarm signals", "with_nothing_recorded": "With nothing recorded",
                                                                                                                                                       "subgroups_with_a_pattern_shown": "Subgroups with a pattern shown", "rule_2": "Rule 2", "rule_3": "Rule 3", "rule_4": "Rule 4"})
    c7 = t["alarms_by_press_in_the_month"]; sums7 = ["alarm_signals", "with_nothing_recorded", "with_a_one_word_text", "with_an_adjustment_recorded"]
    c7 = pd.concat([c7] + [pd.DataFrame([{"press_id": name, **c7[c7["press_id"].isin(ps)][sums7].sum().to_dict()}]) for name, ps in GROUP_ROWS] + [pd.DataFrame([{"press_id": "All presses", **c7[sums7].sum().to_dict()}])], ignore_index=True)
    T["C-7"] = pd.DataFrame({"Press": c7["press_id"], "Alarm signals": c7["alarm_signals"].map(F0), "With nothing recorded": c7["with_nothing_recorded"].map(F0), "Share": (c7["with_nothing_recorded"] / c7["alarm_signals"]).map(lambda v: f"{v * 100:.0f}%"),
                             "With a one-word text": c7["with_a_one_word_text"].map(F0), "With an adjustment recorded": c7["with_an_adjustment_recorded"].map(F0)})
    T["C-7b"] = t["alarms_with_nothing_recorded"].assign(sample_time=lambda x: x["sample_time"].map(lambda v: str(v)[:16]), critical=lambda x: x["critical"].map({True: "yes", False: ""})).rename(
        columns={"press_id": "Press", "part_id": "Part", "characteristic_id": "Characteristic", "characteristic_name": "Name", "sample_time": "Time", "subgroup_type": "Subgroup", "operator_id": "Operator", "rule": "Rule", "critical": "Critical"})
    three = ["month", "twelve_months", "twelve_months_before"]
    T["C-8"] = split(wide(pl.assign(key=pl["press_id"] + " | " + pl["shift"]), "key", [("planned_checks", "Planned"), ("recorded_share", "Recorded")], {"planned_checks": F0, "recorded_share": P1}, three), ("Press", "Shift"))
    T["C-9"] = split(wide(fc.assign(key=fc["press_id"] + " | " + fc["shift"]), "key", [("planned_checks", "Planned"), ("recorded_share", "Recorded")], {"planned_checks": F0, "recorded_share": P1}, three), ("Press", "Shift"))
    T["C-10"] = split(wide(en.assign(key=en["press_id"] + " | " + en["entry_method"]), "key", [("subgroups", "Subgroups"), ("share", "More than 20 minutes after")], {"subgroups": F0, "share": P1}, three), ("Press", "Entry"))
    T["C-11"] = t["limits_recalculated"][t["limits_recalculated"]["method"] != "PPAP study"].rename(columns={"press_id": "Press", "method": "Limits basis", "charts_recalculated": "Charts recalculated", "charts_with_first_limits_under_the_redesign": "Charts with first limits under the redesign", "dies": "Dies"})
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
                              "Shots to the due count": dd["shots_to_the_due_count"].map(F0), "Strokes a day in June": [F0(v) if run else "not run in June" for v, run in zip(dd["strokes_a_day"], dd["run_in_the_month"])],
                              "Days to the due count": ["past due" if s == "past due" else F1(v) for s, v in zip(dd["status"], dd["days_to_the_due_count"])]})
    T["C-17"] = stm.assign(is_pilot_press=lambda x: x["is_pilot_press"].map({True: "historian", False: "fault events"})).rename(columns={"press_id": "Press", "is_pilot_press": "Source", "nothing found": "Nothing found", "punch chipped and replaced": "Punch chipped and replaced",
                                                                                                                                    "punch worn and replaced": "Punch worn and replaced", "slug pulling cleared": "Slug pulling cleared", "stops": "Stops"})
    T["C-18"] = t["punch_replacements"].rename(columns={"led_by": "Punch replacement", **LAB})
    g = t["gauges_past_due_or_out_of_service"]; lost = set(t["gauges_not_active"]["gauge_id"])
    T["C-19"] = pd.DataFrame({"Gauge": g["gauge_id"], "Type": g["type"], "Location": g["location"], "Calibration due": g["due"].map(lambda v: str(v)[:10]), "Removed from service": g["removed_from_service"].map(lambda v: "" if v != v or v is pd.NaT else str(v)[:10]),
                              "Recorded as": g["gauge_id"].map(lambda v: "lost" if v in lost else "")})
    T["C-20"] = wide(t["subgroups_on_gauges"], "press_id", [("subgroups", "Subgroups"), ("on_a_gauge_past_due", "On a gauge past calibration due"), ("on_a_gauge_out_of_service", "On a gauge away for calibration"), ("on_a_gauge_past_due_or_out_of_service", "Past due or away for calibration")],
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


DEFINITION_GROUPS = [
    ("Periods and press groups", [
        ("Periods", "June 2026, May 2026, January to June 2026 and 2025, on all eleven presses."),
        ("The redesign", "In effect on PR-03, PR-06 and PR-09 from 2 February 2026, with per-stroke monitoring from 1 April 2026; the other eight presses run as before."),
        ("Pilot presses", "PR-03, PR-06 and PR-09."),
        ("High-speed presses on paper", "PR-01, PR-02 and PR-04."),
        ("Medium presses not in the pilot", "PR-05, PR-07, PR-08, PR-10 and PR-11."),
    ]),
    ("Signals and recording", [
        ("Alarm signal", "A subgroup on a variable characteristic with an alarm raised under the limits in force at entry."),
        ("Nothing recorded", "An alarm signal with no acknowledgement text and no adjustment."),
        ("One-word text", "An alarm signal whose acknowledgement is a single word. The SPC software holds an alarm until it is acknowledged with a text, so an alarm keyed there always carries one."),
        ("Pattern", "A subgroup shown on rules 2 to 4."),
        ("Planned check", "A check that falls on the clock at the part's check frequency between 06:00 and 23:00 on a day the press recorded a check, on runs of two hours or more. It is recorded when the run carries a routine check from 6 minutes before it to 31 minutes after."),
        ("First check of the shift", "The 06:00 planned time on days and the 15:00 planned time on nights."),
        ("Late entry", "A subgroup entered more than 20 minutes after the parts."),
    ]),
    ("Capability and limits", [
        ("Production Cpk and Ppk", "On critical variable characteristics with 60 subgroups or more in the period: within-subgroup sigma pooled across subgroups, overall sigma from all readings, medians over characteristics. A single month does not carry 60 subgroups on most characteristics, so capability is stated for January to June 2026 and for 2025 only."),
        ("Chart recalculated", "A chart on which a new limit set takes effect in the month. A chart's first limits under the redesign are counted beside, and new printed limits from a PPAP study on a paper press are not counted."),
        ("Due for recalculation", "A chart whose limits in force predate the die's last sharpening and whose baseline on the new edge is complete: 25 subgroups on an X-bar and R chart, 25 subgroups and six coil changes on a three-way chart. Tool-wear charts recalculate on a planned trigger and are not classed."),
    ]),
    ("Dies, gauges and nonconformances", [
        ("Due count", "The shot count at which a die's burr line reaches 80% of the burr limit, counted from the last sharpening."),
        ("Sharpening at or before the due count", "A sharpening where the logged shots of the run interval it ends are at or under the due count. Its press is the press of the die's last run in the interval."),
        ("Shots since sharpening", "The strokes on runs since the last sharpening, the run in process included."),
        ("Due in July", "A die whose shots to the due count, over its strokes per calendar day in June, come to 31 days or fewer."),
        ("Burr over the limit", "A sharpening interval with a burr gauge subgroup mean over the limit, on intervals with five burr gauge subgroups or more."),
        ("Per-stroke stops", "From the historian on PR-03, PR-06 and PR-09."),
        ("Past calibration due", "A gauge whose due date has passed at 30 June with no calibration done. A subgroup is on a gauge past calibration due when the due date had passed on the subgroup's date with no calibration done by then, calibrations still open at 30 June included."),
        ("Away for calibration", "A subgroup is recorded against a gauge away for calibration when its date falls between the gauge's removal for calibration and its return."),
        ("Gauge study", "The latest on the check fixture, by the ANOVA method, %GRR of tolerance at 6 sigma."),
        ("Position of a burr nonconformance", "The die's shots since sharpening at the end of its run over the stated sharpening interval, and over the due count."),
        ("Not in this summary", "Customer PPM, scrap and rework, and cost lines are in the SPC Redesign and Results report."),
    ]),
]
DEFINITIONS = "".join(f"<h4>{title}</h4><ul>" + "".join(f"<li><strong>{term}:</strong> {text}</li>" for term, text in items) + "</ul>" for title, items in DEFINITION_GROUPS)


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

    # -- group figures ------------------------------------------------------
    GROUPS = {"pilot presses": PILOT, "high-speed presses on paper": PAPER, "medium presses not in the pilot": MEDIUM, "other eight presses": PAPER + MEDIUM}
    am = al[al["period"] == M].set_index("press_id"); ag = {k: am.loc[v].sum(numeric_only=True) for k, v in GROUPS.items()}
    rate = {k: x.alarm_signals / x.variable_subgroups * 100 for k, x in ag.items()}; adj = {k: x.with_an_adjustment_recorded / x.alarm_signals for k, x in ag.items()}; nothing = {k: x.with_nothing_recorded / x.alarm_signals for k, x in ag.items()}
    c7 = t["alarms_by_press_in_the_month"].set_index("press_id"); one_word = {k: c7.loc[v, "with_a_one_word_text"].sum() for k, v in GROUPS.items()}
    cbp = t["capability_by_press"]; fp = cbp[(cbp["characteristic_class"] == "formed") & cbp["press_id"].isin(PILOT)].set_index("press_id"); pp_ = cbp[(cbp["characteristic_class"] == "punched") & cbp["press_id"].isin(PILOT)].set_index("press_id")
    pil = cbp[cbp["press_id"].isin(PILOT)]; cby = t["capability_by_characteristic"]
    plm = pl[pl["period"] == M]; nights = {k: plm[plm["press_id"].isin(v) & (plm["shift"] == "nights")][["planned_checks", "recorded"]].sum() for k, v in GROUPS.items()}
    fcm = fc[(fc["period"] == M) & (fc["shift"] == "days")]; first = {k: fcm[fcm["press_id"].isin(v)][["planned_checks", "recorded"]].sum() for k, v in GROUPS.items()}
    sm = t["sharpenings_in_the_month"]; smp = sm[sm["press_id"].isin(PILOT)]; smo = sm[~sm["press_id"].isin(PILOT)]; ok_ = "at or before the due count"
    bim = t["burr_intervals_in_the_month"]; over = bim[bim["highest"] > 1]
    ncm = nc[(nc["period"] == M) & (nc["press_id"] != "all presses")].set_index("press_id"); bn = t["burr_nonconformances"]; bnm = bn[(pd.to_datetime(bn["opened"]) >= t["periods"][M][0]) & (pd.to_datetime(bn["opened"]) < t["periods"][M][1])]
    stm = t["stops_in_the_month"]; pu = t["punch_replacements"].set_index("led_by"); ns = t["characteristics_on_a_gauge_with_no_study"]; cf = t["check_fixtures_by_grr"].set_index("status")["check_fixtures"]; f10 = t["check_fixtures_at_10pct_or_more"]
    sgo = t["subgroups_on_gauges"]; sga = sgo[sgo["press_id"] == "all presses"].set_index("period"); lost = t["gauges_not_active"].merge(g, on="gauge_id").iloc[0]

    def v(x, was, src, f="{:,.0f}"):
        s = f.format(x) if not isinstance(x, str) else x; TRACE.append((SECTION[0], s, src, was)); return s

    def p0(x, was, src, d=0):
        return v(f"{x * 100:.{d}f}%", was, src)

    # -- 1. Summary ----------------------------------------------------------
    body.append(section("summary", "1. Summary"))
    assert ncm.loc[PILOT, "burr_nonconformances"].sum() == 0 and (bnm["position_against_the_due_count"] > 1).all() and not bnm["press_id"].isin(PILOT).any()
    body.append("<p>In June the pilot presses ran at the redesign's level, and the other eight presses ran as they did in 2025.</p><ul>"
                f"<li><strong>Signals:</strong> the pilot presses gave {v(rate['pilot presses'], '4.7', 'alarms: alarm signals per 100 subgroups, pilot presses, June', '{:.1f}')} alarm signals per 100 subgroups and recorded an adjustment on {p0(adj['pilot presses'], '82%', 'alarms: with an adjustment recorded, pilot presses, June')} of them. "
                f"The high-speed presses on paper gave {v(rate['high-speed presses on paper'], '21.3', 'alarms: per 100, high-speed presses on paper, June', '{:.1f}')} and the medium presses {v(rate['medium presses not in the pilot'], '11.9', 'alarms: per 100, medium presses not in the pilot, June', '{:.1f}')}, "
                f"with an adjustment recorded on {p0(adj['high-speed presses on paper'], '21%', 'alarms: adjustment share, high-speed presses on paper, June')} and {p0(adj['medium presses not in the pilot'], '16%', 'alarms: adjustment share, medium presses not in the pilot, June')}.</li>"
                f"<li><strong>Capability:</strong> critical formed characteristics on the pilot presses have a median Ppk of {v(fp['ppk_median'].min(), '1.33', 'capability_by_press.ppk_median, formed, pilot presses, lowest, January to June', '{:.2f}')} to {v(fp['ppk_median'].max(), '1.37', 'the same, highest', '{:.2f}')} for January to June, against "
                f"{v(fp['ppk_median_twelve_months_before'].min(), '0.93', 'capability_by_press.ppk_median, formed, pilot presses, lowest, 2025', '{:.2f}')} to {v(fp['ppk_median_twelve_months_before'].max(), '1.06', 'the same, highest', '{:.2f}')} in 2025.</li>"
                f"<li><strong>Dies:</strong> all {v(len(bnm), '7', 'burr_nonconformances opened in June')} burr nonconformances in June were on the other eight presses, each on a die run past its sharpening count. The pilot presses had none.</li></ul>")
    body.append(f"<p>Across all presses, alarm signals were {v(ala.loc[M, 'alarm_signals_per_100_subgroups'], '9.6', 'alarms.alarm_signals_per_100_subgroups, June', '{:.1f}')} per 100 subgroups against {v(ala.loc[Y0, 'alarm_signals_per_100_subgroups'], '15.2', 'alarms.alarm_signals_per_100_subgroups, 2025', '{:.1f}')} in 2025, and planned checks recorded rose to "
                f"{p0(pla.loc[(M, 'both shifts'), 'recorded_share'], '94.6%', 'planned_checks.recorded_share, June', 1)} from {p0(pla.loc[(B, 'both shifts'), 'recorded_share'], '89.8%', 'planned_checks.recorded_share, May', 1)} in May. The redesign extends to the other eight presses from 3 August 2026.</p>")
    body.append(titled_table("Headline measures, June and May 2026, January to June 2026 and 2025", S.table(T["C-1"])))
    body.append(exhibit(f["headline"], "Monthly measures, January to June 2026", "Each panel is one measure on all presses by month, with June marked and labelled. The dashed lines are 2 February, when the redesign took effect on the pilot presses, and 1 April, when per-stroke monitoring began on them."))

    # -- 2. Capability -------------------------------------------------------
    body.append(section("capability", "2. Capability on critical characteristics"))
    under_p = int(pil["ppk_under_1_33"].sum()); n_p = int(pil["characteristics"].sum()); low = u.sort_values("ppk").iloc[0]
    body.append(f"<p>Capability on the pilot presses has risen above 1.33 on formed characteristics and held on punched characteristics. For January to June, the median Ppk on critical formed characteristics is {v(fp.loc['PR-03', 'ppk_median'], '1.37', 'capability_by_press.ppk_median, formed PR-03', '{:.2f}')} on PR-03, "
                f"{v(fp.loc['PR-06', 'ppk_median'], '1.34', 'capability_by_press.ppk_median, formed PR-06', '{:.2f}')} on PR-06 and {v(fp.loc['PR-09', 'ppk_median'], '1.33', 'capability_by_press.ppk_median, formed PR-09', '{:.2f}')} on PR-09, against "
                f"{v(fp.loc['PR-03', 'ppk_median_twelve_months_before'], '0.94', 'the same, 2025, PR-03', '{:.2f}')}, {v(fp.loc['PR-06', 'ppk_median_twelve_months_before'], '0.93', 'the same, 2025, PR-06', '{:.2f}')} and {v(fp.loc['PR-09', 'ppk_median_twelve_months_before'], '1.06', 'the same, 2025, PR-09', '{:.2f}')} in 2025. "
                f"Punched characteristics are at {v(pp_['ppk_median'].min(), '1.57', 'capability_by_press.ppk_median, punched, pilot presses, lowest', '{:.2f}')} to {v(pp_['ppk_median'].max(), '1.71', 'the same, highest', '{:.2f}')}. Critical characteristics under 1.33 on the pilot presses fell from "
                f"{v(pil['ppk_under_1_33_twelve_months_before'].sum(), '79', 'capability_by_press.ppk_under_1_33, pilot presses, 2025')} of {v(pil['characteristics_twelve_months_before'].sum(), '128', 'capability_by_press.characteristics, pilot presses, 2025')} in 2025 to {v(under_p, '36', 'capability_by_press.ppk_under_1_33, pilot presses, January to June')} of {v(n_p, '120', 'capability_by_press.characteristics, pilot presses, January to June')}.</p>")
    body.append(f"<p>{v(int(u['press_id'].isin(PILOT).sum()), '36', 'capability_under_1_33 on the pilot presses')} of the {v(len(u), '38', 'capability_under_1_33')} characteristics under 1.33 are on the pilot presses, which run {v(int(cby['press_id'].isin(PILOT).sum()), '120', 'capability_by_characteristic on the pilot presses')} of the "
                f"{v(len(cby), '127', 'capability_by_characteristic')} critical characteristics. The lowest is {v(low.characteristic_name, 'formed height E', 'capability_under_1_33.characteristic_name, lowest Ppk')} on {v(low.part_id, 'P-29540', 'capability_under_1_33.part_id, lowest Ppk')} ({v(low.press_id, 'PR-06', 'capability_under_1_33.press_id, lowest Ppk')}), at {v(low.ppk, '0.79', 'capability_under_1_33.ppk, lowest', '{:.2f}')}.</p>")
    body.append(titled_table("Critical characteristics with Ppk under 1.33, January to June 2026", S.table(T["C-4"], {"Ppk": F2, "Cpk": F2})))

    # -- 3. Alarms and reaction ----------------------------------------------
    body.append(section("alarms", "3. Alarms and reaction"))
    body.append("<p>Alarms on the pilot presses are answered, and those on the other eight presses mostly are not.</p>")
    grp = [("Pilot presses", "pilot presses", ("4.7", "1%", "0%", "82%")), ("High-speed presses on paper", "high-speed presses on paper", ("21.3", "70%", "7%", "21%")), ("Medium presses not in the pilot", "medium presses not in the pilot", ("11.9", "0%", "56%", "16%"))]
    rows = [(name, v(rate[k], w[0], f'alarms: per 100, {k}, June', '{:.1f}'), p0(nothing[k], w[1], f'alarms: nothing recorded, {k}, June'), p0(one_word[k] / ag[k].alarm_signals, w[2], f'alarms: one-word text, {k}, June'), p0(adj[k], w[3], f'alarms: adjustment recorded, {k}, June')) for name, k, w in grp]
    body.append(titled_table("Alarm signals by press group, June 2026", S.table(pd.DataFrame(rows, columns=["Press group", "Alarm signals per 100 subgroups", "Nothing recorded", "One-word text", "Adjustment recorded"]))))
    hs, md = ag["high-speed presses on paper"], ag["medium presses not in the pilot"]
    body.append(f"<ul><li><strong>High-speed presses on paper:</strong> {v(hs.with_nothing_recorded, '386', 'alarms.with_nothing_recorded, high-speed presses on paper, June')} of {v(hs.alarm_signals, '552', 'alarms.alarm_signals, high-speed presses on paper, June')} alarm signals carry neither a note nor an adjustment.</li>"
                f"<li><strong>Medium presses:</strong> the software holds each alarm until it is acknowledged, so every alarm carries a text, but {v(one_word['medium presses not in the pilot'], '213', 'alarms: one-word text, medium presses not in the pilot, June')} of {v(md.alarm_signals, '380', 'alarms.alarm_signals, medium presses not in the pilot, June')} texts are a single word "
                f"(\"adj\", \"ck\", \"ok\") and {v(md.with_an_adjustment_recorded, '59', 'alarms.with_an_adjustment_recorded, medium presses not in the pilot, June')} record an adjustment.</li></ul>")
    body.append(exhibit(f["alarms"], "Alarm signals per 100 subgroups by press, June 2026 against 2025"))
    body.append(titled_table("June alarms by press and press group, with what was recorded", S.table(T["C-7"])))
    assert am.loc[PAPER + MEDIUM, "subgroups_with_a_pattern_shown"].sum() == 0
    body.append(f"<p>Only the pilot charts show patterns. Rules 2 to 4 flagged {v(am.loc[PILOT, 'subgroups_with_a_pattern_shown'].sum(), '1,977', 'alarms.subgroups_with_a_pattern_shown, pilot presses, June')} subgroups on PR-03, PR-06 and PR-09 in June, and none on the other presses.</p>")

    # -- 4. Checks and recording ---------------------------------------------
    body.append(section("checks", "4. Checks and recording"))
    np_, no_ = nights["pilot presses"], nights["other eight presses"]; f_p, f_o = first["pilot presses"], first["other eight presses"]
    body.append("<p>Recording on the pilot presses holds on both shifts, and the gap on the other presses is the night shift and the first check on days.</p><ul>"
                f"<li><strong>Night shift:</strong> the pilot presses recorded {p0(np_.recorded / np_.planned_checks, '98.5%', 'planned_checks: nights, pilot presses, June', 1)} of planned checks in June, the other eight presses {p0(no_.recorded / no_.planned_checks, '89.3%', 'planned_checks: nights, other eight presses, June', 1)}.</li>"
                f"<li><strong>First check on days:</strong> the 06:00 check was recorded on {p0(f_p.recorded / f_p.planned_checks, '91%', 'first_check_of_the_shift: days, pilot presses, June')} of pilot press shifts ({v(f_p.recorded, '50', 'the same, recorded')} of {v(f_p.planned_checks, '55', 'the same, planned')}) and "
                f"{p0(f_o.recorded / f_o.planned_checks, '74%', 'first_check_of_the_shift: days, other eight presses, June')} on the other presses ({v(f_o.recorded, '73', 'the same, recorded')} of {v(f_o.planned_checks, '98', 'the same, planned')}).</li>"
                f"<li><strong>Late entries:</strong> {p0(ena.loc[(M, 'gauge-connected'), 'share'], '2.1%', 'entries_after_the_parts.share, gauge-connected, June', 1)} of gauge-connected entries were made more than 20 minutes after the parts, against {p0(ena.loc[(M, 'keyed'), 'share'], '14.4%', 'entries_after_the_parts.share, keyed, June', 1)} of keyed entries.</li></ul>")
    body.append(exhibit(f["checks"], "Planned checks recorded by press and shift, June 2026 against 2025"))

    # -- 5. Limits -----------------------------------------------------------
    body.append(section("limits", "5. Limits"))
    rc = lr[lr["press_id"] == "all presses"].set_index("method"); pr6 = lr[(lr["press_id"] == "PR-06")]; ppap = lr[(lr["press_id"] == "PR-04") & (lr["method"] == "PPAP study")].iloc[0]
    n_rec = int(rc.loc["baseline after sharpening", "charts_recalculated"] + rc.loc["tool-wear regression", "charts_recalculated"])
    assert t["limits_due"].empty
    body.append(f"<p>All pilot charts are on current limits, and none were due for recalculation at 30 June. {v(n_rec, '39', 'limits_recalculated.charts_recalculated: baseline after sharpening and tool-wear regression, June')} charts were recalculated in June: "
                f"{v(rc.loc['baseline after sharpening', 'charts_recalculated'], '35', 'limits_recalculated.charts_recalculated, baseline after sharpening')} at the baseline after a sharpening, on {v(rc.loc['baseline after sharpening', 'dies'], '12', 'limits_recalculated.dies, baseline after sharpening')} dies, and "
                f"{v(rc.loc['tool-wear regression', 'charts_recalculated'], '4', 'limits_recalculated.charts_recalculated, tool-wear regression')} on the tool-wear regression. {v(pr6['charts_with_first_limits_under_the_redesign'].sum(), '3', 'limits_recalculated.charts_with_first_limits_under_the_redesign, PR-06')} charts on PR-06 received their first limits under the redesign. "
                f"On PR-04, {v(ppap.charts_recalculated, '16', 'limits_recalculated.charts_recalculated, PR-04 PPAP study')} charts on {v(WORDS[int(ppap.dies)], 'two', 'limits_recalculated.dies, PR-04 PPAP study')} dies took new limits from PPAP studies.</p>")
    body.append(titled_table("Charts recalculated in June", S.table(T["C-11"]), "New printed limits from a PPAP study on a paper press are not recalculations and are not in the table: 16 charts on two dies on PR-04 in June."))

    # -- 6. Die wear and per-stroke monitoring -------------------------------
    body.append(section("wear", "6. Die wear and per-stroke monitoring"))
    lt = smp[smp["against_the_due_count"] != ok_].sort_values("die_id", ascending=False); ov_o = over[~over["press_id"].isin(PILOT)]; ov_p = over[over["press_id"].isin(PILOT)]
    assert set(lt["die_id"]) == {"D-6315-A", "D-5987-A"} and len(ov_p) == 1
    body.append(f"<p>Pilot dies are sharpened at the count, and dies on the other presses are mostly run past it. {v(int((sm['against_the_due_count'] == ok_).sum()), '18', 'sharpenings_in_the_month at or before the due count')} of {v(int(sm['against_the_due_count'].isin([ok_, 'after the due count']).sum()), '33', 'sharpenings_in_the_month with a burr line')} sharpenings in June were at or before the due count.</p><ul>"
                f"<li><strong>Pilot presses:</strong> {v(int((smp['against_the_due_count'] == ok_).sum()), '4', 'sharpenings_in_the_month, pilot presses, at or before')} of {v(int(smp['against_the_due_count'].isin([ok_, 'after the due count']).sum()), '6', 'sharpenings_in_the_month, pilot presses')}. The two after the count, {lt['die_id'].iloc[0]} and {lt['die_id'].iloc[1]}, were on intervals begun before the count took effect.</li>"
                f"<li><strong>Other presses:</strong> {v(int((smo['against_the_due_count'] == ok_).sum()), '14', 'sharpenings_in_the_month, other presses, at or before')} of {v(int(smo['against_the_due_count'].isin([ok_, 'after the due count']).sum()), '27', 'sharpenings_in_the_month, other presses')}.</li></ul>")
    body.append(f"<p>Burr exceeded the limit on {v(len(over), '5', 'burr_intervals_in_the_month over the limit')} of {v(len(bim), '34', 'burr_intervals_in_the_month')} intervals: {v(WORDS[len(ov_o)], 'four', 'burr_intervals_in_the_month over the limit, other presses')} on the other presses and {ov_p['die_id'].iloc[0]} on {ov_p['press_id'].iloc[0]}.</p>")
    body.append(exhibit(f["sharpenings"], "Sharpenings against the due count by month, January to June 2026", "Each column is the sharpenings in the month on dies with a burr line, with the count at or before the due count over the total above it."))
    pp3 = past[past["press_id"].isin(PILOT)].assign(r=lambda x: x["shots_since_sharpening"] / x["shots_at_80pct_of_limit"]).set_index("die_id")
    assert set(pp3.index) == {"D-5884-A", "D-3708-A", "D-6315-A"} and pd.Timestamp(pp3.loc["D-5884-A", "last_sharpening"]) == pd.Timestamp("2026-01-16")
    body.append(f"<p>{v(WORDS[len(past)].capitalize(), 'Eight', 'dies_due: past due')} dies were past their count at 30 June, and {v(len(dd) - len(past), '18', 'dies_due: due in the month after')} more come due in July at the June shot rate. {v(WORDS[len(pp3)].capitalize(), 'Three', 'dies_due: past due, pilot presses')} of the eight are pilot dies:</p><ul>"
                f"<li>D-5884-A on PR-09, at {v(pp3.loc['D-5884-A', 'r'], '1.33', 'dies_due: shots since over the due count, D-5884-A', '{:.2f}')} times its count, on an interval begun 16 January;</li>"
                f"<li>D-3708-A and D-6315-A on PR-03, at {v(pp3.loc['D-3708-A', 'r'], '1.05', 'the same, D-3708-A', '{:.2f}')} and {v(pp3.loc['D-6315-A', 'r'], '1.06', 'the same, D-6315-A', '{:.2f}')}, neither run since passing it.</li></ul><p>All three are to be sharpened before their next run.</p>")
    body.append(titled_table("Dies past their due count, or due in July 2026 at June's shot rate", S.table(T["C-16"])))
    worn = int(stm["punch worn and replaced"].sum() + stm["punch chipped and replaced"].sum())
    assert set(stm[stm["stops"] > 0]["press_id"]) == {"PR-03", "PR-09"}
    body.append(f"<p>The per-stroke charts stopped PR-03 and PR-09 {v(stm['stops'].sum(), '12', 'stops_in_the_month.stops')} times in June:</p><ul><li>a worn or chipped punch on {v(worn, '9', 'stops_in_the_month: punch worn and punch chipped')};</li>"
                f"<li>slug pulling on {v(stm['slug pulling cleared'].sum(), '1', 'stops_in_the_month.slug pulling cleared')};</li><li>nothing found on {v(stm['nothing found'].sum(), '2', 'stops_in_the_month.nothing found')}.</li></ul>"
                f"<p>{v(pu.loc['after a stop by the per-stroke charts', M], '9', 'punch_replacements: after a stop, June')} of the {v(pu[M].sum(), '24', 'punch_replacements: all, June')} punch replacements followed a stop, and {v(pu.loc['after nonconforming parts', M], '2', 'punch_replacements: after nonconforming parts, June')} followed nonconforming parts.</p>")
    body.append(titled_table("Per-stroke stops in June by press and finding", S.table(T["C-17"])))

    # -- 7. Measurement systems ----------------------------------------------
    body.append(section("measurement", "7. Measurement systems"))
    nsa = ns[ns["press_id"] == "all presses"].set_index("gauge_type"); nsp = ns[ns["press_id"].isin(PILOT)]; studied = int(cf.drop("no study").sum())
    assert "over 30%" not in cf.index and f10["press_id"].isin(PILOT).all() and (pd.to_datetime(f10["study_date"]).dt.strftime("%Y-%m") == "2026-01").all() and lost["status"] == "lost"
    body.append(f"<p>Gauge studies cover the pilot fixtures and few gauges elsewhere. All {v(studied, '30', 'check_fixtures_by_grr: with a study')} studied fixtures are under 30% of tolerance; the {v(cf.loc['10% to 30%'], '11', 'check_fixtures_by_grr: 10% to 30%')} at 10% or more are pilot fixtures studied in January. "
                f"The other eight presses have {v(cf.loc['no study'], '150', 'check_fixtures_by_grr: no study')} fixtures with no study. On every press, including the pilot presses, the burr gauges and the indicators on critical characteristics have no study: "
                f"{v(nsa.loc['burr gauge', 'characteristics'], '180', 'characteristics_on_a_gauge_with_no_study.characteristics, burr gauge')} burr characteristics and {v(nsa.loc['indicator', 'critical_characteristics'], '23', 'characteristics_on_a_gauge_with_no_study.critical_characteristics, indicator')} critical characteristics on indicators, "
                f"{v(nsp[nsp['gauge_type'] == 'indicator']['critical_characteristics'].sum(), '14', 'the same, pilot presses')} of them on the pilot presses.</p>")
    since = pd.Timestamp(lost["due"])
    body.append(f"<p>{v(int(g['past_due'].sum()), '28', 'gauges_past_due_or_out_of_service: past due')} gauges were past calibration due at 30 June, and {v(int(g['out_of_service'].sum()), '8', 'gauges_past_due_or_out_of_service: out of service')} were away for calibration. One, {lost['gauge_id']} on {str(lost['location_x']).replace('press ', '')}, has been past due since "
                f"{v(since.strftime('%B %Y'), 'June 2025', 'gauges_not_active: calibration due')} and is listed as lost. In June, subgroups measured on a gauge past due fell to {v(sga.loc[M, 'on_a_gauge_past_due'], '209', 'subgroups_on_gauges.on_a_gauge_past_due, June')} from {v(sga.loc[B, 'on_a_gauge_past_due'], '904', 'subgroups_on_gauges.on_a_gauge_past_due, May')} in May. "
                f"{v(sga.loc[M, 'on_a_gauge_out_of_service'], '1,135', 'subgroups_on_gauges.on_a_gauge_out_of_service, June')} subgroups in June were recorded against a gauge away for calibration that day, so the gauge that measured them is not on record.</p>")
    body.append(titled_table("Gauges past calibration due or away for calibration at 30 June 2026", S.table(T["C-19"])))

    # -- 8. Nonconformances --------------------------------------------------
    body.append(section("nonconformances", "8. SPC-related nonconformances"))
    se = ncm[ncm["sorting_events"] > 0]
    assert len(se) == 1 and se.index[0] == "PR-01"
    body.append(f"<p>June had {v(WORDS[int(nca.loc[M, 'sorting_events'])], 'one', 'nonconformances_by_press.sorting_events, June')} sorting event, on PR-01, and {v(nca.loc[M, 'burr_nonconformances'], '7', 'nonconformances_by_press.burr_nonconformances, June')} burr nonconformances, all on the other eight presses. "
                f"Each of the 7 was on a die past its due count, at {v(bnm['position_against_the_due_count'].min(), '1.03', 'burr_nonconformances.position_against_the_due_count, June, lowest', '{:.2f}')} to {v(bnm['position_against_the_due_count'].max(), '1.65', 'the same, highest', '{:.2f}')} times it. "
                f"For January to June there were {v(nca.loc[Y, 'sorting_events'], '12', 'nonconformances_by_press.sorting_events, January to June')} sorting events and {v(nca.loc[Y, 'burr_nonconformances'], '40', 'nonconformances_by_press.burr_nonconformances, January to June')} burr nonconformances, against "
                f"{v(nca.loc[Y0, 'sorting_events'], '14', 'nonconformances_by_press.sorting_events, 2025')} and {v(nca.loc[Y0, 'burr_nonconformances'], '62', 'nonconformances_by_press.burr_nonconformances, 2025')} in all of 2025.</p>")
    n_body = FIGURE[0]

    # -- Appendix ------------------------------------------------------------
    SECTION[0] = "Appendix"
    ax = ['<h2 id="appendix">Appendix</h2>', "<h3>Definitions</h3>", DEFINITIONS]
    plan = [("Section 2. Capability on critical characteristics", [("C-3", "Production Ppk and Cpk by press, critical characteristics", {"Ppk, median, Jan to Jun 2026": F2, "Cpk, median, Jan to Jun 2026": F2, "Ppk, median, 2025": F2, "Subgroups": F0, "Characteristics": F0, "Ppk under 1.33": F0, "Characteristics, 2025": F0, "Under 1.33, 2025": F0})]),
            ("Section 3. Alarms and reaction", [("C-5", "Alarm signals by press", None), ("C-6", "June: alarms with nothing recorded and patterns shown, by press", None), ("C-7b", "June: the alarms with nothing recorded", None)]),
            ("Section 4. Checks and recording", [("C-8", "Planned checks recorded by press and shift", None), ("C-9", "The first check of each shift", None), ("C-10", "Entries made more than 20 minutes after the parts, by press and entry", None)]),
            ("Section 5. Limits", [("C-12", "Charts by recalculation status at 30 June", None)]),
            ("Section 6. Die wear and per-stroke monitoring", [("C-13", "Sharpenings against the due count", None), ("C-14", "Sharpenings in June", None), ("C-15", "Sharpening intervals with burr over the limit", None), ("C-18", "Punch replacements by cause", None)]),
            ("Section 7. Measurement systems", [("C-20", "Subgroups on a gauge past calibration due or away for calibration", None), ("C-21", "Check fixtures by latest %GRR of tolerance", None), ("C-21b", "Check fixtures at 10% of tolerance or more on the latest study", None), ("C-22", "Variable characteristics measured on a gauge with no study", None)]),
            ("Section 8. SPC-related nonconformances", [("C-23", "Sorting events and burr nonconformances by press", None), ("C-24", "Burr nonconformances, January to June 2026, with the die's position in its sharpening interval", None)])]
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
    html = S.report_shell("SPC Monthly Summary, June 2026", "", "", content, toc)
    out = S.DOCS / "monthly_summary"; out.mkdir(parents=True, exist_ok=True)
    (out / "spc_monthly_summary_2026_06.html").write_text(html, encoding="utf8", newline="\n")
    trace = pd.DataFrame([tuple(x) + ("",) * (4 - len(x)) for x in TRACE], columns=["section", "value_as_printed", "read_from", "value_in_the_text"])
    off = trace[(trace["value_in_the_text"] != "") & (trace["value_as_printed"].str.lower() != trace["value_in_the_text"].str.lower())]
    print("numbers that differ from the text:", len(off)); print(off.to_string() if len(off) else "")
    return html, trace, n_body, t


if __name__ == "__main__":
    html, trace, n_body, _ = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "monthly_summary_numbers.csv", index=False, lineterminator="\n")
    print(len(html), len(trace), n_body)
