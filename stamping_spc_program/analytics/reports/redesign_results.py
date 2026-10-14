"""SPC Redesign and Results: the report page. Reads the analysis tables, builds the figures and writes
docs/reports/spc_redesign_and_results.html and the table of every number in the body with the table it is read from."""
import numpy as np
import pandas as pd

from analytics.adjustment import adjustment, figures as adjustment_fig
from analytics.capability import capability, figures as capability_fig
from analytics.control_plan import control_plan
from analytics.measurement import measurement, figures as measurement_fig
from analytics.outcomes import outcomes, figures as outcomes_fig
from analytics.per_stroke import per_stroke, figures as per_stroke_fig
from analytics.recording import recording, figures as recording_fig
from analytics.risk_window import risk_window, figures as risk_fig
from analytics.reports.assessment import F0, F2, F3, F4, FIGURE, P0, P1, SECTION, TRACE, anova_block, exhibit, num, pct, section, show, sub, titled_table, word
from analytics.data import query
from analytics.style import style as S

METHOD = ("<p>Per-stroke tonnage is charted for autocorrelated data: a first-order autoregressive model is fitted to the run's first 500 production strokes; the EWMA on the per-stroke total is two-sided with lambda 0.02 and limits at 5.5 sigma of the EWMA, its variance from the fitted model; each channel is charted on its share of the total with one residual beyond 5.5 sigma as the signal. "
          "The chart parameters were set by run-length computation at autocorrelations of 0.50, 0.60 and 0.70 for a combined in-control average run length of at least 500,000 strokes. Setup strokes, those before the monitor's run start, are set aside. "
          "Event counts and complaint counts are compared by the exact Poisson rate test; PPM is pieces rejected over pieces shipped as the customer scored it, with a bootstrap interval over complaints, since rejected pieces arrive in batches; scrapped pieces are compared by the two-proportion score test with the Newcombe interval, shown in the appendix. "
          "Capability is as in the assessment report: within-subgroup sigma pooled across subgroups, overall sigma from all readings, medians over characteristics with 60 subgroups or more in the period and a bootstrap interval over characteristics. Gauge R&amp;R is by the ANOVA method with %tolerance at 6 sigma and ndc; attribute agreement with Fleiss' kappa. "
          "Outcomes are on the pilot presses for April to June and the comparison presses (the other eight) for the same months, each against the same months of 2025 and 2024. Tonnage in kN; dimensions in millimetres; costs as booked, in US dollars. "
          "Data: the SPC software, the press monitor historian (every stroke on the pilot presses), fault events, ERP, QMS, die maintenance log, calibration system, accounting and the gauge study worksheets, as exported to 30 June 2026.</p>")


def p_value(v):
    return "under 0.0001" if v < 0.0001 else (f"{v:.4f}" if v < 0.01 else f"{v:.2f}")


ONE = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
CAP = {k: v.capitalize() for k, v in ONE.items()}


