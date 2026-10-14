"""SPC Assessment: the report page, on the record to 31 December 2025 with the assessment's own studies of January 2026. Reads the analysis tables, builds the figures and writes docs/reports/spc_assessment.html
and the table of every number in the body with the table it is read from."""
import numpy as np
import pandas as pd

from analytics.limits import limits as charts, figures as charts_fig
from analytics.capability import capability as capability, figures as capability_fig
from analytics.risk_window import risk_window as risk, figures as risk_fig
from analytics.measurement import measurement as measurement, figures as measurement_fig
from analytics.adjustment import adjustment as adjustment, figures as adjustment_fig
from analytics.die_wear import die_wear as wear, figures as wear_fig
from analytics.outcomes import outcomes as outcomes
from analytics.recording import recording as recording, figures as recording_fig
from analytics.scope import scope as scope
from analytics.data import query
from analytics.style import style as S

YEAR = 2025
TRACE = []          # (section, value as printed, table and column it is read from, value in the draft text)
SECTION = [""]
FIGURE = [0]
TINT = {scope.HOLDS: "#E3F1E7", scope.PARTIAL: "#FBEBD3", scope.FAILS: "#F9DEDE", scope.NA: "transparent"}


def num(x, src, f="{:,.0f}", was=""):
    s = f.format(x); TRACE.append((SECTION[0], s, src, was)); return s


def pct(x, src, d=0, was=""):
    s = f"{x * 100:.{d}f}%"; TRACE.append((SECTION[0], s, src, was)); return s


def exhibit(img, title, note=None):
    """A figure under its centred title, with one line beneath on how to read it."""
    FIGURE[0] += 1
    return f"<div class='chart-title'>{title}</div>{img}" + (f'<div class="caption">{note}</div>' if note else "")


def titled_table(title, html, note=None):
    return f"<div class='chart-title'>{title}</div>{html}" + (f'<div class="caption">{note}</div>' if note else "")


def show(df, columns, fmt=None):
    d = df[list(columns)].rename(columns=columns)
    return S.table(d, {columns[k]: v for k, v in (fmt or {}).items()})


def P1(v):
    return f"{v * 100:.1f}%"


def P0(v):
    return f"{v * 100:.0f}%"


def F0(v):
    return f"{v:,.0f}"


def F1(v):
    return f"{v:.1f}"


def F2(v):
    return f"{v:.2f}"


def F3(v):
    return f"{v:.3f}"


def F4(v):
    return f"{v:.4f}"


def section(anchor, title):
    SECTION[0] = title
    return f'<h2 id="{anchor}">{title}</h2>'


def sub(anchor, title):
    SECTION[0] = title
    return f'<h3 id="{anchor}">{title}</h3>'


def word(x, words, src, was=""):
    """A small whole number written as a word."""
    s = words[int(round(x))]; TRACE.append((SECTION[0], s, src, was)); return s


def criterion(text):
    return f"<p><em>Criterion: {text}</em></p>"


def about(values, target, src, within=0.02, was=""):
    """A rounded figure stated as 'about': every value behind it lies within the tolerance of the figure printed."""
    assert all(abs(v - target) <= within for v in values), (values, target)
    s = f"about {target * 100:.0f}%"; TRACE.append((SECTION[0], s, src, was)); return s


def anova_block(key, a):
    """One gauge study in the layout Minitab prints: the two-way ANOVA table and the variance components."""
    rows = "".join(f"<tr><td>{s}</td><td class='num'>{df}</td><td class='num'>{ss:.6f}</td><td class='num'>{'' if ms != ms else f'{ms:.6f}'}</td><td class='num'>{'' if fv != fv else f'{fv:.3f}'}</td></tr>" for s, df, ss, ms, fv in a["anova"])
    tv = a["total_var"]; comp = [("Total Gage R&R", a["grr_var"]), ("&nbsp;&nbsp;Repeatability", a["repeatability_var"]), ("&nbsp;&nbsp;Reproducibility", a["reproducibility_var"]),
                                ("&nbsp;&nbsp;&nbsp;&nbsp;Operator", a["operator_var"]), ("&nbsp;&nbsp;&nbsp;&nbsp;Operator*Part", a["interaction_var"]), ("Part-To-Part", a["part_var"]), ("Total Variation", tv)]
    vc = "".join(f"<tr><td>{n}</td><td class='num'>{v:.7f}</td><td class='num'>{v / tv * 100:.2f}</td><td class='num'>{np.sqrt(v):.5f}</td><td class='num'>{6 * np.sqrt(v):.5f}</td></tr>" for n, v in comp)
    pooled = "pooled with repeatability" if a["interaction_pooled"] else "kept"
    return (f"<div class='chart-title'>{key[0]}, {key[1]} study</div><table class='data'><thead><tr><th>Source</th><th>DF</th><th>SS</th><th>MS</th><th>F</th></tr></thead><tbody>{rows}</tbody></table>"
            f"<table class='data'><thead><tr><th>Source</th><th>VarComp</th><th>%Contribution (of VarComp)</th><th>StdDev (SD)</th><th>Study Var (6 x SD)</th></tr></thead><tbody>{vc}</tbody></table>"
            f"<div class='caption'>Interaction p = {a['interaction_p']:.3f}, {pooled}. %Tolerance (SV/Toler) = {a['pct_tolerance']:.1f}. Number of Distinct Categories = {a['ndc']}.</div>")


def simple_table(head, rows, cls="data"):
    return f"<table class='{cls}'><thead><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>"


def status_cell(status, why):
    return f"<td style='background:{TINT[status]}'><strong>{status}</strong><br><span style='font-size:0.85em'>{why}</span></td>"


def matrix_table(m):
    head = ["Characteristic class", "Chart and limits, software presses", "Chart and limits, paper presses", "Capability", "Measurement", "Sampling frequency", "Reaction"]
    rows = "".join(f"<tr><td>{k[0].upper() + k[1:]}</td>" + "".join(status_cell(*m["cells"][(k, c)]) for c in ("software", "paper", "capability", "measurement", "sampling", "reaction")) + "</tr>" for k in scope.MATRIX_CLASSES)
    return "<table class='data'><thead><tr>" + "".join(f"<th>{h}</th>" for h in head) + f"</tr></thead><tbody>{rows}</tbody></table>"


def share_status(share, higher_is_better=True):
    v = share if higher_is_better else 1 - share
    return scope.HOLDS if v >= 0.9 else scope.PARTIAL if v >= 0.5 else scope.FAILS


def plant_wide_table(pw):
    rows = ""
    for name, g in pw.groupby("measure", sort=False):
        g = g.set_index("shift"); better = "more than 20 minutes" not in name
        rows += f"<tr><td>{name}</td>" + "".join(f"<td style='background:{TINT[share_status(g.loc[s, 'share'], better)]}'>{g.loc[s, 'share'] * 100:.1f}%<br><span style='font-size:0.85em'>{int(g.loc[s, 'with']):,} of {int(g.loc[s, 'count']):,}</span></td>" for s in ("days", "nights", "all")) + "</tr>"
    return f"<table class='data'><thead><tr><th>Measure</th><th>Days</th><th>Nights</th><th>All</th></tr></thead><tbody>{rows}</tbody></table>"


METHOD = ("<p>Control charts and capability indices follow AIAG SPC, 2nd edition: within-subgroup sigma is the pooled standard deviation across subgroups and overall sigma the standard deviation of all readings; Cpk intervals by the AIAG approximation and Ppk intervals by bootstrap. "
          "Stability is by Western Electric rules 1 to 4. Average run length is by the Markov chain method. Variance components are from a nested random-effects model (coil within die, subgroup within coil) fitted by REML. The coil regression is ordinary least squares on the coil's certificate values, with receiving values beside. "
          "Gauge R&amp;R follows AIAG MSA, 4th edition, ANOVA method, with %tolerance at 6 sigma and ndc; attribute agreement is with 95% intervals and Fleiss' kappa. Autocorrelation of subgroup means is the lag-1 coefficient of the means less their run-and-coil segment mean, pooled over segments of at least 6 subgroups. "
          "Bounded characteristics (burr, flatness) are on the readings as recorded by the percentile method, with the Box-Cox result beside. Proportions carry Wilson intervals. Readings are used as recorded and none is corrected; a keyed reading that cannot be a measurement of the part (further than five tolerance widths from nominal) is set aside, with the count stated. "
          "Limits as set are the limits the software computed or the paper form carried at each entry; limits as computed are from a stable 25-subgroup baseline after the most recent sharpening. Press monitor times are aligned to the SPC terminal clock on run start. "
          "Data: the SPC software and transcribed paper charts, press monitor fault events, ERP, QMS, die maintenance log, calibration system, accounting and the gauge study worksheets, as exported; record boundaries and coverage are with each table.</p>")


