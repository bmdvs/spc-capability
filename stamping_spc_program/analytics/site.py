"""The landing page (docs/index.html) and the README, written from the marts so that every figure in them is the figure on
the pages. Writes the README's number trace: each figure with the value in the text and the mart it is read from.

Usage: python -m analytics.site"""
import json
import re

import pandas as pd

from analytics.data import query
from analytics.style import style as S

PAGES_BASE = "https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/"          # where the pages are served; README links to pages use it, links to files stay relative
D1, D2 = "docs/reports/control_chart_design.html", "docs/reports/spc_quarterly_review_2026_q2.html"
PAGES = [("Control Chart Design", "reports/control_chart_design.html", "Revalidation", "The chart for each characteristic class from its variance structure, limits governance across sharpenings and rebuilds, ARL and false-alarm rates by chart and rule, the three-way and tool-wear chart designs, the per-stroke EWMA design, and the charts in force at 30 June 2026. Plant-wide, with the PR-03 copper family in full."),
         ("SPC Quarterly Review, April to June 2026", "reports/spc_quarterly_review_2026_q2.html", "Quarterly review", "Signals against expectation and their dispositions, recalculations and verifications, Cpk and Ppk with intervals, gauge studies and operator qualification, sharpenings against the due count, per-stroke stops, first-piece holds and recording. Every signal of the quarter in the appendix."),
         ("SPC Terminal Screen, PR-03", "screens/spc_terminal_pr_03.html", "Screen", "The press-side SPC software on PR-03 at 12:04 on 13 May 2026: the characteristics of the part on the run, the chart in force, the last subgroup, the most recent alarm and the shift event log."),
         ("Press Monitor Screen, PR-03", "screens/press_monitor_pr_03.html", "Screen", "The press monitor historian's display for PR-03 at the same moment: the per-stroke EWMA and channel shares on the run, the stop on a chipped punch an hour earlier, and the die's shots against its sharpening due count.")]

