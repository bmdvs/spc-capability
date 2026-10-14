"""The landing page (docs/index.html) and the README, written from the analysis tables so that every figure in them is
the figure on the pages. Returns the support table: each README figure with the page and the table it is read from.

Usage: python -m analytics.site"""
import json
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
PAGES = [("SPC Assessment", "reports/spc_assessment.html", "Report", "Every chart in use on all eleven presses, assessed on the 2025 record by characteristic class. It covers chart selection and limits, capability, measurement systems, sampling and recording, and reaction, and the three sources of variation behind the gaps. An appendix holds the tables and statistical detail."),
         ("SPC Redesign and Results", "reports/spc_redesign_and_results.html", "Report", "The redesign by characteristic class on PR-03, PR-06 and PR-09 from February 2026, with per-stroke monitoring from April 2026. The results cover April to June 2026 against the same months of 2025, with the other eight presses as the comparison."),
         ("SPC Terminal Screen, PR-03", "screens/spc_terminal_pr_03.html", "Screen", "The press-side SPC software on PR-03 at 12:04 on 13 May 2026: the characteristics of the part on the run, the chart in force, the last subgroup, the most recent alarm and the shift event log."),
         ("Press Monitor Screen, PR-03", "screens/press_monitor_pr_03.html", "Screen", "The press monitor historian's display for PR-03 at the same moment: the per-stroke total and channel shares on the run, the stop log, and the die's shots against its sharpening due count."),
         ("SPC Monthly Summary, June 2026", "monthly_summary/spc_monthly_summary_2026_06.html", "Monthly summary", "The SPC measures of June 2026 on all eleven presses, by press and press group, against May, January to June and 2025. It covers capability, alarms and reaction, recording, chart limits, dies and per-stroke stops, gauges, and sorting and burr nonconformances."),
         ("Control Plans and Chart Book", "control_plan/control_plan_and_chart_book.html", "Reference", "What is in force at 30 June 2026 on the parts that run on PR-03, PR-06 and PR-09: three control plans in full, the chart book, and an index of the other {other_parts} parts.")]

