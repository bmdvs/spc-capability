# Metal stamping: SPC program

Statistical process control as it runs at a progressive-die metal stamper with eleven presses, on the shop's records from July 2025 to June 2026. Two documents from the quality engineer's working set, computed by one pipeline from the exported records:
- the **control chart design revalidation**, which derives the chart for each characteristic class from its variance structure, sets out how limits are governed across sharpenings and rebuilds, and measures each chart's false-alarm rate and detection against its design;
- the **SPC quarterly review** for April to June 2026, which reports signals and their dispositions, limits governance, capability with intervals, measurement gating, dies and per-stroke monitoring, and first-piece approvals.

The plant is covered at summary level, and one part family (three C110 copper parts on PR-03) in full, characteristic by characteristic.

[![SPC terminal screen, PR-03](docs/readme/spc_terminal_screen.png)](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/screens/spc_terminal_pr_03.html)

## What is included

- **Control Chart Design:** [revalidation on the July 2025 to June 2026 record](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/control_chart_design.html). Variance components by class, Phase I baselines and verification, ARL by chart and rule, the three-way chart design for coil-structured variation, the tool-wear chart, the per-stroke EWMA design, and the charts in force. Appendix with the formulas.
- **SPC Quarterly Review, April to June 2026:** [the operating record for the quarter](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_quarterly_review_2026_q2.html). Observed against expected signals, assignable causes and closure, recalculations and verifications, Cpk and Ppk with intervals, gauge studies and operator qualification, sharpenings against the due count, per-stroke stops, first-piece holds and recording. Appendix with every signal of the quarter.
- **Screens, PR-03 at 12:04 on 13 May 2026:** the [SPC terminal screen](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/screens/spc_terminal_pr_03.html) and the [press monitor screen](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/screens/press_monitor_pr_03.html), at the moment of a per-stroke stop on a chipped punch.
- **Index:** [docs/index.html](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/index.html).
- **Pipeline:** dlt, DuckDB and dbt from the exported files to the marts, with schema tests; one build command writes every table, figure and page, and two builds are byte-identical.

## Business Context

The shop is a progressive-die metal stamper:
- about 110 employees, IATF 16949 certified;
- one plant with eleven presses, four high-speed and seven medium;
- about 180 part numbers on about 170 dies, for automotive, appliance, HVAC, industrial, electrical and consumer customers.

The program it runs:
- **Charts by characteristic class.** Formed heights and bend angles on three-way charts with a coil-change chart beside them; hole diameters on tool-wear charts with limits sloped on shots since sharpening; hole position, length, width and flatness on X-bar and R; the burr and pin checks on p charts.
- **Limits held under verification.** Limits are set from a baseline and held across sharpenings; the first 25 subgroups after a sharpening verify them, and a failed verification starts a new baseline. Formed charts are verified after a rebuild or a forming-station repair.
- **Centring at the coil change.** A 10-piece coil-change subgroup centres the die on each coil, and plots on the coil-change chart.
- **Per-stroke monitoring.** An EWMA on the per-stroke tonnage total and a residual chart on each channel's share, on every press, stopping the press on a signal.
- **Measurement gating.** No gauge feeds a chart without a current calibration and a gauge study; check fixtures are verified daily against a master part, and burr check operators are qualified quarterly against the burr gauge.
- **Sharpening at the count.** Each die is sharpened at the shot count where its burr line reaches 80% of the limit.
- **First-piece approval** at every run start, with the run held until release.

The two documents are what that program produces: the annual revalidation of the chart design, and the quarterly review of its operation.

## Analyses

