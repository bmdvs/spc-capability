# Metal stamping: SPC program

Statistical process control at a progressive-die metal stamper with eleven presses, on the shop's records from January 2024 to June 2026. The work has three parts:
- an assessment of every chart in use on all eleven presses in 2025;
- a redesign of the charts, limits, sampling and reaction plan on three pilot presses from February 2026, with per-stroke tonnage monitoring from April 2026;
- the results for April to June 2026 against the same months of 2025, with the other eight presses as the comparison.

The analyses feed two reports, two PR-03 screens (the SPC terminal and the press monitor), an SPC monthly summary, and control plans with a chart book. One pipeline computes all of them from the shop's exported records.

[![SPC terminal screen, PR-03](docs/readme/spc_terminal_screen.png)](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/screens/spc_terminal_pr_03.html)

## What is included

- **Reports:** the [SPC Assessment](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_assessment.html) and the [SPC Redesign and Results](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_redesign_and_results.html). Each has findings and exhibits, and an appendix of the tables and statistical detail behind them.
- **Screens, PR-03 at 12:04 on 13 May 2026:** the [SPC terminal screen](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/screens/spc_terminal_pr_03.html) and the [press monitor screen](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/screens/press_monitor_pr_03.html).
- **Monthly summary:** the [SPC monthly summary](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/monthly_summary/spc_monthly_summary_2026_06.html) for June 2026.
- **Control plans:** the [control plans and chart book](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/control_plan/control_plan_and_chart_book.html), in force at 30 June 2026.
- **Index:** all deliverables are listed at [docs/index.html](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/index.html).
- **Pipeline:** from the exported files to the marts, built with dlt, DuckDB and dbt, with schema tests. One build command writes every table, figure and page.

## Business Context

The shop is a progressive-die metal stamper:
- about 110 employees, IATF 16949 certified;
- one plant with eleven presses;
- about 180 part numbers on about 170 dies, for automotive, appliance, HVAC, industrial, electrical and consumer customers.

Its practice as found:
- it charted six to twelve characteristics a part at the press, in SPC software on the seven medium presses and on paper on the four high-speed presses;
- it filed a Ppk from 300 consecutive pieces at PPAP;
- it sharpened dies on a stated shot interval;
- operators adjusted the die at their discretion.

In 2025 scrap and rework cost 3.12% of revenue ($1,242,201), customer PPM was 463, and 14 sorting events covered 101,154 parts.

The shop assessed every chart in use on the 2025 record. The charts held on punched characteristics and flatness, and failed on formed characteristics, hole diameters and burr:
- **Limits:** rolling limits in the software flagged 17.0% of what baseline limits flag. Printed limits on the paper presses signalled on 42 of every 100 formed-characteristic subgroups, and an action was recorded on 28% of paper signals.
- **Capability:** production Ppk on critical formed characteristics was 1.04, against 1.84 filed at PPAP.
- **Coils:** 54% of the variance on formed characteristics lay between coils.
- **Die wear:** 60 of the 61 burr nonconformances fell on runs past the die's stated sharpening interval.
- **Die events:** 12 of the 14 sorting events traced to a die event between two checks.
- **Gauge studies:** studies covered 2 of the 180 check fixtures.

From 2 February 2026 the shop changed its practice on three pilot presses, PR-03, PR-06 and PR-09:
- **Gauges:** it rebuilt and studied the two reworked fixtures, replaced the burr limit samples, and connected the gauges to the terminals.
- **Charts and limits:** it moved PR-03 from paper to the software. Formed characteristics went onto a three-way chart with a subgroup at each coil change, and hole diameters onto a tool-wear chart. Limits were fixed from a stable baseline after each sharpening.
- **Checks and reaction:** it set check frequency from the parts made between checks and put a written reaction plan on every chart.
- **Sharpening:** it set each die's sharpening count from its burr.

From 1 April 2026 the press monitor's historian kept every stroke on the pilot presses. The per-stroke total and channel shares were charted, and the press stopped on a signal. The same changes reach the other eight presses from 3 August 2026.