README = """# Metal stamping: SPC program

Statistical process control at a progressive-die metal stamper with eleven presses, on the shop's records from January 2024 to June 2026. The work has three parts:
- an assessment of every chart in use on all eleven presses in 2025;
- a redesign of the charts, limits, sampling and reaction plan on three pilot presses from February 2026, with per-stroke tonnage monitoring from April 2026;
- the results for April to June 2026 against the same months of 2025, with the other eight presses as the comparison.

The analyses feed two reports, two PR-03 screens (the SPC terminal and the press monitor), an SPC monthly summary, and control plans with a chart book. One pipeline computes all of them from the shop's exported records.

[![SPC terminal screen, PR-03](docs/readme/spc_terminal_screen.png)](docs/screens/spc_terminal_pr_03.html)

## What is included

- **Reports:** the [SPC Assessment](docs/reports/spc_assessment.html) and the [SPC Redesign and Results](docs/reports/spc_redesign_and_results.html). Each has findings and exhibits, and an appendix of the tables and statistical detail behind them.
- **Screens, PR-03 at 12:04 on 13 May 2026:** the [SPC terminal screen](docs/screens/spc_terminal_pr_03.html) and the [press monitor screen](docs/screens/press_monitor_pr_03.html).
- **Monthly summary:** the [SPC monthly summary](docs/monthly_summary/spc_monthly_summary_2026_06.html) for June 2026.
- **Control plans:** the [control plans and chart book](docs/control_plan/control_plan_and_chart_book.html), in force at 30 June 2026.
- **Index:** all deliverables are listed at [docs/index.html](docs/index.html).
- **Pipeline:** from the exported files to the marts, built with dlt, DuckDB and dbt, with schema tests. One build command writes every table, figure and page.

## Business Context

The shop is a progressive-die metal stamper:
- about 110 employees, IATF 16949 certified;
- one plant with eleven presses;
- about {parts} part numbers on about {dies} dies, for automotive, appliance, HVAC, industrial, electrical and consumer customers.

Its practice as found:
- it charted six to twelve characteristics a part at the press, in SPC software on the seven medium presses and on paper on the four high-speed presses;
- it filed a Ppk from 300 consecutive pieces at PPAP;
- it sharpened dies on a stated shot interval;
- operators adjusted the die at their discretion.

In 2025 scrap and rework cost {scrap_share} of revenue (${scrap_cost}), customer PPM was {ppm}, and {sorts} sorting events covered {sorted} parts.

The shop assessed every chart in use on the 2025 record. The charts held on punched characteristics and flatness, and failed on formed characteristics, hole diameters and burr:
- **Limits:** rolling limits in the software flagged {flagged} of what baseline limits flag. Printed limits on the paper presses signalled on {printed} of every 100 formed-characteristic subgroups, and an action was recorded on {action} of paper signals.
- **Capability:** production Ppk on critical formed characteristics was {ppk_formed}, against {filed_formed} filed at PPAP.
- **Coils:** {coil_share} of the variance on formed characteristics lay between coils.
- **Die wear:** {burr_past} of the {burr_all} burr nonconformances fell on runs past the die's stated sharpening interval.
- **Die events:** {traced} of the {sorts} sorting events traced to a die event between two checks.
- **Gauge studies:** studies covered {fx_before} of the {fixtures} check fixtures.

From 2 February 2026 the shop changed its practice on three pilot presses, PR-03, PR-06 and PR-09:
- **Gauges:** it rebuilt and studied the two reworked fixtures, replaced the burr limit samples, and connected the gauges to the terminals.
- **Charts and limits:** it moved PR-03 from paper to the software. Formed characteristics went onto a three-way chart with a subgroup at each coil change, and hole diameters onto a tool-wear chart. Limits were fixed from a stable baseline after each sharpening.
- **Checks and reaction:** it set check frequency from the parts made between checks and put a written reaction plan on every chart.
- **Sharpening:** it set each die's sharpening count from its burr.

From 1 April 2026 the press monitor's historian kept every stroke on the pilot presses. The per-stroke total and channel shares were charted, and the press stopped on a signal. The same changes reach the other eight presses from 3 August 2026.

From April to June 2026 on the pilot presses, against the same months of 2025:
- **Scrap and rework:** fell from {scrap_before} to {scrap_after} of revenue, about ${saved} in the quarter, while the comparison presses held at {scrap_comparison}.
- **Capability:** production Ppk on critical formed characteristics rose from {ppk_before} to {ppk_after}.
- **Alarms:** alarm signals fell from {alarms_before} to {alarms_after} per 100 subgroups, and an adjustment was recorded on {adj_after} of them, against {adj_before}.
- **Per-stroke stops:** the charts stopped all {breaks} punch breaks on the stroke of the break.

Customer PPM, at {ppm_after} against {ppm_before} on {complaints} complaints in each quarter, and sorting events, {sorts_after} against {sorts_before}, are too few to show an effect in three months.

## Analyses

| Analysis | Question | Finding | Report | PPAP element |
|---|---|---|---|---|
| Charts and limits | Do the limits in use signal when the process changes? | On formed characteristics and hole diameters, the software's rolling limits flag {flagged} of the subgroups that baseline limits flag. On the paper presses, printed limits signal on {printed} of every 100 formed-characteristic subgroups, with an action recorded on {action} of signals. | [SPC Assessment](docs/reports/spc_assessment.html) | 11, initial process studies |
| Capability | Does the Ppk filed at PPAP describe production? | Production Ppk on critical formed characteristics is {ppk_formed} against {filed_formed} filed; punched characteristics hold at {ppk_punched} against {filed_punched}. | [SPC Assessment](docs/reports/spc_assessment.html) | 9 and 11, dimensional results and initial process studies |
| Measurement systems | Are the gauges studied, and do they hold? | Before January 2026, {fx_before} of the {fixtures} check fixtures had a gauge study. The two reworked fixtures consume {grr1} and {grr2} of tolerance, and the burr check agrees with the burr gauge on {agree} of calls (kappa {kappa}). | [SPC Assessment](docs/reports/spc_assessment.html) | 8, measurement system analysis studies |
| Sampling and recording | How many parts pass between checks, and are checks recorded on time? | A median {between_low} to {between_high} parts pass between routine checks, by press. Nights record {nights} of planned checks against {days} on days, and {late} of keyed entries are made more than 20 minutes after the parts. | [SPC Assessment](docs/reports/spc_assessment.html) | IATF 16949 9.1.1.1 |
| Reaction | What follows a signal? | All {alarms} software alarms were acknowledged, {one_word} with a one-word text. Adjusted characteristics carry a lag-1 autocorrelation of {ac_adj} against {ac_not} on the others, and {added} more variance. | [SPC Assessment](docs/reports/spc_assessment.html) | IATF 16949 9.1.1.1 |
| Coil-to-coil variation | Where does the variance on formed characteristics lie? | {coil_share} of it lies between coils, against {coil_punched} on punched characteristics. A coil's level is predictable from its certificate to {coil_fit} of tolerance. | [SPC Assessment](docs/reports/spc_assessment.html) | 11, initial process studies |
| Die wear | Is the sharpening interval set by the die's burr? | {burr_past} of the {burr_all} burr nonconformances of 2025 fell on runs past the stated interval. Sharpenings are logged at a median {logged} times the interval, and on {long} of {fitted} dies the interval is longer than the count at which burr reaches 80% of its limit. | [SPC Assessment](docs/reports/spc_assessment.html) | IATF 16949 9.1.1.1 |
| Die events and sorting | What does a sorting event cover? | {traced} of the {sorts} sorting events of 2025 trace to a die event between two checks. Sorting back to the check before rejects {rej_back} of what it sorts, against {rej_fault} where a fault bounds the event. | [SPC Assessment](docs/reports/spc_assessment.html) | IATF 16949 9.1.1.1 |
| Formed characteristics, redesigned | Does the three-way chart raise capability on formed characteristics? | On {both_n} characteristics, production Ppk rose from {ppk_before} to {ppk_after}, and the gap between Cpk and Ppk fell from {gap_before} to {gap_after}. The die is centred at a coil change on {centred} of {centred_of} coil-change subgroups between one and three sigma off centre. | [SPC Redesign and Results](docs/reports/spc_redesign_and_results.html) | 11, initial process studies |
| Sharpening at the count | Does the count keep burr under its limit? | All {late_n} pilot intervals begun under the count were sharpened at or before it, and none crossed the limit. The tool-wear chart cut alarms on hole diameters from {hd_before} to {hd_after} per 100 subgroups. | [SPC Redesign and Results](docs/reports/spc_redesign_and_results.html) | IATF 16949 9.1.1.1 |
| Per-stroke monitoring | What does charting every stroke find that the check cannot? | The charts stopped the pilot presses {stops} times: on a worn or chipped punch {worn} times, on slug pulling {slug}, and on nothing {nothing} ({nf_rate} per million strokes). All {breaks} punch breaks were stopped on the stroke, and {after_stop} of {replacements} punch replacements followed a stop. | [SPC Redesign and Results](docs/reports/spc_redesign_and_results.html) | IATF 16949 9.1.1.1 |
| Signals and adjustment | Are alarms fewer, and answered? | Alarm signals fell from {alarms_before} to {alarms_after} per 100 subgroups, and the share with an adjustment recorded rose from {adj_before} to {adj_after}. | [SPC Redesign and Results](docs/reports/spc_redesign_and_results.html) | IATF 16949 9.1.1.1 |
| Outcomes | What moved on the pilot presses, against the comparison presses? | Scrap and rework fell from {scrap_before} to {scrap_after} of revenue, and held at {scrap_comparison} on the comparison presses. Customer PPM, at {ppm_after} against {ppm_before}, and sorting are too few to show an effect in three months. | [SPC Redesign and Results](docs/reports/spc_redesign_and_results.html) | 11, initial process studies |

## Methods

**Statistics:**
- **Control charts and capability:** by AIAG SPC, 2nd edition. Within-subgroup sigma is pooled across subgroups, and overall sigma is taken from all readings.
- **Stability:** Western Electric rules 1 to 4, with average run length by the Markov chain method.
- **Variance components:** a nested random-effects model fitted by REML.
- **Gauge R&R:** AIAG MSA, 4th edition, ANOVA method, with %tolerance at 6 sigma and ndc. Attribute agreement uses Fleiss' kappa.
- **Bounded characteristics:** Anderson-Darling, with the Box-Cox transformation.
- **Autocorrelation:** lag-1 autocorrelation of subgroup means within a run and coil.
- **Per-stroke charts:** an EWMA for autocorrelated data on the per-stroke total, and a residual chart on each channel's share.
- **Rates and proportions:** the exact Poisson rate test on event and complaint counts, the two-proportion score test with the Newcombe interval, and bootstrap intervals over complaints on PPM.

Every result carries its interval, its sample size and its coverage.

**Data engineering:**
- The exported files are loaded to DuckDB with dlt, and the per-stroke press monitor export is read in place as Parquet.
- A dbt project builds {models} staging, intermediate and mart models, with {tests} schema tests on every layer.
- Every table, figure and page is written by scripts that read the marts. No number is typed into a page, and two consecutive builds are byte-identical.
- Each deliverable has a table of every number it prints and the mart it is read from, under `analytics/reports/traces/`. This covers both reports, the two screens, the monthly summary and the control plans.

## Data

The record covers thirty months of the shop's records, January 2024 to June 2026, in export batch {batch}. It holds:
- {subgroups} subgroups on {characteristics} characteristics;
- {runs} production runs and {coils} coils;
- {strokes} press strokes on the pilot presses from 1 April 2026.

Conditions of the record, each stated in the reports where it bears on a figure:
- **Keyed readings:** they end in 0 or 5 at {digit} times the expected rate. Readings that cannot be a measurement of the part ({set_aside} of keyed readings) are set aside, with the count stated.
- **Gauge status:** subgroups recorded against a gauge away for calibration that day ({out_of_service} in 2025), or past its calibration due date ({past_due}).
- **Late entries:** {late} of keyed subgroups in 2025 were entered more than 20 minutes after the parts.
- **Coil ids:** missing coil ids are recovered from the run's coil sequence.
- **Complaints:** some are entered twice.
- **Sorting:** sorting is booked to the production run instead of the sorting labor code.
- **Die log:** shot counts are rounded to the thousand on {rounded} of {sharpenings} sharpenings.
- **Paper charts:** they were transcribed for the assessment.

| Source | Tables | Records |
|---|---|---|
{sources}

The pipeline runs in three stages:
- `pipeline/load` loads each exported file to the `raw` schema.
- `pipeline/dbt` builds one staging model per source table, then the intermediate models:
  - the characteristic history, with run, press, coil, die shot count, limits in force and gauge status joined;
  - coil assignment;
  - sharpening intervals;
  - the trace of each sorting event to its die event and the check before.
- It then builds the marts that the analyses, the two screens, the monthly summary and the control plans read. Every mart carries the export batch id.
"""


