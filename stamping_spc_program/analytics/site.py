"""The landing page (docs/index.html) and the README, written from the analysis tables so that every figure in them is
the figure on the pages. Returns the support table: each README figure with the page and the table it is read from.

Usage: python -m analytics.site"""
import re

import pandas as pd

from analytics.adjustment import adjustment
from analytics.capability import capability
from analytics.data import query
from analytics.die_wear import die_wear
from analytics.limits import limits
from analytics.measurement import measurement
from analytics.outcomes import outcomes
from analytics.per_stroke import per_stroke
from analytics.recording import recording
from analytics.risk_window import risk_window
from analytics.style import style as S

R1, R2 = "docs/reports/spc_assessment.html", "docs/reports/spc_redesign_and_results.html"
PAGES_BASE = "https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/"          # where the pages are served; README links to pages use it, links to files stay relative
PAGES = [("SPC Assessment", "reports/spc_assessment.html", "Report", "Every chart in use audited on the record as it stood at 31 December 2024: limits, capability, risk window, measurement, adjustment, die wear and recording, with findings and exhibits, and an appendix of the tables and statistical detail behind them."),
         ("SPC Redesign and Results", "reports/spc_redesign_and_results.html", "Report", "The redesign by characteristic class, per-stroke monitoring on the pilot presses, and the outcomes against 2024 and 2023 with the comparison and rollout presses."),
         ("SPC Terminal Screen, PR-03", "screens/spc_terminal_pr_03.html", "Screen", "The press-side SPC software on PR-03 at 09:45 on 7 October 2025: the characteristics of the part on the run, the chart in force, the last subgroup, the most recent alarm and the shift event log."),
         ("Press Monitor Screen, PR-03", "screens/press_monitor_pr_03.html", "Screen", "The press monitor historian's display for PR-03 at the same moment: the per-stroke total and channel shares on the run, the stop log and the die's shots against its sharpening due count."),
         ("SPC Monthly Summary, December 2025", "monthly_summary/spc_monthly_summary_2025_12.html", "Monthly summary", "The SPC measures of December 2025 on all eleven presses against 2024 and by month: capability, alarms and reaction, checks and recording, limits, die wear and per-stroke monitoring, measurement systems and nonconformances."),
         ("Control Plans and Chart Book", "control_plan/control_plan_and_chart_book.html", "Reference", "What is in force at 31 December 2025 on the parts that run on PR-03, PR-06 and PR-09: three control plans in full, the chart book and an index of the other 27 parts.")]


def landing():
    rows = "".join(f'<tr><td><a href="{href}">{title}</a></td><td>{kind}</td><td>{line}</td></tr>' for title, href, kind, line in PAGES)
    body = ("<p>Statistical process control at a progressive-die metal stamper: the assessment of the charts in use, the redesign and what followed it.</p>"
            f'<table class="data"><thead><tr><th>Deliverable</th><th>Form</th><th>Content</th></tr></thead><tbody>{rows}</tbody></table>')
    meta = "Progressive-die metal stamper, about 110 employees, eleven presses, one plant; IATF 16949 certified. January 2023 to December 2025; SPC software and paper charts, press monitors, ERP, QMS, die maintenance log, calibration system, accounting and gauge study worksheets."
    html = S.shell("SPC Program", "Deliverables", meta, body)
    (S.DOCS / "index.html").write_text(html, encoding="utf8", newline="\n")
    return html