From April to June 2026 on the pilot presses, against the same months of 2025:
- **Scrap and rework:** fell from 2.60% to 1.69% of revenue, about $32,000 in the quarter, while the comparison presses held at 3.32%.
- **Capability:** production Ppk on critical formed characteristics rose from 1.07 to 1.42.
- **Alarms:** alarm signals fell from 15.3 to 5.3 per 100 subgroups, and an adjustment was recorded on 84% of them, against 17%.
- **Per-stroke stops:** the charts stopped all 6 punch breaks on the stroke of the break.

Customer PPM, at 267 against 191 on 6 complaints in each quarter, and sorting events, 0 against 1, are too few to show an effect in three months.

## Analyses

| Analysis | Question | Finding | Report | PPAP element |
|---|---|---|---|---|
| Charts and limits | Do the limits in use signal when the process changes? | On formed characteristics and hole diameters, the software's rolling limits flag 17.0% of the subgroups that baseline limits flag. On the paper presses, printed limits signal on 42 of every 100 formed-characteristic subgroups, with an action recorded on 28% of signals. | [SPC Assessment](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_assessment.html) | 11, initial process studies |
| Capability | Does the Ppk filed at PPAP describe production? | Production Ppk on critical formed characteristics is 1.04 against 1.84 filed; punched characteristics hold at 1.55 against 1.85. | [SPC Assessment](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_assessment.html) | 9 and 11, dimensional results and initial process studies |
| Measurement systems | Are the gauges studied, and do they hold? | Before January 2026, 2 of the 180 check fixtures had a gauge study. The two reworked fixtures consume 31.2% and 33.6% of tolerance, and the burr check agrees with the burr gauge on 80% of calls (kappa 0.44). | [SPC Assessment](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_assessment.html) | 8, measurement system analysis studies |
| Sampling and recording | How many parts pass between checks, and are checks recorded on time? | A median 1,934 to 16,333 parts pass between routine checks, by press. Nights record 84% of planned checks against 94% on days, and 15.1% of keyed entries are made more than 20 minutes after the parts. | [SPC Assessment](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_assessment.html) | IATF 16949 9.1.1.1 |
| Reaction | What follows a signal? | All 10,474 software alarms were acknowledged, 4,691 with a one-word text. Adjusted characteristics carry a lag-1 autocorrelation of -0.14 against -0.07 on the others, and 9.9% more variance. | [SPC Assessment](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_assessment.html) | IATF 16949 9.1.1.1 |
| Coil-to-coil variation | Where does the variance on formed characteristics lie? | 54% of it lies between coils, against 2% on punched characteristics. A coil's level is predictable from its certificate to 2.5% of tolerance. | [SPC Assessment](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_assessment.html) | 11, initial process studies |
| Die wear | Is the sharpening interval set by the die's burr? | 60 of the 61 burr nonconformances of 2025 fell on runs past the stated interval. Sharpenings are logged at a median 1.14 times the interval, and on 41 of 124 dies the interval is longer than the count at which burr reaches 80% of its limit. | [SPC Assessment](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_assessment.html) | IATF 16949 9.1.1.1 |
| Die events and sorting | What does a sorting event cover? | 12 of the 14 sorting events of 2025 trace to a die event between two checks. Sorting back to the check before rejects 37% of what it sorts, against 77% where a fault bounds the event. | [SPC Assessment](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_assessment.html) | IATF 16949 9.1.1.1 |
| Formed characteristics, redesigned | Does the three-way chart raise capability on formed characteristics? | On 46 characteristics, production Ppk rose from 1.07 to 1.42, and the gap between Cpk and Ppk fell from 0.46 to 0.28. The die is centred at a coil change on 30 of 276 coil-change subgroups between one and three sigma off centre. | [SPC Redesign and Results](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_redesign_and_results.html) | 11, initial process studies |
| Sharpening at the count | Does the count keep burr under its limit? | All 13 pilot intervals begun under the count were sharpened at or before it, and none crossed the limit. The tool-wear chart cut alarms on hole diameters from 14.4 to 0.6 per 100 subgroups. | [SPC Redesign and Results](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_redesign_and_results.html) | IATF 16949 9.1.1.1 |
| Per-stroke monitoring | What does charting every stroke find that the check cannot? | The charts stopped the pilot presses 36 times: on a worn or chipped punch 22 times, on slug pulling 9, and on nothing 5 (0.63 per million strokes). All 6 punch breaks were stopped on the stroke, and 22 of 25 punch replacements followed a stop. | [SPC Redesign and Results](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_redesign_and_results.html) | IATF 16949 9.1.1.1 |
| Signals and adjustment | Are alarms fewer, and answered? | Alarm signals fell from 15.3 to 5.3 per 100 subgroups, and the share with an adjustment recorded rose from 17% to 84%. | [SPC Redesign and Results](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_redesign_and_results.html) | IATF 16949 9.1.1.1 |
| Outcomes | What moved on the pilot presses, against the comparison presses? | Scrap and rework fell from 2.60% to 1.69% of revenue, and held at 3.32% on the comparison presses. Customer PPM, at 267 against 191, and sorting are too few to show an effect in three months. | [SPC Redesign and Results](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/reports/spc_redesign_and_results.html) | 11, initial process studies |

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
- A dbt project builds 83 staging, intermediate and mart models, with 263 schema tests on every layer.
- Every table, figure and page is written by scripts that read the marts. No number is typed into a page, and two consecutive builds are byte-identical.
- Each deliverable has a table of every number it prints and the mart it is read from, under `analytics/reports/traces/`. This covers both reports, the two screens, the monthly summary and the control plans.