def landing(other_parts):
    rows = "".join(f'<tr><td><a href="{href}">{title}</a></td><td>{kind}</td><td>{line.format(other_parts=other_parts)}</td></tr>' for title, href, kind, line in PAGES)
    body = ("<p>Statistical process control at a progressive-die metal stamper: the assessment of the charts in use, the redesign and what followed it.</p>"
            f'<table class="data"><thead><tr><th>Deliverable</th><th>Form</th><th>Content</th></tr></thead><tbody>{rows}</tbody></table>')
    meta = "Progressive-die metal stamper, about 110 employees, eleven presses, one plant; IATF 16949 certified. January 2024 to June 2026; SPC software and paper charts, press monitors, ERP, QMS, die maintenance log, calibration system, accounting and gauge study worksheets."
    html = S.shell("SPC Program", "Deliverables", meta, body)
    (S.DOCS / "index.html").write_text(html, encoding="utf8", newline="\n")
    return html


def build():
    lm, cp, rk, ms, ad, dw, rc, ps, oc = limits.compute(), capability.compute(), risk_window.compute(), measurement.compute(), adjustment.compute(), die_wear.compute(), recording.compute(), per_stroke.compute(), outcomes.compute()
    sup = []          # (README figure, value as printed, value in the text, page, read from)
    V = {}

    def v(key, value, was, page, src):
        V[key] = value; sup.append((key, value, was, page, src))

    sc = lm["signal_comparison"].set_index(["limits_as_set_method", "characteristic_class"]); roll = sc.loc["rolling 25 at entry"].loc[["formed", "hole diameter"]]; pa = lm["paper_signals_all_subgroups"].iloc[0]; ack = lm["software_acknowledgements"].iloc[0]
    pf = lm["paper_signals"].set_index("characteristic_class").loc["formed"]; cs = cp["capability_summary"].set_index("characteristic_class"); coil = cp["coil_regression_summary"].iloc[0]; rw = rk["risk_window"]; ss = rk["sorting_summary"].set_index("year").loc[2025]
    sb = rk["sorting_by_basis"].set_index("sort_basis"); grr = ms["gauge_rr"].set_index(["fixture", "study"]); att = ms["attribute_agreement"].set_index("study").loc["at the redesign"]; em = ms["entry_methods"].set_index("entry_method").loc["keyed"]; gs = ms["gauge_status"].iloc[0]
    ac = ad["autocorrelation"].set_index(["period", "characteristics"]); av = ad["variance"].set_index("comparison_runs").loc["no adjustment recorded and no point beyond two sigma"]
    bs = dw["burr_summary"].iloc[0]; il = dw["intervals_as_logged"].iloc[0]; rp = dw["runs_past_the_interval"].iloc[0]; pc = rc["planned_checks"].set_index(["press_group", "shift"]); ea = rc["entry_after_the_parts"].set_index("record").loc["software presses, 2025, keyed"]
    both = ps["stops_by_chart"].set_index("chart").loc["both charts"]; rate = ps["stops_with_nothing_found"].set_index("press_id").loc["pilot presses"]; brk = ps["punch_break_summary"].iloc[0]; pr = ps["punch_replacements"]; pr26 = pr[pr["event_year"] == 2026].set_index("led_by")["punch_replacements"]
    so = oc["sorting"].set_index(["press_set", "year"]); pp = oc["ppm"].set_index(["press_set", "year"]); scr = oc["scrap_and_rework"].set_index(["press_set", "year"]); cap = oc["capability"].set_index(["press_set", "characteristics_class", "year"])
    sg = oc["signals"].set_index(["press_set", "presses", "period_year"]); P, C, ALL = "pilot presses", "comparison presses", "all presses of the set"; iv = oc["pilot_intervals"]; late_iv = iv[~iv["began_before_the_count"]]
    loss = outcomes.plant_losses((2024, 2025)).set_index("year").loc[2025]; hd, _ = outcomes.hole_diameter_under_the_tool_wear_chart(); hd = hd.set_index("year")
    n = {t: int(query(f'select count(*) as n from raw."{t}"')["n"].iloc[0]) for t in ("spc__subgroups", "erp__production_runs", "erp__coils", "qms__nonconformances", "qms__complaints", "qms__sorting_events", "die_room__die_events", "calibration__gauge_studies", "calibration__gauges",
                                                                                      "press_monitor__fault_events", "press_monitor__tonnage_windows", "spc__characteristics", "erp__shipments", "erp__parts", "erp__dies", "qms__dock_audits", "qms__ppap_studies", "qms__scorecards",
                                                                                      "calibration__calibrations", "accounting__quality_cost_lines", "accounting__contribution", "spc__control_limits", "spc__alarms", "spc__reaction_plan_steps", "erp__scrap_transactions", "erp__presses")}
    strokes = int(query("select sum(production_strokes + setup_strokes) as n from marts.mart_per_stroke_run_tonnage")["n"].iloc[0]); batch = query("select export_batch_id from marts.mart_outcomes limit 1")["export_batch_id"].iloc[0]
    models = query("select table_schema, count(*) as n from information_schema.tables where table_schema in ('staging', 'intermediate', 'marts') group by 1").set_index("table_schema")["n"]
    tests = len(json.loads((S.ROOT / "pipeline" / "dbt" / "target" / "manifest.json").read_text(encoding="utf8"))["nodes"]) - int(models.sum()) if (S.ROOT / "pipeline" / "dbt" / "target" / "manifest.json").exists() else None
    tests = sum(1 for k in json.loads((S.ROOT / "pipeline" / "dbt" / "target" / "manifest.json").read_text(encoding="utf8"))["nodes"] if k.startswith("test."))
    span = query("select min(cast(sample_time as date)) as a, max(cast(sample_time as date)) as b from intermediate.int_characteristic_history").iloc[0]
    assert (pd.Timestamp(span.a).strftime("%Y-%m"), pd.Timestamp(span.b).strftime("%Y-%m")) == ("2024-01", "2026-06")
    fx = query("""select count(distinct g.gauge_id) filter (where g."type" = 'check fixture') as fixtures, count(distinct s.gauge_id) filter (where g."type" = 'check fixture' and s."date" < date '2026-01-01') as before
                  from staging.stg_calibration__gauges g left join staging.stg_calibration__gauge_studies s using (gauge_id) where g.status = 'active'""").iloc[0]
    sharp = query("""select count(*) as n, count(*) filter (where shot_count % 1000 = 0) as rounded from staging.stg_die_room__die_events where "type" = 'sharpening' and shot_count is not null""").iloc[0]
    other_parts = int(query("select count(distinct part_id) as n from marts.mart_control_plan")["n"].iloc[0]) - 3
    cq = cap.loc[(P, "formed", 2025)], cap.loc[(P, "formed", 2026)]; s24, s25 = scr.loc[(P, 2025)], scr.loc[(P, 2026)]
    inh, flt = sb.loc["sorted back to the check before, in-house"], sb.loc["sorted from a logged die-protection fault"]
    both_flag = roll["signals_by_both"].sum() / roll["signals_as_computed"].sum(); worn = int(both["punch worn and replaced"] + both["punch chipped and replaced"])
    f0, f1, f2, p0, p1, p2 = (lambda x: f"{x:,.0f}"), (lambda x: f"{x:.1f}"), (lambda x: f"{x:.2f}"), (lambda x: f"{x * 100:.0f}%"), (lambda x: f"{x * 100:.1f}%"), (lambda x: f"{x * 100:.2f}%")
    for key, value, was, page, src in [
        ("parts", f0(round(n["erp__parts"], -1)), "180", "", "raw.erp__parts, to the ten"), ("dies", f0(round(n["erp__dies"], -1)), "", "", "raw.erp__dies, to the ten"),
        ("scrap_share", p2(loss.scrap_and_rework_share_of_revenue), "3.12%", R1, "plant_losses"), ("scrap_cost", f0(loss.scrap_booked + loss.rework_labor_booked), "1,242,201", R1, "plant_losses"), ("ppm", f0(loss.ppm), "463", R1, "plant_losses"),
        ("sorts", f0(ss.sorting_events), "14", R1, "sorting_summary"), ("sorted", f0(ss.quantity_sorted), "101,154", R1, "sorting_summary"), ("traced", f0(ss.traced_to_a_die_event_between_two_checks), "12", R1, "sorting_summary"),
        ("flagged", p1(both_flag), "17.0%", R1, "signal_comparison"), ("printed", f0(pf.printed_per_100), "42", R1, "paper_signals"), ("action", p0(pa.action_share), "28%", R1, "paper_signals_all_subgroups"),
        ("ppk_formed", f2(cs.loc["formed", "ppk"]), "1.04", R1, "capability_summary"), ("filed_formed", f2(cs.loc["formed", "filed_ppk"]), "1.84", R1, "capability_summary"), ("ppk_punched", f2(cs.loc["punched", "ppk"]), "1.55", R1, "capability_summary"),
        ("filed_punched", f2(cs.loc["punched", "filed_ppk"]), "1.85", R1, "capability_summary"), ("coil_share", p0(cs.loc["formed", "share_between_coils"]), "54%", R1, "capability_summary"), ("coil_punched", p0(cs.loc["punched", "share_between_coils"]), "2%", R1, "capability_summary"),
        ("coil_fit", p1(coil.certificate_residual_sd_share_of_tolerance_median), "2.5%", R1, "coil_regression_summary"), ("burr_past", f0(rp.burr_nonconformances_past_the_interval), "60", R1, "runs_past_the_interval"), ("burr_all", f0(rp.burr_nonconformances_with_shots_known), "61", R1, "runs_past_the_interval"),
        ("fx_before", f0(fx.before), "2", R1, "gauge studies on check fixtures before January 2026"), ("fixtures", f0(fx.fixtures), "180", R1, "stg_calibration__gauges"),
        ("grr1", p1(grr.loc[("F-20417", "redesign"), "pct_tolerance"] / 100), "31.2%", R1, "gauge_rr"), ("grr2", p1(grr.loc[("F-31102", "redesign"), "pct_tolerance"] / 100), "33.6%", R1, "gauge_rr"), ("agree", p0(att.against_reference), "80%", R1, "attribute_agreement"), ("kappa", f2(att.fleiss_kappa), "0.44", R1, "attribute_agreement"),
        ("between_low", f0(rw["median_parts_between_checks_at_the_realised_rate"].min()), "1,934", R1, "risk_window"), ("between_high", f0(rw["median_parts_between_checks_at_the_realised_rate"].max()), "16,333", R1, "risk_window"),
        ("nights", p0(pc.loc[("all presses", "nights"), "recorded_share"]), "84%", R1, "planned_checks"), ("days", p0(pc.loc[("all presses", "days"), "recorded_share"]), "94%", R1, "planned_checks"), ("late", p1(ea.share), "15.1%", R1, "entry_after_the_parts"),
        ("alarms", f0(ack.alarms), "10,474", R1, "software_acknowledgements"), ("one_word", f0(ack.text_of_one_word), "4,691", R1, "software_acknowledgements"), ("ac_adj", f2(ac.loc[("2025, before the redesign", "adjusted at the press"), "lag_1_autocorrelation"]), "-0.14", R1, "autocorrelation"),
        ("ac_not", f2(ac.loc[("2025, before the redesign", "not adjusted at the press"), "lag_1_autocorrelation"]), "-0.07", R1, "autocorrelation"), ("added", p1(av.added_variance_median), "9.9%", R1, "variance"),
        ("logged", f2(il.logged_over_stated_median), "1.14", R1, "intervals_as_logged"), ("long", f0(bs.interval_longer_than_the_80pct_count), "41", R1, "burr_summary"), ("fitted", f0(bs.dies_fitted), "124", R1, "burr_summary"),
        ("rej_back", p0(inh.rejected_share), "37%", R1, "sorting_by_basis"), ("rej_fault", p0(flt.rejected_share), "77%", R1, "sorting_by_basis"),
        ("scrap_before", p2(s24.scrap_and_rework_share_of_revenue), "2.60%", R2, "scrap_and_rework"), ("scrap_after", p2(s25.scrap_and_rework_share_of_revenue), "1.69%", R2, "scrap_and_rework"),
        ("saved", f0(round((s24.scrap_and_rework_share_of_revenue - s25.scrap_and_rework_share_of_revenue) * s25.revenue, -3)), "32,000", R2, "scrap_and_rework"), ("scrap_comparison", p2(scr.loc[(C, 2026), "scrap_and_rework_share_of_revenue"]), "3.32%", R2, "scrap_and_rework"),
        ("ppk_before", f2(cq[0].ppk_median), "1.07", R2, "capability, characteristics in both periods"), ("ppk_after", f2(cq[1].ppk_median), "1.42", R2, "capability, characteristics in both periods"), ("both_n", f0(cq[1].characteristics), "46", R2, "capability"),
        ("gap_before", f2(round(cq[0].cpk_median, 2) - round(cq[0].ppk_median, 2)), "0.46", R2, "capability"), ("gap_after", f2(round(cq[1].cpk_median, 2) - round(cq[1].ppk_median, 2)), "0.28", R2, "capability"),
        ("centred", f0(oc["coil_change_by_distance"].set_index("distance_from_the_centre_line").loc[["One to two sigma", "Two to three sigma"], "adjustments_recorded"].sum()), "30", R2, "coil_change_by_distance"), ("centred_of", f0(oc["coil_change_by_distance"].set_index("distance_from_the_centre_line").loc[["One to two sigma", "Two to three sigma"], "coil_change_subgroups"].sum()), "276", R2, "coil_change_by_distance"),
        ("alarms_before", f1(sg.loc[(P, ALL, 2025), "alarm_signals_per_100_subgroups"]), "15.3", R2, "signals"), ("alarms_after", f1(sg.loc[(P, ALL, 2026), "alarm_signals_per_100_subgroups"]), "5.3", R2, "signals"),
        ("adj_before", p0(sg.loc[(P, ALL, 2025), "adjustment_share"]), "17%", R2, "signals"), ("adj_after", p0(sg.loc[(P, ALL, 2026), "adjustment_share"]), "84%", R2, "signals"), ("breaks", f0(brk.punch_breaks_stopped_by_the_charts), "6", R2, "punch_break_summary"),
        ("ppm_before", f0(pp.loc[(P, 2025), "ppm"]), "191", R2, "ppm"), ("ppm_after", f0(pp.loc[(P, 2026), "ppm"]), "267", R2, "ppm"), ("complaints", f0(pp.loc[(P, 2026), "complaints"]), "6", R2, "ppm"),
        ("sorts_before", f0(so.loc[(P, 2025), "sorting_events"]), "1", R2, "sorting"), ("sorts_after", f0(so.loc[(P, 2026), "sorting_events"]), "0", R2, "sorting"), ("late_n", f0(len(late_iv)), "13", R2, "pilot_intervals"),
        ("hd_before", f1(hd.loc[2025, "alarm_signals_per_100_subgroups"]), "14.4", R2, "hole_diameter_under_the_tool_wear_chart"), ("hd_after", f1(hd.loc[2026, "alarm_signals_per_100_subgroups"]), "0.6", R2, "hole_diameter_under_the_tool_wear_chart"),
        ("stops", f0(both.stops), "36", R2, "stops_by_chart"), ("worn", f0(worn), "22", R2, "stops_by_chart"), ("slug", f0(both["slug pulling cleared"]), "9", R2, "stops_by_chart"), ("nothing", f0(both["nothing found"]), "5", R2, "stops_by_chart"),
        ("nf_rate", f2(rate.nothing_found_per_million_strokes), "0.63", R2, "stops_with_nothing_found"), ("after_stop", f0(pr26.get("after a stop by the per-stroke charts", 0)), "22", R2, "punch_replacements"), ("replacements", f0(pr26.sum()), "25", R2, "punch_replacements"),
        ("models", f0(models.sum()), "", "", "information_schema.tables: staging, intermediate, marts"), ("tests", f0(tests), "", "", "dbt manifest: test nodes"), ("batch", batch, "", "", "mart_outcomes.export_batch_id"),
        ("subgroups", f0(n["spc__subgroups"]), "", "", "raw.spc__subgroups"), ("characteristics", f0(n["spc__characteristics"]), "", "", "raw.spc__characteristics"), ("runs", f0(n["erp__production_runs"]), "", "", "raw.erp__production_runs"), ("coils", f0(n["erp__coils"]), "", "", "raw.erp__coils"),
        ("strokes", f0(strokes), "", "", "mart_per_stroke_run_tonnage"), ("digit", f2(em.times_the_uniform_expectation), "1.76", R1, "entry_methods"), ("set_aside", p2(em.set_aside_share), "", R1, "entry_methods"),
        ("out_of_service", p1(gs.share_out_of_service), "4.4%", R1, "gauge_status"), ("past_due", p1(gs.share_past_due), "2.7%", R1, "gauge_status"), ("rounded", f0(sharp.rounded), "349", "", "stg_die_room__die_events"), ("sharpenings", f0(sharp.n), "845", "", "stg_die_room__die_events"),
    ]:
        v(key, value, was, page, src)
    assert int(pp.loc[(P, 2025), "complaints"]) == int(pp.loc[(P, 2026), "complaints"]) and int(brk.strokes_largest) == 1 and int(late_iv["over_the_limit"].sum()) == 0
    src = [("SPC software", "characteristics, control limits, subgroups, alarms, reaction plan steps", n["spc__characteristics"] + n["spc__control_limits"] + n["spc__subgroups"] + n["spc__alarms"] + n["spc__reaction_plan_steps"]),
           ("Press monitors", "per-stroke peaks (pilot presses), tonnage windows, fault events", strokes + n["press_monitor__tonnage_windows"] + n["press_monitor__fault_events"]),
           ("ERP", "parts, dies, presses, production runs, coils, scrap, shipments", n["erp__parts"] + n["erp__dies"] + n["erp__presses"] + n["erp__production_runs"] + n["erp__coils"] + n["erp__scrap_transactions"] + n["erp__shipments"]),
           ("QMS", "nonconformances, sorting events, complaints, dock audits, PPAP studies, scorecards", n["qms__nonconformances"] + n["qms__sorting_events"] + n["qms__complaints"] + n["qms__dock_audits"] + n["qms__ppap_studies"] + n["qms__scorecards"]),
           ("Die maintenance log", "sharpenings, punch replacements, rebuilds, repairs", n["die_room__die_events"]), ("Calibration system", "gauges, calibrations, gauge studies", n["calibration__gauges"] + n["calibration__calibrations"] + n["calibration__gauge_studies"]),
           ("Accounting", "quality cost lines, contribution by part", n["accounting__quality_cost_lines"] + n["accounting__contribution"]),
           ("Study worksheets", "gauge R&R and attribute agreement studies, as recorded", len(list((S.ROOT / "data" / "raw" / "studies").glob("*.csv"))))]
    V["sources"] = "\n".join(f"| {a} | {b} | {c:,} |" for a, b, c in src)
    for a, b, c in src:
        sup.append((f"records: {a}", f"{c:,}", "", "", b))
    md = [README.format(**V)]
    md.append("## How to run\n")
    md.append("Python 3.12 or later. Run from `stamping_spc_program/`.\n\n```bash\npython -m venv .venv\n```\n\nActivate it: `.venv\\Scripts\\activate` on Windows, `source .venv/bin/activate` on Linux and macOS. Then:\n\n```bash\npip install -e .\n```\n\n```bash\npython -m pipeline.load.load_exports\n```\n\n"
              "```bash\ncd pipeline/dbt && dbt build --profiles-dir . && cd ../..\n```\n\n```bash\npython -m analytics.build_all\n```\n\n"
              "The last command writes every figure under `docs/figures`, the two reports, the two screens, the monthly summary, the control plans and chart book, `docs/index.html`, this README and the number traces.\n")
    md.append("## Author\n")
    md.append("Brian Davis. Data engineering and applied analytics/ML for manufacturers. Other work: [github.com/brimsystems](https://github.com/brimsystems?tab=repositories).\n")
    text = "\n".join(md)
    text = re.sub(r"\]\((docs/[^)]+\.html)\)", lambda m: f"]({PAGES_BASE}{m.group(1)})", text)
    (S.ROOT / "README.md").write_text(text, encoding="utf8", newline="\n")
    html = landing(other_parts)
    sup = pd.DataFrame(sup, columns=["readme_figure", "value", "value_in_the_text", "page", "read_from"])
    off = sup[(sup["value_in_the_text"] != "") & (sup["value"] != sup["value_in_the_text"])]
    print("README numbers that differ from the text:", len(off)); print(off.to_string() if len(off) else "")
    return text, html, sup


if __name__ == "__main__":
    text, html, sup = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    sup.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "readme_numbers.csv", index=False, lineterminator="\n")
    print(len(text), len(html), len(sup))
