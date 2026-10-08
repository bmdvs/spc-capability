"""SPC Assessment: the report page, on the record to 31 December 2024 with the assessment's own studies of January 2025. Reads the analysis tables, builds the figures and writes docs/reports/spc_assessment.html
and the table of every number in the body with the table it is read from."""
import numpy as np
import pandas as pd

from analytics.limits import limits as charts, figures as charts_fig
from analytics.capability import capability as capability, figures as capability_fig
from analytics.risk_window import risk_window as risk, figures as risk_fig
from analytics.measurement import measurement as measurement, figures as measurement_fig
from analytics.adjustment import adjustment as adjustment, figures as adjustment_fig
from analytics.die_wear import die_wear as wear, figures as wear_fig
from analytics.recording import recording as recording, figures as recording_fig
from analytics.style import style as S

TRACE = []          # (section, value as printed, table and column it is read from)
SECTION = [""]
FIGURE = [0]


def num(x, src, f="{:,.0f}"):
    s = f.format(x); TRACE.append((SECTION[0], s, src)); return s


def pct(x, src, d=0):
    s = f"{x * 100:.{d}f}%"; TRACE.append((SECTION[0], s, src)); return s


def figure(img, caption):
    FIGURE[0] += 1
    return f'{img}<div class="caption"><b>Figure {FIGURE[0]}.</b> {caption}</div>'


def show(df, columns, fmt=None):
    d = df[list(columns)].rename(columns=columns)
    return S.table(d, {columns[k]: v for k, v in (fmt or {}).items()})


def P1(v):
    return f"{v * 100:.1f}%"


def P0(v):
    return f"{v * 100:.0f}%"


def F0(v):
    return f"{v:,.0f}"


def F2(v):
    return f"{v:.2f}"


def F3(v):
    return f"{v:.3f}"


def F4(v):
    return f"{v:.4f}"


def section(anchor, title):
    SECTION[0] = title
    return f'<h2 id="{anchor}">{title}</h2>'


def anova_block(key, a):
    """One gauge study in the layout Minitab prints: the two-way ANOVA table and the variance components."""
    rows = "".join(f"<tr><td>{s}</td><td class='num'>{df}</td><td class='num'>{ss:.6f}</td><td class='num'>{'' if ms != ms else f'{ms:.6f}'}</td><td class='num'>{'' if fv != fv else f'{fv:.3f}'}</td></tr>" for s, df, ss, ms, fv in a["anova"])
    tv = a["total_var"]; comp = [("Total Gage R&R", a["grr_var"]), ("&nbsp;&nbsp;Repeatability", a["repeatability_var"]), ("&nbsp;&nbsp;Reproducibility", a["reproducibility_var"]),
                                ("&nbsp;&nbsp;&nbsp;&nbsp;Operator", a["operator_var"]), ("&nbsp;&nbsp;&nbsp;&nbsp;Operator*Part", a["interaction_var"]), ("Part-To-Part", a["part_var"]), ("Total Variation", tv)]
    vc = "".join(f"<tr><td>{n}</td><td class='num'>{v:.7f}</td><td class='num'>{v / tv * 100:.2f}</td><td class='num'>{np.sqrt(v):.5f}</td><td class='num'>{6 * np.sqrt(v):.5f}</td></tr>" for n, v in comp)
    pooled = "pooled with repeatability" if a["interaction_pooled"] else "kept"
    return (f"<h3>{key[0]}, {key[1]} study</h3><table class='data'><thead><tr><th>Source</th><th>DF</th><th>SS</th><th>MS</th><th>F</th></tr></thead><tbody>{rows}</tbody></table>"
            f"<table class='data'><thead><tr><th>Source</th><th>VarComp</th><th>%Contribution (of VarComp)</th><th>StdDev (SD)</th><th>Study Var (6 x SD)</th></tr></thead><tbody>{vc}</tbody></table>"
            f"<div class='caption'>Interaction p = {a['interaction_p']:.3f}, {pooled}. %Tolerance (SV/Toler) = {a['pct_tolerance']:.1f}. Number of Distinct Categories = {a['ndc']}.</div>")