| Analysis | Question | Finding | Document |
|---|---|---|---|
| Variance structure | Where does each class's variance lie, and which chart follows? | Formed characteristics carry 49.7% of their incoming variance between coils and 80.0% within the subgroup after centring; hole diameters carry 36.2% in the wear trend; hole position and flatness carry 97.4% and 97.5% within the subgroup. | [Control Chart Design](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/control_chart_design.html) |
| Coil effect | Is the coil effect predictable from the certificate? | Certificate thickness and hardness explain the coil means with R squared 0.82; the residual is 3.2% of tolerance against coil means that spread 10.1%. | [Control Chart Design](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/control_chart_design.html) |
| Limits governance | How are limits set, held and verified? | 244 baselines and 1,308 verifications in the year; 8.1% of sharpenings failed verification on at least one chart; 23 of 45 annual-review three-way sets spanned fewer than ten coil changes. | [Control Chart Design](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/control_chart_design.html) |
| Chart performance | What does each chart cost in false alarms, and what does it catch? | ARL by Markov chain for rules 1 to 4 and for the EWMA on AR(1) data; observed signals at 1.30, 0.83 and 1.79 times expectation on X-bar and R, three-way and tool-wear charts, with the causes. | [Control Chart Design](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/control_chart_design.html) |
| Three-way chart design | How is coil-structured variation charted without constant false alarms? | Centring on a 10-piece coil-change subgroup, individuals limits from the spread of the baseline means, rule 1 only: 0.27 false alarms per 100 points, against 20.5 with moving-range limits and rules 1 to 4. | [Control Chart Design](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/control_chart_design.html) |
| Per-stroke monitoring | How are the EWMA parameters chosen, and what do the charts catch? | Lambda 0.02 and L 5.5 for parameters estimated from 500 strokes (in-control ARL 2.64 million strokes); 1.02 false stops per million strokes; chipped punches stopped at a median 0 strokes against up to 11,773 parts under an hourly check. | [Control Chart Design](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/control_chart_design.html) |
| Signals and reaction | Did the quarter's signals run at the design rate, and were causes found? | 3.80 signals per 100 subgroups against 3.08 expected; 418 alarms with an assignable cause, all closed; six special causes caught by the chart designed to catch them. | [SPC Quarterly Review](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_quarterly_review_2026_q2.html) |
| Capability | Is the process capable, by the right index for each chart? | 93 of 100 critical characteristics at or above Ppk 1.33; Cpk by between/within sigma on three-way charts and about the regression on tool-wear charts; Bissell intervals. | [SPC Quarterly Review](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_quarterly_review_2026_q2.html) |
| Measurement gating | Did every chart run on a gauge in gating status? | 0 of 897 charts fed by a gauge past due, away or unstudied; a drifting fixture seen on the charts four days before its verification failed, pulled and rebuilt; 24 operators qualified at kappa 0.78 to 0.89. | [SPC Quarterly Review](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_quarterly_review_2026_q2.html) |
| Dies, first pieces and recording | Is the rest of the program running to its rules? | 69 of 76 sharpenings at or before the due count, burr at most 90.8% of its limit; 19 of 583 run starts held at the first piece; planned checks recorded on 97.9% of day and 96.9% of night occasions. | [SPC Quarterly Review](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_quarterly_review_2026_q2.html) |

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
- A dbt project builds 75 staging, intermediate and mart models with 297 schema tests, and every mart carries the export batch id.
- Every table, figure and page is written by scripts that read the marts; no number is typed into a page, and each page has a trace of every number it prints and the mart it is read from under `analytics/reports/traces/`. Two consecutive builds are byte-identical.

## Data

Twelve months of the shop's records, 1 July 2025 to 30 June 2026, in export batch 20260713T053000Z-SPC12M:
- 379,677 subgroups on 1,560 characteristics;
- 2,228 production runs and 1,914 coils;
- 37.9 million press strokes: April to June 2026 on all presses, and the full year on PR-03.

Conditions of the record, stated in the documents where they bear on a figure:
- the die log carries dates without times, so 15 runs that start on a sharpening day are placed in a sharpening interval by the day;
- the SPC software leaves the subgroup mean blank on laboratory burr readings, which are averaged from the readings;
- a run started on a coil already in use plots no new point on the coil-change chart;
- 0.27% of the quarter's subgroups were recorded against a gauge away for calibration.

| Source | Tables | Records |
|---|---|---|
| SPC software | characteristics, control limits, limit verifications, subgroups, alarms with dispositions, reaction plan steps | 404,717 |
| Press monitors | per-stroke peaks, tonnage windows, fault events | 37,905,094 |
| ERP | parts, dies, presses, production runs, coils | 4,503 |
| QMS | nonconformances, corrective actions, first-piece approvals | 2,403 |
| Die maintenance log | sharpenings with corrections, punch replacements, rebuilds, repairs | 1,114 |
| Calibration system | gauges, calibrations, gauge studies, fixture verifications, attribute qualifications | 5,913 |
| Study worksheets | gauge R&R studies, as recorded | 52 |

The pipeline runs in three stages:
- `pipeline/load` loads each exported file to the `raw` schema;
- `pipeline/dbt` builds one staging model per source table, then the intermediate models (the characteristic history with run, press, coil, die shot count, limits in force and gauge status joined; coil assignment; sharpening intervals; limit sets with their basis and verifications; alarm dispositions with time to reaction and closure), then the marts the two documents and the screens read;
- `analytics/build_all.py` writes every figure, both documents, the two screens, `docs/index.html`, this README and the number traces.

## How to run

Python 3.12 or later. Run from `stamping_spc_program/`.

```bash
python -m venv .venv
```

Activate it: `.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on Linux and macOS. Then:

```bash
pip install -e .
```

```bash
python -m pipeline.load.load_exports
```

```bash
cd pipeline/dbt && dbt build --profiles-dir . && cd ../..
```

```bash
python -m analytics.build_all
```

The last command writes every figure under `docs/figures`, the two documents, the two screens, `docs/index.html`, this README and the number traces.

## Author

Brian Davis. Data engineering and applied analytics/ML for manufacturers. Other work: [github.com/brimsystems](https://github.com/brimsystems?tab=repositories).