def build():
    TRACE.clear(); FIGURE[0] = 0
    m, a, k, rec, ps, o = measurement.compute(), adjustment.compute(), capability.compute(), recording.compute(), per_stroke.compute(), outcomes.compute()
    fr = risk_fig.build(risk_window.compute())
    fm, fa, fk, frec, fps, fo = measurement_fig.build(m), adjustment_fig.build(a), capability_fig.build(k), recording_fig.build(rec), per_stroke_fig.build(ps), outcomes_fig.build(o)
    f_sets, f_burr, f_alarm = outcomes_fig.press_sets_five_measures(o), outcomes_fig.burr_over_the_limit(o), outcomes_fig.alarm_rate_and_response(o)
    f_hole, hole = outcomes_fig.hole_diameter_on_the_tool_wear_chart(); hd, hd_by = outcomes.hole_diameter_under_the_tool_wear_chart(); hdy = hd.set_index("year")
    body = []

    # -- values read once ----------------------------------------------------
    so = o["sorting"].set_index(["press_set", "year"]); pp = o["ppm"].set_index(["press_set", "year"]); sc = o["scrap_and_rework"].set_index(["press_set", "year"])
    cap = o["capability"].set_index(["press_set", "characteristics_class", "year"]); sg = o["signals"].set_index(["press_set", "presses", "period_year"]); bu = o["burr"].set_index(["press_set", "period_year"])
    P, C, ALL = "pilot presses", "comparison presses", "all presses of the set"
    sbc = ps["stops_by_chart"].set_index("chart"); both = sbc.loc["both charts"]; rate = ps["stops_with_nothing_found"].set_index("press_id").loc["pilot presses"]; ton = ps["tonnage_by_press"].set_index("press_id").loc["pilot presses"]
    pr = ps["punch_replacements"]; brk = ps["punch_break_summary"].iloc[0]; rise = ps["rise_before_the_stop"].set_index(["finding", "chart"]); srt = ps["sorting_before_and_under_monitoring"].set_index("period"); one = ps["sorting_under_monitoring"]
    sbp = ps["stops_by_press"].set_index("press_id"); rr = ps["rise_rows"]
    nf = rr[(rr["finding"] == "nothing found") & (rr["chart"] == "EWMA on the total")]["rise_against_the_first_500"]
    grr = m["gauge_rr"].set_index(["fixture", "study"]); att = m["attribute_agreement"].set_index("study"); em = m["entry_methods"].set_index("entry_method")
    ac = a["autocorrelation"].set_index(["period", "characteristics"]); arp = a["after_the_reaction_plan"].iloc[0]
    ea = rec["entry_after_the_parts"].set_index("record"); tp = rec["time_of_the_parts"].set_index("record"); ppc = rec["pilot_planned_checks"].set_index(["press_id", "period", "shift"]); stamps = rec["pilot_stamps"].set_index(["press_id", "period", "entry_method"])
    cm = pd.DataFrame(o["pilot_complaints_by_month"]); cm["month_start"] = pd.to_datetime(cm["month_start"]); march = int(cm[cm["month_start"] == "2026-04-01"]["complaints"].sum())
    w = fo["ppk_table"]; rm = o["rule_1_by_month"]
    y25 = pr[pr["event_year"] == 2026]["punch_replacements"].sum(); after_stop = pr[(pr["event_year"] == 2026) & (pr["led_by"] == "after a stop by the per-stroke charts")]["punch_replacements"].sum()
    y23, y24 = pr[pr["event_year"] == 2024]["punch_replacements"].sum(), pr[pr["event_year"] == 2025]["punch_replacements"].sum()
    d_pilot = sc.loc[(P, 2026), "pieces_scrapped_share"] - sc.loc[(P, 2025), "pieces_scrapped_share"]; d_comp = sc.loc[(C, 2026), "pieces_scrapped_share"] - sc.loc[(C, 2025), "pieces_scrapped_share"]
    hours = srt.loc["before per-stroke monitoring, 2024 to 31 March 2026"]
    st = o["pilot_sorting_starts"].iloc[0]; sh = o["sharpening_at_the_count"].set_index("dies_on")
    ops_after = m["attribute_by_operator"]; ops_after = ops_after[ops_after["study"] == "after new limit samples"]; widest = float((ops_after["reject_rate"] - ops_after["reference_reject_rate"]).abs().max()) * 100
    g1, g2 = grr.loc[("F-20417", "rebuilt")], grr.loc[("F-31102", "rebuilt")]; b1, b2 = att.loc["at the redesign"], att.loc["after new limit samples"]
    p_adj, p_not, b_adj, b_not = ac.loc[("pilot presses, April to June 2026", "adjusted at the press")], ac.loc[("pilot presses, April to June 2026", "not adjusted at the press")], ac.loc[("2025, before the redesign", "adjusted at the press")], ac.loc[("2025, before the redesign", "not adjusted at the press")]
    e0, e1, e2 = ea.loc["pilot presses, April to June 2025, keyed"], ea.loc["pilot presses, April to June 2026, gauge-connected"], ea.loc["pilot presses, April to June 2026, keyed (attribute checks)"]
    nights = {pr_: (ppc.loc[(pr_, "April to June 2025", "nights"), "recorded_share"], ppc.loc[(pr_, "April to June 2026", "nights"), "recorded_share"]) for pr_ in ("PR-03", "PR-06", "PR-09")}
    cb = o["cost_lines"].set_index(["press_set", "category"]); bi24, bi25 = bu.loc[(P, 2025)], bu.loc[(P, 2026)]; 
    nc = pr[pr["led_by"] == "after nonconforming parts"].set_index("event_year")["punch_replacements"]

    # -- 1. Summary ----------------------------------------------------------
    body.append(section("summary", "1. Summary: outcomes on the pilot presses"))
    body.append("<p>The redesign ran on PR-03, PR-06 and PR-09 (the pilot presses) from 2 February 2026, with per-stroke monitoring from 1 April 2026. The other eight presses, unchanged through June, are the comparison. Results compare April to June 2026 with April to June 2025.</p>")
    s24, s25 = sc.loc[(P, 2025)], sc.loc[(P, 2026)]; saved = (s24.scrap_and_rework_share_of_revenue - s25.scrap_and_rework_share_of_revenue) * s25.revenue; fall = 1 - s25.scrap_and_rework_share_of_revenue / s24.scrap_and_rework_share_of_revenue
    cq = cap.loc[(P, "formed", 2025)], cap.loc[(P, "formed", 2026)]; cpn = cap.loc[(P, "punched", 2025)], cap.loc[(P, "punched", 2026)]
    assert 0.30 <= fall <= 0.37 and cq[1].ppk_median > 1.33 and abs(sc.loc[(C, 2026), "scrap_and_rework_share_of_revenue"] - sc.loc[(C, 2025), "scrap_and_rework_share_of_revenue"]) < 0.0005
    body.append("<p>In its first quarter the redesign cut scrap and rework on the pilot presses by a third and raised capability on formed characteristics above 1.33, while the comparison presses did not move.</p><ul>"
                f"<li><strong>Scrap and rework:</strong> {pct(s24.scrap_and_rework_share_of_revenue, 'scrap_and_rework.scrap_and_rework_share_of_revenue, pilot 2025', 2, '2.60%')} of revenue fell to {pct(s25.scrap_and_rework_share_of_revenue, 'scrap_and_rework.scrap_and_rework_share_of_revenue, pilot 2026', 2, '1.69%')}, "
                f"about ${num(round(saved, -3), 'scrap_and_rework: the fall in the share of revenue, pilot 2025 to 2026, times revenue of 2026, to the thousand', was='32,000')} in the quarter. On the comparison presses it held at "
                f"{pct(sc.loc[(C, 2026), 'scrap_and_rework_share_of_revenue'], 'scrap_and_rework.scrap_and_rework_share_of_revenue, comparison 2026', 2, '3.32%')}.</li>"
                f"<li><strong>Scrapped pieces:</strong> the share fell {num(-d_pilot * 100, 'scrap_and_rework.pieces_scrapped_share, pilot 2026 less 2025', '{:.2f}', '0.77')} points on the pilot presses and "
                f"{num(-d_comp * 100, 'scrap_and_rework.pieces_scrapped_share, comparison 2026 less 2025', '{:.2f}', '0.19')} on the comparison presses.</li></ul>")
    assert int(brk.strokes_largest) == 1
    body.append(f"<p>Production Ppk on critical formed characteristics rose from {num(cq[0].ppk_median, 'capability.ppk_median, pilot formed 2025, characteristics in both periods', '{:.2f}', '1.07')} to {num(cq[1].ppk_median, 'capability.ppk_median, pilot formed 2026, characteristics in both periods', '{:.2f}', '1.42')} (Section 3.1). "
                f"Alarm signals fell from {num(sg.loc[(P, ALL, 2025), 'alarm_signals_per_100_subgroups'], 'signals.alarm_signals_per_100_subgroups, pilot 2025', '{:.1f}', '15.3')} to {num(sg.loc[(P, ALL, 2026), 'alarm_signals_per_100_subgroups'], 'signals.alarm_signals_per_100_subgroups, pilot 2026', '{:.1f}', '5.3')} per 100 subgroups, "
                f"with an acknowledgement or adjustment recorded on {pct(sg.loc[(P, ALL, 2026), 'acknowledgement_or_adjustment_share'], 'signals.acknowledgement_or_adjustment_share, pilot 2026', was='99%')} against "
                f"{pct(sg.loc[(P, ALL, 2025), 'acknowledgement_or_adjustment_share'], 'signals.acknowledgement_or_adjustment_share, pilot 2025', was='65%')} (Section 4). The per-stroke charts stopped all {num(brk.punch_breaks_stopped_by_the_charts, 'punch_break_summary.punch_breaks_stopped_by_the_charts', was='6')} punch breaks on the stroke of the break (Section 3.3).</p>")
    body.append(f"<p>Customer PPM and sorting are too few to show an effect in three months. PPM was {num(pp.loc[(P, 2026), 'ppm'], 'ppm.ppm, pilot 2026', was='267')} on {num(pp.loc[(P, 2026), 'complaints'], 'ppm.complaints, pilot 2026', was='6')} complaints, against "
                f"{num(pp.loc[(P, 2025), 'ppm'], 'ppm.ppm, pilot 2025', was='191')} on {num(pp.loc[(P, 2025), 'complaints'], 'ppm.complaints, pilot 2025', was='6')} in 2025 and {num(pp.loc[(P, 2024), 'ppm'], 'ppm.ppm, pilot 2024', was='193')} on {num(pp.loc[(P, 2024), 'complaints'], 'ppm.complaints, pilot 2024', was='5')} in 2024. "
                f"There was {word(so.loc[(P, 2025), 'sorting_events'], ONE, 'sorting.sorting_events, pilot 2025', 'one')} sorting event in the quarter of 2025 and {word(so.loc[(P, 2026), 'sorting_events'], ONE, 'sorting.sorting_events, pilot 2026', 'none')} in 2026 (Section 5).</p>")
    body.append(exhibit(f_sets, "Five measures by press set, April to June 2024 to 2026", "Each row is one press set and each panel one measure for April to June of 2024, 2025 and 2026, with the 95% interval on PPM and on Ppk. Ppk is on the characteristics with 60 subgroups or more in both 2025 and 2026."))
    assert all(cb.loc[(P, x), 2026] < cb.loc[(P, x), 2025] for x in ("scrap", "rework labor", "premium freight")) and pp.loc[(P, 2026), "complaints"] == pp.loc[(P, 2025), "complaints"]
    body.append(f"<p>Quality costs booked to the pilot presses fell on scrap, rework and premium freight, and rose on customer charge-backs: ${num(cb.loc[(P, 'customer charge-back'), 2026], 'cost_lines: customer charge-back, pilot 2026', was='3,734')} against "
                f"${num(cb.loc[(P, 'customer charge-back'), 2025], 'cost_lines: customer charge-back, pilot 2025', was='2,925')}, on the same number of complaints.</p>")
    body.append(exhibit(fo["costs"], "Quality cost lines as booked, pilot presses, April to June", "Each group is one category of quality cost booked to the pilot presses for April to June of the three years, on a log scale."))

    # -- 2. The redesign -----------------------------------------------------
    body.append(section("redesign", "2. The redesign"))
    body.append("<p>Each characteristic class now runs on a chart and limits set for its behaviour.</p>")
    cp = control_plan.plan()
    design = {"three-way chart": ("Formed height and bend angle", "Subgroup means on an individuals chart with limits from the moving range of the baseline means, and a range chart", "Baseline of at least 25 subgroups spanning at least five coil changes; recomputed after each sharpening; coil-change subgroup; adjust on a rule 1 alarm"),
              "tool-wear chart": ("Hole diameter", "Centre line on the regression of diameter on shots since sharpening, limits about the line", "The die's earlier sharpening intervals; recomputed on a planned trigger"),
              "X-bar and R": ("Hole position, length, width and flatness", "Means and range charts", "Stable 25-subgroup baseline after each sharpening, held until the next"),
              "attribute check": ("Burr against the limit sample; hole diameter by pin gauge", "Accept or reject", "New limit samples; operators qualified against the burr gauge"),
              "no limit set in force": ("Burr height on the laboratory gauge", "No chart", "Controlled by the sharpening count, set from the die's burr line")}
    rd = cp.groupby("chart_in_force").agg(characteristics=("characteristic_id", "count"), critical=("critical", "sum"), subgroups_used_median=("subgroups_used", lambda x: pd.to_numeric(x, errors="coerce").astype(float).median()), coil_changes_spanned_median=("coil_changes_spanned", lambda x: pd.to_numeric(x, errors="coerce").astype(float).median())).reindex(list(design)).reset_index()
    for col in ("subgroups_used_median", "coil_changes_spanned_median"):
        rd[col] = pd.to_numeric(rd[col], errors="coerce").astype(float)
    rd["class"] = rd["chart_in_force"].map(lambda c: design[c][0]); rd["scheme"] = rd["chart_in_force"].map(lambda c: design[c][1]); rd["basis"] = rd["chart_in_force"].map(lambda c: design[c][2])
    rd["chart_in_force"] = rd["chart_in_force"].map(control_plan.CHART_NAME)
    body.append(show(rd, {"class": "Characteristic class", "chart_in_force": "Chart", "basis": "Limits", "characteristics": "Characteristics", "critical": "Critical"}))
    burr_gauge = int((cp["chart_in_force"] == "no limit set in force").sum()); burr_attribute = int(((cp["chart_in_force"] == "attribute check") & (cp["characteristic_type"] == "burr height")).sum())
    rpn = o["reaction_plan"]
    body.append("<p>Every chart carries a written reaction plan: rule 1 alarms at the press, a die adjustment is made only on a rule 1 signal or at a coil-change subgroup, and every adjustment is recorded. "
                "Critical characteristics are checked every 30 minutes on the high-speed press and hourly on the medium presses, with a check at each coil change. Pilot dies are sharpened at the shot count where burr reaches 80% of its limit. "
                "Per-stroke monitoring runs on every die on the pilot presses from 1 April 2026.</p>")

    # -- 3. Results by element of the redesign -------------------------------
    body.append(section("results", "3. Results by element of the redesign"))
    body.append(sub("formed", "3.1 Formed characteristics: three-way charts and the coil-change subgroup"))
    assert len(w) == int(cq[1].characteristics) == int(cq[0].characteristics)
    gap24, gap25 = round(cq[0].cpk_median, 2) - round(cq[0].ppk_median, 2), round(cq[1].cpk_median, 2) - round(cq[1].ppk_median, 2)
    body.append(f"<p>Capability on formed characteristics rose above 1.33 on most characteristics. On the {num(len(w), 'capability_by_characteristic: pilot formed characteristics in both periods', was='46')} characteristics measured in both quarters, production Ppk rose from "
                f"{num(cq[0].ppk_median, 'capability.ppk_median, pilot formed 2025, characteristics in both periods', '{:.2f}', '1.07')} to {num(cq[1].ppk_median, 'capability.ppk_median, pilot formed 2026, characteristics in both periods', '{:.2f}', '1.42')}, and those under 1.33 fell from "
                f"{num(int((w[2025] < 1.33).sum()), 'capability_by_characteristic: Ppk under 1.33 in 2025', was='36')} to {num(int((w[2026] < 1.33).sum()), 'capability_by_characteristic: Ppk under 1.33 in 2026', was='10')}. "
                f"{num(int((w[2026] > w[2025]).sum()), 'capability_by_characteristic: Ppk higher in 2026', was='39')} of the {num(len(w), 'capability_by_characteristic: pilot formed characteristics in both periods', was='46')} are higher. "
                f"Cpk rose only from {num(cq[0].cpk_median, 'capability.cpk_median, pilot formed 2025, characteristics in both periods', '{:.2f}', '1.53')} to {num(cq[1].cpk_median, 'capability.cpk_median, pilot formed 2026, characteristics in both periods', '{:.2f}', '1.70')}, and the gap between Cpk and Ppk fell from "
                f"{num(gap24, 'capability: cpk_median less ppk_median as printed, pilot formed 2025', '{:.2f}', '0.46')} to {num(gap25, 'capability: cpk_median less ppk_median as printed, pilot formed 2026', '{:.2f}', '0.28')}, so most of the gain is variation between subgroups removed. "
                f"Punched characteristics held at {num(cpn[0].ppk_median, 'capability.ppk_median, pilot punched 2025, characteristics in both periods', '{:.2f}', '1.57')} to {num(cpn[1].ppk_median, 'capability.ppk_median, pilot punched 2026, characteristics in both periods', '{:.2f}', '1.63')}.</p>")
    body.append(exhibit(fo["ppk"], "Production Ppk by characteristic, April to June 2025 against 2026", "Each point is one critical formed characteristic of the pilot presses: its production Ppk from April to June 2025 against April to June 2026, with the equal line and 1.33 on both axes."))

    cd = o["coil_change_by_distance"].set_index("distance_from_the_centre_line"); cf = o["coil_change_what_follows"].set_index(["period", "at_the_coil_change"]); mid = cd.loc[["One to two sigma", "Two to three sigma"]].sum(); far = cd.loc["Beyond three sigma"]
    assert int(far.rule_1_alarms) == int(far.coil_change_subgroups) and query("select count(*) as n from staging.stg_spc__reaction_plan_steps where signal not in ('rule 1', 'rules 2 to 4')")["n"].iloc[0] == 0
    body.append("<p>The die is centred at a coil change when the coil-change subgroup raises a rule 1 alarm, and rarely otherwise.</p><ul>"
                f"<li><strong>Beyond three sigma:</strong> an adjustment is recorded on {num(far.adjustments_recorded, 'coil_change_by_distance.adjustments_recorded, beyond three sigma', was='158')} of {num(far.coil_change_subgroups, 'coil_change_by_distance.coil_change_subgroups, beyond three sigma', was='159')} coil-change subgroups.</li>"
                f"<li><strong>One to three sigma off centre:</strong> an adjustment is recorded on {num(mid.adjustments_recorded, 'coil_change_by_distance.adjustments_recorded, one to three sigma', was='30')} of {num(mid.coil_change_subgroups, 'coil_change_by_distance.coil_change_subgroups, one to three sigma', was='276')}. The reaction plan carries no coil-change step.</li></ul>"
                f"<p>Coils left off centre stay there. In April to June, {pct(cf.loc[('April to June 2026', 'no adjustment recorded'), 'share'], 'coil_change_what_follows.share, April to June 2026, no adjustment recorded', was='59%')} of the next five subgroups on a coil left past one sigma fell beyond one sigma on the same side, against "
                f"{pct(cf.loc[('April to June 2026', 'adjustment recorded'), 'share'], 'coil_change_what_follows.share, April to June 2026, adjustment recorded', was='39%')} after a centring step.</p>")
    body.append(titled_table("Coil-change subgroups by distance from the centre line, with adjustments recorded, pilot presses, 2 February to 30 June 2026",
                             show(o["coil_change_by_distance"], {"distance_from_the_centre_line": "Distance from the centre line", "coil_change_subgroups": "Coil-change subgroups", "rule_1_alarms": "Rule 1 alarms", "adjustments_recorded": "Adjustments recorded"}, {k: F0 for k in ("coil_change_subgroups", "rule_1_alarms", "adjustments_recorded")})))

    body.append(sub("sharpening", "3.2 Sharpening at the count and tool-wear charts"))
    iv = o["pilot_intervals"]; late = iv[~iv["began_before_the_count"]]; early = iv[iv["began_before_the_count"]]
    past = early[early["shots_in_interval_logged"] > early["shots_at_80pct_of_limit"]]; worst = early.sort_values("logged_over_the_count").iloc[-1]
    op = o["pilot_open_intervals"]; still = op[op["began_before_the_count"]]; worst_open = still.sort_values("over_the_count").iloc[-1]
    assert worst_open.die_id == "D-5884-A"
    assert int(late["over_the_limit"].sum()) == 0 and int((late["shots_in_interval_logged"] > late["shots_at_80pct_of_limit"]).sum()) == 0 and len(iv) == int(bi25.intervals_with_burr_gauge_subgroups)
    assert int(early["over_the_limit"].sum()) == int(bi25.intervals_with_burr_over_the_limit) == 2 and int(bi24.intervals_with_burr_over_the_limit) == 2 and worst.over_the_limit and round(worst.logged_over_the_count) == 2 and early["interval_end"].notna().all()
    body.append(f"<p>Sharpening at the count has kept burr under its limit on every interval begun under it: all {num(len(late), 'pilot_intervals: began on or after 2 February 2026', was='13')} pilot intervals begun after 2 February were sharpened at or before the count, and none crossed the limit. "
                f"The count applied from each die's next sharpening, so the {num(len(early), 'pilot_intervals: began before 2 February 2026', was='8')} intervals already running carried on. {word(len(past), CAP, 'pilot_intervals: began before 2 February 2026 and passed the count', 'Five')} of them passed their count, and "
                f"{word(int(early['over_the_limit'].sum()), ONE, 'pilot_intervals: over the limit, began before 2 February 2026', 'two')} crossed the limit, {worst.die_id} at twice its count. Of the {num(len(iv), 'pilot_intervals: ending April to June 2026 with burr gauge subgroups', was='21')} intervals ending in April to June, the share over the limit is unchanged at "
                f"{pct(bi25.share_over_the_limit, 'burr.share_over_the_limit, pilot 2026', was='10%')}, against {pct(bi24.share_over_the_limit, 'burr.share_over_the_limit, pilot 2025', was='9%')} in 2025. "
                f"All eight have since been sharpened. {word(len(still), CAP, 'pilot dies on an interval begun before 2 February 2026 and open at 30 June', 'Eight')} other pilot dies are still on intervals begun before 2 February, and {worst_open.die_id} is at "
                f"{num(worst_open.over_the_count, 'pilot dies with an open interval: shots since sharpening over the due count, highest of those begun before 2 February', '{:.2f}', '1.33')} times its count. "
                f"Burr nonconformances at the press check were {num(bi25.burr_nonconformances_at_the_press_check, 'burr.burr_nonconformances_at_the_press_check, pilot 2026', was='1')}, against {num(bi24.burr_nonconformances_at_the_press_check, 'burr.burr_nonconformances_at_the_press_check, pilot 2025', was='2')}.</p>")
    body.append(exhibit(f_burr, "Sharpening intervals with burr over the limit before the sharpening", "Each column is the share of the sharpening intervals ending in the period with a burr gauge reading over the limit before the sharpening, with its 95% interval and the count above it."))
    body.append(f"<p>On hole diameters the tool-wear chart cut alarm signals from {num(hdy.loc[2025, 'alarm_signals_per_100_subgroups'], 'hole_diameter_under_the_tool_wear_chart.alarm_signals_per_100_subgroups, 2025', '{:.1f}', '14.4')} to "
                f"{num(hdy.loc[2026, 'alarm_signals_per_100_subgroups'], 'hole_diameter_under_the_tool_wear_chart.alarm_signals_per_100_subgroups, 2026', '{:.1f}', '0.6')} per 100 subgroups, with production Ppk unchanged at "
                f"{num(hdy.loc[2026, 'ppk_median'], 'hole_diameter_under_the_tool_wear_chart.ppk_median, 2026', '{:.2f}', '1.55')} against {num(hdy.loc[2025, 'ppk_median'], 'hole_diameter_under_the_tool_wear_chart.ppk_median, 2025', '{:.2f}', '1.57')}.</p>")
    body.append(exhibit(f_hole, f"Hole diameter {hole['characteristic_id']} on its tool-wear chart, die {hole['die_id']}", f"Interval begun {hole['interval_begun']}, in progress at 30 June: {hole['subgroups']} subgroup means against shots since sharpening, with the centre line and limits in force at each entry."))

    body.append(sub("monitoring", "3.3 Per-stroke monitoring"))
    ew = rise.loc[("punch worn and replaced", "EWMA on the total")]; kw = fps["worn_stop"]; kb = fps["break_stop"]
    worn = int(both["punch worn and replaced"] + both["punch chipped and replaced"])
    body.append(f"<p>Per-stroke monitoring cut the parts made between a punch failure and its finding from a median {num(hours.parts_since_the_check_before_median, 'sorting_before_and_under_monitoring.parts_since_the_check_before_median, hourly check', was='5,756')} under the hourly check to "
                f"{word(brk.strokes_largest, ONE, 'punch_break_summary.strokes_largest', 'one')} stroke. The charts stopped the pilot presses {num(both.stops, 'stops_by_chart.stops, both charts', was='36')} times in three months:</p><ul>"
                f"<li>a worn or chipped punch on {num(worn, 'stops_by_chart: punch worn and punch chipped, both charts', was='22')};</li><li>slug pulling on {num(both['slug pulling cleared'], 'stops_by_chart.slug pulling cleared, both charts', was='9')};</li>"
                f"<li>nothing found on {num(both['nothing found'], 'stops_by_chart.nothing found, both charts', was='5')}.</li></ul>"
                f"<p>Stops with nothing found run at {num(rate.nothing_found_per_million_strokes, 'stops_with_nothing_found.nothing_found_per_million_strokes, pilot presses', '{:.2f}', '0.63')} per million strokes, against a design ceiling of "
                f"{num(rate.design_false_signals_per_million_at_most, 'stops_with_nothing_found.design_false_signals_per_million_at_most', '{:.1f}', '2.0')}.</p>")
    body.append(exhibit(fps["break"], "Channel shares over the 300 strokes before a punch break", f"Each line is one channel's share of the total over the 300 strokes before stop {kb['fault_event_id']} on {kb['press_id']}, die {kb['die_id']}, the first punch break on a press with four channels, with the channel that stepped in colour."))
    body.append(f"<p>Punch replacements now follow the charts rather than nonconforming parts. {num(after_stop, 'punch_replacements: after a stop by the per-stroke charts, 2026', was='22')} of the {num(y25, 'punch_replacements: all, 2026', was='25')} replacements in April to June followed a stop and "
                f"{num(nc.loc[2026], 'punch_replacements: after nonconforming parts, 2026', was='1')} followed nonconforming parts, against {num(nc.loc[2025], 'punch_replacements: after nonconforming parts, 2025', was='3')} of {num(y24, 'punch_replacements: all, 2025', was='15')} after nonconforming parts in the same months of 2025.</p>")
    body.append(exhibit(fps["replacements"], "Punch replacements, April to June, by what led to them", "Each column is the punch replacements on the dies run on the pilot presses in April to June of one year, split by what led to them."))

    # -- 4. Signals, adjustment and the record -------------------------------
    body.append(section("signals", "4. Signals, adjustment and the record"))
    assert int(arp.following_neither) == 0
    body.append(f"<p>Alarms are now fewer and answered: {num(sg.loc[(P, ALL, 2026), 'alarm_signals_per_100_subgroups'], 'signals.alarm_signals_per_100_subgroups, pilot 2026', '{:.1f}', '5.3')} per 100 subgroups against "
                f"{num(sg.loc[(P, ALL, 2025), 'alarm_signals_per_100_subgroups'], 'signals.alarm_signals_per_100_subgroups, pilot 2025', '{:.1f}', '15.3')}, with an adjustment recorded on {pct(sg.loc[(P, ALL, 2026), 'adjustment_share'], 'signals.adjustment_share, pilot 2026', was='84%')} against "
                f"{pct(sg.loc[(P, ALL, 2025), 'adjustment_share'], 'signals.adjustment_share, pilot 2025', was='17%')}. Every recorded adjustment follows a rule 1 alarm or a coil-change subgroup. The within-coil autocorrelation on adjusted characteristics moved from "
                f"{num(b_adj.lag_1_autocorrelation, 'autocorrelation.lag_1_autocorrelation, 2025 adjusted', '{:.2f}', '-0.14')} to {num(p_adj.lag_1_autocorrelation, 'autocorrelation.lag_1_autocorrelation, pilot adjusted', '{:.2f}', '0.07')}.</p>")
    body.append(exhibit(f_alarm, "Alarm signals and adjustments recorded, by press set", "Each column is April to June of one year. The left panel is alarm signals per 100 subgroups and the right panel the share of alarm signals with an adjustment recorded."))
    body.append(exhibit(fa["autocorrelation_after"], "Lag-1 autocorrelation of subgroup means, 2025 and the pilot presses in 2026", "Each point is the lag-1 autocorrelation of subgroup means within a run and coil with its 95% interval; the dashed line is zero. The upper pair is 2025 and the lower pair the pilot presses from April to June 2026."))
    days6 = ppc.loc[("PR-06", "April to June 2026", "days"), "recorded_share"]
    body.append("<p>The record under the charts is restored.</p><ul>"
                f"<li><strong>Fixtures:</strong> the two rebuilt fixtures stand at {pct(g1.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-20417 after rebuild', 1, '7.7%')} and {pct(g2.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-31102 after rebuild', 1, '9.5%')} of tolerance.</li>"
                f"<li><strong>Burr check:</strong> it agrees with the gauge on {pct(b2.against_reference, 'attribute_agreement.against_reference, after new limit samples', was='92%')} of calls (kappa {num(b2.fleiss_kappa, 'attribute_agreement.fleiss_kappa, after', '{:.2f}', '0.78')}).</li>"
                f"<li><strong>Late entries:</strong> {pct(e1.share, 'entry_after_the_parts.share, pilot gauge-connected 2026', 1, '2.1%')} of gauge-connected entries are made more than 20 minutes after the parts, against {pct(e0.share, 'entry_after_the_parts.share, pilot keyed 2025', 1, '15.4%')} of keyed entries in 2025.</li>"
                f"<li><strong>Night shift:</strong> planned checks recorded on PR-06 and PR-09 rose from {pct(nights['PR-06'][0], 'pilot_planned_checks.recorded_share, PR-06 nights 2025', was='77%')} and {pct(nights['PR-09'][0], 'pilot_planned_checks.recorded_share, PR-09 nights 2025', was='72%')} to "
                f"{pct(nights['PR-06'][1], 'pilot_planned_checks.recorded_share, PR-06 nights 2026', was='86%')} and {pct(nights['PR-09'][1], 'pilot_planned_checks.recorded_share, PR-09 nights 2026', was='90%')}.</li></ul>")
    body.append(exhibit(frec["entry_after"], "Minutes from the parts to the entry, pilot presses", "Each line is the distribution of the minutes from the parts to the entry on a log scale, and the dashed line marks 20 minutes."))

    # -- 5. What has not moved -----------------------------------------------
    body.append(section("open", "5. What has not moved"))
    twelve = "Report again on twelve months"
    left = pd.DataFrame([
        ("Customer PPM, pilot presses", f"{pp.loc[(P, 2025), 'ppm']:.0f} to {pp.loc[(P, 2026), 'ppm']:.0f}, on {pp.loc[(P, 2026), 'complaints']:.0f} complaints in each quarter", twelve, "ppm.ppm and complaints, pilot 2025 and 2026", "191 to 267, on 6 complaints in each quarter"),
        ("Customer charge-backs, pilot presses", f"${cb.loc[(P, 'customer charge-back'), 2025]:,.0f} to ${cb.loc[(P, 'customer charge-back'), 2026]:,.0f}", "Report with PPM on twelve months", "cost_lines: customer charge-back, pilot 2025 and 2026", "$2,925 to $3,734"),
        ("Sorting events, pilot presses", f"{so.loc[(P, 2025), 'sorting_events']:.0f} to {so.loc[(P, 2026), 'sorting_events']:.0f}; {so.loc[(P, 2024), 'sorting_events']:.0f} in 2024", twelve, "sorting.sorting_events, pilot", "1 to 0; 3 in 2024"),
        ("Burr over the limit, pilot dies", f"{bi25.intervals_with_burr_over_the_limit:.0f} of {bi25.intervals_with_burr_gauge_subgroups:.0f} intervals, both begun before 2 February; {len(o['pilot_open_intervals'][o['pilot_open_intervals']['began_before_the_count']])} pilot dies still on intervals begun before it", f"Sharpen each of the {len(o['pilot_open_intervals'][o['pilot_open_intervals']['began_before_the_count']])} at its count; report on intervals begun under the count", "burr.intervals_with_burr_over_the_limit and intervals_with_burr_gauge_subgroups, pilot 2026; pilot_intervals; pilot_open_intervals", "2 of 21 intervals, both begun before 2 February; 8 pilot dies still on intervals begun before it"),
        ("Centring at the coil change, pilot presses", f"Adjustment recorded on {mid.adjustments_recorded:.0f} of {mid.coil_change_subgroups:.0f} coil-change subgroups between one and three sigma off centre", "Add a coil-change step to the reaction plan: centre the die when the coil-change subgroup is past one sigma",
         "coil_change_by_distance: adjustments_recorded and coil_change_subgroups, one to three sigma", "Adjustment recorded on 30 of 276 coil-change subgroups between one and three sigma off centre"),
        ("Night shift, PR-06", f"{nights['PR-06'][1] * 100:.0f}% of planned checks recorded, against {days6 * 100:.0f}% on days", "Weekly review by shift", "pilot_planned_checks.recorded_share, PR-06 nights and days 2026", "86% of planned checks recorded, against 99% on days"),
    ], columns=["Item", "As found", "Action", "read_from", "was"])
    assert len(left) == 6
    body.append("<p>Six items are not yet conclusive or not yet in place.</p>")
    for v, src, was in zip(left["As found"], left["read_from"], left["was"]):
        TRACE.append((SECTION[0], v, src, was))
    body.append(S.table(left.drop(columns=["read_from", "was"])))
    body.append("<p>The redesign and per-stroke monitoring extend to the other eight presses from 3 August 2026.</p>")
    n_body = FIGURE[0]

    # -- Appendix ------------------------------------------------------------
    SECTION[0] = "Appendix"
    ax = ['<h2 id="appendix">Appendix</h2>', "<h3>Method and data</h3>", METHOD]
    ax.append("<h3>Appendix 1. The redesign (Section 2)</h3>")
    ax.append(show(rd, {"class": "Characteristic class", "chart_in_force": "Chart", "scheme": "Scheme", "basis": "Limits", "characteristics": "Characteristics, 30 June 2026", "critical": "Critical", "subgroups_used_median": "Subgroups used, median", "coil_changes_spanned_median": "Coil changes spanned, median"},
                   {"subgroups_used_median": F0, "coil_changes_spanned_median": F0}))
    ax.append(show(o["redesign_by_class"], {"characteristic_class": "Characteristic class", "limits_basis": "Limits basis as recorded", "characteristics": "Characteristics", "critical_characteristics": "Critical", "subgroups_used_median": "Subgroups used, median", "coil_changes_spanned_median": "Coil changes spanned, median",
                                            "check_frequency_minutes_in_the_master": "Check frequency in the master, minutes"}, {"subgroups_used_median": F0, "coil_changes_spanned_median": F0}))
    ax.append(show(rpn, {"signal": "Signal", "step": "Step", "action": "Action", "owner": "Owner", "characteristics": "Characteristics", "first_in_force": "First in force"}, {"first_in_force": lambda v: str(v)[:10]}))
    ax.append(show(rec["pilot_stamps"], {"press_id": "Press", "period": "Period", "entry_method": "Entry", "subgroups": "Routine subgroups", "hour_share": "Within five minutes of the hour", "half_hour_share": "Within five minutes of the half hour"}, {"subgroups": F0, "hour_share": P1, "half_hour_share": P1}))

    ax.append("<h3>Appendix 2. Measurement, adjustment and recording (Section 4)</h3>")
    ax.append(exhibit(fm["grr_after"], "Gauge R&amp;R by study, after rebuild", "Each column is one gauge R&amp;R study on a check fixture, with %GRR of tolerance and ndc at its top. The dashed lines are at 10% and 30%."))
    ax.append(exhibit(fm["burr_after"], "Burr check by operator, at the assessment and after new limit samples", f"Each point is one operator's share of the {num(b1.parts, 'attribute_agreement.parts')} parts rejected over {num(b1.trials, 'attribute_agreement.trials')} trials, and the vertical line is the share the burr gauge rejects. "
                                        f"Operators are in the same order in both panels, by their reject rate at the assessment. After the new limit samples and qualification all {num(len(ops_after), 'attribute_by_operator: operators')} operators reject within {num(widest, 'attribute_by_operator: widest reject rate less the burr gauge, after')} points of the gauge."))
    gt = m["gauge_rr"].assign(study=lambda x: x["study"].map({"PPAP": "PPAP", "redesign": "assessment, January 2026", "rebuilt": "after rebuild"})).reset_index(drop=True)
    ax.append(show(gt, {"fixture": "Fixture", "study": "Study", "study_date": "Date", "tolerance_mm": "Tolerance, mm", "pct_tolerance": "%GRR of tolerance", "pct_study_variation": "%Study variation", "ndc": "ndc", "repeatability_sd_mm": "Repeatability SD, mm", "reproducibility_sd_mm": "Reproducibility SD, mm", "interaction_p": "Interaction p"},
                   {"study_date": lambda v: str(v)[:10], "tolerance_mm": F2, "pct_tolerance": lambda v: f"{v:.1f}", "pct_study_variation": lambda v: f"{v:.1f}", "repeatability_sd_mm": F4, "reproducibility_sd_mm": F4, "interaction_p": F3}))
    for key in sorted(m["anova_tables"]):
        if key[1] == "rebuilt":
            ax.append(anova_block((key[0], "after rebuild"), m["anova_tables"][key]))
    ax.append(exhibit(fm["split_after"], "Gauge variance by study: repeatability and reproducibility", "Each bar is the gauge variance of one study, split between repeatability and reproducibility between operators. The lighter bars are the studies after rebuild."))
    ax.append(show(m["attribute_agreement"].assign(study=lambda x: x["study"].map({"at the redesign": "assessment, January 2026", "after new limit samples": "after new limit samples"})), {"study": "Burr check study", "calls": "Calls", "within_operator": "Within operator", "all_operators_agree": "All operators agree", "pairs_of_operators_agree": "Pairs of operators agree",
                                              "against_reference": "Against the burr gauge", "reference_low": "Low", "reference_high": "High", "fleiss_kappa": "Fleiss' kappa", "kappa_low": "Kappa low", "kappa_high": "Kappa high"},
                   {"within_operator": P0, "all_operators_agree": P0, "pairs_of_operators_agree": P0, "against_reference": P1, "reference_low": P1, "reference_high": P1, "fleiss_kappa": F2, "kappa_low": F2, "kappa_high": F2}))
    ax.append(show(m["entry_methods"], {"entry_method": "Entry method", "readings": "Readings", "ending_0_or_5": "Ending in 0 or 5", "times_the_uniform_expectation": "Times the uniform rate", "set_aside_by_the_plausibility_rule": "Set aside as mis-keyed"}, {"readings": F0, "ending_0_or_5": F0, "times_the_uniform_expectation": F2, "set_aside_by_the_plausibility_rule": F0}))
    ax.append(exhibit(fm["digit_after"], "Last digit of readings by entry method", "Each panel gives the share of readings ending in each digit for one entry method, with the reading count in the panel title. The dashed line is the 10% each digit would hold if none were preferred."))
    ax.append(exhibit(fk["cmm_after"], "Check fixture reading less CMM reading on matched first pieces", "Each point is one first-piece subgroup measured on both the check fixture and the CMM, as the fixture reading less the CMM reading; the marker beside each group is its mean with a 95% interval, and the line is zero. "
                                       "The check fixture reads to 0.01 mm, so the differences fall on a grid. The rebuilt fixtures have one matched first piece."))
    ax.append(show(a["autocorrelation"], {"period": "Period", "characteristics": "Characteristics", "lag_1_autocorrelation": "Lag-1 autocorrelation", "low": "Low", "high": "High", "segments": "Segments", "characteristics_n": "Characteristics, count"}, {"lag_1_autocorrelation": F3, "low": F3, "high": F3, "segments": F0}))
    ax.append(show(rec["entry_after_the_parts"], {"record": "Record", "subgroups": "Subgroups", "entered_more_than_20_minutes_after": "Entered more than 20 minutes after the parts", "share": "Share", "share_low": "Low", "share_high": "High", "minutes_to_entry_median": "Minutes to entry, median"},
                   {"subgroups": F0, "entered_more_than_20_minutes_after": F0, "share": P1, "share_low": P1, "share_high": P1, "minutes_to_entry_median": lambda v: f"{v:.1f}"}))
    ax.append(show(rec["pilot_planned_checks"], {"press_id": "Press", "period": "Period", "shift": "Shift", "planned_checks": "Planned checks", "recorded": "Recorded", "recorded_share": "Share", "recorded_share_low": "Low", "recorded_share_high": "High"}, {"planned_checks": F0, "recorded": F0, "recorded_share": P1, "recorded_share_low": P1, "recorded_share_high": P1}))
    ax.append(exhibit(frec["pilot"], "Planned checks recorded by pilot press and shift", "Each row is one pilot press and shift: the share of planned checks recorded from April to June 2025 and from April to June 2026. PR-03 is counted at the 60 minutes in the characteristics master."))
    t0, t1 = tp.loc["April to June 2025, keyed"], tp.loc["April to June 2026, gauge-connected"]
    ax.append(f"<div class='caption'>On PR-06 and PR-09 the time of the parts is within five minutes of the hour on {P1(t0['share'])} of keyed subgroups from April to June 2025 and {P1(t1['share'])} of gauge-connected subgroups from April to June 2026; gauge-connected readings post as taken, so the stamp is the time of the parts. "
              f"The gauge-connected readings are 2026 on centred characteristics and are not like for like with the keyed readings of 2025 at the specification limits. A planned check is defined as in the assessment report.</div>")

    ax.append("<h3>Appendix 3. Per-stroke monitoring (Section 3.3)</h3>")
    ax.append(exhibit(fps["worn"], "Per-stroke total before a stop with a worn punch found", f"The points are the per-stroke total over the 6,500 strokes before stop {kw['fault_event_id']} on {kw['press_id']} (every third stroke drawn), the line is the EWMA, the grey line the level of the run's first 500 strokes and the dashed lines the EWMA limits. "
                                   f"The stop is the one whose rise is nearest the median of the stops with a worn punch found; the press stops when the EWMA reaches its upper limit, {pct(kw['rise_against_the_first_500'], 'rise_rows.rise_against_the_first_500, the stop shown', 1)} above the level of the first 500 strokes."))
    pr9 = sbp.loc["PR-09", "slug pulling cleared"]
    ax.append(exhibit(fps["stops"], "Stops by chart and the toolmaker's finding", "Each bar is the stops by one chart from 1 April to 30 June 2026, split by the toolmaker's finding."))
    ax.append(show(ps["tonnage_by_press"], {"press_id": "Press", "runs": "Runs", "production_strokes": "Production strokes", "setup_strokes_set_aside": "Setup strokes set aside", "lag_1_autocorrelation_median": "Lag-1 autocorrelation, median by run", "lowest": "Lowest", "highest": "Highest", "ar1_coefficient_first_500_median": "AR(1) coefficient, first 500 strokes",
                                            "coefficient_of_variation_median": "Coefficient of variation"}, {"runs": F0, "production_strokes": F0, "setup_strokes_set_aside": F0, "lag_1_autocorrelation_median": F2, "lowest": F2, "highest": F2, "ar1_coefficient_first_500_median": F2, "coefficient_of_variation_median": P1}))
    ax.append(S.table(ps["stops_by_chart"].rename(columns={"chart": "Chart", "stops": "Stops"})))
    ax.append(S.table(ps["stops_by_press"].rename(columns={"press_id": "Press", "stops": "Stops"})))
    ax.append(show(ps["stops_with_nothing_found"], {"press_id": "Press", "production_strokes": "Production strokes", "stops": "Stops", "stops_with_nothing_found": "With nothing found", "nothing_found_per_million_strokes": "Per 1,000,000 strokes", "low": "Low", "high": "High", "design_false_signals_per_million_at_most": "Design, at most"},
                   {"production_strokes": F0, "nothing_found_per_million_strokes": F2, "low": F2, "high": F2, "design_false_signals_per_million_at_most": lambda v: f"{v:.1f}"}))
    ax.append(show(ps["rise_before_the_stop"], {"finding": "Finding", "chart": "Chart", "stops": "Stops", "rise_against_the_first_500_median": "Total at the stop against the first 500 strokes, median", "rise_p10": "10th percentile", "rise_p90": "90th percentile", "with_6000_strokes_before": "With 6,000 strokes before", "rise_over_the_last_6000_median": "Over the last 6,000 strokes, median"},
                   {"rise_against_the_first_500_median": P1, "rise_p10": P1, "rise_p90": P1, "rise_over_the_last_6000_median": P1}))
    ax.append(show(ps["punch_breaks"], {"fault_event_id": "Stop", "press_id": "Press", "die_id": "Die", "channel": "Channel", "share_at_the_stop_in_sigma": "Share at the stop, sigma", "channel_peak_before_kn": "Channel peak before, kN", "channel_peak_from_the_step_kn": "From the step, kN", "fall_in_the_channel_peak": "Fall", "strokes_from_the_step_to_the_stop": "Strokes from the step to the stop"},
                   {"share_at_the_stop_in_sigma": lambda v: f"{v:.1f}", "channel_peak_before_kn": F0, "channel_peak_from_the_step_kn": F0, "fall_in_the_channel_peak": P1}))
    ax.append(exhibit(fps["falls"], "Fall in the channel peak at the punch breaks", "Each point is one of the punch breaks: the fall in the affected channel's peak at the stop."))
    ax.append(show(pr, {"event_year": "Year, 1 April to 30 June", "led_by": "Punch replacement", "punch_replacements": "Count"}))
    ax.append(show(ps["sorting_before_and_under_monitoring"], {"period": "Sorting events found at the press, pilot presses", "sorting_events_found_at_the_press": "Events", "parts_since_the_check_before_median": "Parts since the check before (estimated), median", "quantity_sorted_median": "Quantity sorted, median", "quantity_sorted_largest": "Largest"},
                   {"parts_since_the_check_before_median": F0, "quantity_sorted_median": F0, "quantity_sorted_largest": F0}))
    ax.append(exhibit(fps["autocorrelation"], "Lag-1 autocorrelation of the per-stroke total, by run", "Each point is one run: the lag-1 autocorrelation of the per-stroke total, with the median by press marked and the autocorrelation range covered by the chart design shaded."))
    ax.append(f"<div class='caption'>The channel that stepped at a punch break is the one whose peak fell furthest at the stop; a stroke is part of the step when the channel's share is more than 4 sigma from its level over the strokes 300 to 21 before the stop. The rise in the total is the mean over the last 200 strokes before the stop against the run's first 500 production strokes. "
              f""
              f"The time by which a stop came before a worn punch would have made a nonconforming part is not in the record and is not reported.</div>")

    ax.append("<h3>Appendix 4. Outcomes (Sections 1, 3 and 5)</h3>")
    ax.append(exhibit(fo["pilot"], "The pilot presses on five measures, April to June", "Each panel is one measure on the pilot presses for April to June of 2024, 2025 and 2026, with the 95% interval on PPM and on Ppk."))
    cf24, cf25 = cap.loc[(C, "formed", 2025)], cap.loc[(C, "formed", 2026)]
    ax.append(exhibit(fo["sets"], "Three press sets on five measures, 2025 against 2026", "Each row is one press set on its own months, 2025 in grey and 2026 in blue, on the same five measures."))
    names = {"press_set": "Press set", "months": "Months", "year": "Year"}
    ax.append(show(o["sorting"], {**names, "sorting_events": "Sorting events", "low": "Low", "high": "High", "quantity_sorted": "Quantity sorted", "quantity_per_event_median": "Per event, median", "cost_booked": "Cost booked, $", "cost_booked_or_estimated": "Booked or estimated, $", "p_2026_against_this_year": "p, 2026 against this year"},
                   {"low": lambda v: f"{v:.1f}", "high": lambda v: f"{v:.1f}", "quantity_sorted": F0, "quantity_per_event_median": F0, "cost_booked": F0, "cost_booked_or_estimated": F0, "p_2026_against_this_year": p_value}))
    ax.append(show(o["ppm"], {**names, "complaints": "Complaints", "duplicate_entries_left_out": "Duplicate entries left out", "pieces_rejected": "Pieces rejected", "pieces_shipped": "Pieces shipped", "ppm": "PPM", "low": "Low", "high": "High", "p_2026_against_this_year": "p, 2026 against this year"},
                   {"pieces_rejected": F0, "pieces_shipped": F0, "ppm": F0, "low": F0, "high": F0, "p_2026_against_this_year": p_value}))
    ax.append(show(o["scrap_and_rework"], {**names, "scrap_booked": "Scrap booked, $", "rework_labor_booked": "Rework labor booked, $", "revenue": "Revenue, $", "scrap_and_rework_share_of_revenue": "Share of revenue"},
                   {"scrap_booked": F0, "rework_labor_booked": F0, "revenue": F0, "scrap_and_rework_share_of_revenue": lambda v: f"{v * 100:.2f}%"}))
    ax.append(show(o["scrap_and_rework"], {**names, "pieces_scrapped": "Pieces scrapped", "pieces_produced": "Pieces produced", "pieces_scrapped_share": "Share of pieces", "p_2026_against_this_year": "Score test p, 2026 against this year", "difference_low": "Difference to 2026, points, low", "difference_high": "High"},
                   {"pieces_scrapped": F0, "pieces_produced": F0, "pieces_scrapped_share": lambda v: f"{v * 100:.2f}%", "p_2026_against_this_year": p_value, "difference_low": lambda v: f"{v * 100:.2f}", "difference_high": lambda v: f"{v * 100:.2f}"}))
    ax.append(show(o["capability"], {"press_set": "Press set", "characteristics_class": "Class", "year": "Year", "characteristics": "Characteristics", "subgroups": "Subgroups", "ppk_median": "Ppk, median", "ppk_low": "Low", "ppk_high": "High", "cpk_median": "Cpk, median", "cpk_low": "Cpk low", "cpk_high": "Cpk high", "characteristics_with_ppk_under_1_33": "Ppk under 1.33"},
                   {"subgroups": F0, "ppk_median": F2, "ppk_low": F2, "ppk_high": F2, "cpk_median": F2, "cpk_low": F2, "cpk_high": F2}))
    ax.append("<div class='caption'>Characteristics with 60 subgroups or more in both April to June 2025 and April to June 2026; the 2024 row is on those of them with 60 subgroups in April to June 2024. This is the comparison the body quotes.</div>")
    ax.append(show(o["capability_own_sets"], {"press_set": "Press set", "characteristics_class": "Class", "year": "Year", "characteristics": "Characteristics", "subgroups": "Subgroups", "ppk_median": "Ppk, median", "ppk_low": "Low", "ppk_high": "High", "cpk_median": "Cpk, median", "cpk_low": "Cpk low", "cpk_high": "Cpk high", "characteristics_with_ppk_under_1_33": "Ppk under 1.33"},
                   {"subgroups": F0, "ppk_median": F2, "ppk_low": F2, "ppk_high": F2, "cpk_median": F2, "cpk_low": F2, "cpk_high": F2}))
    ax.append("<div class='caption'>The same on each period's own characteristics with 60 subgroups or more.</div>")
    ax.append(show(o["burr"], {"press_set": "Press set", "period_year": "Year", "burr_nonconformances_at_the_press_check": "Burr nonconformances at the press check", "burr_nonconformances_at_the_dock_audit": "At the dock audit", "burr_nonconformances_at_the_customer": "At the customer", "intervals_with_burr_gauge_subgroups": "Sharpening intervals with burr gauge subgroups",
                               "intervals_with_burr_over_the_limit": "With burr over the limit", "share_over_the_limit": "Share", "low": "Low", "high": "High"}, {"share_over_the_limit": P0, "low": P0, "high": P0}))
    ax.append(show(o["signals"], {"press_set": "Press set", "presses": "Presses", "period_year": "Year", "variable_subgroups": "Subgroups", "alarm_signals_per_100_subgroups": "Alarm signals per 100", "rule_1_per_100_subgroups": "Rule 1 per 100", "acknowledgement_or_adjustment_share": "With an acknowledgement or adjustment", "adjustment_share": "With an adjustment recorded"},
                   {"variable_subgroups": F0, "alarm_signals_per_100_subgroups": lambda v: f"{v:.1f}", "rule_1_per_100_subgroups": lambda v: f"{v:.1f}", "acknowledgement_or_adjustment_share": P0, "adjustment_share": P0}))
    ax.append(show(rm, {"month_start": "Month, 2026", "subgroups": "Subgroups on formed characteristics, pilot presses", "rule_1_alarms": "Rule 1 alarms", "rule_1_per_100_subgroups": "Per 100 subgroups"}, {"month_start": lambda v: str(v)[:7], "subgroups": F0, "rule_1_alarms": F0, "rule_1_per_100_subgroups": lambda v: f"{v:.1f}"}))
    ax.append(show(hd, {"months": "Hole diameters, pilot presses", "year": "Year", "characteristics": "Characteristics", "subgroups": "Subgroups", "alarm_signals": "Alarm signals", "alarm_signals_per_100_subgroups": "Alarm signals per 100", "ppk_median": "Ppk, median", "ppk_low": "Low", "ppk_high": "High"},
                   {"subgroups": F0, "alarm_signals_per_100_subgroups": lambda v: f"{v:.1f}", "ppk_median": F2, "ppk_low": F2, "ppk_high": F2}))
    hw = hd_by.pivot_table(index=["characteristic_id", "die_id", "press_id"], columns="year", values=["subgroups", "alarm_signals", "ppk"]); hw.columns = [f"{a}_{b}" for a, b in hw.columns]; hw = hw.reset_index()
    for col in ("subgroups_2025", "alarm_signals_2025", "subgroups_2026", "alarm_signals_2026"):
        hw[col] = hw[col].astype(int)
    ax.append(show(hw, {"characteristic_id": "Hole diameter", "die_id": "Die", "press_id": "Press", "subgroups_2025": "Subgroups, 2025", "alarm_signals_2025": "Alarm signals, 2025", "ppk_2025": "Ppk, 2025", "subgroups_2026": "Subgroups, 2026", "alarm_signals_2026": "Alarm signals, 2026", "ppk_2026": "Ppk, 2026"},
                   {"ppk_2025": F2, "ppk_2026": F2}))
    cl = o["cost_lines"].copy(); cl.columns = [str(c) for c in cl.columns]
    ax.append(show(cl, {"press_set": "Press set", "category": "Quality cost line as booked", "2024": "2024, $", "2025": "2025, $", "2026": "2026, $"}, {"2024": F0, "2025": F0, "2026": F0}))
    cp = o["cost_lines_plant_level"].copy(); cp.columns = [str(c) for c in cp.columns]
    ax.append(show(cp, {"months": "Months", "category": "Booked at plant level", "2024": "2024, $", "2025": "2025, $", "2026": "2026, $"}, {"2024": F0, "2025": F0, "2026": F0}))
    ax.append(exhibit(fr["years_to_2026"], "Sorting events and cost by year and basis of the sorting, 2024 to 2026", "The left panel counts sorting events on all presses by year and by the basis of the sorting; the right panel gives their cost as booked, with the estimate for sorting booked to the run. Totals are above the columns."))
    ax.append(exhibit(fr["exposure_to_2026"], "Quantity sorted against parts made since the check before, 2024 to 2026", "Each point is one sorting event found at the press in 2024 to 2026: the parts made since the check before the finding, estimated at the press's realised rate, against the quantity the shop sorted, both on log scales. "
                                              "Points on the line are sorting events covering everything made since the check; points below it are bounded by a fault in the die-protection log."))
    ax.append(exhibit(fr["rejected_to_2026"], "Rejected share of the quantity sorted, by basis of the sorting, 2024 to 2026", "Shares are on pieces pooled over events."))
    ax.append(exhibit(fo["complaints"], "Complaints received by month on the pilot presses' parts", "Each bar is the complaints received in a month on the pilot presses' parts, 2024 to 2026, with the dates of the redesign and of per-stroke monitoring marked."))
    ax.append("<div class='caption'>The score test on pieces rejects on the comparison presses as well as on the pilot presses: pieces scrapped on one run are not independent, so the test does not carry the finding and the body gives the size of the change. "
              "A complaint entered a second time for the same customer, part, run, quantity and defect code is a duplicate entry; the first received is kept. Sorting events are counted on the date the sorting started, complaints on the date received, shipments on the ship date, scrap and rework on the accounting month, and revenue on runs ended in the period at the part's price for the year. "
              "A complaint and a shipment belong to the press of their run. The sorting estimate beside the booked cost is from run hours above standard where sorting was not booked to the sorting labor code. Inspection labor, calibration, and gauge and fixture repair are booked at plant level and are not traced to a press.</div>")

    toc = [("summary", "1. Summary: outcomes on the pilot presses"), ("redesign", "2. The redesign"), ("results", "3. Results by element of the redesign"), ("formed", "3.1 Formed characteristics", 1), ("sharpening", "3.2 Sharpening at the count and tool-wear charts", 1),
           ("monitoring", "3.3 Per-stroke monitoring", 1), ("signals", "4. Signals, adjustment and the record"), ("open", "5. What has not moved"), ("appendix", "Appendix")]
    html = S.report_shell("Report: SPC Redesign and Results", "", "", "\n".join(body + ax), toc)
    out = S.DOCS / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / "spc_redesign_and_results.html").write_text(html, encoding="utf8", newline="\n")
    trace = pd.DataFrame(list(TRACE), columns=["section", "value_as_printed", "read_from", "value_in_the_text"])
    off = trace[(trace["value_in_the_text"] != "") & (trace["value_as_printed"].str.lower() != trace["value_in_the_text"].str.lower())]
    assert off.empty, off.to_string()          # every number in the body text is the value the record gives
    return html, trace, n_body, FIGURE[0]


if __name__ == "__main__":
    html, trace, n_body, n_all = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "redesign_and_results_numbers.csv", index=False, lineterminator="\n")
    print(len(html), len(trace), n_body, n_all)