def build():
    lm, cp, rk, ms, ad, dw, rc, ps, oc = limits.compute(), capability.compute(), risk_window.compute(), measurement.compute(), adjustment.compute(), die_wear.compute(), recording.compute(), per_stroke.compute(), outcomes.compute()
    sup = []          # (README figure, value, page, read from)

    def v(value, what, page, src):
        sup.append((what, value, page, src)); return value

    sc = lm["signal_comparison"].set_index(["limits_as_set_method", "characteristic_class"]); roll = sc.loc["rolling 25 at entry"].loc[["formed", "hole diameter"]]; pa = lm["paper_signals_all_subgroups"].iloc[0]
    cs = cp["capability_summary"].set_index("characteristic_class"); rw = rk["risk_window"]; ss = rk["sorting_summary"].set_index("year")
    grr = ms["gauge_rr"].set_index(["fixture", "study"]); att = ms["attribute_agreement"].set_index("study"); em = ms["entry_methods"].set_index("entry_method"); gs = ms["gauge_status"].iloc[0]
    ap = ad["after_a_point"].set_index(["adjusted_at_the_press", "entry_method"]); ac = ad["autocorrelation"].set_index(["period", "characteristics"]); av = ad["variance"].set_index("comparison_runs").loc["no adjustment recorded and no point beyond two sigma"]
    bs = dw["burr_summary"].iloc[0]; il = dw["intervals_as_logged"].iloc[0]; rp = dw["runs_past_the_interval"].iloc[0]
    oh = rc["on_the_hour"].set_index("entry_method"); pc = rc["planned_checks"].set_index(["press_group", "shift"]); ea = rc["entry_after_the_parts"].set_index("record")
    both = ps["stops_by_chart"].set_index("chart").loc["both charts"]; rate = ps["stops_with_nothing_found"].set_index("press_id").loc["pilot presses"]; brk = ps["punch_break_summary"].iloc[0]; pr = ps["punch_replacements"]
    so = oc["sorting"].set_index(["press_set", "year"]); pp = oc["ppm"].set_index(["press_set", "year"]); scr = oc["scrap_and_rework"].set_index(["press_set", "year"]); cap = oc["capability"].set_index(["press_set", "characteristics_class", "year"])
    sg = oc["signals"].set_index(["press_set", "presses", "period_year"]); P, C, ALL = "pilot presses", "comparison presses", "all presses of the set"
    n = {t: int(query(f'select count(*) as n from raw."{t}"')["n"].iloc[0]) for t in ("spc__subgroups", "erp__production_runs", "erp__coils", "qms__nonconformances", "qms__complaints", "qms__sorting_events", "die_room__die_events", "calibration__gauge_studies",
                                                                                      "press_monitor__fault_events", "spc__characteristics", "erp__shipments", "qms__dock_audits", "qms__ppap_studies", "calibration__calibrations", "accounting__quality_cost_lines", "spc__control_limits", "spc__alarms")}
    strokes = int(query("select sum(production_strokes + setup_strokes) as n from marts.mart_per_stroke_run_tonnage")["n"].iloc[0]); minutes = int(query("select sum(minutes) as n from marts.mart_per_stroke_rollout_strokes")["n"].iloc[0])
    batch = query("select export_batch_id from marts.mart_outcomes limit 1")["export_batch_id"].iloc[0]
    y25 = int(pr[pr["event_year"] == 2025]["punch_replacements"].sum())

    f_limits = (f"On {v(f'{int(roll.characteristics.sum())}', 'formed characteristics and hole diameters on the software presses', R1, 'signal_comparison')} formed characteristics and hole diameters the software's rolling limits flagged "
                f"{v(f'{roll.signals_by_both.sum() / roll.signals_as_computed.sum() * 100:.1f}%', 'share of baseline-limit signals the rolling limits also flag', R1, 'signal_comparison')} of the subgroups that fixed baseline limits flag; on the paper presses the printed limits signalled on "
                f"{v(f'{pa.signal_rate * 100:.1f}%', 'paper presses, subgroups signalled', R1, 'paper_signals_all_subgroups')} of subgroups with an action recorded on {v(f'{pa.action_share * 100:.1f}%', 'paper presses, signals with an action', R1, 'paper_signals_all_subgroups')} of signals.")
    f_cap = (f"On {v(str(int(cs.loc['formed', 'characteristics'])), 'critical formed characteristics', R1, 'capability_summary')} critical formed characteristics the PPAP Ppk is {v(f'{cs.loc['formed', 'filed_ppk']:.2f}', 'PPAP Ppk, formed', R1, 'capability_summary')} and the production Ppk "
             f"{v(f'{cs.loc['formed', 'ppk']:.2f}', 'production Ppk, formed', R1, 'capability_summary')} ({cs.loc['formed', 'ppk_low']:.2f} to {cs.loc['formed', 'ppk_high']:.2f}); {v(f'{cs.loc['formed', 'share_between_coils'] * 100:.0f}%', 'variance between coils, formed', R1, 'capability_summary')} of the overall variance is between coils.")
    f_risk = (f"Between routine checks {v(f'{rw['fewest_parts_between_checks_at_the_realised_rate'].min():,.0f}', 'parts between checks, lowest', R1, 'risk_window')} to {v(f'{rw['most_parts_between_checks_at_the_realised_rate'].max():,.0f}', 'parts between checks, highest', R1, 'risk_window')} parts pass by part; "
              f"{v(str(int(ss.loc[2024, 'traced_to_a_die_event_between_two_checks'])), 'sorting events of 2024 traced', R1, 'sorting_summary')} of the {v(str(int(ss.loc[2024, 'sorting_events'])), 'sorting events of 2024', R1, 'sorting_summary')} sorting events of 2024 trace to a die event between two checks.")
    f_meas = (f"Two reworked check fixtures consumed {v(f'{grr.loc[('F-20417', 'redesign'), 'pct_tolerance']:.1f}%', '%GRR, F-20417 assessment study', R1, 'gauge_rr')} and {v(f'{grr.loc[('F-31102', 'redesign'), 'pct_tolerance']:.1f}%', '%GRR, F-31102 assessment study', R1, 'gauge_rr')} of tolerance against "
              f"{v(f'{grr.loc[('F-20417', 'PPAP'), 'pct_tolerance']:.1f}%', '%GRR, F-20417 PPAP', R1, 'gauge_rr')} and {v(f'{grr.loc[('F-31102', 'PPAP'), 'pct_tolerance']:.1f}%', '%GRR, F-31102 PPAP', R1, 'gauge_rr')} at PPAP; the burr check agreed with the burr gauge on "
              f"{v(f'{att.loc['at the redesign', 'against_reference'] * 100:.0f}%', 'burr check agreement', R1, 'attribute_agreement')} of calls (kappa {v(f'{att.loc['at the redesign', 'fleiss_kappa']:.2f}', 'burr check kappa', R1, 'attribute_agreement')}); keyed readings end in 0 or 5 at "
              f"{v(f'{em.loc['keyed', 'times_the_uniform_expectation']:.2f}', 'keyed readings ending 0 or 5, times uniform', R1, 'entry_methods')} times the uniform rate.")
    f_adj = (f"{v(f'{ap.loc[(True, 'keyed'), 'recorded_share'] * 100:.1f}%', 'points beyond two sigma with a recorded adjustment', R1, 'after_a_point')} of points beyond two sigma carry a recorded adjustment; subgroup means on the characteristics adjusted at the press carry a within-coil autocorrelation of "
             f"{v(f'{ac.loc[('2024, before the redesign', 'adjusted at the press'), 'lag_1_autocorrelation']:.2f}', 'autocorrelation, adjusted', R1, 'autocorrelation')} against {v(f'{ac.loc[('2024, before the redesign', 'not adjusted at the press'), 'lag_1_autocorrelation']:.2f}', 'autocorrelation, not adjusted', R1, 'autocorrelation')} on the others and "
             f"{v(f'{av.added_variance_median * 100:.1f}%', 'added variance', R1, 'variance')} more variance.")
    f_wear = (f"On {v(str(int(bs.interval_longer_than_the_80pct_count)), 'dies with the stated interval past the count at 80%', R1, 'burr_summary')} of {v(str(int(bs.dies_fitted)), 'dies fitted', R1, 'burr_summary')} dies the stated sharpening interval is longer than the shot count at which burr reaches 80% of its limit; sharpenings are logged a median "
              f"{v(f'{il.logged_over_stated_median:.2f}', 'logged over stated interval, median', R1, 'intervals_as_logged')} times the stated interval; {v(str(int(rp.burr_nonconformances_past_the_interval)), 'burr nonconformances past the interval', R1, 'runs_past_the_interval')} of the "
              f"{v(str(int(rp.burr_nonconformances_with_shots_known)), 'burr nonconformances with shots known', R1, 'runs_past_the_interval')} burr nonconformances of 2024 fell on runs that carried the die past it.")
    f_rec = (f"{v(f'{oh.loc['all routine subgroups', 'stamped_share'] * 100:.1f}%', 'routine checks within five minutes of the hour', R1, 'on_the_hour')} of routine checks are stamped within five minutes of the hour; the night shift records "
             f"{v(f'{pc.loc[('all presses', 'nights'), 'recorded_share'] * 100:.0f}%', 'planned checks recorded, nights', R1, 'planned_checks')} of planned checks against {v(f'{pc.loc[('all presses', 'days'), 'recorded_share'] * 100:.0f}%', 'planned checks recorded, days', R1, 'planned_checks')} on days; "
             f"{v(f'{ea.loc['software presses, 2024, keyed', 'share'] * 100:.1f}%', 'keyed entries more than 20 minutes after the parts', R1, 'entry_after_the_parts')} of keyed subgroups were entered more than 20 minutes after the parts.")
    f_ps = (f"The per-stroke charts stopped the pilot presses {v(str(int(both.stops)), 'per-stroke stops', R2, 'stops_by_chart')} times; the toolmaker found a worn or chipped punch on {v(str(int(both['punch worn and replaced'] + both['punch chipped and replaced'])), 'stops with a worn or chipped punch', R2, 'stops_by_chart')}, slug pulling on "
            f"{v(str(int(both['slug pulling cleared'])), 'stops with slug pulling', R2, 'stops_by_chart')} and nothing on {v(str(int(both['nothing found'])), 'stops with nothing found', R2, 'stops_by_chart')} ({v(f'{rate.nothing_found_per_million_strokes:.2f}', 'nothing found per 1,000,000 strokes', R2, 'stops_with_nothing_found')} per 1,000,000 strokes); "
            f"all {v(str(y25), 'punch replacements in the monitoring months', R2, 'punch_replacements')} punch replacements followed a stop and every one of the {v(str(int(brk.punch_breaks_stopped_by_the_charts)), 'punch breaks', R2, 'punch_break_summary')} punch breaks was stopped on the stroke of the break.")
    f_out = (f"On the pilot presses customer PPM fell from {v(f'{pp.loc[(P, 2024), 'ppm']:.0f}', 'pilot PPM 2024', R2, 'ppm')} to {v(f'{pp.loc[(P, 2025), 'ppm']:.0f}', 'pilot PPM 2025', R2, 'ppm')} (p = {v(f'{pp.loc[(P, 2024), 'p_2025_against_this_year']:.4f}', 'p against 2024', R2, 'ppm')}; against 2023's "
             f"{v(f'{pp.loc[(P, 2023), 'ppm']:.0f}', 'pilot PPM 2023', R2, 'ppm')}, p = {v(f'{pp.loc[(P, 2023), 'p_2025_against_this_year']:.2f}', 'p against 2023', R2, 'ppm')}), scrap and rework from {v(f'{scr.loc[(P, 2024), 'scrap_and_rework_share_of_revenue'] * 100:.2f}%', 'pilot scrap and rework 2024', R2, 'scrap_and_rework')} to "
             f"{v(f'{scr.loc[(P, 2025), 'scrap_and_rework_share_of_revenue'] * 100:.2f}%', 'pilot scrap and rework 2025', R2, 'scrap_and_rework')} of revenue, production Ppk on critical formed characteristics from {v(f'{cap.loc[(P, 'formed', 2024), 'ppk_median']:.2f}', 'pilot Ppk 2024', R2, 'capability')} to "
             f"{v(f'{cap.loc[(P, 'formed', 2025), 'ppk_median']:.2f}', 'pilot Ppk 2025', R2, 'capability')}, and alarm signals from {v(f'{sg.loc[(P, ALL, 2024), 'alarm_signals_per_100_subgroups']:.1f}', 'pilot alarm signals 2024', R2, 'signals')} to {v(f'{sg.loc[(P, ALL, 2025), 'alarm_signals_per_100_subgroups']:.1f}', 'pilot alarm signals 2025', R2, 'signals')} "
             f"per 100 subgroups; sorting events fell from {v(str(int(so.loc[(P, 2024), 'sorting_events'])), 'pilot sorting events 2024', R2, 'sorting')} to {v(str(int(so.loc[(P, 2025), 'sorting_events'])), 'pilot sorting events 2025', R2, 'sorting')} (p = {v(f'{so.loc[(P, 2024), 'p_2025_against_this_year']:.2f}', 'p, sorting', R2, 'sorting')}); the comparison presses moved within their 2024 intervals.")

    a1, a2 = "[SPC Assessment](docs/reports/spc_assessment.html)", "[SPC Redesign and Results](docs/reports/spc_redesign_and_results.html)"
    table = [("Charts and limits", "Do the limits in use signal when the process changes?", f_limits, a1, "11, initial process studies"),
             ("Subgrouping and capability", "Does the Ppk filed at PPAP describe production?", f_cap, a1, "9 and 11, dimensional results and initial process studies"),
             ("Risk window and sorting", "How many parts pass between checks, and what does a sorting event cover?", f_risk, a1, "IATF 16949 9.1.1.1"),
             ("Measurement systems", "How much of the tolerance do the check fixtures and the burr check consume?", f_meas, a1, "8, measurement system analysis studies"),
             ("Adjustment", "What follows a point near the limits?", f_adj, a1, "IATF 16949 9.1.1.1"),
             ("Die wear", "Is the sharpening interval set by the die's burr?", f_wear, a1, "IATF 16949 9.1.1.1"),
             ("Recording", "Are the planned checks recorded, and when?", f_rec, a1, "IATF 16949 9.1.1.1"),
             ("Per-stroke monitoring", "What does charting every stroke find that the hourly check cannot?", f_ps, a2, "IATF 16949 9.1.1.1"),
             ("Outcomes", "What moved on the pilot presses, against 2024, 2023 and the comparison presses?", f_out, a2, "11, initial process studies")]
    md = []
    md.append("# mfg-spc-program\n")
    md.append("Statistical process control at a progressive-die metal stamper, January 2023 to December 2025: an assessment of every chart in use on the shop's own record, a redesign of the charts, limits, sampling and reaction plan on three pilot presses with per-stroke tonnage monitoring, and the results against the same months of 2024 and 2023 with the other presses as the comparison. "
              "Nine analyses feed two reports, an SPC terminal screen and a press monitor screen for PR-03, an SPC monthly summary, and control plans and a chart book, all computed from the shop's exported records by one pipeline.\n")
    md.append("[![SPC terminal screen, PR-03](docs/readme/spc_terminal_screen.png)](docs/screens/spc_terminal_pr_03.html)\n")
    md.append("## What is included\n")
    md.append("- Two reports: the [SPC Assessment](docs/reports/spc_assessment.html) and the [SPC Redesign and Results](docs/reports/spc_redesign_and_results.html), each with findings and exhibits, and an appendix of the tables and statistical detail behind them.\n"
              "- The [SPC terminal screen](docs/screens/spc_terminal_pr_03.html) and the [press monitor screen](docs/screens/press_monitor_pr_03.html) for PR-03.\n"
              "- The [SPC monthly summary](docs/monthly_summary/spc_monthly_summary_2025_12.html) for December 2025.\n"
              "- The [control plans and chart book](docs/control_plan/control_plan_and_chart_book.html). Index of deliverables: [docs/index.html](docs/index.html).\n"
              "- The pipeline from the exported files to the marts: dlt, DuckDB and dbt with schema tests, and one build command that writes every table, figure and page.\n")
    md.append("## Business Context\n")
    md.append("The shop is a progressive-die metal stamper: about 110 employees, IATF 16949 certified, one plant, eleven presses, about 180 part numbers on about 170 dies for automotive, appliance, HVAC, industrial, electrical and consumer customers. It charted six to twelve characteristics a part at the press, in SPC software on the seven medium presses and on paper on the four high-speed presses, filed a Ppk from 300 consecutive pieces at PPAP, sharpened dies on a stated shot interval, and adjusted the die at the operator's discretion. "
              f"The assessment of that record as it stood at 31 December 2024 found that the software's rolling limits flagged {roll.signals_by_both.sum() / roll.signals_as_computed.sum() * 100:.1f}% of what fixed limits flag, that the printed limits on the paper presses signalled on {pa.signal_rate * 100:.1f}% of subgroups, "
              f"that production Ppk on critical formed characteristics was {cs.loc['formed', 'ppk']:.2f} against {cs.loc['formed', 'filed_ppk']:.2f} filed, with {cs.loc['formed', 'share_between_coils'] * 100:.0f}% of the variance between coils, that two reworked check fixtures consumed {grr.loc[('F-20417', 'redesign'), 'pct_tolerance']:.1f}% and {grr.loc[('F-31102', 'redesign'), 'pct_tolerance']:.1f}% of tolerance, "
              f"and that {int(rp.burr_nonconformances_past_the_interval)} of the {int(rp.burr_nonconformances_with_shots_known)} burr nonconformances of 2024 fell on runs that carried the die past its stated sharpening interval.\n")
    md.append("From 3 February 2025 the shop changed its practice on three pilot presses, PR-03, PR-06 and PR-09. It rebuilt and studied the two fixtures again, replaced the burr limit samples and qualified the operators, connected the gauges to the terminals, moved the paper press to the software, fixed limits from a stable baseline after each sharpening, "
              "charted formed characteristics on a three-way chart that carries coil-to-coil variation and hole diameters on a tool-wear chart, recorded a coil-change subgroup with a centring step, set check frequency from the parts between checks, put a written reaction plan on every chart and set the sharpening count from each die's burr. "
              "From 5 May 2025 the press monitor's historian kept every stroke on those presses and the per-stroke total and channel shares were charted, with the press stopping on a signal. From 2 September 2025 the same changes reached the other eight presses.\n")
    md.append(f"From March to December 2025 on the pilot presses, against the same months of 2024, customer PPM was {pp.loc[(P, 2025), 'ppm']:.0f} against {pp.loc[(P, 2024), 'ppm']:.0f} (and {pp.loc[(P, 2023), 'ppm']:.0f} in 2023, p = {pp.loc[(P, 2023), 'p_2025_against_this_year']:.2f}), scrap and rework {scr.loc[(P, 2025), 'scrap_and_rework_share_of_revenue'] * 100:.2f}% of revenue against {scr.loc[(P, 2024), 'scrap_and_rework_share_of_revenue'] * 100:.2f}%, "
              f"production Ppk on critical formed characteristics {cap.loc[(P, 'formed', 2025), 'ppk_median']:.2f} against {cap.loc[(P, 'formed', 2024), 'ppk_median']:.2f}, and alarm signals {sg.loc[(P, ALL, 2025), 'alarm_signals_per_100_subgroups']:.1f} per 100 subgroups against {sg.loc[(P, ALL, 2024), 'alarm_signals_per_100_subgroups']:.1f}. "
              f"The per-stroke charts stopped the press {int(both.stops)} times, all {y25} punch replacements followed a stop, and sorting events were {int(so.loc[(P, 2025), 'sorting_events'])} against {int(so.loc[(P, 2024), 'sorting_events'])} (p = {so.loc[(P, 2024), 'p_2025_against_this_year']:.2f}). "
              f"On the comparison presses, where nothing changed from February to August, PPM was {pp.loc[(C, 2025), 'ppm']:.0f} against {pp.loc[(C, 2024), 'ppm']:.0f} and every measure moved within its 2024 interval.\n")
    md.append("## Analyses\n")
    md.append("| Analysis | Question | Finding | Report | PPAP element |\n|---|---|---|---|---|\n" + "\n".join(f"| {a} | {q} | {f} | {r} | {e} |" for a, q, f, r, e in table) + "\n")
    md.append("## Methods\n")
    md.append("Statistics: control charts and capability indices by AIAG SPC, 2nd edition, with within-subgroup sigma pooled across subgroups and overall sigma from all readings; stability by Western Electric rules 1 to 4; average run length by the Markov chain method; variance components by a nested random-effects model fitted by REML; gauge R&R by the AIAG MSA, 4th edition, ANOVA method with %tolerance at 6 sigma and ndc; attribute agreement with Fleiss' kappa; "
              "Anderson-Darling with the Box-Cox transformation on bounded characteristics; lag-1 autocorrelation of subgroup means within a run and coil; an EWMA for autocorrelated data on the per-stroke total and a residual chart on each channel's share; the exact Poisson rate test on event and complaint counts, a bootstrap interval over complaints on PPM, and the two-proportion score test with the Newcombe interval. Every result carries its interval, its sample size and its coverage.\n")
    nodes = query("select count(*) as n from information_schema.tables where table_schema in ('staging', 'intermediate', 'marts')")["n"].iloc[0]
    md.append(f"Data engineering: the exported files are loaded to DuckDB with dlt, the per-stroke and per-minute press monitor exports are read in place as Parquet, and a dbt project builds {v(str(int(nodes)), 'dbt models', 'pipeline/dbt', 'information_schema.tables')} staging, intermediate and mart models with schema tests on every layer. "
              "Every table, figure and page is written by scripts that read the marts; no number is typed into a page, and two consecutive builds are byte-identical. Each report, the two screens, the monthly summary and the control plans has a table of every number it prints with the mart it is read from, under `analytics/reports/traces/`.\n")
    md.append("## Data\n")
    md.append(f"Thirty-six months of the shop's records, January 2023 to December 2025, export batch {batch}: {v(f'{n['spc__subgroups']:,}', 'subgroups', 'data/raw/spc', 'raw.spc__subgroups')} subgroups on {v(f'{n['spc__characteristics']:,}', 'characteristics', 'data/raw/spc', 'raw.spc__characteristics')} characteristics, "
              f"{v(f'{n['erp__production_runs']:,}', 'production runs', 'data/raw/erp', 'raw.erp__production_runs')} production runs, {v(f'{n['erp__coils']:,}', 'coils', 'data/raw/erp', 'raw.erp__coils')} coils and {v(f'{strokes:,}', 'strokes kept by the historian', 'data/raw/press_monitor', 'mart_per_stroke_run_tonnage')} press strokes on the pilot presses from 5 May 2025.\n")
    md.append(f"Conditions of the record, each stated in the reports where it bears on a figure: keyed readings that prefer 0 and 5 ({em.loc['keyed', 'times_the_uniform_expectation']:.2f} times the uniform rate) and readings that cannot be a measurement of the part ({em.loc['keyed', 'set_aside_share'] * 100:.2f}% of keyed readings, set aside with the count stated), "
              f"subgroups on a gauge out of service that day ({gs.share_out_of_service * 100:.1f}%) or past its calibration due date ({gs.share_past_due * 100:.1f}%), entries made after the parts ({ea.loc['software presses, 2024, keyed', 'share'] * 100:.1f}% of keyed subgroups more than 20 minutes after), "
              "coil ids missing from subgroups and recovered from the run's coil sequence, complaints entered twice, sorting booked to the production run instead of the sorting labor code, shot counts rounded to the thousand in the die log, and paper charts transcribed for the assessment.\n")
    src = [("SPC software", "characteristics, control limits, subgroups, alarms, reaction plan steps", n["spc__characteristics"] + n["spc__control_limits"] + n["spc__subgroups"] + n["spc__alarms"]), ("Press monitors", "per-stroke peaks (pilot presses), per-minute summaries, tonnage windows, fault events", strokes + minutes + n["press_monitor__fault_events"]),
           ("ERP", "parts, dies, presses, production runs, coils, scrap, shipments", n["erp__production_runs"] + n["erp__coils"] + n["erp__shipments"]), ("QMS", "nonconformances, sorting events, complaints, dock audits, PPAP studies, scorecards", n["qms__nonconformances"] + n["qms__sorting_events"] + n["qms__complaints"] + n["qms__dock_audits"] + n["qms__ppap_studies"]),
           ("Die maintenance log", "sharpenings, punch replacements, rebuilds, repairs", n["die_room__die_events"]), ("Calibration system", "gauges, calibrations, gauge studies", n["calibration__calibrations"] + n["calibration__gauge_studies"]), ("Accounting", "quality cost lines, contribution by part", n["accounting__quality_cost_lines"]),
           ("Study worksheets", "seven gauge R&R studies and two attribute agreement studies, as recorded", 9)]
    md.append("| Source | Tables | Records |\n|---|---|---|\n" + "\n".join(f"| {a} | {b} | {c:,} |" for a, b, c in src) + "\n")
    md.append("Pipeline: `pipeline/load` loads each exported file to the `raw` schema; `pipeline/dbt` builds one staging model per source table, the intermediate models (the characteristic history with run, press, coil, die shot count, limits in force and gauge status joined; coil assignment; sharpening intervals; the trace of each sorting event to its die event and the check before) and the marts each analysis, the two screens, the monthly summary and the control plans read. Every mart carries the export batch id.\n")
    md.append("## How to run\n")
    md.append("Python 3.12 or later. Run from `stamping_spc_program/`.\n\n```bash\npython -m venv .venv\n```\n\nActivate it: `.venv\\Scripts\\activate` on Windows, `source .venv/bin/activate` on Linux and macOS. Then:\n\n```bash\npip install -e .\n```\n\n```bash\npython -m pipeline.load.load_exports\n```\n\n"
              "```bash\ncd pipeline/dbt && dbt build --profiles-dir . && cd ../..\n```\n\n```bash\npython -m analytics.build_all\n```\n\n"
              "The last command writes every figure under `docs/figures`, the two reports, the two screens, the monthly summary, the control plans and chart book, `docs/index.html`, this README and the number traces.\n")
    md.append("## Author\n")
    md.append("Brian Davis. Data engineering and applied analytics/ML for manufacturers. Other work: [github.com/brimsystems](https://github.com/brimsystems?tab=repositories).\n")
    text = "\n".join(md)
    text = re.sub(r"\]\((docs/[^)]+\.html)\)", lambda m: f"]({PAGES_BASE}{m.group(1)})", text)
    (S.ROOT / "README.md").write_text(text, encoding="utf8", newline="\n")
    html = landing()
    return text, html, pd.DataFrame(sup, columns=["readme_figure", "value", "page", "read_from"])


if __name__ == "__main__":
    text, html, sup = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    sup.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "readme_numbers.csv", index=False, lineterminator="\n")
    print(len(text), len(html), len(sup))