README = """# Metal stamping: SPC program

Statistical process control as it runs at a progressive-die metal stamper with eleven presses, on the shop's records from July 2025 to June 2026. Two documents from the quality engineer's working set, computed by one pipeline from the exported records:
- the **control chart design revalidation**, which derives the chart for each characteristic class from its variance structure, sets out how limits are governed across sharpenings and rebuilds, and measures each chart's false-alarm rate and detection against its design;
- the **SPC quarterly review** for April to June 2026, which reports signals and their dispositions, limits governance, capability with intervals, measurement gating, dies and per-stroke monitoring, and first-piece approvals.

The plant is covered at summary level, and one part family (three C110 copper parts on PR-03) in full, characteristic by characteristic.

[![SPC terminal screen, PR-03](docs/readme/spc_terminal_screen.png)](docs/screens/spc_terminal_pr_03.html)

## What is included

- **Control Chart Design:** [revalidation on the July 2025 to June 2026 record](docs/reports/control_chart_design.html). Variance components by class, Phase I baselines and verification, ARL by chart and rule, the three-way chart design for coil-structured variation, the tool-wear chart, the per-stroke EWMA design, and the charts in force. Appendix with the formulas.
- **SPC Quarterly Review, April to June 2026:** [the operating record for the quarter](docs/reports/spc_quarterly_review_2026_q2.html). Observed against expected signals, assignable causes and closure, recalculations and verifications, Cpk and Ppk with intervals, gauge studies and operator qualification, sharpenings against the due count, per-stroke stops, first-piece holds and recording. Appendix with every signal of the quarter.
- **Screens, PR-03 at 12:04 on 13 May 2026:** the [SPC terminal screen](docs/screens/spc_terminal_pr_03.html) and the [press monitor screen](docs/screens/press_monitor_pr_03.html), at the moment of a per-stroke stop on a chipped punch.
- **Index:** [docs/index.html](docs/index.html).
- **Pipeline:** dlt, DuckDB and dbt from the exported files to the marts, with schema tests; one build command writes every table, figure and page, and two builds are byte-identical.

## Business Context

The shop is a progressive-die metal stamper:
- about 110 employees, IATF 16949 certified;
- one plant with eleven presses, four high-speed and seven medium;
- about {parts} part numbers on about {dies} dies, for automotive, appliance, HVAC, industrial, electrical and consumer customers.

The program it runs:
- **Charts by characteristic class.** Formed heights and bend angles on three-way charts with a coil-change chart beside them; hole diameters on tool-wear charts with limits sloped on shots since sharpening; hole position, length, width and flatness on X-bar and R; the burr and pin checks on p charts.
- **Limits held under verification.** Limits are set from a baseline and held across sharpenings; the first {verify_n} subgroups after a sharpening verify them, and a failed verification starts a new baseline. Formed charts are verified after a rebuild or a forming-station repair.
- **Centring at the coil change.** A {cc_n}-piece coil-change subgroup centres the die on each coil, and plots on the coil-change chart.
- **Per-stroke monitoring.** An EWMA on the per-stroke tonnage total and a residual chart on each channel's share, on every press, stopping the press on a signal.
- **Measurement gating.** No gauge feeds a chart without a current calibration and a gauge study; check fixtures are verified daily against a master part, and burr check operators are qualified quarterly against the burr gauge.
- **Sharpening at the count.** Each die is sharpened at the shot count where its burr line reaches {burr_share} of the limit.
- **First-piece approval** at every run start, with the run held until release.

The two documents are what that program produces: the annual revalidation of the chart design, and the quarterly review of its operation.

## Analyses

| Analysis | Question | Finding | Document |
|---|---|---|---|
| Variance structure | Where does each class's variance lie, and which chart follows? | Formed characteristics carry {incoming} of their incoming variance between coils and {formed_within} within the subgroup after centring; hole diameters carry {trend} in the wear trend; hole position and flatness carry {hp_within} and {fl_within} within the subgroup. | [Control Chart Design](docs/reports/control_chart_design.html) |
| Coil effect | Is the coil effect predictable from the certificate? | Certificate thickness and hardness explain the coil means with R squared {r2}; the residual is {resid} of tolerance against coil means that spread {spread}. | [Control Chart Design](docs/reports/control_chart_design.html) |
| Limits governance | How are limits set, held and verified? | {baselines} baselines and {verifications} verifications in the year; {sharp_fail} of sharpenings failed verification on at least one chart; {below} of {annual_tw} annual-review three-way sets spanned fewer than ten coil changes. | [Control Chart Design](docs/reports/control_chart_design.html) |
| Chart performance | What does each chart cost in false alarms, and what does it catch? | ARL by Markov chain for rules 1 to 4 and for the EWMA on AR(1) data; observed signals at {oe_xr}, {oe_tw3} and {oe_tw} times expectation on X-bar and R, three-way and tool-wear charts, with the causes. | [Control Chart Design](docs/reports/control_chart_design.html) |
| Three-way chart design | How is coil-structured variation charted without constant false alarms? | Centring on a {cc_n}-piece coil-change subgroup, individuals limits from the spread of the baseline means, rule 1 only: {tw_rate} false alarms per 100 points, against {mr_rate} with moving-range limits and rules 1 to 4. | [Control Chart Design](docs/reports/control_chart_design.html) |
| Per-stroke monitoring | How are the EWMA parameters chosen, and what do the charts catch? | Lambda {lam} and L {L} for parameters estimated from {base_strokes} strokes (in-control ARL {arl_est} million strokes); {nf_rate} false stops per million strokes; chipped punches stopped at a median {chip_med} strokes against up to {hourly} parts under an hourly check. | [Control Chart Design](docs/reports/control_chart_design.html) |
| Signals and reaction | Did the quarter's signals run at the design rate, and were causes found? | {obs} signals per 100 subgroups against {exp} expected; {assignable} alarms with an assignable cause, all closed; six special causes caught by the chart designed to catch them. | [SPC Quarterly Review](docs/reports/spc_quarterly_review_2026_q2.html) |
| Capability | Is the process capable, by the right index for each chart? | {cap_ok} of {cap_n} critical characteristics at or above Ppk 1.33; Cpk by between/within sigma on three-way charts and about the regression on tool-wear charts; Bissell intervals. | [SPC Quarterly Review](docs/reports/spc_quarterly_review_2026_q2.html) |
| Measurement gating | Did every chart run on a gauge in gating status? | {gate_out} of {var_charts} charts fed by a gauge past due, away or unstudied; a drifting fixture seen on the charts four days before its verification failed, pulled and rebuilt; {operators} operators qualified at kappa {k_lo} to {k_hi}. | [SPC Quarterly Review](docs/reports/spc_quarterly_review_2026_q2.html) |
| Dies, first pieces and recording | Is the rest of the program running to its rules? | {on_time} of {sharpenings} sharpenings at or before the due count, burr at most {burr_max} of its limit; {held} of {starts} run starts held at the first piece; planned checks recorded on {days} of day and {nights} of night occasions. | [SPC Quarterly Review](docs/reports/spc_quarterly_review_2026_q2.html) |

## Methods

**Statistics:**
- **Control charts:** X-bar and R, three-way (individuals on subgroup means with limits from the spread of the baseline means, moving range, range), tool-wear charts with limits about a regression on shots since sharpening, p charts; Western Electric rules 1 to 4 where in force.
- **Capability:** Ppk on overall sigma; Cpk by chart class (pooled within-subgroup, between/within, residual about the regression); one-sided indices on bounded characteristics; Bissell's approximation for intervals.
- **Variance components:** nested method of moments (within subgroup, between subgroups within coil, between coils, between sharpening intervals).
- **Chart performance:** ARL by the Markov chain method for rules 1 to 4, for AR(1) subgroup means, and for the EWMA on AR(1) per-stroke data; the coil-change chart's expectation by Monte Carlo on the record's coil lots.
- **Measurement:** gauge R&R by the AIAG MSA ANOVA method, %tolerance at 6 sigma and ndc; attribute agreement by Fleiss' kappa.
- **Normality:** Anderson-Darling on baseline means, with Box-Cox on bounded characteristics.

**Data engineering:**
- The exported files are loaded to DuckDB with dlt; the per-stroke press monitor export is read in place as Parquet.
- A dbt project builds {models} staging, intermediate and mart models with {tests} schema tests, and every mart carries the export batch id.
- Every table, figure and page is written by scripts that read the marts; no number is typed into a page, and each page has a trace of every number it prints and the mart it is read from under `analytics/reports/traces/`. Two consecutive builds are byte-identical.

## Data

Twelve months of the shop's records, 1 July 2025 to 30 June 2026, in export batch {batch}:
- {subgroups} subgroups on {characteristics} characteristics;
- {runs} production runs and {coils} coils;
- {strokes} million press strokes: April to June 2026 on all presses, and the full year on PR-03.

Conditions of the record, stated in the documents where they bear on a figure:
- the die log carries dates without times, so {same_day} runs that start on a sharpening day are placed in a sharpening interval by the day;
- the SPC software leaves the subgroup mean blank on laboratory burr readings, which are averaged from the readings;
- a run started on a coil already in use plots no new point on the coil-change chart;
- {away} of the quarter's subgroups were recorded against a gauge away for calibration.

| Source | Tables | Records |
|---|---|---|
{sources}

The pipeline runs in three stages:
- `pipeline/load` loads each exported file to the `raw` schema;
- `pipeline/dbt` builds one staging model per source table, then the intermediate models (the characteristic history with run, press, coil, die shot count, limits in force and gauge status joined; coil assignment; sharpening intervals; limit sets with their basis and verifications; alarm dispositions with time to reaction and closure), then the marts the two documents and the screens read;
- `analytics/build_all.py` writes every figure, both documents, the two screens, `docs/index.html`, this README and the number traces.
"""