def build():
    TRACE.clear(); FIGURE[0] = 0
    c, k, r, m, a, w, rec = charts.compute(), capability.compute(), risk.compute(), measurement.compute(), adjustment.compute(), wear.compute(), recording.compute()
    fc, fk, fr, fm, fa, fw, frec = charts_fig.build(c), capability_fig.build(k), risk_fig.build(r), measurement_fig.build(m), adjustment_fig.build(a), wear_fig.build(w), recording_fig.build(rec)
    body = []

    # -- values read once ----------------------------------------------------
    sc = c["signal_comparison"].set_index(["limits_as_set_method", "characteristic_class"])
    roll = sc.loc["rolling 25 at entry"].loc[["formed", "hole diameter"]]; ref = sc.loc[("rolling 25 at entry", "other punched and dimensional")]
    pa = c["paper_signals_all_subgroups"].iloc[0]; age = c["paper_limit_age"].iloc[0]; ack = c["software_acknowledgements"].iloc[0]
    cs = k["capability_summary"].set_index("characteristic_class"); cmm = k["fixture_against_cmm"].set_index("group"); coil = k["coil_regression_summary"].iloc[0]
    rw = r["risk_window"]; ss = r["sorting_summary"].set_index("year"); sb = r["sorting_by_basis"].set_index("sort_basis")
    grr = m["gauge_rr"].set_index(["fixture", "study"]); ms = m["measurement_share"].set_index("fixture"); att = m["attribute_agreement"].set_index("study"); em = m["entry_methods"].set_index("entry_method")
    gs = m["gauge_status"].iloc[0]; ld = m["last_digits"]
    ap = a["after_a_point"].set_index(["adjusted_at_the_press", "entry_method"]); rt = a["return_toward_centre"].set_index(["entry_method", "points_group"]); ac = a["autocorrelation"].set_index(["period", "characteristics"])
    av = a["variance"].set_index("comparison_runs"); est = a["adjustment_estimate"]
    hs = w["hole_diameter_summary"].iloc[0]; bs = w["burr_summary"].iloc[0]; bd = w["burr_by_die"]; il = w["intervals_as_logged"].iloc[0]; rp = w["runs_past_the_interval"].iloc[0]; bo = w["burr_over_the_limit_by_interval"].iloc[0]
    oh = rec["on_the_hour"].set_index("entry_method"); pc = rec["planned_checks"].set_index(["press_group", "shift"]); ph = rec["planned_checks_by_hour"]; sr = rec["short_runs"].set_index("run_length")
    ea = rec["entry_after_the_parts"].set_index("record")
    logged_n = int(bd["logged_interval_median"].notna().sum()); logged_longer = int((bd["logged_interval_median"] > bd["shots_at_80pct_of_limit"]).sum())
    day_hours = ph[(ph["press_group"] == "all presses") & (ph["shift"] == "days")]; six = day_hours[day_hours["hour_of_day"] == 6].iloc[0]; rest = day_hours[day_hours["hour_of_day"] != 6]["recorded_share"]

    mp = rec["minute_of_the_hour"]; mp = mp[mp["entry_method"] == "paper transcription"].set_index("minute_of_the_hour")["subgroups"].reindex(range(60)).fillna(0)
    paper_last = int(max(i for i in range(55) if mp[i] > 0)); paper_gap = int(mp.loc[0:paper_last].idxmin())
    TRACE.append(("Appendix", str(paper_last), "minute_of_the_hour.subgroups, paper: last minute before 55 with a subgroup")); TRACE.append(("Appendix", str(paper_gap), "minute_of_the_hour.subgroups, paper: minute with the fewest up to the last"))

    # -- 1. Findings ---------------------------------------------------------
    body.append(section("findings", "1. Findings"))
    both = roll["signals_by_both"].sum() / roll["signals_as_computed"].sum()
    body.append("<ol>"
        f"<li><b>Charts and limits.</b> On {num(roll['characteristics'].sum(), 'signal_comparison.characteristics, rolling: formed and hole diameter')} formed characteristics and hole diameters on the software presses, the rolling limits flagged "
        f"{pct(both, 'signal_comparison.signals_by_both over signals_as_computed, rolling: formed and hole diameter', 1)} of the subgroups that limits fixed from a stable baseline flag. On the paper presses the printed limits signalled on "
        f"{pct(pa.signal_rate, 'paper_signals_all_subgroups.signal_rate', 1)} of subgroups and an action was recorded on {pct(pa.action_share, 'paper_signals_all_subgroups.action_share', 1)} of signals (Section 2).</li>"
        f"<li><b>Capability.</b> On {num(cs.loc['formed', 'characteristics'], 'capability_summary.characteristics, formed')} critical formed characteristics the PPAP Ppk is {num(cs.loc['formed', 'filed_ppk'], 'capability_summary.filed_ppk, formed', '{:.2f}')} and the production Ppk is "
        f"{num(cs.loc['formed', 'ppk'], 'capability_summary.ppk, formed', '{:.2f}')} ({num(cs.loc['formed', 'ppk_low'], 'capability_summary.ppk_low, formed', '{:.2f}')} to {num(cs.loc['formed', 'ppk_high'], 'capability_summary.ppk_high, formed', '{:.2f}')}, {num(cs.loc['formed', 'subgroups'], 'capability_summary.subgroups, formed')} subgroups on {num(cs.loc['formed', 'studies'], 'capability_summary.studies, formed')} studies); "
        f"{pct(cs.loc['formed', 'share_between_coils'], 'capability_summary.share_between_coils, formed')} of the overall variance is between coils (Section 3).</li>"
        f"<li><b>Risk window and sorting.</b> Between routine checks {num(rw['fewest_parts_between_checks_at_the_realised_rate'].min(), 'risk_window.fewest_parts_between_checks_at_the_realised_rate, lowest')} to "
        f"{num(rw['most_parts_between_checks_at_the_realised_rate'].max(), 'risk_window.most_parts_between_checks_at_the_realised_rate, highest')} parts pass by part; {num(ss.loc[2024, 'traced_to_a_die_event_between_two_checks'], 'sorting_summary.traced_to_a_die_event_between_two_checks, 2024')} of the "
        f"{num(ss.loc[2024, 'sorting_events'], 'sorting_summary.sorting_events, 2024')} sorting events of 2024 trace to a die event between two checks (Section 4).</li>"
        f"<li><b>Measurement.</b> Check fixture F-20417 consumed {pct(grr.loc[('F-20417', 'redesign'), 'pct_tolerance'] / 100, 'gauge_rr.pct_tolerance, F-20417 redesign', 1)} of tolerance and F-31102 {pct(grr.loc[('F-31102', 'redesign'), 'pct_tolerance'] / 100, 'gauge_rr.pct_tolerance, F-31102 redesign', 1)}, "
        f"against {pct(grr.loc[('F-20417', 'PPAP'), 'pct_tolerance'] / 100, 'gauge_rr.pct_tolerance, F-20417 PPAP', 1)} and {pct(grr.loc[('F-31102', 'PPAP'), 'pct_tolerance'] / 100, 'gauge_rr.pct_tolerance, F-31102 PPAP', 1)} at PPAP; the burr check agreed with the burr gauge on "
        f"{pct(att.loc['at the redesign', 'against_reference'], 'attribute_agreement.against_reference, at the redesign')} of calls (Section 5).</li>"
        f"<li><b>Adjustment.</b> {pct(ap.loc[(True, 'keyed'), 'recorded_share'], 'after_a_point.recorded_share, adjusted at the press, keyed', 1)} of points beyond two sigma carry a recorded adjustment, and subgroup means on the characteristics adjusted at the press carry a within-coil autocorrelation of "
        f"{num(ac.loc[('2024, before the redesign', 'adjusted at the press'), 'lag_1_autocorrelation'], 'autocorrelation.lag_1_autocorrelation, 2024 adjusted', '{:.2f}')} against {num(ac.loc[('2024, before the redesign', 'not adjusted at the press'), 'lag_1_autocorrelation'], 'autocorrelation.lag_1_autocorrelation, 2024 not adjusted', '{:.2f}')} on the others (Section 6).</li>"
        f"<li><b>Die wear.</b> On {num(bs.interval_longer_than_the_80pct_count, 'burr_summary.interval_longer_than_the_80pct_count')} of {num(bs.dies_fitted, 'burr_summary.dies_fitted')} dies the stated sharpening interval is longer than the shot count at which burr reaches 80% of its limit, and "
        f"{num(rp.burr_nonconformances_past_the_interval, 'runs_past_the_interval.burr_nonconformances_past_the_interval')} of the {num(rp.burr_nonconformances_with_shots_known, 'runs_past_the_interval.burr_nonconformances_with_shots_known')} burr nonconformances of 2024 fell on runs that carried the die past its stated interval (Section 7).</li>"
        f"<li><b>Recording.</b> {pct(oh.loc['all routine subgroups', 'stamped_share'], 'on_the_hour.stamped_share, all', 1)} of routine checks are stamped within five minutes of the hour; the night shift records {pct(pc.loc[('all presses', 'nights'), 'recorded_share'], 'planned_checks.recorded_share, all presses nights')} of planned checks against "
        f"{pct(pc.loc[('all presses', 'days'), 'recorded_share'], 'planned_checks.recorded_share, all presses days')} on days (Section 8).</li>"
        "</ol>")

    # -- 2. Charts and limits ------------------------------------------------
    body.append(section("limits", "2. Charts and limits"))
    body.append(f"<p>The software's rolling limits follow the process, and the printed limits on the paper presses sit off the process centre. On other punched and dimensional characteristics, where neither coil shifts nor wear dominate, the rolling limits flag "
                f"{pct(ref.share_of_computed_also_set, 'signal_comparison.share_of_computed_also_set, rolling: other punched and dimensional')} of what baseline limits flag. The gap on formed characteristics is not a case for fixed within-subgroup limits there; Sections 3 and 7 give what those characteristics carry between coils and with wear.</p>")
    body.append(figure(fc["signals"], "Each pair of columns is one class of characteristic. The dark column is how often the shop's own limits signalled in 2024, the light column how often limits computed from a stable baseline after each sharpening signal on the same subgroups. "
                                      "The rolling limits on the software presses signal far less often than fixed limits on formed characteristics and hole diameters, and the printed limits on the paper presses signal more often."))
    body.append(figure(fc["paper"], "The left panel sets the signal rate under the printed limits beside the rate freshly computed limits give on the same subgroups, with the rate of a stable process on correct limits as a dashed line. The right panel is the share of printed-limit signals with an action recorded, with its 95% interval. "
                                    "Most of the signalling on formed characteristics and hole diameters is there under any within-subgroup limits, and the printed limits add to it."))
    body.append(f"<p>On the software presses every one of the {num(ack.alarms, 'software_acknowledgements.alarms')} alarms of 2024 was acknowledged with a text; {num(ack.text_of_one_word, 'software_acknowledgements.text_of_one_word')} of the texts are one word and "
                f"{num(ack.adjustment_recorded, 'software_acknowledgements.adjustment_recorded')} alarms carry a recorded adjustment. Limits on the paper charts were set at the most recent rebuild on {num(age.dies_with_every_limit_set_at_the_most_recent_rebuild, 'paper_limit_age.dies_with_every_limit_set_at_the_most_recent_rebuild')} of "
                f"{num(age.dies, 'paper_limit_age.dies')} dies, and on the other {num(age.dies - age.dies_with_every_limit_set_at_the_most_recent_rebuild, 'paper_limit_age.dies less dies_with_every_limit_set_at_the_most_recent_rebuild')} the record does not reach back to the date.</p>")
    body.append(figure(fc["age"], "Each point is one die on the paper presses at 31 December 2024. The horizontal position is how long its printed limits had been in force and the vertical position how many times the die had been sharpened since; the open points are dies whose limits predate the die log in the record. "
                                  "Limits are set at the rebuild and not recomputed at a sharpening, so the count rises with the months."))

    # -- 3. Capability -------------------------------------------------------
    body.append(section("capability", "3. Subgrouping and capability"))
    body.append(f"<p>The Ppk filed at PPAP is {num(cs.loc['formed', 'filed_less_production_ppk'], 'capability_summary.filed_less_production_ppk, formed', '{:.2f}')} above the production Ppk on critical formed characteristics, and at least 0.40 above it on "
                f"{num(cs.loc['formed', 'studies_filed_at_least_0_40_above'], 'capability_summary.studies_filed_at_least_0_40_above, formed')} of {num(cs.loc['formed', 'studies'], 'capability_summary.studies, formed')} studies. On punched characteristics the two agree within 0.25 on "
                f"{num(cs.loc['punched', 'studies_within_0_25'], 'capability_summary.studies_within_0_25, punched')} of {num(cs.loc['punched', 'studies'], 'capability_summary.studies, punched')}; the others are hole diameters, which Section 7 takes up.</p>")
    body.append(figure(fk["capability"], "Each point is one PPAP study: the Ppk filed from 300 consecutive pieces on the CMM against the Ppk of the production record on the check fixture over the months after it, with the 95% interval of the production figure as a light bar. "
                                         "Points on the diagonal are studies where the two agree; the dashed line is 1.33. Punched characteristics sit near the diagonal and formed characteristics well below it."))
    body.append(figure(fk["components"], "Each bar divides the overall variance of a class of characteristic into three parts, as the median across studies. On formed characteristics more than half lies between coils; on punched characteristics nearly all is within the subgroup."))
    body.append(f"<p>A coil's level on a formed height follows the thickness and hardness on its certificate: the fit leaves {pct(coil.certificate_residual_sd_share_of_tolerance_median, 'coil_regression_summary.certificate_residual_sd_share_of_tolerance_median', 1)} of the tolerance about it against "
                f"{pct(coil.sd_of_coil_means_share_of_tolerance_median, 'coil_regression_summary.sd_of_coil_means_share_of_tolerance_median', 1)} between coil means (Appendix 2).</p>")
    b0 = cmm.loc["all fixtures, before the redesign"]
    body.append(f"<p>The check fixtures read {num(b0.mean_difference_mm, 'fixture_against_cmm.mean_difference_mm, to 31 December 2024', '{:.3f}')} mm higher than the CMM ({num(b0.low, 'fixture_against_cmm.low', '{:.3f}')} to {num(b0.high, 'fixture_against_cmm.high', '{:.3f}')}) on "
                f"{num(b0.matched_first_pieces, 'fixture_against_cmm.matched_first_pieces, to 31 December 2024')} matched first pieces on {num(b0.fixtures, 'fixture_against_cmm.fixtures, to 31 December 2024')} fixtures.</p>")
    body.append(figure(fk["cmm"], "Each point is one first-piece subgroup to 31 December 2024 measured on both the check fixture and the CMM, as the fixture reading less the CMM reading; the marker beside the points is the mean with its 95% interval, and the line is zero. "
                                  "The check fixture reads to 0.01 mm, so the differences fall on a grid."))

    # -- 4. Risk window and sorting ------------------------------------------
    body.append(section("risk", "4. Risk window and sorting"))
    y24 = ss.loc[2024]
    body.append(f"<p>The {num(y24.sorting_events, 'sorting_summary.sorting_events, 2024')} sorting events of 2024 covered {num(y24.quantity_sorted, 'sorting_summary.quantity_sorted, 2024')} parts at {num(y24.hours_booked_or_estimated, 'sorting_summary.hours_booked_or_estimated, 2024')} hours and "
                f"${num(y24.cost_booked_or_estimated, 'sorting_summary.cost_booked_or_estimated, 2024')}, of which {pct(y24.share_of_hours_booked, 'sorting_summary.share_of_hours_booked, 2024')} of the hours were booked to the sorting labor code. At run speed the ceiling between checks is "
                f"{num(rw['fewest_parts_between_checks'].min(), 'risk_window.fewest_parts_between_checks, lowest')} to {num(rw['most_parts_between_checks'].max(), 'risk_window.most_parts_between_checks, highest')} parts.</p>")
    body.append(figure(fr["risk"], "Each bar is one press: the range across its parts of the parts that can pass between two routine checks at run speed, with the median part marked. The diamond is the median part at the stroke rate the press realises. "
                                   "Between checks the high-speed presses pass several times what the medium presses pass, and at the realised rate about half the ceiling."))
    flt = sb.loc["sorted from a logged die-protection fault"]; inh = sb.loc["sorted back to the check before, in-house"]
    body.append(f"<p>Where a fault in the die-protection log bounds the event the shop sorts from the fault: {num(flt.events, 'sorting_by_basis.events, from a logged fault')} events in 2023 and 2024, a median {num(flt.quantity_sorted_median, 'sorting_by_basis.quantity_sorted_median, from a logged fault')} parts, "
                f"{pct(flt.rejected_share, 'sorting_by_basis.rejected_share, from a logged fault')} rejected. Where none does it sorts back to the check before: {num(inh.events, 'sorting_by_basis.events, back to the check in-house')} in-house events at a median "
                f"{num(inh.quantity_sorted_median, 'sorting_by_basis.quantity_sorted_median, back to the check in-house')} parts, {pct(inh.rejected_share, 'sorting_by_basis.rejected_share, back to the check in-house')} rejected.</p>")
    body.append(figure(fr["exposure"], "Each point is one sorting event found at the press in 2023 and 2024: the parts made since the check before the finding, estimated, against the quantity the shop sorted, both on log scales. Points on the line are sorting events covering everything made since the check; points below it are bounded by a fault in the die-protection log. "
                                       "Parts since the check before are estimated at the press's realised rate, and a press that stood for part of the interval made fewer. Where no fault bounds the event the shop sorts back to the check, and the largest of those go to the sorting service."))
    body.append(figure(fr["years"], "The left panel counts sorting events by year and by the basis of the sorting; the right panel gives their cost as booked, with the estimate for sorting booked to the run. Totals are above the columns. "
                                    "Sorting events back to the check before carry the largest share of the cost in both years."))

    # -- 5. Measurement ------------------------------------------------------
    body.append(section("measurement", "5. Measurement systems"))
    g1, g2, p1, p2 = grr.loc[("F-20417", "redesign")], grr.loc[("F-31102", "redesign")], grr.loc[("F-20417", "PPAP")], grr.loc[("F-31102", "PPAP")]
    body.append(f"<p>The two check fixtures reworked since their PPAP study stood above 30% of tolerance at the assessment study (ndc {num(g1.ndc, 'gauge_rr.ndc, F-20417 assessment study')} and {num(g2.ndc, 'gauge_rr.ndc, F-31102 assessment study')}), with "
                f"{pct(g1.reproducibility_share_of_grr, 'gauge_rr.reproducibility_share_of_grr, F-20417 assessment study')} and {pct(g2.reproducibility_share_of_grr, 'gauge_rr.reproducibility_share_of_grr, F-31102 assessment study')} of their gauge variance between operators (Appendix 4). "
                f"Measurement was {pct(ms.loc['F-20417', 'measurement_share_of_variance'], 'measurement_share.measurement_share_of_variance, F-20417', 1)} of the apparent variation on F-20417's formed height from March 2024 and {pct(ms.loc['F-31102', 'measurement_share_of_variance'], 'measurement_share.measurement_share_of_variance, F-31102', 1)} on F-31102 from June 2024.</p>")
    body.append(figure(fm["grr"], f"Each column is one gauge R&amp;R study on a check fixture, with %GRR of tolerance and ndc at its top. The dashed lines are at 10% and 30%. The two reworked fixtures stood at {pct(g1.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-20417 assessment study', 1)} and {pct(g2.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-31102 assessment study', 1)} "
                                  f"against {pct(p1.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-20417 PPAP', 1)} and {pct(p2.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-31102 PPAP', 1)} at PPAP; F-10823, with no rework, stood at {pct(grr.loc[('F-10823', 'redesign'), 'pct_tolerance'] / 100, 'gauge_rr.pct_tolerance, F-10823 assessment study', 1)}."))
    b1 = att.loc["at the redesign"]
    body.append(figure(fm["burr"], f"Each point is one operator's share of the {num(b1.parts, 'attribute_agreement.parts')} parts rejected over {num(b1.trials, 'attribute_agreement.trials')} trials against the limit samples, and the vertical line is the share the burr gauge rejects. Operators are in order of their reject rate. "
                                   f"Agreement with the gauge was {pct(b1.against_reference, 'attribute_agreement.against_reference, assessment study')} (kappa {num(b1.fleiss_kappa, 'attribute_agreement.fleiss_kappa, assessment study', '{:.2f}')}); two operators reject more than the gauge and four fewer."))
    op = m["attribute_by_operator"]; op = op[op["study"] == "at the redesign"].sort_values("reject_rate")
    body.append(show(op, {"operator": "Operator", "reject_rate": "Parts rejected", "reference_reject_rate": "Rejected by the burr gauge", "against_reference": "Agreement with the burr gauge"}, {"reject_rate": P0, "reference_reject_rate": P0, "against_reference": P0}))
    body.append(f"<p>Keyed readings end in 0 or 5 at {num(em.loc['keyed', 'times_the_uniform_expectation'], 'entry_methods.times_the_uniform_expectation, keyed', '{:.2f}')} times the rate of an unpreferred digit and paper transcriptions at {num(em.loc['paper transcription', 'times_the_uniform_expectation'], 'entry_methods.times_the_uniform_expectation, paper', '{:.2f}')}; "
                f"{pct(em.loc['keyed', 'set_aside_share'], 'entry_methods.set_aside_share, keyed', 2)} of keyed readings cannot be a measurement of the part (more than five tolerance widths from nominal) and are set aside from every figure in this report. The record was examined for a pile-up of readings at the specification limits and shows none that can be separated from the shape of the distribution (Appendix 4). "
                f"In 2024, {pct(gs.share_out_of_service, 'gauge_status.share_out_of_service', 1)} of subgroups carry a gauge that was out of service that day and {pct(gs.share_past_due, 'gauge_status.share_past_due', 1)} a gauge past its calibration due date.</p>")

    # -- 6. Adjustment -------------------------------------------------------
    body.append(section("adjustment", "6. Adjustment"))
    r_rec, r_un = rt.loc[("keyed", adjustment.GROUPS[0])], rt.loc[("keyed", adjustment.GROUPS[1])]
    body.append(f"<p>On keyed entry {pct(ap.loc[(True, 'keyed'), 'recorded_share'], 'after_a_point.recorded_share, keyed', 1)} of points beyond two sigma carry a recorded adjustment, and on paper {pct(ap.loc[(True, 'paper transcription'), 'recorded_share'], 'after_a_point.recorded_share, paper', 1)} of points beyond the printed limit. "
                f"Points with none recorded keep {num(r_un.next_as_share_of_position, 'return_toward_centre.next_as_share_of_position, keyed, none recorded', '{:.2f}')} of their position at the next subgroup against {num(r_rec.next_as_share_of_position, 'return_toward_centre.next_as_share_of_position, keyed, adjustment recorded', '{:.2f}')} where an adjustment is recorded, "
                f"so some were adjusted and the record cannot say how many.</p>")
    body.append(figure(fa["return"], "Each column is the position of the next subgroup as a share of the position of the point, for one group of points on keyed entry in 2024, with a 95% interval from a bootstrap over characteristics. A value of 1 is no return toward the centre line and 0 is a return to it. "
                                     "Points beyond two sigma on characteristics not adjusted at the press return as far as the recorded adjustments do, which is why the record cannot separate adjusted from unadjusted points among those with nothing recorded."))
    pl = rt.loc[("paper transcription", adjustment.GROUPS[1])]; v0 = av.loc["no adjustment recorded and no point beyond two sigma"]
    body.append(f"<p>On the paper presses a point beyond the printed limit averages {num(pl.mean_position_in_sigma, 'return_toward_centre.mean_position_in_sigma, paper, none recorded', '{:.1f}')} chart sigma and the next subgroup keeps {num(pl.next_as_share_of_position, 'return_toward_centre.next_as_share_of_position, paper, none recorded', '{:.2f}')} of its position: "
                f"most of those points are a coil at its own level (Section 2), not a disturbance to correct. The characteristics adjusted at the press carry {pct(v0.added_variance_median, 'variance.added_variance_median, no adjustment and no point beyond two sigma', 1)} more variance over all runs than in their runs with no adjustment and no point beyond two sigma "
                f"({pct(v0.low, 'variance.low', 1)} to {pct(v0.high, 'variance.high', 1)}; {num(v0.characteristics_with_more_variance, 'variance.characteristics_with_more_variance')} of {num(v0.characteristics, 'variance.characteristics')} characteristics higher).</p>")
    a_adj, a_not = ac.loc[("2024, before the redesign", "adjusted at the press")], ac.loc[("2024, before the redesign", "not adjusted at the press")]
    body.append(figure(fa["autocorrelation"], f"Each point is the lag-1 autocorrelation of subgroup means within a run and coil in 2024 with its 95% interval; the dashed line is zero. It is {num(a_adj.lag_1_autocorrelation, 'autocorrelation.lag_1_autocorrelation, 2024 adjusted', '{:.2f}')} "
                                              f"({num(a_adj.low, 'autocorrelation.low, 2024 adjusted', '{:.2f}')} to {num(a_adj.high, 'autocorrelation.high, 2024 adjusted', '{:.2f}')}) on the characteristics adjusted at the press against {num(a_not.lag_1_autocorrelation, 'autocorrelation.lag_1_autocorrelation, 2024 not adjusted', '{:.2f}')} "
                                              f"({num(a_not.low, 'autocorrelation.low, 2024 not adjusted', '{:.2f}')} to {num(a_not.high, 'autocorrelation.high, 2024 not adjusted', '{:.2f}')}) on the others, and the intervals do not overlap."))

    # -- 7. Die wear ---------------------------------------------------------
    body.append(section("wear", "7. Die wear"))
    body.append(f"<p>No die's stated sharpening interval reaches the shot count at which its burr reaches the limit ({num(bs.interval_longer_than_the_count_at_the_limit, 'burr_summary.interval_longer_than_the_count_at_the_limit')} of {num(bs.dies_fitted, 'burr_summary.dies_fitted')}), but sharpenings are logged a median "
                f"{num(il.logged_over_stated_median, 'intervals_as_logged.logged_over_stated_median', '{:.2f}')} times the stated interval and {pct(il.share_longer_than_stated, 'intervals_as_logged.share_longer_than_stated')} of the {num(il.intervals_with_shot_counts, 'intervals_as_logged.intervals_with_shot_counts')} intervals ending in 2024 run longer. Runs end past the count and the sharpening is logged after. "
                f"{num(bo.with_a_subgroup_mean_over_the_limit, 'burr_over_the_limit_by_interval.with_a_subgroup_mean_over_the_limit')} of the {num(bo.with_a_burr_gauge_subgroup, 'burr_over_the_limit_by_interval.with_a_burr_gauge_subgroup')} intervals ending in 2024 with burr gauge readings carry a reading over the limit before the sharpening. "
                f"Critical hole diameters grow {num(hs.slope_by_die_lowest, 'hole_diameter_summary.slope_by_die_lowest', '{:.4f}')} to {num(hs.slope_by_die_highest, 'hole_diameter_summary.slope_by_die_highest', '{:.4f}')} mm per 100,000 shots by die, at the same rate in every interval (Appendix 6).</p>")
    body.append(figure(fw["count"], f"Each point is a die: the shot count at which its burr reaches 80% of the limit against its stated sharpening interval on the left and its median interval as run on the right. Dies below the dashed line are sharpened later than their burr allows; the dies of three parts on PR-03, PR-06 and PR-09 are circled. "
                                    f"On {num(bs.interval_longer_than_the_80pct_count, 'burr_summary.interval_longer_than_the_80pct_count')} of {num(bs.dies_fitted, 'burr_summary.dies_fitted')} dies the stated sharpening interval is longer than the shot count at which burr reaches 80% of its limit; on the interval as actually run it is {num(logged_longer, 'burr_by_die: logged_interval_median over shots_at_80pct_of_limit')} of {num(logged_n, 'burr_by_die: dies with a logged interval')}."))
    body.append(figure(fw["position"], f"Each point is a nonconformance opened in 2024, placed at the die's shots since sharpening at the end of its run as a multiple of the stated sharpening interval, by defect code and where it was detected; the histogram beneath is the {num(rp.runs_with_shots_known, 'runs_past_the_interval.runs_with_shots_known')} runs of 2024 with shots known, and the dashed line is the stated interval. "
                                       f"{num(rp.burr_nonconformances_past_the_interval, 'runs_past_the_interval.burr_nonconformances_past_the_interval')} of the {num(rp.burr_nonconformances_with_shots_known, 'runs_past_the_interval.burr_nonconformances_with_shots_known')} burr nonconformances lie past the stated interval "
                                       f"(median {num(rp.position_median_lowest_by_detection, 'runs_past_the_interval.position_median_lowest_by_detection', '{:.1f}')} to {num(rp.position_median_highest_by_detection, 'runs_past_the_interval.position_median_highest_by_detection', '{:.1f}')} times it) against {pct(rp.share_of_runs_past, 'runs_past_the_interval.share_of_runs_past')} of all runs."))

    # -- 8. Recording --------------------------------------------------------
    body.append(section("recording", "8. Recording"))
    e0 = ea.loc["software presses, 2024, keyed"]
    body.append(f"<p>{pct(oh.loc['keyed', 'stamped_share'], 'on_the_hour.stamped_share, keyed', 1)} of keyed routine subgroups and {pct(oh.loc['paper transcription', 'stamped_share'], 'on_the_hour.stamped_share, paper', 1)} of the times noted on paper charts fall within five minutes of the hour. "
                f"Keyed entries are stamped a median {num(e0.minutes_to_entry_median, 'entry_after_the_parts.minutes_to_entry_median, keyed 2024', '{:.1f}')} minutes after the parts; on the time of the parts the figure is {pct(oh.loc['all routine subgroups', 'parts_time_share'], 'on_the_hour.parts_time_share, all', 1)}. "
                f"{pct(e0.share, 'entry_after_the_parts.share, keyed 2024', 1)} of keyed entries are made more than 20 minutes after the parts (Appendix 7).</p>")
    body.append(figure(frec["minute"], "Each bar is the share of the keyed routine subgroups of 2024 entered at that minute of the hour; the dashed line is the share each minute would hold under uniform timing. Entries pile up in the first minutes of the hour."))
    body.append(f"<p>The 06:00 planned time, the first of the day shift, is recorded on {pct(six.recorded_share, 'planned_checks_by_hour.recorded_share, all presses 06:00')} of occasions against {pct(rest.min(), 'planned_checks_by_hour.recorded_share, lowest other day hour')} to {pct(rest.max(), 'planned_checks_by_hour.recorded_share, highest other day hour')} for every other day-shift hour. "
                f"{num(sr.loc['under two hours', 'with_no_routine_check'], 'short_runs.with_no_routine_check, under two hours')} of the {num(sr.loc['under two hours', 'runs'], 'short_runs.runs, under two hours')} runs under two hours carry no routine check.</p>")
    body.append(figure(frec["by_hour"], f"Each point is the share of the planned checks of 2024 at that hour with a routine check recorded, with its 95% interval, for the high-speed presses (paper) and the medium presses (software); the dashed line is the shift change at 14:30. "
                                        f"On nights the high-speed presses record {pct(pc.loc[('high_speed', 'nights'), 'recorded_share'], 'planned_checks.recorded_share, high-speed nights', 1)} and the medium presses {pct(pc.loc[('medium', 'nights'), 'recorded_share'], 'planned_checks.recorded_share, medium nights', 1)}."))

    # -- 9. Actions ----------------------------------------------------------
    body.append(section("actions", "9. Actions"))
    actions = pd.DataFrame([
        ("2", "Limits follow the process on the software presses; printed limits are off centre on the paper presses", "Compute limits from a stable baseline after each sharpening and hold them until the next; stop rolling recalculation; move the paper presses to the software", "Quality engineer"),
        ("3", f"Formed characteristics carry {cs.loc['formed', 'share_between_coils'] * 100:.0f}% of their variance between coils", "Chart formed characteristics on limits that carry coil-to-coil variation; record a coil-change subgroup and centre on it when its mean is outside one sigma of target; report production Ppk beside the PPAP figure", "Quality engineer"),
        ("4", "Sorting events run back to the check before where no fault bounds them", "Set check frequency by characteristic class from the parts between checks; keep the press monitor's per-stroke record so a sorting event can be bounded at the stroke", "Quality manager"),
        ("5", f"Two reworked check fixtures at {g1.pct_tolerance:.0f}% and {g2.pct_tolerance:.0f}% of tolerance; burr check at kappa {b1.fleiss_kappa:.2f}; keyed readings prefer 0 and 5", "Rebuild and re-study the two fixtures; put check fixtures on the annual gauge study schedule; replace the burr limit samples and qualify operators against the burr gauge; connect gauges to the terminals", "Quality engineer"),
        ("6", f"Adjustment at the operator's discretion; {v0.added_variance_median * 100:.0f}% more variance on the adjusted characteristics", "Put a written reaction plan on every chart: a die adjustment follows a run-rule signal or a coil-change subgroup, and is recorded", "Quality manager"),
        ("7", "Sharpening is logged after the stated interval has passed", "Set each die's sharpening interval from its burr regression at 80% of the burr limit and pull the die at the count", "Die room"),
        ("8", "Night shift and first-of-shift checks under-recorded; entries after the parts", "Post readings from the gauge at the time of the check; review planned checks recorded by shift each week", "Quality manager"),
    ], columns=["Section", "Finding", "Action", "Owner"])
    body.append(S.table(actions))

    # -- Method and data -----------------------------------------------------
    body.append(section("method", "Method and data note"))
    body.append("<p class='glossary'>Control charts and capability indices follow AIAG SPC, 2nd edition: within-subgroup sigma is the pooled standard deviation across subgroups and overall sigma the standard deviation of all readings; Cpk intervals by the AIAG approximation and Ppk intervals by bootstrap. "
                "Stability is by Western Electric rules 1 to 4. Average run length is by the Markov chain method. Variance components are from a nested random-effects model (coil within die, subgroup within coil) fitted by REML. The coil regression is ordinary least squares on the coil's certificate values, with receiving values beside. "
                "Gauge R&amp;R follows AIAG MSA, 4th edition, ANOVA method, with %tolerance at 6 sigma and ndc; attribute agreement is with 95% intervals and Fleiss' kappa. Autocorrelation of subgroup means is the lag-1 coefficient of the means less their run-and-coil segment mean, pooled over segments of at least 6 subgroups. "
                "Bounded characteristics (burr, flatness) are on the readings as recorded by the percentile method, with the Box-Cox result beside. Proportions carry Wilson intervals. Readings are used as recorded and none is corrected; a keyed reading that cannot be a measurement of the part (further than five tolerance widths from nominal) is set aside, with the count stated. "
                "Limits as set are the limits the software computed or the paper form carried at each entry; limits as computed are from a stable 25-subgroup baseline after the most recent sharpening. Press monitor times are aligned to the SPC terminal clock on run start. "
                "Data: the SPC software and transcribed paper charts, press monitor fault events, ERP, QMS, die maintenance log, calibration system, accounting and the gauge study worksheets, as exported; record boundaries and coverage are in the appendix.</p>")

    n_body_figures = FIGURE[0]

    # -- Appendix ------------------------------------------------------------
    SECTION[0] = "Appendix"
    ax = ['<h2 id="appendix">Appendix</h2>']
    ax.append("<h3>Appendix 1. Charts and limits (Section 2)</h3>")
    ax.append(show(c["chart_audit"], {"limits_as_set_method": "Limits as set", "press_group": "Presses", "characteristics": "Characteristics", "critical_characteristics": "Critical", "subgroups": "Subgroups, 2024", "subgroups_with_a_reading_set_aside": "With a reading set aside",
                                      "subgroups_used_to_set": "Subgroups used to set", "signals_rule_1": "Rule 1 signals", "signals_any_rule": "Signals, any rule", "signals_with_action_recorded": "With an action recorded"}, {"subgroups": F0, "subgroups_with_a_reading_set_aside": F0, "signals_rule_1": F0, "signals_any_rule": F0, "signals_with_action_recorded": F0, "subgroups_used_to_set": F0}))
    ax.append(show(c["signal_comparison"], {"limits_as_set_method": "Limits as set", "characteristic_class": "Class", "characteristics": "Characteristics", "subgroups": "Subgroups compared", "signals_as_computed": "Signals as computed", "signals_as_set": "Signals as set", "signals_by_both": "By both",
                                            "share_of_computed_also_set": "Share of computed also set", "share_low": "Low", "share_high": "High", "rate_as_set_per_100": "As set per 100", "rate_as_computed_per_100": "As computed per 100"},
                   {"subgroups": F0, "signals_as_computed": F0, "signals_as_set": F0, "signals_by_both": F0, "share_of_computed_also_set": P1, "share_low": P1, "share_high": P1, "rate_as_set_per_100": lambda v: f"{v:.1f}", "rate_as_computed_per_100": lambda v: f"{v:.1f}"}))
    ax.append(show(c["baseline_coverage"], {"baseline_basis": "Baseline after the sharpening", "intervals": "Intervals", "characteristics": "Characteristics", "usable_subgroups": "Usable subgroups"}, {"intervals": F0, "usable_subgroups": F0}))
    rl = c["run_lengths"][c["run_lengths"]["in_report"]]
    ax.append(show(rl, {"limits_as_set_method": "Presses by limits as set", "characteristic_class": "Class", "limits": "Limits", "arl_in_control": "ARL in control", "arl_shift_1_sigma": "ARL, 1 sigma shift", "arl_shift_1_5_sigma": "ARL, 1.5 sigma shift"},
                   {"arl_in_control": lambda v: f"{v:.1f}", "arl_shift_1_sigma": F2, "arl_shift_1_5_sigma": F2}))
    ax.append(figure(fc["run_lengths"], "Columns give the average number of subgroups to a rule-1 signal, on a log scale. The three groups are the process in control and after a sustained shift of 1 and 1.5 within-subgroup sigma away from the printed centre. The printed limits signal sooner than computed limits in every case, including with nothing changed."))
    ax.append("<div class='caption'>Coverage: subgroups of 2024 with limits in force; subgroups before a die's first logged sharpening carry no computed limits. Shifts in the run length table are in units of the within-subgroup sigma of the mean; the spread of means between subgroups is in the model.</div>")

    ax.append("<h3>Appendix 2. Subgrouping and capability (Section 3)</h3>")
    ax.append(show(k["capability_summary"], {"characteristic_class": "Class", "studies": "Studies", "characteristics": "Characteristics", "subgroups": "Subgroups", "readings": "Readings", "subgroups_set_aside": "Subgroups set aside", "filed_ppk": "Ppk filed", "cpk": "Cpk", "cpk_low": "Low", "cpk_high": "High", "ppk": "Ppk",
                                             "ppk_low": "Ppk low", "ppk_high": "Ppk high"},
                   {"subgroups": F0, "readings": F0, "filed_ppk": F2, "cpk": F2, "cpk_low": F2, "cpk_high": F2, "ppk": F2, "ppk_low": F2, "ppk_high": F2}))
    ax.append(show(k["capability_summary"], {"characteristic_class": "Variance components by class", "share_between_coils": "Between coils", "share_between_coils_low": "Low", "share_between_coils_high": "High", "share_between_subgroups_within_coil": "Between subgroups within coil", "share_within_subgroup": "Within subgroup",
                                             "between_over_within_variance": "Between over within variance", "studies_filed_at_least_0_40_above": "Studies filed at least 0.40 above", "studies_within_0_25": "Studies within 0.25"},
                   {"share_between_coils": P0, "share_between_coils_low": P0, "share_between_coils_high": P0, "share_between_subgroups_within_coil": P0, "share_within_subgroup": P0, "between_over_within_variance": F2}))
    ax.append(show(k["punched_by_type"], {"characteristic_type": "Punched characteristic", "studies": "Studies", "filed_ppk": "Ppk filed", "production_ppk": "Production Ppk", "production_cpk": "Production Cpk", "filed_at_least_0_40_above": "Filed at least 0.40 above", "within_0_25": "Within 0.25"},
                   {"filed_ppk": F2, "production_ppk": F2, "production_cpk": F2}))
    ax.append(show(k["fixture_against_cmm"][k["fixture_against_cmm"]["group"] == "all fixtures, before the redesign"].assign(group="all fixtures, to 31 December 2024"), {"group": "Matched first pieces", "matched_first_pieces": "Parts", "fixtures": "Fixtures", "mean_difference_mm": "Fixture less CMM, mm", "low": "Low", "high": "High", "sd_mm": "SD, mm", "p_value": "p"}, {"mean_difference_mm": F3, "low": F3, "high": F3, "sd_mm": F3, "p_value": lambda v: "under 0.001" if v < 0.001 else f"{v:.3f}"}))
    ax.append(figure(fk["coil"], f"The left panel is one characteristic over one study window: each point is a coil's mean formed height against the thickness on its certificate, with the fitted line and a band of two residual standard deviations. "
                                   f"The right panel gives, for all {num(coil.study_windows, 'coil_regression_summary.study_windows')} windows, the spread of coil means and the spread left about the fit, as a share of the tolerance. Thickness and hardness from the certificate place a coil's level to within a few percent of the tolerance."))
    ax.append(show(k["bounded_summary"], {"characteristic_type": "Bounded characteristic", "characteristics": "Characteristics", "readings": "Readings", "normal_fit_rejected": "Normal fit rejected (Anderson-Darling)", "box_cox_fit_rejected": "Rejected after Box-Cox", "box_cox_lambda_median": "Box-Cox lambda", "ppu_percentile_median": "Ppu, percentile",
                                          "ppu_normal_median": "Ppu, normal", "ppu_box_cox_median": "Ppu, Box-Cox"}, {"readings": F0, "box_cox_lambda_median": F2, "ppu_percentile_median": F2, "ppu_normal_median": F2, "ppu_box_cox_median": F2}))
    ax.append(figure(fk["bounded"], "Columns give the median upper capability index on burr height and flatness by three methods. The percentile method on the readings as recorded is the report's figure; the normal fit and Box-Cox are shown beside it."))
    ax.append("<div class='caption'>Coverage: every critical characteristic with a PPAP study in the record, on the production record of the twelve months after the study or to 31 December 2024. Capability intervals in the table are the bootstrap interval of the median over studies.</div>")

    ax.append("<h3>Appendix 3. Risk window and sorting (Section 4)</h3>")
    ax.append(show(rw, {"press_id": "Press", "parts": "Parts", "runs": "Runs, 2024", "strokes_per_minute": "Strokes a minute, median", "plan_frequency_minutes": "Check frequency, minutes", "fewest_parts_between_checks": "Fewest parts between checks", "median_parts_between_checks": "Median", "most_parts_between_checks": "Most",
                        "realised_share_of_run_speed": "Realised share of run speed", "median_parts_between_checks_at_the_realised_rate": "Median at the realised rate"},
                   {"strokes_per_minute": F0, "plan_frequency_minutes": F0, "fewest_parts_between_checks": F0, "median_parts_between_checks": F0, "most_parts_between_checks": F0, "realised_share_of_run_speed": F2, "median_parts_between_checks_at_the_realised_rate": F0}))
    ax.append(show(r["sorting_by_basis"], {"sort_basis": "Basis of the sorting, found at the press, 2023 and 2024", "events": "Events", "quantity_sorted_median": "Quantity sorted, median", "quantity_sorted_max": "Largest", "rejected_share": "Rejected share", "parts_since_check_before_at_realised_rate_median": "Parts since the check before (estimated), median",
                                           "cost_booked_or_estimated": "Cost booked or estimated, $"}, {"quantity_sorted_median": F0, "quantity_sorted_max": F0, "rejected_share": P0, "parts_since_check_before_at_realised_rate_median": F0, "cost_booked_or_estimated": F0}))
    ax.append(show(r["sorting_summary"][r["sorting_summary"]["year"] <= 2024], {"year": "Year", "sorting_events": "Sorting events", "traced_to_a_die_event_between_two_checks": "Traced to a die event between two checks", "followed_a_customer_complaint": "Followed a customer complaint", "quantity_sorted": "Quantity sorted", "hours_booked": "Hours booked",
                                          "hours_estimated_from_run_hours": "Hours estimated from run hours", "cost_booked": "Cost booked, $", "cost_booked_or_estimated": "Cost booked or estimated, $"}, {"year": lambda v: f"{int(v)}", "sorting_events": F0, "traced_to_a_die_event_between_two_checks": F0, "followed_a_customer_complaint": F0, "quantity_sorted": F0, "hours_booked": lambda v: f"{v:.1f}", "hours_estimated_from_run_hours": lambda v: f"{v:.1f}", "cost_booked": F0, "cost_booked_or_estimated": F0}))
    ax.append(figure(fr["rejected"], "Rejected share of the quantity sorted by the basis of the sorting, 2023 and 2024. Shares are on pieces pooled over events."))
    ax.append("<div class='caption'>The realised stroke rate is strokes over working clock time (06:00 to 23:00 on days the press recorded a check), per press over all 2024 runs. A fault bounds a sorting event when the nonconformance quantity is no more than the parts at run speed from the fault to the finding, with a quarter allowed; a fault logged within 10 minutes of the check before gives the same quantity on either basis and is its own row. "
              "Sorting hours estimated from run hours are the run's labor hours above standard where the sorting was not booked to the sorting labor code.</div>")

    ax.append("<h3>Appendix 4. Measurement systems (Section 5)</h3>")
    study_name = {"PPAP": "PPAP", "redesign": "assessment, January 2025"}
    gt = m["gauge_rr"][m["gauge_rr"]["study"].isin(study_name)].assign(study=lambda x: x["study"].map(study_name)).reset_index(drop=True)
    ax.append(show(gt, {"fixture": "Fixture", "study": "Study", "study_date": "Date", "tolerance_mm": "Tolerance, mm", "recorded_pct_tolerance": "%GRR as recorded", "pct_tolerance": "%GRR of tolerance", "pct_study_variation": "%Study variation", "ndc": "ndc", "repeatability_sd_mm": "Repeatability SD, mm",
                        "reproducibility_sd_mm": "Reproducibility SD, mm", "interaction_p": "Interaction p"}, {"study_date": lambda v: str(v)[:10], "tolerance_mm": F2, "recorded_pct_tolerance": lambda v: f"{v:.1f}", "pct_tolerance": lambda v: f"{v:.1f}", "pct_study_variation": lambda v: f"{v:.1f}", "repeatability_sd_mm": F4, "reproducibility_sd_mm": F4, "interaction_p": F3}))
    ax.append(figure(fm["split"], "Each bar is the gauge variance of one assessment study, split between repeatability and reproducibility between operators. On both reworked fixtures most of the gauge variance is between operators."))
    for key in sorted(m["anova_tables"]):
        if key[1] in study_name:
            ax.append(anova_block((key[0], study_name[key[1]]), m["anova_tables"][key]))
    ax.append(show(m["measurement_share"], {"fixture": "Fixture", "characteristic_id": "Characteristic", "period": "Period of 2024", "readings": "Readings", "production_sd_mm": "Production SD, mm", "gauge_sd_mm": "Gauge SD, mm", "measurement_share_of_variance": "Measurement share of variance", "measurement_share_whole_year": "All of 2024"},
                   {"readings": F0, "production_sd_mm": F4, "gauge_sd_mm": F4, "measurement_share_of_variance": P1, "measurement_share_whole_year": P1}))
    ax.append(show(m["attribute_agreement"][m["attribute_agreement"]["study"] == "at the redesign"].assign(study="assessment, January 2025"), {"study": "Burr check study", "calls": "Calls", "within_operator": "Within operator", "all_operators_agree": "All operators agree", "pairs_of_operators_agree": "Pairs of operators agree", "against_reference": "Against the burr gauge", "reference_low": "Low", "reference_high": "High", "fleiss_kappa": "Fleiss' kappa", "kappa_low": "Kappa low", "kappa_high": "Kappa high"},
                   {"within_operator": P0, "all_operators_agree": P0, "pairs_of_operators_agree": P0, "against_reference": P1, "reference_low": P1, "reference_high": P1, "fleiss_kappa": F2, "kappa_low": F2, "kappa_high": F2}))
    ax.append(show(m["entry_methods"][m["entry_methods"]["entry_method"] != "gauge-connected"], {"entry_method": "Entry method", "readings": "Readings, 2024", "ending_0_or_5": "Ending in 0 or 5", "times_the_uniform_expectation": "Times the uniform rate", "chi_square_last_digit": "Chi-square, last digit", "set_aside_by_the_plausibility_rule": "Set aside as mis-keyed", "at_or_one_step_inside_a_limit": "At or one step inside a limit",
                                        "one_or_two_steps_outside_a_limit": "One or two steps outside"}, {"readings": F0, "ending_0_or_5": F0, "times_the_uniform_expectation": F2, "chi_square_last_digit": F0, "set_aside_by_the_plausibility_rule": F0, "at_or_one_step_inside_a_limit": F0, "one_or_two_steps_outside_a_limit": F0}))
    ax.append(figure(fm["digit"], "Each panel gives the share of the readings of 2024 ending in each digit for one entry method, with the reading count in the panel title. The dashed line is the 10% each digit would hold if none were preferred. Keyed readings pile up on 0 and 5; paper transcriptions do not."))
    ax.append(figure(fm["limit"], "Each line counts one entry method's readings of 2024 by the number of reading steps from the nearer specification limit, negative inside and positive outside, on a log scale. The dashed line marks the limit. The counts fall through the limit on both lines with no step at it."))
    ax.append(show(m["reading_steps"], {"reading_step": "Reading step", "characteristics": "Characteristics"}, {"reading_step": lambda v: f"{v:g}"}))
    ax.append(f"<div class='caption'>The reading step of a characteristic is inferred from its own readings: the coarsest of 1, 0.5, 0.1, 0.05, 0.01, 0.005 and 0.001 that 99% of its readings sit on. The chi-square on the last digit is large on both entry methods because the distributions are narrow on their reading steps. Measurement share is on the months after each fixture's last rework. "
              f"Gauge status, 2024: {F0(gs.on_a_gauge_out_of_service)} of {F0(gs.subgroups)} subgroups on a gauge out of service that day, {F0(gs.on_a_gauge_past_due)} on a gauge past due; {F0(gs.gauges_recorded_as_lost)} gauge is recorded as lost, and no characteristic and no subgroup carries it.</div>")

    ax.append("<h3>Appendix 5. Adjustment (Section 6)</h3>")
    ax.append(show(a["return_toward_centre"], {"entry_method": "Entry", "points_group": "Points", "points": "Count", "characteristics": "Characteristics", "mean_position_in_sigma": "Mean position, sigma", "next_as_share_of_position": "Next subgroup as a share of the position", "low": "Low", "high": "High"},
                   {"points": F0, "mean_position_in_sigma": F2, "next_as_share_of_position": F2, "low": F2, "high": F2}))
    ax.append(show(a["autocorrelation"][a["autocorrelation"]["period"].str.startswith("2024")], {"characteristics": "Characteristics, 2024", "lag_1_autocorrelation": "Lag-1 autocorrelation", "low": "Low", "high": "High", "segments": "Segments", "characteristics_n": "Characteristics, count"}, {"lag_1_autocorrelation": F3, "low": F3, "high": F3, "segments": F0}))
    k1, k2 = fa["runs_shown"]
    ax.append(figure(fa["run"], f"The left panel is the run with the most recorded adjustments among single-coil runs of a formed characteristic on a software press in 2024 ({k1['characteristic_id']}, run {k1['run_id']}), and the right panel the run with the most among all such runs ({k2['characteristic_id']}, run {k2['run_id']}); each shows the subgroup means, the software's limits in force at each entry and the recorded adjustments circled. "
                                f"The left shows {'the adjustment at subgroup' if len(fa['overshoot_at']) == 1 else 'the adjustments at subgroups'} {' and '.join(str(q) for q in fa['overshoot_at'])} followed by a mean on the other side of the centre line, limits carried in from the previous run at a higher level, and limits widened beyond the scale by a mis-keyed reading after subgroup {fa['limits_widen_after']}. "
                                "The right shows a coil at its own level with adjustments recorded against it and the limits climbing to absorb it."))
    ax.append(show(a["variance"], {"comparison_runs": "Comparison runs", "characteristics": "Characteristics", "added_variance_median": "Added variance, median", "low": "Low", "high": "High", "characteristics_with_more_variance": "Characteristics with more variance"}, {"added_variance_median": P1, "low": P1, "high": P1}))
    ax.append(figure(fa["variance"], "Each bar is one characteristic adjusted at the press: the variance of its readings over all 2024 runs against its runs with no recorded adjustment and no point beyond two sigma, less one. The dashed line is the median. The long right tail is characteristics whose runs with a point beyond two sigma include level shifts, and the median is the figure for that reason."))
    s_est = est[est["reference_for_a_point_left_alone"].str.contains("sensitivity") & est["measure"].str.contains("estimated")]
    ax.append(show(a["after_a_point"], {"adjusted_at_the_press": "Adjusted at the press", "entry_method": "Entry", "points": "Points beyond two sigma or the printed limit", "adjustment_recorded": "Adjustment recorded", "recorded_share": "Share", "points_with_a_next_subgroup": "With a next subgroup", "next_on_the_other_side_beyond_one_sigma": "Next on the other side by more than one sigma", "other_side_share": "Share of those"},
                   {"adjusted_at_the_press": lambda v: "yes" if v else "no", "points": F0, "adjustment_recorded": F0, "recorded_share": P1, "points_with_a_next_subgroup": F0, "next_on_the_other_side_beyond_one_sigma": F0, "other_side_share": P1}))
    ax.append(f"<div class='caption'>Routine subgroups on variable characteristics with limits in force; position is the subgroup mean less the centre line in units of the chart's sigma of the mean. A characteristic adjusted at the press is a formed height, a bend angle or a hole-to-edge position; no characteristic of another type carries a recorded adjustment in 2024. "
              f"The sign change after a point (last table) is the measure first named for an unrecorded adjustment; it does not separate adjusted characteristics from the rest and is not used as a count. Estimated, on the points between one and two sigma as the reference for a point left alone: an adjustment followed {P1(s_est.iloc[0]['estimate'])} of points beyond two sigma on keyed entry ({P1(s_est.iloc[0]['low'])} to {P1(s_est.iloc[0]['high'])}), "
              f"{P1(s_est.iloc[1]['estimate'])} of them recorded. The reference in the same position class, points beyond two sigma on characteristics not adjusted at the press, gave no estimate, because the punched characteristics return from beyond two sigma as fast as an adjusted formed characteristic does. "
              f"In the first variance row the reference leaves out runs with a special cause, so the figure includes their variance; in the second the reference includes runs with an unrecorded adjustment, so the figure understates. "
              f"</div>")

    ax.append("<h3>Appendix 6. Die wear (Section 7)</h3>")
    ax.append(show(w["hole_diameter_by_die"].sort_values("slope_mm_per_100k_shots", ascending=False), {"die_id": "Die", "characteristic_id": "Hole diameter", "intervals": "Intervals", "subgroups": "Subgroups", "slope_mm_per_100k_shots": "Growth, mm per 100,000 shots", "slope_low": "Low", "slope_high": "High", "r_squared_within_intervals": "R-squared within intervals",
                                                                                                         "sharpening_interval_shots": "Stated interval, shots", "growth_as_share_of_tolerance": "Growth over the interval, share of tolerance"},
                   {"slope_mm_per_100k_shots": F4, "slope_low": F4, "slope_high": F4, "r_squared_within_intervals": F2, "sharpening_interval_shots": F0, "growth_as_share_of_tolerance": P0}))
    bsum = pd.DataFrame([("Dies fitted (30 burr gauge subgroups or more, 2023 and 2024)", F0(bs.dies_fitted)), ("Burr gauge subgroups per die, median", F0(bd["subgroups"].median())), ("R-squared by die, median", F2(bs.r_squared_median)),
                         ("Shots at 80% of the burr limit, median by die", F0(bs.shots_at_80pct_median)), ("Stated sharpening interval, median over the same dies", F0(bs.sharpening_interval_median)),
                         ("Dies whose stated interval is longer than the count at 80%", f"{F0(bs.interval_longer_than_the_80pct_count)} of {F0(bs.dies_fitted)}"), ("The same, longer than the upper bound of the count", F0(bs.the_same_beyond_the_upper_bound_of_the_count)),
                         ("Dies whose interval as run (logged median) is longer than the count at 80%", f"{logged_longer} of {logged_n}"), ("Dies whose stated interval is longer than the count at the limit", F0(bs.interval_longer_than_the_count_at_the_limit)),
                         ("Run intervals ending in 2024 with shot counts at both ends", F0(il.intervals_with_shot_counts)),
                         ("Logged intervals ending in 2024, and those left out", f"A logged interval under 20,000 shots is a sharpening followed by a rebuild, or an entry with no shots between it and the one beside it, and is not a run interval; {F0(il.left_out_as_not_run_intervals)} of the {F0(il.logged_intervals)} intervals ending in 2024 are left out on this rule."), ("Logged shots over the stated interval, median (quartiles)", f"{il.logged_over_stated_median:.2f} ({il.lower_quartile:.2f} to {il.upper_quartile:.2f})")], columns=["Burr height on the burr gauge against shots since sharpening", "Value"])
    ax.append(S.table(bsum))
    ax.append(show(w["burr_nonconformances"], {"defect_code": "Defect code", "detected_at": "Detected at", "nonconformances": "Nonconformances, 2024", "quantity_affected": "Quantity affected", "with_shots_since_sharpening": "With shots known", "within_the_sharpening_interval": "Run ended within the stated interval", "past_the_sharpening_interval": "Past it",
                                               "share_of_the_interval_median": "Position, median"}, {"quantity_affected": F0, "share_of_the_interval_median": F2}))
    hd = w["hole_diameter_by_die"].set_index("die_id").loc["D-0417-B"]
    ax.append(figure(fw["hole"], f"Each colour is one sharpening interval of 2024 on hole diameter {hd.characteristic_id}, die D-0417-B: the subgroup means against shots since sharpening, with the slope common to the intervals drawn through each at its own level. The shaded band is the tolerance. "
                                 f"The hole grows {hd.slope_mm_per_100k_shots:.4f} mm per 100,000 shots ({hd.slope_low:.4f} to {hd.slope_high:.4f}) in every interval."))
    one = bd.set_index("die_id").loc[fw["burr_die"]]
    ax.append(figure(fw["burr"], f"Each point is a burr gauge subgroup of 2023 and 2024 on die {fw['burr_die']} as a share of the burr limit, with the fitted line and its 95% band; the vertical lines mark the shot count at which the line reaches 80% of the limit, the stated sharpening interval and the median interval as run. "
                                 f"Burr reaches 80% of its limit at {one.shots_at_80pct_of_limit:,.0f} shots, the stated interval is {one.sharpening_interval_shots:,.0f} and the die has been run a median {one.logged_interval_median:,.0f} between sharpenings."))
    ax.append("<div class='caption'>Subgroup means of variable readings with the die's shots since sharpening known; first-piece, routine and last-piece subgroups. A sharpening interval enters the hole diameter regression with at least 15 subgroups spanning at least 60,000 shots. The burr fit pools each die's intervals on one line, with burr near a quarter of the limit at every sharpening. "
              "The stated sharpening interval is the die room's figure in the die master. The defect code \"hole burr and size\" is shown beside \"burr\" and not added to it.</div>")

    ax.append("<h3>Appendix 7. Recording (Section 8)</h3>")
    ax.append(show(rec["planned_checks"], {"press_group": "Presses", "shift": "Shift", "planned_checks": "Planned checks, 2024", "recorded": "Recorded", "recorded_share": "Share", "recorded_share_low": "Low", "recorded_share_high": "High"}, {"press_group": lambda v: v.replace("_", "-"), "planned_checks": F0, "recorded": F0, "recorded_share": P1, "recorded_share_low": P1, "recorded_share_high": P1}))
    ax.append(show(ph[ph["press_group"] == "all presses"], {"hour_of_day": "Planned time, hour", "shift": "Shift", "planned_checks": "Planned checks", "recorded": "Recorded", "recorded_share": "Share"}, {"hour_of_day": lambda v: f"{int(v):02d}:00", "planned_checks": F0, "recorded": F0, "recorded_share": P1}))
    ax.append(show(rec["entry_after_the_parts"].iloc[:1], {"record": "Record", "subgroups": "Subgroups", "entered_more_than_20_minutes_after": "Entered more than 20 minutes after the parts", "share": "Share", "share_low": "Low", "share_high": "High", "minutes_to_entry_median": "Minutes to entry, median"},
                   {"subgroups": F0, "entered_more_than_20_minutes_after": F0, "share": P1, "share_low": P1, "share_high": P1, "minutes_to_entry_median": lambda v: f"{v:.1f}"}))
    ax.append(figure(frec["entry"], "The line is the distribution of the minutes from the parts to the entry on keyed routine subgroups of 2024, on a log scale, and the dashed line marks 20 minutes. Entries fall in two groups, one within minutes of the parts and one from 20 minutes to about three hours after."))
    ax.append(figure(frec["minute_paper"], f"Each bar is the share of the routine subgroups of 2024 on paper charts at that minute of the hour noted on the form. The times noted on the chart forms fall at the hour or within {paper_last} minutes after it and none later, and almost none at minute {paper_gap}."))
    ax.append("<div class='caption'>A planned check falls on the clock at the part's check frequency, between 06:00 and 23:00 on a day the press recorded a check, from 20 minutes after production started to 2 minutes before the run ended, on runs of two hours or more; it is recorded when the run carries a routine check from 6 minutes before it to 31 minutes after. "
              "The plan counts planned times at which the press may have stood, so the figures understate recording by that amount; the contrast between shifts holds either way. A short run is under two hours from production start to end on the wall clock.</div>")

    toc = [("findings", "Findings"), ("limits", "Charts and limits"), ("capability", "Capability"), ("risk", "Risk window"), ("measurement", "Measurement"), ("adjustment", "Adjustment"), ("wear", "Die wear"), ("recording", "Recording"), ("actions", "Actions"), ("appendix", "Appendix")]
    meta = ("Progressive-die metal stamper, about 110 employees, eleven presses, one plant; IATF 16949 certified. The record from 1 January 2023 to 31 December 2024, with the assessment's own studies of January 2025; "
            "SPC software and paper charts, press monitors, ERP, QMS, die maintenance log, calibration system, accounting and gauge study worksheets. Dimensions in millimetres.<br>PPAP elements 8, 9 and 11; IATF 16949 9.1.1.1.")
    html = S.shell("SPC Assessment", "Report", meta, "\n".join(body + ax), toc)
    out = S.DOCS / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / "spc_assessment.html").write_text(html, encoding="utf8", newline="\n")
    trace = pd.DataFrame(TRACE, columns=["section", "value_as_printed", "read_from"])
    return html, trace, n_body_figures, FIGURE[0]


if __name__ == "__main__":
    html, trace, n_body, n_all = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "assessment_numbers.csv", index=False, lineterminator="\n")
    print(len(html), len(trace), n_body, n_all)