def build():
    TRACE.clear(); FIGURE[0] = 0
    c, k, r, m, a, w, rec = charts.compute(), capability.compute(), risk.compute(), measurement.compute(), adjustment.compute(), wear.compute(), recording.compute()
    sp = scope.compute(c, k, r, m, a, rec); sco, mx, pw = sp["scope"], sp["matrix"], sp["plant_wide"]
    fc, fk, fr, fm, fa, fw, frec = charts_fig.build(c), capability_fig.build(k), risk_fig.build(r), measurement_fig.build(m), adjustment_fig.build(a), wear_fig.build(w), recording_fig.build(rec)
    merged_limits = charts_fig.signals_and_actions(c); fixtures_fig = measurement_fig.fixture_status(mx["latest_gauge_studies"]); losses = outcomes.plant_losses((YEAR - 1, YEAR))
    body = []

    # -- values read once ----------------------------------------------------
    sc = c["signal_comparison"].set_index(["limits_as_set_method", "characteristic_class"]); OTHER = "other punched and dimensional"
    roll = sc.loc["rolling 25 at entry"].loc[["formed", "hole diameter"]]
    pa = c["paper_signals_all_subgroups"].iloc[0]; age = c["paper_limit_age"].iloc[0]; ack = c["software_acknowledgements"].iloc[0]
    pf = c["paper_signals"].set_index("characteristic_class").loc["formed"]; rl = c["run_lengths"]; rl = rl[(rl["limits_as_set_method"] == "PPAP study") & rl["in_report"]]
    arl_p = rl[rl["limits"].str.startswith("as set")].set_index("characteristic_class")["arl_in_control"]; arl_c = rl[rl["limits"].str.startswith("computed")].set_index("characteristic_class")["arl_in_control"]
    cs = k["capability_summary"].set_index("characteristic_class"); coil = k["coil_regression_summary"].iloc[0]; pt = k["punched_by_type"].set_index("characteristic_type"); bd_ = k["bounded_summary"].set_index("characteristic_type")
    rw = r["risk_window"]; ss = r["sorting_summary"].set_index("year"); sb = r["sorting_by_basis"].set_index("sort_basis")
    grr = m["gauge_rr"].set_index(["fixture", "study"]); ms = m["measurement_share"].set_index("fixture"); att = m["attribute_agreement"].set_index("study"); em = m["entry_methods"].set_index("entry_method")
    gs = m["gauge_status"].iloc[0]
    ap = a["after_a_point"].set_index(["adjusted_at_the_press", "entry_method"]); rt = a["return_toward_centre"].set_index(["entry_method", "points_group"]); ac = a["autocorrelation"].set_index(["period", "characteristics"])
    av = a["variance"].set_index("comparison_runs"); est = a["adjustment_estimate"]
    hs = w["hole_diameter_summary"].iloc[0]; hdd = w["hole_diameter_by_die"]; bs = w["burr_summary"].iloc[0]; bd = w["burr_by_die"]; il = w["intervals_as_logged"].iloc[0]; rp = w["runs_past_the_interval"].iloc[0]
    oh = rec["on_the_hour"].set_index("entry_method"); pc = rec["planned_checks"].set_index(["press_group", "shift"]); ph = rec["planned_checks_by_hour"]; sr = rec["short_runs"].set_index("run_length")
    ea = rec["entry_after_the_parts"].set_index("record")
    logged_n = int(bd["logged_interval_median"].notna().sum()); logged_longer = int((bd["logged_interval_median"] > bd["shots_at_80pct_of_limit"]).sum())
    day_hours = ph[(ph["press_group"] == "all presses") & (ph["shift"] == "days")]; six = day_hours[day_hours["hour_of_day"] == 6].iloc[0]; rest = day_hours[day_hours["hour_of_day"] != 6]["recorded_share"]
    g1, g2, g3, p1, p2 = grr.loc[("F-20417", "redesign")], grr.loc[("F-31102", "redesign")], grr.loc[("F-10823", "redesign")], grr.loc[("F-20417", "PPAP")], grr.loc[("F-31102", "PPAP")]
    b1 = att.loc["at the redesign"]; op = m["attribute_by_operator"]; op = op[op["study"] == "at the redesign"].sort_values("reject_rate")
    v0 = av.loc["no adjustment recorded and no point beyond two sigma"]; a_adj, a_not = ac.loc[(f"{YEAR}, before the redesign", "adjusted at the press")], ac.loc[(f"{YEAR}, before the redesign", "not adjusted at the press")]
    s_est = est[est["reference_for_a_point_left_alone"].str.contains("sensitivity") & est["measure"].str.contains("estimated")]
    e0 = ea.loc[f"software presses, {YEAR}, keyed"]; flt = sb.loc["sorted from a logged die-protection fault"]; inh = sb.loc["sorted back to the check before, in-house"]
    back = query(f"""select median(quantity_sorted) as quantity_sorted_median, sum(quantity_rejected) / sum(quantity_sorted) as rejected_share, count(*) as events from marts.mart_sorting_events
                     where sort_basis like 'sorted back to the check before%' and sort_year between {YEAR - 1} and {YEAR}""").iloc[0]
    cost = query(f"""with g as (select sort_year, case when sort_basis like 'sorted back to the check before%' then 'back' else sort_basis end as basis, sum(sorting_cost_booked_or_estimated) as cost
                               from marts.mart_sorting_events where sort_year between {YEAR - 1} and {YEAR} group by 1, 2)
                     select sort_year, sum(cost) as cost, sum(cost) filter (where basis = 'back') as back_cost, max(cost) as largest_basis_group_cost from g group by 1 order by 1""").set_index("sort_year")
    found_after = scope.found_after_the_press(); l24 = losses.set_index("year").loc[YEAR - 1]
    fx_before = int(query(f"""select count(distinct s.gauge_id) as n from staging.stg_calibration__gauge_studies s join staging.stg_calibration__gauges g using (gauge_id)
                                where g."type" = 'check fixture' and s."date" < date '{YEAR + 1}-01-01'""")["n"].iloc[0])
    y25 = ss.loc[YEAR]; l25 = losses.set_index("year").loc[YEAR]; k1, k2 = fa["runs_shown"]; cmm = k["fixture_against_cmm"].set_index("group").loc["all fixtures, before the redesign"]
    hp = pt.loc[["hole-to-hole", "hole-to-edge"]]; hd_ = pt.loc["hole diameter"]; kb = fw_die = bd.set_index("die_id").loc[fw["burr_die"]]; hdie = hdd.set_index("die_id").loc["D-0417-B"]
    tol = [float(x.tolerance_mm) for x in (g1, g2, g3)]; bias_share = [cmm.mean_difference_mm / t_ for t_ in tol]
    fx = mx["latest_gauge_studies"]; fx = fx[fx["gauge_type"] == "check fixture"]; fx_under = int((fx["pct_grr_of_tolerance"] < 10).sum()); fx_none = int(fx["pct_grr_of_tolerance"].isna().sum())
    pwi = pw.set_index(["measure", "shift"]); in_service = pwi.loc[("Subgroups on a gauge in service and in calibration", "all"), "share"]
    med = rw.set_index("press_id"); ratios = [med.loc[x, "median_parts_between_checks_at_the_realised_rate"] / med.loc[y, "median_parts_between_checks_at_the_realised_rate"]
                                             for x in med.index[med["press_group"] == "high_speed"] for y in med.index[med["press_group"] == "medium"] if med.loc[x, "plan_frequency_minutes"] == med.loc[y, "plan_frequency_minutes"]]
    classes = sco["classes"]; total_ch = int(classes["characteristics"].sum()); total_sg = int(classes["subgroups"].sum())

    # -- 1. Executive summary ------------------------------------------------
    body.append(section("summary", "1. Executive summary"))
    charted_parts = int(query(f"""select count(distinct k.part_id) as n from intermediate.int_characteristic_history h join staging.stg_spc__characteristics k using (characteristic_id)
                                   where k.part_id in (select part_id from intermediate.int_run_shots where year(production_start) = {YEAR})""")["n"].iloc[0])
    assert charted_parts == int(sco["parts"])          # every part run in the year is charted at the press
    days = pc.loc[("all presses", "days"), "recorded_share"]
    body.append(f"<p>The shop runs a complete SPC program, and much of it holds. Every part in production is charted at the press, about {num(round(total_ch, -1), 'scope.classes.characteristics, total, to the ten', was='1,550')} characteristics on "
                f"{num(sco['parts'], 'scope.parts', was='179')} parts. {pct(in_service, 'plant_wide.share, subgroups on a gauge in service and in calibration, all', was='93%')} of subgroups were measured on a gauge in service and in calibration, "
                f"the software presses acknowledged all {num(ack.alarms, 'software_acknowledgements.alarms', was='10,474')} alarms, and the day shift recorded {pct(days, 'planned_checks.recorded_share, all presses days', was='94%')} of planned checks. "
                f"On punched characteristics and flatness, the charts signal close to the rate of correctly set limits, and production capability stays above 1.33: "
                f"Ppk {num(cs.loc['punched', 'ppk'], 'capability_summary.ppk, punched', '{:.2f}', '1.55')} on punched characteristics and Ppu {num(bd_.loc['flatness', 'ppu_percentile_median'], 'bounded_summary.ppu_percentile_median, flatness', '{:.2f}', '1.79')} on flatness.</p>")
    body.append(f"<p>The program does not hold on formed characteristics, hole diameters and burr. Production Ppk on critical formed characteristics is {num(cs.loc['formed', 'ppk'], 'capability_summary.ppk, formed', '{:.2f}', '1.04')} against "
                f"{num(cs.loc['formed', 'filed_ppk'], 'capability_summary.filed_ppk, formed', '{:.2f}', '1.84')} filed at PPAP. "
                f"{num(rp.burr_nonconformances_past_the_interval, 'runs_past_the_interval.burr_nonconformances_past_the_interval', was='60')} of the {num(rp.burr_nonconformances_with_shots_known, 'runs_past_the_interval.burr_nonconformances_with_shots_known', was='61')} burr nonconformances of {YEAR} fell on runs past the die's stated sharpening interval.</p>")
    body.append(f"<p>Three sources of variation sit behind these gaps. Coil-to-coil shifts carry {pct(cs.loc['formed', 'share_between_coils'], 'capability_summary.share_between_coils, formed', was='54%')} of the variance on formed characteristics. "
                f"Burr and hole size grow with shots since sharpening, and dies are sharpened at a median {num(il.logged_over_stated_median, 'intervals_as_logged.logged_over_stated_median', '{:.2f}', '1.14')} times their stated interval. "
                f"Die events between routine checks led to {num(y25.traced_to_a_die_event_between_two_checks, f'sorting_summary.traced_to_a_die_event_between_two_checks, {YEAR}', was='12')} of the {num(y25.sorting_events, f'sorting_summary.sorting_events, {YEAR}', was='14')} sorting events of {YEAR}.</p>")
    assert min(g1.pct_tolerance, g2.pct_tolerance) > 30
    body.append("<p>Two gaps cut across every class:</p><ul>"
                f"<li>On the paper presses an action is recorded on {pct(pa.action_share, 'paper_signals_all_subgroups.action_share', was='28%')} of signals, and adjustment at the press adds {pct(v0.added_variance_median, 'variance.added_variance_median, no adjustment and no point beyond two sigma', was='10%')} to the variance of the characteristics it targets.</li>"
                f"<li>{num(fx_none, 'latest_gauge_studies: check fixtures with no study on file', was='164')} of the {num(len(fx), 'latest_gauge_studies: check fixtures', was='180')} check fixtures have no gauge study on file, and the two reworked fixtures that were studied consume more than 30% of tolerance.</li></ul>")
    body.append(f"<p>In {YEAR} scrap and rework were {pct(l25.scrap_and_rework_share_of_revenue, f'plant_losses.scrap_and_rework_share_of_revenue, {YEAR}', 2, '3.12%')} of revenue (${num(l25.scrap_booked + l25.rework_labor_booked, f'plant_losses: scrap_booked plus rework_labor_booked, {YEAR}', was='1,242,201')}). "
                f"Customer PPM was {num(l25.ppm, f'plant_losses.ppm, {YEAR}', was='463')} on {num(l25.complaints, f'plant_losses.complaints, {YEAR}', was='58')} complaints, level with {num(l24.ppm, f'plant_losses.ppm, {YEAR - 1}', was='491')} in {YEAR - 1}. "
                f"{num(y25.sorting_events, f'sorting_summary.sorting_events, {YEAR}', was='14')} sorting events covered {num(y25.quantity_sorted, f'sorting_summary.quantity_sorted, {YEAR}', was='101,154')} parts.</p>")
    assert int(l25.sorting_events) == int(y25.sorting_events) and int(l25.quantity_sorted) == int(y25.quantity_sorted) and l25.low < l24.ppm < l25.high
    loss_rows = [("Scrap booked, $", F0(l25.scrap_booked)), ("Rework labor booked, $", F0(l25.rework_labor_booked)), ("Scrap and rework, share of revenue", f"{l25.scrap_and_rework_share_of_revenue * 100:.2f}%"), ("Revenue, $", F0(l25.revenue)),
                 ("Complaints, with duplicate entries left out", F0(l25.complaints)), ("Customer PPM (95% interval)", f"{l25.ppm:,.0f} ({l25.low:,.0f} to {l25.high:,.0f})"), ("Sorting events", F0(l25.sorting_events)), ("Quantity sorted", F0(l25.quantity_sorted)),
                 ("Sorting cost booked or estimated, $", F0(l25.sorting_cost_booked_or_estimated))]
    body.append(titled_table(f"Quality losses, all presses, {YEAR}", simple_table(["Measure", str(YEAR)], loss_rows),
                             "Share of revenue is scrap and rework booked over revenue. Complaints leave out duplicate entries. Sorting cost is as booked, with the estimate from run hours where sorting was not booked to the sorting labor code."))

    # -- 2. Scope ------------------------------------------------------------
    body.append(section("scope", "2. Scope"))
    gst = sco["gauge_studies"]; ast = sco["attribute_study"]; first_day = pd.Timestamp(gst["study_date"].min()); last_day = pd.Timestamp(ast["date"])
    assert (first_day.year, first_day.month) == (last_day.year, last_day.month) == (YEAR + 1, 1)
    body.append(f"<p>The assessment covered every chart in use on all eleven presses in {YEAR}: about {num(round(total_ch, -1), 'scope.classes.characteristics, total, to the ten', was='1,550')} characteristics on {num(sco['parts'], 'scope.parts', was='179')} parts, and about "
                f"{num(round(total_sg, -3), 'scope.classes.subgroups, total, to the thousand', was='203,000')} subgroups. The four high-speed presses chart on paper and the seven medium presses on the SPC software. The assessment drew on seven source systems and ran three studies of its own, from "
                f"{num(first_day.day, 'scope.gauge_studies.study_date, earliest, day of January', '{:d}', '12')} to {num(last_day.day, 'scope.attribute_study.date, day of January', '{:d}', '15')} January {YEAR + 1}: gauge R&amp;R on three check fixtures, and attribute agreement on the burr check. "
                f"Capability was measured on the {num(sco['base_characteristics'], 'capability_summary.characteristics, all critical', was='130')} critical characteristics with a PPAP study on file, against the production record that followed each study.</p>")
    pr = sco["presses"]; hs_ids = pr[pr["press_group"] == "high_speed"]["press_id"].tolist(); md_ids = pr[pr["press_group"] == "medium"]["press_id"].tolist()
    cls_lines = "<br>".join(f"{r_.characteristic_class[0].upper() + r_.characteristic_class[1:]}: {int(r_.characteristics):,} ({int(r_.critical_characteristics):,} critical)" for r_ in classes.itertuples())
    src_lines = "<br>".join(f"{name}: " + "; ".join(f"{n_:,} {lab}" for lab, n_ in rows_) for name, rows_ in sco["sources"])
    scope_rows = [("Presses", f"{len(pr)}: {len(hs_ids)} high-speed charting on paper ({hs_ids[0]} to {hs_ids[-1]}) and {len(md_ids)} medium charting in the SPC software ({md_ids[0]} to {md_ids[-1]})"),
                  ("Parts and dies", f"{sco['parts']:,} parts and {sco['dies']:,} dies run in {YEAR}, on {sco['runs']:,} production runs"),
                  (f"Characteristics charted in {YEAR}, by class", cls_lines + f"<br><strong>Total: {total_ch:,} ({int(classes['critical_characteristics'].sum()):,} critical)</strong>"),
                  (f"Subgroups recorded in {YEAR}", f"{total_sg:,}: {int(classes['subgroups_keyed'].sum()):,} keyed in the SPC software and {int(classes['subgroups_on_paper'].sum()):,} on paper charts, transcribed"),
                  (f"Sources, with rows of {YEAR}", src_lines),
                  ("Studies run by the assessment", "Gauge R&amp;R: " + "; ".join(f"{g_.fixture} on {g_.characteristic_id}, {pd.Timestamp(g_.study_date).strftime('%d %B %Y').lstrip('0')}" for g_ in gst.itertuples())
                   + f"<br>Burr attribute agreement: {pd.Timestamp(ast['date']).strftime('%d %B %Y').lstrip('0')}, {ast['operators']} operators, {ast['parts']} parts, {ast['trials']} trials"),
                  ("Capability base", f"{sco['base_characteristics']} critical characteristics with a PPAP study on file; {sco['base_studies']} studies; each compared against the production record of the twelve months after the study, or to 31 December {YEAR}")]
    body.append(titled_table("Scope of the assessment", simple_table(["Item", "Assessed"], scope_rows)))

    # -- 3. SPC assessment ---------------------------------------------------
    body.append(section("assessment", "3. SPC assessment"))
    assert int(ack.acknowledged_with_text) == int(ack.alarms)
    body.append("<p>Charts, limits and capability hold on punched characteristics and flatness, and do not hold on formed characteristics, hole diameters and burr.</p><p>Where it holds:</p><ul>"
                f"<li><strong>Charting:</strong> every part in production is charted at the press, and the software presses acknowledged all {num(ack.alarms, 'software_acknowledgements.alarms', was='10,474')} alarms.</li>"
                f"<li><strong>Punched characteristics:</strong> the software runs at {num(sc.loc[('rolling 25 at entry', OTHER), 'rate_as_set_per_100'], 'signal_comparison.rate_as_set_per_100, rolling: other punched', '{:.1f}', '2.6')} signals per 100 subgroups against "
                f"{num(sc.loc[('rolling 25 at entry', OTHER), 'rate_as_computed_per_100'], 'signal_comparison.rate_as_computed_per_100, rolling: other punched', '{:.1f}', '3.5')} under computed limits, and production Ppk is {num(cs.loc['punched', 'ppk'], 'capability_summary.ppk, punched', '{:.2f}', '1.55')}. "
                f"Hole position stays within 0.25 of the filed Ppk on {num(hp['within_0_25'].sum(), 'punched_by_type.within_0_25, hole-to-hole and hole-to-edge', was='22')} of {num(hp['studies'].sum(), 'punched_by_type.studies, hole-to-hole and hole-to-edge', was='36')} studies.</li>"
                f"<li><strong>Flatness:</strong> production Ppu is {num(bd_.loc['flatness', 'ppu_percentile_median'], 'bounded_summary.ppu_percentile_median, flatness', '{:.2f}', '1.79')}.</li>"
                f"<li><strong>Gauges:</strong> {pct(in_service, 'plant_wide.share, subgroups on a gauge in service and in calibration, all', was='93%')} of subgroups were measured on a gauge in service and in calibration. Check fixtures read "
                f"{num(cmm.mean_difference_mm, 'fixture_against_cmm.mean_difference_mm, to the assessment date', '{:.3f}', '0.014')} mm above the CMM, {pct(min(bias_share), 'fixture_against_cmm.mean_difference_mm over gauge_rr.tolerance_mm, lowest of the three studied fixtures', was='3%')} to "
                f"{pct(max(bias_share), 'the same, highest', was='5%')} of tolerance, and readings show no pile-up at the specification limits.</li>"
                f"<li><strong>Recording on days:</strong> the day shift records {pct(pc.loc[('all presses', 'days'), 'recorded_share'], 'planned_checks.recorded_share, all presses days', was='94%')} of planned checks, and "
                f"{pct(rest.min(), 'planned_checks_by_hour.recorded_share, lowest other day hour', was='95%')} to {pct(rest.max(), 'planned_checks_by_hour.recorded_share, highest other day hour', was='97%')} at every hour after the first.</li></ul><p>Where it does not hold:</p><ul>"
                "<li><strong>Formed characteristics</strong> fail on limits, capability and reaction.</li><li><strong>Hole diameters</strong> fail on limits, and their capability is out of line with PPAP.</li>"
                "<li><strong>Burr on the lab gauge</strong> fails on capability and has no gauge study; the burr check by limit sample is partial on measurement.</li></ul>"
                "<p>Two gaps run across every class: gauge studies cover few of the gauges in use, which leaves measurement short on every class but hole diameters, and signals on the paper presses mostly go unanswered. "
                "Plant-wide, recording holds on the day shift and falls short on nights and at the first check of the shift.</p>")
    body.append(titled_table("Assessment matrix", matrix_table(mx), "Status by the thresholds in the appendix for Sections 3.1 to 3.5; the number in each cell is the measure that sets it."))
    body.append(titled_table("Plant-wide", plant_wide_table(pw)))

    body.append(sub("limits", "3.1 Chart selection and limits"))
    body.append(criterion("each class charted on a chart that fits its variation, with limits from a stable baseline held until a planned trigger."))
    both = roll["signals_by_both"].sum() / roll["signals_as_computed"].sum()
    body.append("<p>Chart selection and limits hold on punched characteristics and flatness, and fail on formed characteristics and hole diameters, in opposite ways on the two chart media.</p><ul>"
                f"<li><strong>Software presses:</strong> rolling limits absorb the shifts they should flag. On formed characteristics and hole diameters they flag {pct(both, 'signal_comparison.signals_by_both over signals_as_computed, rolling: formed and hole diameter', 1, '17.0%')} of the subgroups that baseline limits flag.</li>"
                f"<li><strong>Paper presses:</strong> limits printed from the PPAP study signal on {num(pf.printed_per_100, 'paper_signals.printed_per_100, formed', was='42')} of every 100 formed-characteristic subgroups, and an action is recorded on {pct(pa.action_share, 'paper_signals_all_subgroups.action_share', was='28%')} of paper signals.</li>"
                f"<li><strong>Other punched characteristics:</strong> the software runs close to computed limits, at {num(sc.loc[('rolling 25 at entry', OTHER), 'rate_as_set_per_100'], 'signal_comparison.rate_as_set_per_100, rolling: other punched', '{:.1f}', '2.6')} signals per 100 subgroups against "
                f"{num(sc.loc[('rolling 25 at entry', OTHER), 'rate_as_computed_per_100'], 'signal_comparison.rate_as_computed_per_100, rolling: other punched', '{:.1f}', '3.5')}. On paper the printed limits signal more often, at {num(sc.loc[('PPAP study', OTHER), 'rate_as_set_per_100'], 'signal_comparison.rate_as_set_per_100, printed: other punched', '{:.1f}', '5.4')} against "
                f"{num(sc.loc[('PPAP study', OTHER), 'rate_as_computed_per_100'], 'signal_comparison.rate_as_computed_per_100, printed: other punched', '{:.1f}', '3.6')}.</li></ul>")
    body.append(f"<p>Fixed within-subgroup limits are not the remedy on formed characteristics. Computed baseline limits there signal on {num(sc.loc[('rolling 25 at entry', 'formed'), 'rate_as_computed_per_100'], 'signal_comparison.rate_as_computed_per_100, rolling: formed', was='42')} of 100 subgroups, because the coil shifts of Section 4.1 sit outside them.</p>")
    body.append(exhibit(merged_limits, "Signals under the limits as set and as computed, with actions recorded on the paper presses", f"Dark columns: the shop's limits as set in {YEAR}; light columns: limits computed from a stable baseline after each sharpening, on the same subgroups."))
    body.append(f"<p>The printed limits signal whether or not the process has moved. With nothing changed, they signal every {num(arl_p['formed'], 'run_lengths.arl_in_control, printed limits, formed', '{:.1f}', '4.5')} subgroups on formed characteristics and every "
                f"{num(arl_p['hole diameter'], 'run_lengths.arl_in_control, printed limits, hole diameter', '{:.1f}', '17.0')} on hole diameters, against every {num(arl_c['formed'], 'run_lengths.arl_in_control, computed limits, formed', '{:.1f}', '31.4')} and "
                f"{num(arl_c['hole diameter'], 'run_lengths.arl_in_control, computed limits, hole diameter', '{:.1f}', '38.4')} under computed limits.</p>")
    body.append(exhibit(fc["run_lengths"], "Average run length under printed and computed limits, paper presses", "Subgroups to a rule-1 signal; shifts in units of the within-subgroup sigma of the mean."))
    body.append(f"<p>Printed limits are not recomputed after a sharpening. On {num(age.dies_with_every_limit_set_at_the_most_recent_rebuild, 'paper_limit_age.dies_with_every_limit_set_at_the_most_recent_rebuild', was='54')} of the {num(age.dies, 'paper_limit_age.dies', was='57')} dies on the paper presses they date from the last rebuild, "
                "and every sharpening since has run on them.</p>")
    body.append(exhibit(fc["age"], "Age of the printed limits against sharpenings since, by die", f"Each point is one die on the paper presses at 31 December {YEAR}."))

    body.append(sub("capability", "3.2 Capability"))
    body.append(criterion("production Ppk of 1.33 or more on critical characteristics, in line with the Ppk filed at PPAP."))
    body.append(f"<p>Capability holds in production on punched characteristics and flatness. On formed characteristics the filed Ppk overstates production by {num(cs.loc['formed', 'filed_less_production_ppk'], 'capability_summary.filed_less_production_ppk, formed', '{:.1f}', '0.8')}: production Ppk is "
                f"{num(cs.loc['formed', 'ppk'], 'capability_summary.ppk, formed', '{:.2f}', '1.04')} against {num(cs.loc['formed', 'filed_ppk'], 'capability_summary.filed_ppk, formed', '{:.2f}', '1.84')} filed, and on {num(cs.loc['formed', 'studies_filed_at_least_0_40_above'], 'capability_summary.studies_filed_at_least_0_40_above, formed', was='86')} of "
                f"{num(cs.loc['formed', 'studies'], 'capability_summary.studies, formed', was='94')} studies the filed figure is at least 0.40 above production. Punched characteristics stay capable at {num(cs.loc['punched', 'ppk'], 'capability_summary.ppk, punched', '{:.2f}', '1.55')}, against "
                f"{num(cs.loc['punched', 'filed_ppk'], 'capability_summary.filed_ppk, punched', '{:.2f}', '1.85')} filed.</p>")
    body.append(exhibit(fk["capability"], "Ppk filed at PPAP against production Ppk, by study", "Points below the equal line are studies where production capability falls short of the filed figure."))
    hh, he = pt.loc["hole-to-hole"], pt.loc["hole-to-edge"]
    body.append("<p>Within punched characteristics, hole position stays closest to PPAP and hole diameter furthest from it.</p><ul>"
                f"<li><strong>Hole position:</strong> hole-to-hole and hole-to-edge run at {num(hh.production_ppk, 'punched_by_type.production_ppk, hole-to-hole', '{:.2f}', '1.60')} and {num(he.production_ppk, 'punched_by_type.production_ppk, hole-to-edge', '{:.2f}', '1.54')}, against "
                f"{num(hh.filed_ppk, 'punched_by_type.filed_ppk, hole-to-hole', '{:.2f}', '1.79')} and {num(he.filed_ppk, 'punched_by_type.filed_ppk, hole-to-edge', '{:.2f}', '1.77')} filed, and fall within 0.25 of filed on {num(hp['within_0_25'].sum(), 'punched_by_type.within_0_25, hole-to-hole and hole-to-edge', was='22')} of "
                f"{num(hp['studies'].sum(), 'punched_by_type.studies, hole-to-hole and hole-to-edge', was='36')} studies.</li>"
                f"<li><strong>Hole diameter:</strong> production Ppk is {num(hd_.production_ppk, 'punched_by_type.production_ppk, hole diameter', '{:.2f}', '1.45')} against {num(hd_.filed_ppk, 'punched_by_type.filed_ppk, hole diameter', '{:.2f}', '1.98')} filed, within 0.25 on "
                f"{num(hd_.within_0_25, 'punched_by_type.within_0_25, hole diameter', was='1')} of {num(hd_.studies, 'punched_by_type.studies, hole diameter', was='16')}. Cpk on hole diameters is {num(hd_.production_cpk, 'punched_by_type.production_cpk, hole diameter', '{:.2f}', '2.13')}, so the shortfall is drift between subgroups (Section 4.2), not spread within them.</li></ul>")
    body.append(exhibit(fk["punched"], "Filed and production Ppk by punched sub-class, with production Cpk", "Medians over studies; the gap between Cpk and production Ppk is variation between subgroups."))
    body.append(f"<p>Flatness is capable, at a Ppu of {num(bd_.loc['flatness', 'ppu_percentile_median'], 'bounded_summary.ppu_percentile_median, flatness', '{:.2f}', '1.79')}. Burr height sits at {num(bd_.loc['burr height', 'ppu_percentile_median'], 'bounded_summary.ppu_percentile_median, burr height', '{:.2f}', '1.05')}.</p>")
    body.append(exhibit(fk["bounded"], "Upper capability on flatness and burr height", "Median Ppu over characteristics, percentile method on the readings as recorded."))

    body.append(sub("measurement", "3.3 Measurement systems"))
    body.append(criterion("every gauge in use studied, with gauge R&amp;R under 10% of tolerance on the check fixtures; attribute checks in agreement with the reference gauge; readings recorded as measured."))
    fx_studied = len(fx) - fx_none
    body.append("<p>Measurement holds where it has been studied, but the studies cover few gauges, and two reworked fixtures and the burr check fall short.</p><ul>"
                f"<li><strong>Study coverage:</strong> before January {YEAR + 1} the record held a gauge study on {num(fx_before, f'gauge studies on check fixtures dated before January {YEAR + 1}: fixtures', was='2')} of the {num(len(fx), 'latest_gauge_studies: check fixtures', was='180')} check fixtures, both from PPAP. "
                f"The January studies bring that to {num(fx_studied, 'latest_gauge_studies: check fixtures with a study on file', was='16')}, of which {num(fx_under, 'latest_gauge_studies: check fixtures under 10% on the latest study on file', was='8')} stand under 10% of tolerance.</li>"
                f"<li><strong>Gauge status:</strong> {pct(in_service, 'plant_wide.share, subgroups on a gauge in service and in calibration, all', was='93%')} of subgroups were measured on a gauge in service and in calibration. "
                f"{pct(gs.share_out_of_service, 'gauge_status.share_out_of_service', 1, '4.4%')} were on a gauge away for calibration that day, and {pct(gs.share_past_due, 'gauge_status.share_past_due', 1, '2.7%')} on one past its calibration due date.</li></ul>")
    body.append(exhibit(fixtures_fig, "Check fixtures by %GRR of tolerance on the latest study on file", "%GRR of tolerance, ANOVA method at 6 sigma, on each fixture's latest study."))
    body.append(f"<p>The two fixtures reworked since PPAP consume {pct(g1.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-20417 assessment study', 1, '31.2%')} and {pct(g2.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-31102 assessment study', 1, '33.6%')} of tolerance, against "
                f"{pct(p1.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-20417 PPAP', 1, '8.9%')} and {pct(p2.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-31102 PPAP', 1, '8.4%')} at PPAP. F-10823, which was not reworked, stands at {pct(g3.pct_tolerance / 100, 'gauge_rr.pct_tolerance, F-10823 assessment study', 1, '11.3%')}.</p>")
    body.append(exhibit(fm["grr"], "Gauge R&amp;R as a share of tolerance, by fixture and study", "ANOVA method at 6 sigma; ndc is the number of distinct categories."))
    body.append(f"<p>{about([g1.reproducibility_share_of_grr, g2.reproducibility_share_of_grr], 0.7, 'gauge_rr.reproducibility_share_of_grr, F-20417 and F-31102 assessment studies', was='About 70%').replace('about', 'About')} of the gauge variance on the two reworked fixtures lies between operators.</p>")
    body.append(exhibit(fm["split"], "Repeatability and reproducibility as shares of the gauge variance, reworked fixtures", f"Gauge variance on the assessment study, January {YEAR + 1}."))
    body.append(f"<p>Check fixtures read {num(cmm.mean_difference_mm, 'fixture_against_cmm.mean_difference_mm, to the assessment date', '{:.3f}', '0.014')} mm above the CMM on {num(cmm.matched_first_pieces, 'fixture_against_cmm.matched_first_pieces', was='163')} matched first pieces, "
                f"{pct(min(bias_share), 'fixture_against_cmm.mean_difference_mm over gauge_rr.tolerance_mm, lowest of the three studied fixtures', was='3%')} to {pct(max(bias_share), 'the same, highest', was='5%')} of the tolerance on the studied fixtures.</p>")
    body.append(exhibit(fk["cmm"], "Check fixture reading less CMM reading, matched first pieces", "The check fixture reads to 0.01 mm, so the differences fall on a grid."))
    body.append(f"<p>The burr check falls short. Operators agree with the burr gauge on {pct(b1.against_reference, 'attribute_agreement.against_reference, assessment study', was='80%')} of calls (kappa {num(b1.fleiss_kappa, 'attribute_agreement.fleiss_kappa, assessment study', '{:.2f}', '0.44')}), "
                f"and their reject rates run from {pct(op['reject_rate'].min(), 'attribute_by_operator.reject_rate, lowest, assessment study', was='27%')} to {pct(op['reject_rate'].max(), 'attribute_by_operator.reject_rate, highest, assessment study', was='75%')} on parts the gauge rejects at "
                f"{pct(b1.reference_reject_rate, 'attribute_agreement.reference_reject_rate, assessment study', was='52%')}.</p>")
    body.append(exhibit(fm["burr"], "Parts rejected on the burr check by operator, against the burr gauge", f"{int(b1.parts)} parts, {int(b1.trials)} trials each, against the limit samples; the vertical line is the share the burr gauge rejects."))
    body.append(f"<p>Keyed readings end in 0 or 5 at {num(em.loc['keyed', 'times_the_uniform_expectation'], 'entry_methods.times_the_uniform_expectation, keyed', '{:.2f}', '1.76')} times the expected rate. Paper transcriptions show no preference.</p>")
    body.append(exhibit(fm["digit"], "Last digit of the reading, by entry method", "Share of readings ending in each digit; the dashed line is the share if no digit were preferred."))
    body.append("<p>Readings show no pile-up at the specification limits on either entry method. Studying the check fixtures on critical characteristics, rebuilding the two reworked fixtures, and replacing the burr limit samples address these gaps.</p>")
    body.append(exhibit(fm["limit"], "Readings by distance from the nearer specification limit, by entry method", "A pile-up just inside the limit would show as a step at zero."))

    body.append(sub("sampling", "3.4 Sampling frequency and recording"))
    body.append(criterion("checks frequent enough to bound what a die event can pass, recorded on time on every shift."))
    WORD = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}; fa_ = found_after.set_index("defect_code")
    body.append("<p>Check frequency leaves wide windows on the high-speed presses, and recording holds on days but not on nights or at the start of the shift.</p><ul>"
                f"<li><strong>Window size:</strong> between two routine checks a press passes a median {num(rw['median_parts_between_checks_at_the_realised_rate'].min(), 'risk_window.median_parts_between_checks_at_the_realised_rate, lowest press', was='1,934')} to "
                f"{num(rw['median_parts_between_checks_at_the_realised_rate'].max(), 'risk_window.median_parts_between_checks_at_the_realised_rate, highest press', was='16,333')} parts at its realised rate, and up to {num(rw['most_parts_between_checks'].max(), 'risk_window.most_parts_between_checks, highest', was='38,160')} at run speed. "
                f"On the same 60- and 120-minute frequencies, the high-speed presses pass {word(min(ratios), WORD, 'risk_window: high-speed over medium median at the realised rate, same frequency, lowest pair', 'five')} to {word(max(ratios), WORD, 'the same, highest pair', 'six')} times what the medium presses pass.</li>"
                f"<li><strong>What the checks miss:</strong> in {YEAR}, {pct(fa_.loc['burr', 'found_after_the_press_share'], f'found_after_the_press.found_after_the_press_share, burr, {YEAR}', was='40%')} of burr nonconformances and "
                f"{pct(fa_.loc['missing or deformed hole', 'found_after_the_press_share'], f'found_after_the_press.found_after_the_press_share, missing or deformed hole, {YEAR}', was='33%')} of missing or deformed holes were found after the press, at the dock audit or the customer.</li></ul>")
    body.append(exhibit(fr["risk"], "Parts between routine checks, by press", f"Run speed and the realised stroke rate over {YEAR}; the bar is the range across each press's parts."))
    body.append(f"<p>The day shift records {pct(pc.loc[('all presses', 'days'), 'recorded_share'], 'planned_checks.recorded_share, all presses days', was='94%')} of planned checks, and nights {pct(pc.loc[('all presses', 'nights'), 'recorded_share'], 'planned_checks.recorded_share, all presses nights', was='84%')}. "
                f"The first check of the day shift is recorded on {pct(six.recorded_share, 'planned_checks_by_hour.recorded_share, all presses 06:00', was='76%')} of occasions, against {pct(rest.min(), 'planned_checks_by_hour.recorded_share, lowest other day hour', was='95%')} to {pct(rest.max(), 'planned_checks_by_hour.recorded_share, highest other day hour', was='97%')} at every later hour. "
                f"On nights the medium presses record {pct(pc.loc[('medium', 'nights'), 'recorded_share'], 'planned_checks.recorded_share, medium nights', 1, '80.8%')}, the lowest of any press group and shift.</p>")
    assert pc.loc[("medium", "nights"), "recorded_share"] == pc.drop(index="all presses", level=0)["recorded_share"].min()
    body.append(exhibit(frec["by_hour"], "Planned checks recorded by hour of the day and press group", "Share of planned checks with a routine check recorded."))
    body.append(f"<p>Recorded check times cluster on the hour: {pct(oh.loc['keyed', 'stamped_share'], 'on_the_hour.stamped_share, keyed', 1, '59.9%')} of keyed routine subgroups and {pct(oh.loc['paper transcription', 'stamped_share'], 'on_the_hour.stamped_share, paper', 1, '75.2%')} of times noted on paper fall within five minutes of it.</p>")
    body.append(exhibit(frec["minute"], "Routine subgroups by minute of the hour, keyed and paper", "Share of routine subgroups at each minute of the hour; the dashed line is uniform timing."))
    body.append(f"<p>{pct(e0.share, f'entry_after_the_parts.share, keyed {YEAR}', 1, '15.1%')} of keyed entries are made more than 20 minutes after the parts, in a second group that runs to about three hours. Connecting gauges to the terminals removes the delay on variable checks.</p>")
    body.append(exhibit(frec["entry"], "Minutes from the parts to the entry, keyed routine subgroups", "Minutes from the parts to the entry."))

    body.append(sub("reaction", "3.5 Reaction to signals"))
    body.append(criterion("every signal answered by the reaction its chart prescribes, with adjustments made only on a signal and recorded."))
    assert int(ack.acknowledged_with_text) == int(ack.alarms)
    body.append("<p>Signals are acknowledged but not acted on consistently, and adjustment at the press adds variation.</p><ul>"
                f"<li><strong>Software presses:</strong> all {num(ack.alarms, 'software_acknowledgements.alarms', was='10,474')} alarms were acknowledged, {num(ack.text_of_one_word, 'software_acknowledgements.text_of_one_word', was='4,691')} of them with a one-word text.</li>"
                f"<li><strong>Paper presses:</strong> an action is recorded on {pct(pa.action_share, 'paper_signals_all_subgroups.action_share', was='28%')} of signals.</li>"
                f"<li><strong>Adjusted characteristics:</strong> subgroup means swing back and forth within a coil, with a lag-1 autocorrelation of {num(a_adj.lag_1_autocorrelation, f'autocorrelation.lag_1_autocorrelation, {YEAR} adjusted', '{:.2f}', '-0.14')} against "
                f"{num(a_not.lag_1_autocorrelation, f'autocorrelation.lag_1_autocorrelation, {YEAR} not adjusted', '{:.2f}', '-0.07')} on the others.</li></ul>")
    body.append(exhibit(fa["autocorrelation"], "Lag-1 autocorrelation of subgroup means within a run and coil", "Lag-1 autocorrelation of subgroup means less their run-and-coil mean, pooled over segments of six subgroups or more."))
    body.append(f"<p>The adjusted characteristics carry {pct(v0.added_variance_median, 'variance.added_variance_median, no adjustment and no point beyond two sigma', 1, '9.9%')} more variance over all runs than in their runs with no adjustment, and {num(v0.characteristics_with_more_variance, 'variance.characteristics_with_more_variance', was='165')} of "
                f"{num(v0.characteristics, 'variance.characteristics', was='204')} are higher.</p>")
    body.append(exhibit(fa["variance"], "Added variance by adjusted characteristic", f"Each characteristic's variance over all {YEAR} runs against its runs with no adjustment and no point beyond two sigma, less one."))
    body.append(f"<p>{about([1 - s_est.iloc[1]['estimate']], 0.5, 'adjustment_estimate.estimate: one less the share of those adjustments recorded', 0.06, 'about 50%').replace('about 50%', 'About half')} of the adjustments are not recorded. An estimated "
                f"{pct(s_est.iloc[0]['estimate'], 'adjustment_estimate.estimate: an adjustment followed a point beyond two sigma, reference between one and two sigma', was='50%')} of points beyond two sigma are followed by an adjustment, and "
                f"{pct(ap.loc[(True, 'keyed'), 'recorded_share'], 'after_a_point.recorded_share, keyed', 1, '22.5%')} carry one in the record.</p>")
    body.append(exhibit(fa["return"], "Position of the next subgroup as a share of the point's position, by group of points", "0 is a full return to the centre line, 1 no return."))
    body.append("<p>On a single run the pattern is visible: an adjustment followed by a mean on the other side of the centre line, and limits rising to absorb a coil at its own level. A written reaction plan that ties adjustment to a signal or a coil change addresses this.</p>")
    body.append(exhibit(fa["run"], "Two runs with recorded adjustments", "Subgroup means with the software's limits as in force at each entry; circles are recorded adjustments."))

    # -- 4. Sources of variation ---------------------------------------------
    body.append(section("sources", "4. Sources of variation"))
    body.append("<p>Three sources of variation explain why the gaps in Section 3 fall on formed characteristics, hole diameters and burr.</p>")
    body.append(sub("coils", "4.1 Coil-to-coil shifts"))
    body.append(f"<p>Coil-to-coil shifts are the largest source on formed characteristics. {pct(cs.loc['formed', 'share_between_coils'], 'capability_summary.share_between_coils, formed', was='54%')} of their variance lies between coils, against {pct(cs.loc['punched', 'share_between_coils'], 'capability_summary.share_between_coils, punched', was='2%')} on punched characteristics, "
                f"where {pct(cs.loc['punched', 'share_within_subgroup'], 'capability_summary.share_within_subgroup, punched', was='88%')} lies within the subgroup.</p>")
    body.append(exhibit(fk["components"], "Overall variance by component, formed and punched characteristics", "Median shares across studies, nested random-effects model."))
    body.append(f"<p>A coil's level is predictable from its certificate. Thickness and hardness leave {pct(coil.certificate_residual_sd_share_of_tolerance_median, 'coil_regression_summary.certificate_residual_sd_share_of_tolerance_median', 1, '2.5%')} of tolerance about the fit, against "
                f"{pct(coil.sd_of_coil_means_share_of_tolerance_median, 'coil_regression_summary.sd_of_coil_means_share_of_tolerance_median', 1, '12.1%')} between coil means. Charting formed characteristics on limits that carry coil-to-coil variation, with a centring step at each coil change, addresses this source.</p>")
    body.append(exhibit(fk["coil"], "Coil mean against certificate thickness, and the spread about the fit", "Coil means of one formed height against certificate thickness (left); spread as a share of tolerance, every study window (right)."))

    body.append(sub("wear", "4.2 Die wear"))
    body.append(f"<p>Die wear drives the burr nonconformances and the hole-diameter drift. {num(rp.burr_nonconformances_past_the_interval, 'runs_past_the_interval.burr_nonconformances_past_the_interval', was='60')} of the {num(rp.burr_nonconformances_with_shots_known, 'runs_past_the_interval.burr_nonconformances_with_shots_known', was='61')} burr nonconformances of {YEAR} "
                f"fell on runs past the die's stated sharpening interval, against {pct(rp.share_of_runs_past, 'runs_past_the_interval.share_of_runs_past', was='17%')} of all runs.</p>")
    body.append(exhibit(fw["position"], "Burr nonconformances by the die's position in its sharpening interval", "Shots since sharpening at the end of the run, as a multiple of the stated sharpening interval."))
    body.append(f"<p>Sharpening runs late, and the stated interval is often set too long. Sharpenings are logged at a median {num(il.logged_over_stated_median, 'intervals_as_logged.logged_over_stated_median', '{:.2f}', '1.14')} times the stated interval. On {num(bs.interval_longer_than_the_80pct_count, 'burr_summary.interval_longer_than_the_80pct_count', was='41')} of "
                f"{num(bs.dies_fitted, 'burr_summary.dies_fitted', was='124')} dies the stated interval is longer than the shot count at which burr reaches 80% of its limit.</p>")
    body.append(exhibit(fw["count"], "Shot count at 80% of the burr limit against the sharpening interval, by die", "Dies below the line are sharpened later than their burr allows."))
    body.append(f"<p>On die {fw['burr_die']} burr reaches 80% of its limit at {num(kb.shots_at_80pct_of_limit, 'burr_by_die.shots_at_80pct_of_limit, the die shown', was='364,211')} shots, against a stated interval of {num(kb.sharpening_interval_shots, 'burr_by_die.sharpening_interval_shots, the die shown', was='400,000')} and a median "
                f"{num(kb.logged_interval_median, 'burr_by_die.logged_interval_median, the die shown', was='471,403')} as run.</p>")
    body.append(exhibit(fw["burr"], f"Burr height against shots since sharpening, die {fw['burr_die']}", f"Burr gauge subgroups, {YEAR - 1} and {YEAR}, as a share of the burr limit."))
    body.append(f"<p>Hole diameters grow at a steady rate within each interval: {num(hdie.slope_mm_per_100k_shots, 'hole_diameter_by_die.slope_mm_per_100k_shots, D-0417-B', '{:.4f}', '0.0092')} mm per 100,000 shots on D-0417-B, and {num(hs.slope_by_die_lowest, 'hole_diameter_summary.slope_by_die_lowest', '{:.4f}', '0.0040')} to "
                f"{num(hs.slope_by_die_highest, 'hole_diameter_summary.slope_by_die_highest', '{:.4f}', '0.0094')} mm across dies. That is {pct(hdd['growth_as_share_of_tolerance'].min(), 'hole_diameter_by_die.growth_as_share_of_tolerance, lowest', was='16%')} to "
                f"{pct(hs.growth_as_share_of_tolerance_highest, 'hole_diameter_summary.growth_as_share_of_tolerance_highest', was='32%')} of tolerance over a stated interval. Setting each die's interval from its burr regression and pulling the die at the count addresses both burr and hole size.</p>")
    body.append(exhibit(fw["hole"], "Hole diameter against shots since sharpening, die D-0417-B", f"Each colour is one sharpening interval of {YEAR}."))

    body.append(sub("events", "4.3 Die events between checks"))
    body.append(f"<p>Die events between checks cause most sorting, and the check before sets how much is sorted. {num(y25.traced_to_a_die_event_between_two_checks, f'sorting_summary.traced_to_a_die_event_between_two_checks, {YEAR}', was='12')} of the {num(y25.sorting_events, f'sorting_summary.sorting_events, {YEAR}', was='14')} sorting events of {YEAR} trace to a die event between two checks. "
                f"Where a die-protection fault bounds the event, the shop sorted a median {num(flt.quantity_sorted_median, 'sorting_by_basis.quantity_sorted_median, from a logged fault', was='3,374')} parts. Where none does, it sorted back to the check before, a median {num(inh.quantity_sorted_median, 'sorting_by_basis.quantity_sorted_median, back to the check in-house', was='4,996')}.</p>")
    body.append(exhibit(fr["exposure"], "Quantity sorted against parts made since the check before", "Points on the line sorted everything made since the check before; points below it are bounded by a die-protection fault."))
    body.append(f"<p>Sorting back to the check before mostly sorts good parts: {pct(inh.rejected_share, 'sorting_by_basis.rejected_share, back to the check in-house', was='37%')} are rejected, against {pct(flt.rejected_share, 'sorting_by_basis.rejected_share, from a logged fault', was='77%')} where a fault bounds the event.</p>")
    body.append(exhibit(fr["rejected"], "Rejected share of the quantity sorted, by basis of the sorting", f"Pieces rejected over pieces sorted, pooled over events, {YEAR - 1} and {YEAR}."))
    assert all(cost.loc[y_, "back_cost"] == cost.loc[y_, "largest_basis_group_cost"] for y_ in (YEAR - 1, YEAR))
    body.append(f"<p>Sorting back to the check before carries the largest share of sorting cost in both years: ${num(cost.loc[YEAR, 'back_cost'], f'mart_sorting_events.sorting_cost_booked_or_estimated, sorted back to the check before, {YEAR}', was='3,739')} of ${num(cost.loc[YEAR, 'cost'], f'mart_sorting_events.sorting_cost_booked_or_estimated, {YEAR}', was='8,674')} in {YEAR}, and "
                f"${num(cost.loc[YEAR - 1, 'back_cost'], f'mart_sorting_events.sorting_cost_booked_or_estimated, sorted back to the check before, {YEAR - 1}', was='4,237')} of ${num(cost.loc[YEAR - 1, 'cost'], f'mart_sorting_events.sorting_cost_booked_or_estimated, {YEAR - 1}', was='12,500')} in {YEAR - 1}. "
                "A per-stroke record would bound these events at the stroke.</p>")
    body.append(exhibit(fr["years"], f"Sorting events and cost by year and basis of the sorting, {YEAR - 1} and {YEAR}", "Cost as booked, with the estimate for sorting booked to the run."))
    n_body_figures = FIGURE[0]

    # -- Appendix: the method note and tables only ----------------------------
    SECTION[0] = "Appendix"
    th = {t_[0]: t_ for t_ in scope.THRESHOLDS}

    def thresholds(*names):
        return titled_table("Thresholds behind the status", simple_table(["Area", "Measure", "Holds", "Partial", "Does not hold", "Basis"], [th[n_] for n_ in names]))

    ax = ['<h2 id="appendix">Appendix</h2>', "<h3>Method and data</h3>", METHOD]
    ax.append("<h3>Chart selection and limits (Section 3.1)</h3>")
    ax.append(thresholds("Chart and limits: the chart fits the variation", "Chart and limits: the limits as set"))
    ax.append(show(c["chart_audit"], {"limits_as_set_method": "Limits as set", "press_group": "Presses", "characteristics": "Characteristics", "critical_characteristics": "Critical", "subgroups": f"Subgroups, {YEAR}", "subgroups_with_a_reading_set_aside": "With a reading set aside",
                                      "subgroups_used_to_set": "Subgroups used to set", "signals_rule_1": "Rule 1 signals", "signals_any_rule": "Signals, any rule", "signals_with_action_recorded": "With an action recorded"}, {"subgroups": F0, "subgroups_with_a_reading_set_aside": F0, "signals_rule_1": F0, "signals_any_rule": F0, "signals_with_action_recorded": F0, "subgroups_used_to_set": F0}))
    ax.append(show(c["signal_comparison"], {"limits_as_set_method": "Limits as set", "characteristic_class": "Class", "characteristics": "Characteristics", "subgroups": "Subgroups compared", "signals_as_computed": "Signals as computed", "signals_as_set": "Signals as set", "signals_by_both": "By both",
                                            "share_of_computed_also_set": "Share of computed also set", "share_low": "Low", "share_high": "High", "rate_as_set_per_100": "As set per 100", "rate_as_computed_per_100": "As computed per 100"},
                   {"subgroups": F0, "signals_as_computed": F0, "signals_as_set": F0, "signals_by_both": F0, "share_of_computed_also_set": P1, "share_low": P1, "share_high": P1, "rate_as_set_per_100": F1, "rate_as_computed_per_100": F1}))
    lm = mx["limits"].assign(m=lambda x: x["limits_as_set_method"].map({"rolling 25 at entry": "Software presses, rolling limits", "PPAP study": "Paper presses, printed limits"}))
    ax.append(show(lm.sort_values(["m", "characteristic_class"]), {"m": "Presses and limits as set, by matrix class", "characteristic_class": "Class", "characteristics": "Characteristics", "subgroups": "Subgroups", "as_set_per_100": "As set per 100", "as_computed_per_100": "As computed per 100", "set_over_computed": "As set over as computed"},
                   {"subgroups": F0, "as_set_per_100": F1, "as_computed_per_100": F1, "set_over_computed": lambda v: "" if v != v else f"{v:.2f}"}))
    ax.append(show(c["baseline_coverage"], {"baseline_basis": "Baseline after the sharpening", "intervals": "Intervals", "characteristics": "Characteristics", "usable_subgroups": "Usable subgroups"}, {"intervals": F0, "usable_subgroups": F0}))
    rl_ = c["run_lengths"][c["run_lengths"]["in_report"]]
    ax.append(show(rl_, {"limits_as_set_method": "Presses by limits as set", "characteristic_class": "Class", "limits": "Limits", "arl_in_control": "ARL in control", "arl_shift_1_sigma": "ARL, 1 sigma shift", "arl_shift_1_5_sigma": "ARL, 1.5 sigma shift"}, {"arl_in_control": F1, "arl_shift_1_sigma": F2, "arl_shift_1_5_sigma": F2}))
    ax.append(show(c["paper_limit_age"], {"dies": "Dies on the paper presses", "characteristics": "Characteristics", "dies_with_every_limit_set_at_the_most_recent_rebuild": "Limits set at the most recent rebuild", "months_in_force_median": "Months in force, median", "months_in_force_max": "Longest",
                                          "sharpenings_since_set_median": "Sharpenings since, median", "sharpenings_since_set_max": "Most"}, {"months_in_force_median": F1, "months_in_force_max": F1, "sharpenings_since_set_median": F0}))
    ax.append(f"<div class='caption'>Coverage: subgroups of {YEAR} with limits in force; subgroups before a die's first logged sharpening carry no computed limits. Shifts in the run length table are in units of the within-subgroup sigma of the mean; the spread of means between subgroups is in the model. "
              f"On the paper presses the printed limits signalled on {P1(pa.signal_rate)} of all subgroups with limits in force.</div>")

    ax.append("<h3>Capability (Section 3.2)</h3>")
    ax.append(thresholds("Capability"))
    ax.append(show(k["capability_summary"], {"characteristic_class": "Class", "studies": "Studies", "characteristics": "Characteristics", "subgroups": "Subgroups", "readings": "Readings", "subgroups_set_aside": "Subgroups set aside", "filed_ppk": "Ppk filed", "cpk": "Cpk", "cpk_low": "Low", "cpk_high": "High", "ppk": "Ppk",
                                             "ppk_low": "Ppk low", "ppk_high": "Ppk high", "studies_filed_at_least_0_40_above": "Studies filed at least 0.40 above", "studies_within_0_25": "Studies within 0.25"},
                   {"subgroups": F0, "readings": F0, "filed_ppk": F2, "cpk": F2, "cpk_low": F2, "cpk_high": F2, "ppk": F2, "ppk_low": F2, "ppk_high": F2}))
    ax.append(show(k["punched_by_type"], {"characteristic_type": "Punched characteristic", "studies": "Studies", "filed_ppk": "Ppk filed", "production_ppk": "Production Ppk", "production_cpk": "Production Cpk", "filed_at_least_0_40_above": "Filed at least 0.40 above", "within_0_25": "Within 0.25"},
                   {"filed_ppk": F2, "production_ppk": F2, "production_cpk": F2}))
    ax.append(show(k["bounded_summary"], {"characteristic_type": "Bounded characteristic", "characteristics": "Characteristics", "readings": "Readings", "normal_fit_rejected": "Normal fit rejected (Anderson-Darling)", "box_cox_fit_rejected": "Rejected after Box-Cox", "box_cox_lambda_median": "Box-Cox lambda", "ppu_percentile_median": "Ppu, percentile",
                                          "ppu_normal_median": "Ppu, normal", "ppu_box_cox_median": "Ppu, Box-Cox"}, {"readings": F0, "box_cox_lambda_median": F2, "ppu_percentile_median": F2, "ppu_normal_median": F2, "ppu_box_cox_median": F2}))
    losses = losses.assign(ppm_interval=[f"{x.ppm:,.0f} ({x.low:,.0f} to {x.high:,.0f})" for x in losses.itertuples()])
    ax.append(show(losses, {"year": "Quality losses, all presses, year", "scrap_booked": "Scrap booked, $", "rework_labor_booked": "Rework labor booked, $", "revenue": "Revenue, $", "scrap_and_rework_share_of_revenue": "Share of revenue", "complaints": "Complaints", "pieces_rejected": "Pieces rejected",
                            "pieces_shipped": "Pieces shipped", "ppm_interval": "PPM (95% interval)", "sorting_events": "Sorting events", "quantity_sorted": "Quantity sorted", "sorting_cost_booked_or_estimated": "Sorting cost, $"},
                   {"year": lambda v: f"{int(v)}", "scrap_booked": F0, "rework_labor_booked": F0, "revenue": F0, "scrap_and_rework_share_of_revenue": lambda v: f"{v * 100:.2f}%", "complaints": F0, "pieces_rejected": F0, "pieces_shipped": F0, "sorting_events": F0, "quantity_sorted": F0,
                    "sorting_cost_booked_or_estimated": F0}))
    ax.append(f"<div class='caption'>Coverage: every critical characteristic with a PPAP study in the record, on the production record of the twelve months after the study or to 31 December {YEAR}. Capability intervals in the table are the bootstrap interval of the median over studies.</div>")

    ax.append("<h3>Measurement systems (Section 3.3)</h3>")
    ax.append(thresholds("Measurement: the study result", "Measurement: coverage"))
    fxs = fx[fx["pct_grr_of_tolerance"].notna()].sort_values(["study_date", "gauge_id"])
    ax.append(show(fxs, {"gauge_id": "Check fixture, latest study on file", "location": "Location", "study_date": "Study date", "trigger": "Trigger as recorded", "pct_grr_of_tolerance": "%GRR of tolerance", "ndc": "ndc"}, {"study_date": lambda v: str(v)[:10], "pct_grr_of_tolerance": F1, "ndc": F0}))
    ax.append(show(mx["measurement"], {"characteristic_class": "Class", "characteristics": f"Characteristics charted in {YEAR}", "gauges": "Gauges", "gauges_with_a_study": "With a study on file", "pct_grr_median": "%GRR, median", "pct_grr_highest": "Highest", "studies_over_30": "Over 30%",
                                       "characteristics_on_a_gauge_with_no_study": "Characteristics on a gauge with no study"}, {"pct_grr_median": lambda v: "" if v != v else f"{v:.1f}", "pct_grr_highest": lambda v: "" if v != v else f"{v:.1f}"}))
    study_name = {"PPAP": "PPAP", "redesign": f"assessment, January {YEAR + 1}"}
    gt = m["gauge_rr"][m["gauge_rr"]["study"].isin(study_name)].assign(study=lambda x: x["study"].map(study_name)).reset_index(drop=True)
    ax.append(show(gt, {"fixture": "Fixture", "study": "Study", "study_date": "Date", "tolerance_mm": "Tolerance, mm", "recorded_pct_tolerance": "%GRR as recorded", "pct_tolerance": "%GRR of tolerance", "pct_study_variation": "%Study variation", "ndc": "ndc", "repeatability_sd_mm": "Repeatability SD, mm",
                        "reproducibility_sd_mm": "Reproducibility SD, mm", "reproducibility_share_of_grr": "Reproducibility share of gauge variance", "interaction_p": "Interaction p"},
                   {"study_date": lambda v: str(v)[:10], "tolerance_mm": F2, "recorded_pct_tolerance": F1, "pct_tolerance": F1, "pct_study_variation": F1, "repeatability_sd_mm": F4, "reproducibility_sd_mm": F4, "reproducibility_share_of_grr": P0, "interaction_p": F3}))
    for key in sorted(m["anova_tables"]):
        if key[1] in study_name:
            ax.append(anova_block((key[0], study_name[key[1]]), m["anova_tables"][key]))
    ax.append(show(m["measurement_share"], {"fixture": "Fixture", "characteristic_id": "Characteristic", "period": f"Period of {YEAR}", "readings": "Readings", "production_sd_mm": "Production SD, mm", "gauge_sd_mm": "Gauge SD, mm", "measurement_share_of_variance": "Measurement share of variance", "measurement_share_whole_year": f"All of {YEAR}"},
                   {"readings": F0, "production_sd_mm": F4, "gauge_sd_mm": F4, "measurement_share_of_variance": P1, "measurement_share_whole_year": P1}))
    ax.append(show(k["fixture_against_cmm"][k["fixture_against_cmm"]["group"] == "all fixtures, before the redesign"].assign(group=f"all fixtures, to 31 December {YEAR}"), {"group": "Matched first pieces", "matched_first_pieces": "Parts", "fixtures": "Fixtures", "mean_difference_mm": "Fixture less CMM, mm", "low": "Low", "high": "High", "sd_mm": "SD, mm", "p_value": "p"},
                   {"mean_difference_mm": F3, "low": F3, "high": F3, "sd_mm": F3, "p_value": lambda v: "under 0.001" if v < 0.001 else f"{v:.3f}"}))
    ax.append(show(m["attribute_agreement"][m["attribute_agreement"]["study"] == "at the redesign"].assign(study=f"assessment, January {YEAR + 1}"), {"study": "Burr check study", "calls": "Calls", "within_operator": "Within operator", "all_operators_agree": "All operators agree", "pairs_of_operators_agree": "Pairs of operators agree", "against_reference": "Against the burr gauge", "reference_low": "Low", "reference_high": "High", "fleiss_kappa": "Fleiss' kappa", "kappa_low": "Kappa low", "kappa_high": "Kappa high"},
                   {"within_operator": P0, "all_operators_agree": P0, "pairs_of_operators_agree": P0, "against_reference": P1, "reference_low": P1, "reference_high": P1, "fleiss_kappa": F2, "kappa_low": F2, "kappa_high": F2}))
    ax.append(show(op, {"operator": "Operator, burr check study", "reject_rate": "Parts rejected", "reference_reject_rate": "Rejected by the burr gauge", "against_reference": "Agreement with the burr gauge"}, {"reject_rate": P0, "reference_reject_rate": P0, "against_reference": P0}))
    ax.append(show(m["entry_methods"][m["entry_methods"]["entry_method"] != "gauge-connected"], {"entry_method": "Entry method", "readings": f"Readings, {YEAR}", "ending_0_or_5": "Ending in 0 or 5", "times_the_uniform_expectation": "Times the uniform rate", "chi_square_last_digit": "Chi-square, last digit", "set_aside_by_the_plausibility_rule": "Set aside as mis-keyed", "at_or_one_step_inside_a_limit": "At or one step inside a limit",
                                        "one_or_two_steps_outside_a_limit": "One or two steps outside"}, {"readings": F0, "ending_0_or_5": F0, "times_the_uniform_expectation": F2, "chi_square_last_digit": F0, "set_aside_by_the_plausibility_rule": F0, "at_or_one_step_inside_a_limit": F0, "one_or_two_steps_outside_a_limit": F0}))
    ax.append(show(m["reading_steps"], {"reading_step": "Reading step", "characteristics": "Characteristics"}, {"reading_step": lambda v: f"{v:g}"}))
    ax.append(f"<div class='caption'>A check fixture carries its own study; a hand gauge is covered by the latest study of its family, the gauges of its type at its press. Studies on file are to 16 January {YEAR + 1}. The reading step of a characteristic is inferred from its own readings: the coarsest of 1, 0.5, 0.1, 0.05, 0.01, 0.005 and 0.001 that 99% of its readings sit on. "
              f"The chi-square on the last digit is large on both entry methods because the distributions are narrow on their reading steps. Measurement share is on the months after each fixture's last rework. {em.loc['keyed', 'set_aside_share'] * 100:.2f}% of keyed readings cannot be a measurement of the part and are set aside from every figure in this report. "
              f"Gauge status, {YEAR}: {F0(gs.on_a_gauge_out_of_service)} of {F0(gs.subgroups)} subgroups on a gauge away for calibration that day, {F0(gs.on_a_gauge_past_due)} on a gauge past due; {F0(gs.gauges_recorded_as_lost)} gauge is recorded as lost, and no characteristic and no subgroup carries it.</div>")

    ax.append("<h3>Sampling frequency and recording (Section 3.4)</h3>")
    ax.append(thresholds("Sampling frequency"))
    ax.append(show(rw, {"press_id": "Press", "parts": "Parts", "runs": f"Runs, {YEAR}", "strokes_per_minute": "Strokes a minute, median", "plan_frequency_minutes": "Check frequency, minutes", "fewest_parts_between_checks": "Fewest parts between checks", "median_parts_between_checks": "Median", "most_parts_between_checks": "Most",
                        "realised_share_of_run_speed": "Realised share of run speed", "median_parts_between_checks_at_the_realised_rate": "Median at the realised rate"},
                   {"strokes_per_minute": F0, "plan_frequency_minutes": F0, "fewest_parts_between_checks": F0, "median_parts_between_checks": F0, "most_parts_between_checks": F0, "realised_share_of_run_speed": F2, "median_parts_between_checks_at_the_realised_rate": F0}))
    ax.append(show(mx["sampling"], {"characteristic_class": "Class", "characteristics": "Characteristics with routine checks", "frequency_minutes_median": "Check frequency, minutes, median", "parts_between_checks_median": "Parts between checks at the realised rate, median", "parts_between_checks_p90": "90th percentile"},
                   {"frequency_minutes_median": F0, "parts_between_checks_median": F0, "parts_between_checks_p90": F0}))
    ax.append(show(found_after, {"defect_code": f"Nonconformances of {YEAR} by defect code", "at_the_press": "Found at the press", "at_the_dock_audit": "At the dock audit", "at_the_customer": "At the customer", "nonconformances": "All", "found_after_the_press_share": "Found after the press"},
                   {"found_after_the_press_share": P0}))
    ax.append(show(rec["planned_checks"], {"press_group": "Presses", "shift": "Shift", "planned_checks": f"Planned checks, {YEAR}", "recorded": "Recorded", "recorded_share": "Share", "recorded_share_low": "Low", "recorded_share_high": "High"}, {"press_group": lambda v: v.replace("_", "-"), "planned_checks": F0, "recorded": F0, "recorded_share": P1, "recorded_share_low": P1, "recorded_share_high": P1}))
    ax.append(show(ph[ph["press_group"] == "all presses"], {"hour_of_day": "Planned time, hour", "shift": "Shift", "planned_checks": "Planned checks", "recorded": "Recorded", "recorded_share": "Share"}, {"hour_of_day": lambda v: f"{int(v):02d}:00", "planned_checks": F0, "recorded": F0, "recorded_share": P1}))
    ax.append(show(rec["on_the_hour"], {"entry_method": "Routine subgroups", "subgroups": "Subgroups", "stamped_within_five_minutes_of_the_hour": "Stamped within five minutes of the hour", "stamped_share": "Share", "parts_time_share": "On the time of the parts"}, {"subgroups": F0, "stamped_within_five_minutes_of_the_hour": F0, "stamped_share": P1, "parts_time_share": P1}))
    ax.append(show(rec["entry_after_the_parts"].iloc[:1], {"record": "Record", "subgroups": "Subgroups", "entered_more_than_20_minutes_after": "Entered more than 20 minutes after the parts", "share": "Share", "share_low": "Low", "share_high": "High", "minutes_to_entry_median": "Minutes to entry, median"},
                   {"subgroups": F0, "entered_more_than_20_minutes_after": F0, "share": P1, "share_low": P1, "share_high": P1, "minutes_to_entry_median": F1}))
    ax.append(show(rec["short_runs"].reset_index() if "run_length" not in rec["short_runs"].columns else rec["short_runs"], {"run_length": "Runs by length", "runs": "Runs", "with_no_routine_check": "With no routine check"}, {"runs": F0, "with_no_routine_check": F0}))
    pwt = pw.assign(share=pw["share"], low=pw["low"], high=pw["high"])
    ax.append(show(pwt, {"measure": "Plant-wide item", "shift": "Shift", "count": "Count", "with": "With", "share": "Share", "low": "Low", "high": "High"}, {"count": F0, "with": F0, "share": P1, "low": P1, "high": P1}))
    ax.append("<div class='caption'>The realised stroke rate is strokes over working clock time (06:00 to 23:00 on days the press recorded a check), per press over all runs of the year. A planned check falls on the clock at the part's check frequency, between 06:00 and 23:00 on a day the press recorded a check, from 20 minutes after production started to 2 minutes before the run ended, on runs of two hours or more; "
              "it is recorded when the run carries a routine check from 6 minutes before it to 31 minutes after. The plan counts planned times at which the press may have stood, so the figures understate recording by that amount; the contrast between shifts holds either way. The first check of the shift is the first planned hour of each shift. "
              "Plant-wide items are tinted by the share: 90% or more holds, 50% to 90% is partial, under 50% does not hold; entries made more than 20 minutes after the parts are judged on the share made within 20 minutes.</div>")

    ax.append("<h3>Reaction to signals (Section 3.5)</h3>")
    ax.append(thresholds("Reaction"))
    ax.append(show(c["software_acknowledgements"], {"alarms": f"Software alarms, {YEAR}", "rule_1": "Rule 1", "rule_2_only": "Rule 2 only", "acknowledged_with_text": "Acknowledged with a text", "text_of_one_word": "Text of one word", "adjustment_recorded": "Adjustment recorded"}, {k_: F0 for k_ in ("alarms", "rule_1", "rule_2_only", "acknowledged_with_text", "text_of_one_word", "adjustment_recorded")}))
    ax.append(show(c["paper_actions"], {"characteristic_class": "Paper presses, class", "characteristics": "Characteristics", "subgroups": "Subgroups", "signals": "Signals", "signals_with_action_recorded": "With an action recorded", "action_share": "Share", "action_share_low": "Low", "action_share_high": "High"}, {"subgroups": F0, "signals": F0, "signals_with_action_recorded": F0, "action_share": P1, "action_share_low": P1, "action_share_high": P1}))
    ax.append(show(a["return_toward_centre"], {"entry_method": "Entry", "points_group": "Points", "points": "Count", "characteristics": "Characteristics", "mean_position_in_sigma": "Mean position, sigma", "next_as_share_of_position": "Next subgroup as a share of the position", "low": "Low", "high": "High"},
                   {"points": F0, "mean_position_in_sigma": F2, "next_as_share_of_position": F2, "low": F2, "high": F2}))
    ax.append(show(a["autocorrelation"][a["autocorrelation"]["period"].str.startswith(str(YEAR))], {"characteristics": f"Characteristics, {YEAR}", "lag_1_autocorrelation": "Lag-1 autocorrelation", "low": "Low", "high": "High", "segments": "Segments", "characteristics_n": "Characteristics, count"}, {"lag_1_autocorrelation": F3, "low": F3, "high": F3, "segments": F0}))
    ax.append(show(a["variance"], {"comparison_runs": "Comparison runs", "characteristics": "Characteristics", "added_variance_median": "Added variance, median", "low": "Low", "high": "High", "characteristics_with_more_variance": "Characteristics with more variance"}, {"added_variance_median": P1, "low": P1, "high": P1}))
    ax.append(show(mx["added_variance"], {"characteristic_class": "Adjusted characteristics by class", "adjusted_characteristics": "Characteristics", "added_variance_median": "Added variance, median", "low": "Low", "high": "High", "with_more_variance": "With more variance"}, {"added_variance_median": P1, "low": P1, "high": P1}))
    ax.append(show(a["after_a_point"], {"adjusted_at_the_press": "Adjusted at the press", "entry_method": "Entry", "points": "Points beyond two sigma or the printed limit", "adjustment_recorded": "Adjustment recorded", "recorded_share": "Share", "points_with_a_next_subgroup": "With a next subgroup", "next_on_the_other_side_beyond_one_sigma": "Next on the other side by more than one sigma", "other_side_share": "Share of those"},
                   {"adjusted_at_the_press": lambda v: "yes" if v else "no", "points": F0, "adjustment_recorded": F0, "recorded_share": P1, "points_with_a_next_subgroup": F0, "next_on_the_other_side_beyond_one_sigma": F0, "other_side_share": P1}))
    ax.append(f"<div class='caption'>Routine subgroups on variable characteristics with limits in force; position is the subgroup mean less the centre line in units of the chart's sigma of the mean. A characteristic adjusted at the press is a formed height, a bend angle or a hole-to-edge position; no characteristic of another type carries a recorded adjustment in {YEAR}. "
              f"The sign change after a point (last table) is the measure first named for an unrecorded adjustment; it does not separate adjusted characteristics from the rest and is not used as a count. Estimated, on the points between one and two sigma as the reference for a point left alone: an adjustment followed {P1(s_est.iloc[0]['estimate'])} of points beyond two sigma on keyed entry ({P1(s_est.iloc[0]['low'])} to {P1(s_est.iloc[0]['high'])}), "
              f"{P1(s_est.iloc[1]['estimate'])} of them recorded. In the first variance row the reference leaves out runs with a special cause, so the figure includes their variance; in the second the reference includes runs with an unrecorded adjustment, so the figure understates. "
              f"The two runs shown are {k1['characteristic_id']} on run {k1['run_id']}, the single-coil run of a formed characteristic on a software press with the most recorded adjustments in {YEAR}, and {k2['characteristic_id']} on run {k2['run_id']}, the run with the most among all such runs.</div>")

    ax.append("<h3>Coil-to-coil variation (Section 4.1)</h3>")
    ax.append(show(k["capability_summary"], {"characteristic_class": "Variance components by class", "share_between_coils": "Between coils", "share_between_coils_low": "Low", "share_between_coils_high": "High", "share_between_subgroups_within_coil": "Between subgroups within coil", "share_within_subgroup": "Within subgroup",
                                             "between_over_within_variance": "Between over within variance"},
                   {"share_between_coils": P0, "share_between_coils_low": P0, "share_between_coils_high": P0, "share_between_subgroups_within_coil": P0, "share_within_subgroup": P0, "between_over_within_variance": F2}))
    ax.append(show(k["coil_regression_summary"], {"characteristics": "Formed heights fitted", "study_windows": "Study windows", "coils_median": "Coils a window, median", "sd_of_coil_means_share_of_tolerance_median": "Spread of coil means, share of tolerance", "certificate_residual_sd_share_of_tolerance_median": "Spread about the certificate fit",
                                                  "receiving_residual_sd_share_of_tolerance_median": "About the receiving fit", "certificate_r_squared_median": "R-squared, certificate", "receiving_r_squared_median": "R-squared, receiving"},
                   {"coils_median": F0, "sd_of_coil_means_share_of_tolerance_median": P1, "certificate_residual_sd_share_of_tolerance_median": P1, "receiving_residual_sd_share_of_tolerance_median": P1, "certificate_r_squared_median": F2, "receiving_r_squared_median": F2}))

    ax.append("<h3>Die wear (Section 4.2)</h3>")
    ax.append(show(w["hole_diameter_by_die"].sort_values("slope_mm_per_100k_shots", ascending=False), {"die_id": "Die", "characteristic_id": "Hole diameter", "intervals": "Intervals", "subgroups": "Subgroups", "slope_mm_per_100k_shots": "Growth, mm per 100,000 shots", "slope_low": "Low", "slope_high": "High", "r_squared_within_intervals": "R-squared within intervals",
                                                                                                         "sharpening_interval_shots": "Stated interval, shots", "growth_as_share_of_tolerance": "Growth over the interval, share of tolerance"},
                   {"slope_mm_per_100k_shots": F4, "slope_low": F4, "slope_high": F4, "r_squared_within_intervals": F2, "sharpening_interval_shots": F0, "growth_as_share_of_tolerance": P0}))
    bsum = pd.DataFrame([(f"Dies fitted (30 burr gauge subgroups or more, {YEAR - 1} and {YEAR})", F0(bs.dies_fitted)), ("Burr gauge subgroups per die, median", F0(bd["subgroups"].median())), ("R-squared by die, median", F2(bs.r_squared_median)),
                         ("Shots at 80% of the burr limit, median by die", F0(bs.shots_at_80pct_median)), ("Stated sharpening interval, median over the same dies", F0(bs.sharpening_interval_median)),
                         ("Dies whose stated interval is longer than the count at 80%", f"{F0(bs.interval_longer_than_the_80pct_count)} of {F0(bs.dies_fitted)}"), ("The same, longer than the upper bound of the count", F0(bs.the_same_beyond_the_upper_bound_of_the_count)),
                         ("Dies whose interval as run (logged median) is longer than the count at 80%", f"{logged_longer} of {logged_n}"), ("Dies whose stated interval is longer than the count at the limit", F0(bs.interval_longer_than_the_count_at_the_limit)),
                         (f"Run intervals ending in {YEAR} with shot counts at both ends", F0(il.intervals_with_shot_counts)),
                         (f"Logged intervals ending in {YEAR}, and those left out", f"A logged interval under 20,000 shots is a sharpening followed by a rebuild, or an entry with no shots between it and the one beside it, and is not a run interval; {F0(il.left_out_as_not_run_intervals)} of the {F0(il.logged_intervals)} intervals ending in {YEAR} are left out on this rule."),
                         ("Logged shots over the stated interval, median (quartiles)", f"{il.logged_over_stated_median:.2f} ({il.lower_quartile:.2f} to {il.upper_quartile:.2f})"), ("Intervals longer than stated", P0(il.share_longer_than_stated))], columns=["Burr height on the burr gauge against shots since sharpening", "Value"])
    ax.append(S.table(bsum))
    ax.append(show(w["burr_nonconformances"], {"defect_code": "Defect code", "detected_at": "Detected at", "nonconformances": f"Nonconformances, {YEAR}", "quantity_affected": "Quantity affected", "with_shots_since_sharpening": "With shots known", "within_the_sharpening_interval": "Run ended within the stated interval", "past_the_sharpening_interval": "Past it",
                                               "share_of_the_interval_median": "Position, median"}, {"quantity_affected": F0, "share_of_the_interval_median": F2}))
    ax.append("<div class='caption'>Subgroup means of variable readings with the die's shots since sharpening known; first-piece, routine and last-piece subgroups. A sharpening interval enters the hole diameter regression with at least 15 subgroups spanning at least 60,000 shots. The burr fit pools each die's intervals on one line, with burr near a quarter of the limit at every sharpening. "
              "The stated sharpening interval is the die room's figure in the die master. The defect code \"hole burr and size\" is shown beside \"burr\" and not added to it. The die shown for burr is the one with the most burr gauge subgroups among the dies whose stated interval is longer than the count at 80% and whose median interval as run is longer than the stated interval.</div>")

    ax.append("<h3>Die events and sorting (Section 4.3)</h3>")
    ax.append(show(r["sorting_by_basis"], {"sort_basis": f"Basis of the sorting, found at the press, {YEAR - 1} and {YEAR}", "events": "Events", "quantity_sorted_median": "Quantity sorted, median", "quantity_sorted_max": "Largest", "rejected_share": "Rejected share", "parts_since_check_before_at_realised_rate_median": "Parts since the check before (estimated), median",
                                           "cost_booked_or_estimated": "Cost booked or estimated, $"}, {"quantity_sorted_median": F0, "quantity_sorted_max": F0, "rejected_share": P0, "parts_since_check_before_at_realised_rate_median": F0, "cost_booked_or_estimated": F0}))
    ax.append(show(r["sorting_summary"][r["sorting_summary"]["year"] <= YEAR], {"year": "Year", "sorting_events": "Sorting events", "traced_to_a_die_event_between_two_checks": "Traced to a die event between two checks", "followed_a_customer_complaint": "Followed a customer complaint", "quantity_sorted": "Quantity sorted", "hours_booked": "Hours booked",
                                          "hours_estimated_from_run_hours": "Hours estimated from run hours", "cost_booked": "Cost booked, $", "cost_booked_or_estimated": "Cost booked or estimated, $", "share_of_hours_booked": "Share of hours booked"},
                   {"year": lambda v: f"{int(v)}", "sorting_events": F0, "traced_to_a_die_event_between_two_checks": F0, "followed_a_customer_complaint": F0, "quantity_sorted": F0, "hours_booked": F1, "hours_estimated_from_run_hours": F1, "cost_booked": F0, "cost_booked_or_estimated": F0, "share_of_hours_booked": P0}))
    ax.append("<div class='caption'>A fault bounds a sorting event when the nonconformance quantity is no more than the parts at run speed from the fault to the finding, with a quarter allowed; a fault logged within 10 minutes of the check before gives the same quantity on either basis and is its own row. "
              "Sorting hours estimated from run hours are the run's labor hours above standard where the sorting was not booked to the sorting labor code.</div>")

    toc = [("summary", "1. Executive summary"), ("scope", "2. Scope"), ("assessment", "3. SPC assessment"), ("limits", "3.1 Chart selection and limits", 1), ("capability", "3.2 Capability", 1), ("measurement", "3.3 Measurement systems", 1), ("sampling", "3.4 Sampling frequency and recording", 1),
           ("reaction", "3.5 Reaction to signals", 1), ("sources", "4. Sources of variation"), ("coils", "4.1 Coil-to-coil shifts", 1), ("wear", "4.2 Die wear", 1), ("events", "4.3 Die events between checks", 1), ("appendix", "5. Appendix")]
    html = S.report_shell("Report: SPC Assessment", "", "", "\n".join(body + ax), toc)
    out = S.DOCS / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / "spc_assessment.html").write_text(html, encoding="utf8", newline="\n")
    trace = pd.DataFrame(TRACE, columns=["section", "value_as_printed", "read_from", "value_in_the_text"])
    off = trace[(trace["value_in_the_text"] != "") & (trace["value_as_printed"].str.lower() != trace["value_in_the_text"].str.lower())]
    assert off.empty, off.to_string()          # every number in the text is the value the record gives
    return html, trace, n_body_figures, FIGURE[0], {"matrix": mx, "plant_wide": pw, "scope": sco, "burr_die": fw["burr_die"], "runs_shown": (k1, k2), "cost": cost, "back": back}


if __name__ == "__main__":
    html, trace, n_body, n_all, extra = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "assessment_numbers.csv", index=False, lineterminator="\n")
    print(len(html), len(trace), n_body, n_all)