HOW_TO_RUN = ("## How to run\n\nPython 3.12 or later. Run from `stamping_spc_program/`.\n\n```bash\npython -m venv .venv\n```\n\nActivate it: `.venv\\Scripts\\activate` on Windows, `source .venv/bin/activate` on Linux and macOS. Then:\n\n```bash\npip install -e .\n```\n\n```bash\npython -m pipeline.load.load_exports\n```\n\n"
              "```bash\ncd pipeline/dbt && dbt build --profiles-dir . && cd ../..\n```\n\n```bash\npython -m analytics.build_all\n```\n\n"
              "The last command writes every figure under `docs/figures`, the two documents, the two screens, `docs/index.html`, this README and the number traces.\n")

AUTHOR = "## Author\n\nBrian Davis. Data engineering and applied analytics/ML for manufacturers. Other work: [github.com/brimsystems](https://github.com/brimsystems?tab=repositories).\n"


def landing():
    rows = "".join(f'<tr><td><a href="{href}">{title}</a></td><td>{kind}</td><td>{line}</td></tr>' for title, href, kind, line in PAGES)
    body = ("<p>Statistical process control as it runs at a progressive-die metal stamper with eleven presses: the control chart design revalidation, the quarterly review for April to June 2026, and the PR-03 SPC terminal and press monitor screens.</p>"
            f'<table class="data"><thead><tr><th>Deliverable</th><th>Form</th><th>Content</th></tr></thead><tbody>{rows}</tbody></table>')
    meta = "Progressive-die metal stamper, about 110 employees, eleven presses, one plant; IATF 16949 certified. July 2025 to June 2026; SPC software, press monitors, ERP, QMS, die maintenance log, calibration system and gauge study worksheets."
    html = S.shell("SPC Program", "Deliverables", meta, body)
    (S.DOCS / "index.html").write_text(html, encoding="utf8", newline="\n")
    return html


