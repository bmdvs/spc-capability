# spc-quality-ml

SPC and quality analytics for two shops. At an injection molder, every shot from an instrumented cell is retained, charted, measured and screened. At a progressive-die metal stamper, every chart in use is assessed, then redesigned with per-stroke tonnage monitoring, and the results are measured.

## Injection molding: cavity pressure monitoring and predictive quality

A data platform, an SPC layer and three model components for an injection molder's instrumented cell of two presses and six molds with cavity pressure sensors. The work joins every shot to its job, resin lot, setpoints and audits, runs the shop's control-chart rules on every shot, adds drift detection, puts a predicted weight and dimension on every shot and screens for shots unlike anything validated, and measures what each layer detects against how often it flags good parts. It delivers the monitoring unit screen and shift chart, run reports at job close, a quality dashboard, an ML overview, an ML technical report and an MLOps monitoring report.

[![Monitoring unit screen with the predicted weight, dimension and anomaly state](molding_predictive_quality/docs/screenshots/unit_screen.png)](https://brimsystems.github.io/spc-quality-ml/molding_predictive_quality/docs/reports/unit_screen.html)

Read the [case README](molding_predictive_quality/README.md) and the [deliverables index](https://brimsystems.github.io/spc-quality-ml/molding_predictive_quality/docs/index.html).

## Metal stamping: SPC program

An SPC program for a progressive-die metal stamper with eleven presses: an assessment of every chart in use (limits, capability, the risk window between checks, measurement systems, adjustment, die wear and recording), a redesign of the charts, limits, sampling and reaction plan on three pilot presses with per-stroke tonnage monitoring, and the results against the same months of the two years before, with the other presses as the comparison. It delivers the SPC Assessment report, the SPC Redesign and Results report, a control plan and chart book, an SPC board for each pilot press and a plant quality dashboard.

[![SPC board, PR-06](stamping_spc_program/docs/readme/pr_06_board.png)](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/spc_board/pr_06.html)

Read the [case README](stamping_spc_program/README.md) and the [deliverables index](https://brimsystems.github.io/spc-quality-ml/stamping_spc_program/docs/index.html).

## Author

Brian Davis. Data engineering and applied analytics/ML for manufacturers. Other work: [github.com/brimsystems](https://github.com/brimsystems?tab=repositories).