## Data

The record covers thirty months of the shop's records, January 2024 to June 2026, in export batch 20260713T053000Z-SPC30M. It holds:
- 525,576 subgroups on 1,560 characteristics;
- 5,620 production runs and 4,665 coils;
- 8,030,315 press strokes on the pilot presses from 1 April 2026.

Conditions of the record, each stated in the reports where it bears on a figure:
- **Keyed readings:** they end in 0 or 5 at 1.76 times the expected rate. Readings that cannot be a measurement of the part (0.35% of keyed readings) are set aside, with the count stated.
- **Gauge status:** subgroups recorded against a gauge away for calibration that day (4.4% in 2025), or past its calibration due date (2.7%).
- **Late entries:** 15.1% of keyed subgroups in 2025 were entered more than 20 minutes after the parts.
- **Coil ids:** missing coil ids are recovered from the run's coil sequence.
- **Complaints:** some are entered twice.
- **Sorting:** sorting is booked to the production run instead of the sorting labor code.
- **Die log:** shot counts are rounded to the thousand on 349 of 845 sharpenings.
- **Paper charts:** they were transcribed for the assessment.

| Source | Tables | Records |
|---|---|---|
| SPC software | characteristics, control limits, subgroups, alarms, reaction plan steps | 591,376 |
| Press monitors | per-stroke peaks (pilot presses), tonnage windows, fault events | 8,050,637 |
| ERP | parts, dies, presses, production runs, coils, scrap, shipments | 33,411 |
| QMS | nonconformances, sorting events, complaints, dock audits, PPAP studies, scorecards | 8,468 |
| Die maintenance log | sharpenings, punch replacements, rebuilds, repairs | 1,909 |
| Calibration system | gauges, calibrations, gauge studies | 2,478 |
| Accounting | quality cost lines, contribution by part | 1,358 |
| Study worksheets | gauge R&R and attribute agreement studies, as recorded | 9 |

The pipeline runs in three stages:
- `pipeline/load` loads each exported file to the `raw` schema.
- `pipeline/dbt` builds one staging model per source table, then the intermediate models:
  - the characteristic history, with run, press, coil, die shot count, limits in force and gauge status joined;
  - coil assignment;
  - sharpening intervals;
  - the trace of each sorting event to its die event and the check before.
- It then builds the marts that the analyses, the two screens, the monthly summary and the control plans read. Every mart carries the export batch id.

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

The last command writes every figure under `docs/figures`, the two reports, the two screens, the monthly summary, the control plans and chart book, `docs/index.html`, this README and the number traces.

## Author

Brian Davis. Data engineering and applied analytics/ML for manufacturers. Other work: [github.com/brimsystems](https://github.com/brimsystems?tab=repositories).