def trace_value(trace, page, label):
    """A value as printed on a page, read from the page's own number trace."""
    t = trace[page]
    hit = t[t["read_from"] == label]
    assert len(hit) >= 1, (page, label)
    return hit["value_as_printed"].iloc[0]


def build():
    sup = []          # (README figure, value as printed, value in the text, read from)
    V = {}
    tr = {p: pd.read_csv(S.ROOT / "analytics" / "reports" / "traces" / f, dtype=str, keep_default_na=False) for p, f in ((D1, "control_chart_design_numbers.csv"), (D2, "quarterly_review_numbers.csv"))}

    def v(key, value, was, src):
        V[key] = value; sup.append((key, value, was, src))

    def page(key, p, label, was):
        v(key, trace_value(tr, p, label), was, f"{p}: {label}")

    n = {t: int(query(f'select count(*) as n from raw."{t}"')["n"].iloc[0]) for t in (
        "spc__characteristics", "spc__control_limits", "spc__limit_verifications", "spc__subgroups", "spc__alarms", "spc__reaction_plan_steps", "press_monitor__tonnage_windows", "press_monitor__fault_events",
        "erp__parts", "erp__dies", "erp__presses", "erp__production_runs", "erp__coils", "qms__nonconformances", "qms__corrective_actions", "qms__first_piece_approvals", "die_room__die_events",
        "calibration__gauges", "calibration__calibrations", "calibration__gauge_studies", "calibration__fixture_verifications", "calibration__attribute_qualifications")}
    strokes = int(query("select count(*) n from read_parquet(?)", [str(S.ROOT / "data" / "raw" / "press_monitor" / "strokes" / "*" / "*.parquet")])["n"].iloc[0])
    worksheets = len(list((S.ROOT / "data" / "raw" / "studies").glob("*.csv")))
    design = query("select parameter, value from marts.mart_chart_design").set_index("parameter")["value"]
    manifest = json.loads((S.ROOT / "pipeline" / "dbt" / "target" / "manifest.json").read_text(encoding="utf8"))
    models = sum(1 for k in manifest["nodes"] if k.startswith("model.")); tests = sum(1 for k in manifest["nodes"] if k.startswith("test."))
    f0 = lambda x: f"{x:,.0f}"
    v("parts", f0(round(n["erp__parts"], -1)), "180", "raw.erp__parts, to the ten"); v("dies", f0(round(n["erp__dies"], -1)), "170", "raw.erp__dies, to the ten")
    v("verify_n", f0(design["verification_subgroups"]), "25", "mart_chart_design.verification_subgroups"); v("cc_n", f0(design["coil_change_subgroup_size"]), "10", "mart_chart_design.coil_change_subgroup_size")
    v("burr_share", f"{design['sharpening_burr_share_of_limit'] * 100:.0f}%", "80%", "mart_chart_design.sharpening_burr_share_of_limit")
    for key, p, label, was in [
        ("incoming", D1, "mart_variance_components.incoming_coil_share, formed, median", "49.7%"), ("formed_within", D1, "mart_variance_components.share_within, formed", "80.0%"),
        ("trend", D1, "mart_variance_components.trend_share, hole diameter, median", "36.2%"), ("hp_within", D1, "mart_variance_components.share_within, hole position, median", "97.4%"),
        ("fl_within", D1, "mart_variance_components.share_within, flatness, median", "97.5%"), ("r2", D1, "mart_coil_fit.r_squared, median", "0.82"),
        ("resid", D1, "mart_coil_fit.residual_sigma_share_of_tolerance, median", "3.2%"), ("spread", D1, "mart_coil_fit.coil_means_sigma_share_of_tolerance, median", "10.1%"),
        ("baselines", D1, "mart_phase1_baselines: baselines", "244"), ("sharp_fail", D1, "share of sharpenings failed", "8.1%"),
        ("below", D1, "mart_limit_sets: three-way annual-review sets below the coil-change minimum", "23"), ("annual_tw", D1, "mart_limit_sets: three-way sets at the annual review", "45"),
        ("oe_xr", D1, "observed over expected, X-bar and R", "1.30"), ("oe_tw3", D1, "observed over expected, three-way", "0.83"), ("oe_tw", D1, "observed over expected, tool-wear", "1.79"),
        ("tw_rate", D1, "coil_block_rate, rule 1, limits in force", "0.27"), ("mr_rate", D1, "coil_block_rate, rules 1 to 4, moving-range limits", "20.5"),
        ("lam", D1, "mart_chart_design.ewma_lambda", "0.02"), ("L", D1, "mart_chart_design.ewma_L", "5.5"), ("base_strokes", D1, "mart_chart_design.ewma_baseline_strokes", "500"),
        ("arl_est", D1, "ewma_arl averaged over the estimates, L 5.5, millions", "2.64"), ("nf_rate", D1, "mart_per_stroke_stop_rates: nothing found per million strokes", "1.02"),
        ("chip_med", D1, "mart_parts_exposed.strokes_exposed_per_stroke_charts, median", "0"), ("hourly", D1, "mart_parts_exposed.parts_exposed_hourly_check_up_to, PR-03, median", "11,773"),
        ("obs", D2, "observed per 100, quarter", "3.80"), ("exp", D2, "expected per 100, quarter", "3.08"), ("assignable", D2, "mart_signals: assignable-cause alarms, quarter", "418"),
        ("cap_ok", D2, "mart_capability: critical characteristics at or above 1.33", "93"), ("cap_n", D2, "mart_capability: critical characteristics", "100"),
        ("gate_out", D2, "mart_charts_in_force with mart_gauge_quarter_end: variable charts fed by a gauge past due, away or without a study", "0"), ("var_charts", D2, "mart_charts_in_force: variable charts", "897"),
        ("operators", D2, "mart_operator_kappa: operators", "24"), ("k_lo", D2, "latest kappa, lowest", "0.78"), ("k_hi", D2, "latest kappa, highest", "0.89"),
        ("on_time", D2, "mart_sharpenings: on time, quarter", "69"), ("sharpenings", D2, "mart_sharpenings: quarter", "76"), ("burr_max", D2, "mart_sharpenings.burr_peak_share_of_limit, highest", "90.8%"),
        ("held", D2, "mart_first_piece_approvals.held", "19"), ("starts", D2, "mart_first_piece_approvals: run starts", "583"), ("days", D2, "planned checks recorded, days", "97.9%"), ("nights", D2, "planned checks recorded, nights", "96.9%"),
        ("same_day", D2, "int_run_shots: runs starting on the day their sharpening is logged", "15"), ("away", D2, "share of the quarter", "0.27%")]:
        page(key, p, label, was)
    v("verifications", f0(n["spc__limit_verifications"]), "1,308", "raw.spc__limit_verifications")
    v("models", f0(models), "75", "dbt manifest: model nodes"); v("tests", f0(tests), "297", "dbt manifest: test nodes")
    v("batch", query("select min(export_batch_id) b from marts.mart_chart_design")["b"].iloc[0], "20260713T053000Z-SPC12M", "mart_chart_design.export_batch_id")
    v("subgroups", f0(n["spc__subgroups"]), "379,677", "raw.spc__subgroups"); v("characteristics", f0(n["spc__characteristics"]), "1,560", "raw.spc__characteristics")
    v("runs", f0(n["erp__production_runs"]), "2,228", "raw.erp__production_runs"); v("coils", f0(n["erp__coils"]), "1,914", "raw.erp__coils")
    v("strokes", f"{strokes / 1e6:.1f}", "37.9", "data/raw/press_monitor/strokes: rows, millions")
    src = [("SPC software", "characteristics, control limits, limit verifications, subgroups, alarms with dispositions, reaction plan steps", sum(n[t] for t in ("spc__characteristics", "spc__control_limits", "spc__limit_verifications", "spc__subgroups", "spc__alarms", "spc__reaction_plan_steps"))),
           ("Press monitors", "per-stroke peaks, tonnage windows, fault events", strokes + n["press_monitor__tonnage_windows"] + n["press_monitor__fault_events"]),
           ("ERP", "parts, dies, presses, production runs, coils", sum(n[t] for t in ("erp__parts", "erp__dies", "erp__presses", "erp__production_runs", "erp__coils"))),
           ("QMS", "nonconformances, corrective actions, first-piece approvals", sum(n[t] for t in ("qms__nonconformances", "qms__corrective_actions", "qms__first_piece_approvals"))),
           ("Die maintenance log", "sharpenings with corrections, punch replacements, rebuilds, repairs", n["die_room__die_events"]),
           ("Calibration system", "gauges, calibrations, gauge studies, fixture verifications, attribute qualifications", sum(n[t] for t in ("calibration__gauges", "calibration__calibrations", "calibration__gauge_studies", "calibration__fixture_verifications", "calibration__attribute_qualifications"))),
           ("Study worksheets", "gauge R&R studies, as recorded", worksheets)]
    V["sources"] = "\n".join(f"| {a} | {b} | {c:,} |" for a, b, c in src)
    for a, b, c in src:
        sup.append((f"records: {a}", f"{c:,}", "", b))
    text = "\n".join([README.format(**V), HOW_TO_RUN, AUTHOR])
    text = re.sub(r"\]\((docs/[^)]+\.html)\)", lambda m: f"]({PAGES_BASE}{m.group(1)})", text)
    (S.ROOT / "README.md").write_text(text, encoding="utf8", newline="\n")
    html = landing()
    sup = pd.DataFrame(sup, columns=["readme_figure", "value", "value_in_the_text", "read_from"])
    off = sup[(sup["value_in_the_text"] != "") & (sup["value"] != sup["value_in_the_text"])]
    print("README numbers that differ from the text:", len(off)); print(off.to_string() if len(off) else "")
    return text, html, sup


if __name__ == "__main__":
    text, html, sup = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    sup.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "readme_numbers.csv", index=False, lineterminator="\n")
    print(len(text), len(html), len(sup))
    print(sup[sup["readme_figure"].str.startswith("records")].to_string())
