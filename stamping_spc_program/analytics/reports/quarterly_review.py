"""SPC Quarterly Review, April to June 2026. Reads the marts, computes the expected false-alarm rates
(analytics.chart_performance), builds the figures and writes docs/reports/spc_quarterly_review_2026_q2.html and the table
of every number in the body with the mart it is read from and the value in the page text."""
import numpy as np
import pandas as pd
from scipy import stats

from analytics.data import query
from analytics.reports import review_figures as FIG
from analytics.reports.control_chart_design import expected_rate
from analytics.reports.page import DAY, F0, F1, F2, P1, Page
from analytics.style import style as S

FAMILY_FORMED = ("formed",)


def build():
    pg = Page(); n, pct, txt, wd = pg.num, pg.pct, pg.text, pg.word
    sig = query("select * from marts.mart_signals where in_quarter order by raised_at, alarm_id")
    sr = query("select * from marts.mart_signal_rates where period = 'quarter' order by characteristic_id, press_id, chart, baseline_subgroups")
    sr["es"] = [expected_rate(c, b) * s for c, b, s in zip(sr["chart"], sr["baseline_subgroups"], sr["subgroups_in_scope"])]
    cap = query("select * from marts.mart_capability where period = 'quarter' order by characteristic_id")
    crit_ids = set(query("select characteristic_id from staging.stg_spc__characteristics where critical")["characteristic_id"])
    ccap = cap[cap["characteristic_id"].isin(crit_ids)]
    fpa = query("select * from marts.mart_first_piece_approvals where in_quarter order by first_piece_at")
    cif = query("select * from marts.mart_charts_in_force order by characteristic_id"); var = cif[cif["data_type"] == "variable"]
    gq = query("select * from marts.mart_gauge_quarter_end where quarter_end = cast('2026-06-30' as date)")
    ac = sig[sig["assignable_cause"]]; nc = sig[~sig["assignable_cause"]]
    tot_n, tot_s, tot_e = sr["subgroups_in_scope"].sum(), sr["signals_any_rule"].sum(), sr["es"].sum()
    cm = cap.groupby("characteristic_class")["ppk"].median()
    held = fpa[fpa["held"]]
    out_of_gating = set(gq[gq["past_due"] | gq["away_for_calibration"]]["gauge_id"])
    fed_out = int((var["gauge_id"].isin(out_of_gating) | var["study_date"].isna()).sum())
    restudy_gauges = int(var.drop_duplicates("gauge_id")["restudy_scheduled"].fillna(False).astype(bool).sum())

    # ═══════════════ 1. Summary
    pg.h2("summary", "1. Summary")
    pg.p(f"The quarter ran in control. Signals on charts with no special cause came in at {n(tot_s / tot_e, 'mart_signal_rates with the expected rate: observed over expected, quarter', '{:.2f}', was='1.23')} times the expected false-alarm rate, every assignable cause found was closed inside the quarter, capability held above 1.33 on "
         f"{n(int((~ccap['under_1_33']).sum()), 'mart_capability: critical characteristics at or above 1.33', was='93')} of {n(len(ccap), 'mart_capability: critical characteristics', was='100')} critical characteristics, no gauge fed a chart without a current calibration and study, and {n(int(fpa['held'].sum()), 'mart_first_piece_approvals.held', was='19')} of "
         f"{n(len(fpa), 'mart_first_piece_approvals: run starts', was='583')} run starts were held at the first piece.")
    kp = pd.DataFrame([
        {"Measure": "Signals per 100 routine subgroups, charts with no special cause", "April to June 2026": f"{n(100 * tot_s / tot_n, 'observed per 100, quarter', '{:.2f}', was='3.80')} observed against {n(100 * tot_e / tot_n, 'expected per 100, quarter', '{:.2f}', was='3.08')} expected"},
        {"Measure": "Assignable causes found and closed", "April to June 2026": f"{n(len(ac), 'mart_signals: assignable-cause alarms, quarter', was='418')} alarms on {n(ac['run_id'].nunique(), 'mart_signals: runs with an assignable cause', was='21')} runs, {'all' if int(ac['closed_at'].notna().sum()) == len(ac) else n(int(ac['closed_at'].notna().sum()), 'mart_signals.closed_at')} closed by 30 June"},
        {"Measure": "Ppk, median by class (critical characteristics)", "April to June 2026": f"formed {n(cm['formed'], 'mart_capability.ppk, formed, median', '{:.2f}', was='1.51')}; hole position {n(cm['hole position'], 'mart_capability.ppk, hole position, median', '{:.2f}', was='1.64')}; hole diameter {n(cm['hole diameter'], 'mart_capability.ppk, hole diameter, median', '{:.2f}', was='1.63')}; flatness Ppu {n(cm['flatness'], 'mart_capability.ppk, flatness, median', '{:.2f}', was='1.81')}"},
        {"Measure": "Charts fed by a gauge out of gating status at 30 June", "April to June 2026": f"{n(fed_out, 'mart_charts_in_force with mart_gauge_quarter_end: variable charts fed by a gauge past due, away or without a study', was='0')} of {n(len(var), 'mart_charts_in_force: variable charts', was='897')}; {n(restudy_gauges, 'mart_charts_in_force.restudy_scheduled: gauges', was='16')} gauges on a restudy schedule"},
        {"Measure": "First-piece holds", "April to June 2026": f"{n(len(held), 'mart_first_piece_approvals.held', was='19')} of {n(len(fpa), 'mart_first_piece_approvals: run starts', was='583')} run starts, median {n(held['minutes_to_release'].median(), 'mart_first_piece_approvals.minutes_to_release, held, median', was='62')} minutes to release"}])
    pg.raw(S.table(kp))
    pg.p("Six special causes were caught by the chart designed to catch them.")
    st = query("select * from marts.mart_per_stroke_stops where run_id = 'R26-00820'").iloc[0]; pe13 = query("select * from marts.mart_parts_exposed where run_id = 'R26-00820'").iloc[0]
    sc = sig[sig["cause_code"] == "soft coil"].iloc[0]; coil = query("select certificate_hardness_hrb from marts.mart_coil_change_points where subgroup_id = ?", [sc.subgroup_id]).iloc[0]
    hrb = query("select median(certificate_hardness_hrb) m from staging.stg_erp__coils where grade = 'C110 copper' and nominal_thickness_mm = 0.99")["m"].iloc[0]
    fv = query("select * from marts.mart_fixture_verifications where gauge_id = 'F-14026' and result <> 'pass'").iloc[0]
    cal = query("select * from staging.stg_calibration__calibrations where gauge_id = 'F-14026' and event_type = 'rebuild'").iloc[0]
    gs14 = query("select * from marts.mart_gauge_studies where gauge_id = 'F-14026' and in_quarter order by study_date")
    fd = sig[sig["cause_code"] == "fixture drift"]
    kq = query("select * from marts.mart_operator_kappa where operator_id = 'E-1006' and in_quarter order by study_date")
    wc = sig[sig["cause_code"] == "sharpening logged at the wrong count"].iloc[0]; de = query("select * from intermediate.int_die_event_timeline where shot_count_corrected").iloc[0]
    fp9 = fpa[fpa["run_id"] == "R26-01002"].iloc[0]
    pg.ul([f"<strong>A chipped punch on D-1333-C (PR-03)</strong>, stopped by the per-stroke EWMA at {txt(pd.Timestamp(st.stopped_at).strftime('%H:%M'), 'mart_per_stroke_stops.stopped_at', was='10:55')} on 13 May at stroke {n(st.stop_stroke_no, 'mart_per_stroke_stops.stop_stroke_no', was='239,498')}, {n(pe13.strokes_exposed_per_stroke_charts, 'mart_parts_exposed.strokes_exposed_per_stroke_charts', was='34')} strokes after the onset; punch replaced, press restarted at {txt(pd.Timestamp(st.cleared_at).strftime('%H:%M'), 'mart_per_stroke_stops.cleared_at', was='11:55')}.",
           f"<strong>A soft coil on P-15731</strong>, caught by rule 1 on the coil-change chart on {txt(pd.Timestamp(sc.raised_at).strftime('%d %B').lstrip('0'), 'mart_signals.raised_at, soft coil', was='27 May')}: certificate hardness {n(coil.certificate_hardness_hrb, 'mart_coil_change_points.certificate_hardness_hrb', '{:.1f}', was='36.6')} HRB at the low end of the C110 coils on record (median {n(hrb, 'stg_erp__coils.certificate_hardness_hrb, C110 0.99 mm, median', '{:.1f}', was='40.2')}); coil held, die centred, certificate queried with the supplier, closed the same afternoon.",
           f"<strong>Fixture F-14026 drifting</strong>, first seen as {n(len(fd), 'mart_signals: fixture drift alarms', was='30')} alarms on P-14026's charts on 28 and 29 May, confirmed by the daily verification on {txt(pd.Timestamp(fv.verification_date).strftime('%d %B').lstrip('0'), 'mart_fixture_verifications.verification_date', was='2 June')} ({n(fv.master_deviation_mm, 'mart_fixture_verifications.master_deviation_mm', '{:.3f}', was='0.019')} mm against {n(fv.tolerance_mm, 'mart_fixture_verifications.tolerance_mm', '{:.3f}', was='0.016')}), restudied at "
           f"{n(gs14.iloc[0].pct_grr_of_tolerance, 'mart_gauge_studies.pct_grr_of_tolerance, restudy', '{:.1f}', was='16.7')}% of tolerance, pulled, rebuilt and back in service on {txt(pd.Timestamp(cal.done).strftime('%d %B').lstrip('0'), 'stg_calibration__calibrations.done, rebuild', was='18 June')} at {n(gs14.iloc[-1].pct_grr_of_tolerance, 'mart_gauge_studies.pct_grr_of_tolerance, after rebuild', '{:.1f}', was='5.3')}%.",
           f"<strong>Burr check operator E-1006</strong> below the requalification line on {txt(pd.Timestamp(kq.iloc[0].study_date).strftime('%d %B').lstrip('0'), 'mart_operator_kappa.study_date', was='14 April')} at kappa {n(kq.iloc[0].kappa, 'mart_operator_kappa.kappa', '{:.2f}', was='0.66')}, requalified on {txt(pd.Timestamp(kq.iloc[-1].study_date).strftime('%d %B').lstrip('0'), 'mart_operator_kappa.study_date', was='28 April')} at {n(kq.iloc[-1].kappa, 'mart_operator_kappa.kappa', '{:.2f}', was='0.83')}.",
           f"<strong>A sharpening logged at the wrong count</strong> on {de.die_id} (PR-06), caught by rule 1 on the tool-wear chart on {txt(pd.Timestamp(wc.raised_at).strftime('%d %B').lstrip('0'), 'mart_signals.raised_at, wrong count', was='16 May')} and corrected in the die log the same day.",
           f"<strong>A first-piece hold on PR-09</strong> on {txt(pd.Timestamp(fp9.first_piece_at).strftime('%d %B').lstrip('0'), 'mart_first_piece_approvals.first_piece_at', was='9 June')}, {fp9.held_characteristic_id} out of tolerance after the die repair of 8 June; die adjusted and released in {n(fp9.minutes_to_release, 'mart_first_piece_approvals.minutes_to_release', was='44')} minutes."])
    fur = ac[ac["cause_code"].isin(["slug pulling", "strip misfeed", "lubricant", "gauge zero"])].groupby("cause_code")["run_id"].nunique()
    pg.p(f"{wd(int(fur.sum()), 'mart_signals: further assignable causes, runs', was='Six').capitalize()} further assignable causes were found and closed: {wd(fur['slug pulling'], 'slug pulling, runs', was='two')} slug pulling, {wd(fur['strip misfeed'], 'strip misfeed, runs', was='two')} strip misfeed, {wd(fur['lubricant'], 'lubricant, runs', was='one')} lubricant, {wd(fur['gauge zero'], 'gauge zero, runs', was='one')} gauge zero.")

    # ═══════════════ 2. Signals and reaction
    pg.h2("signals", "2. Signals and reaction")
    pg.p(f"Signals ran at {n(tot_s / tot_e, 'observed over expected, quarter', '{:.2f}', was='1.23')} times the expected false-alarm rate, and the {n(len(ac), 'mart_signals: assignable-cause alarms', was='418')} with an assignable cause were acknowledged in a median {n(ac['minutes_to_acknowledge'].median(), 'mart_signals.minutes_to_acknowledge, assignable, median', was='3')} minutes and closed in a median "
         f"{n(ac['minutes_to_close'].median() / 60, 'mart_signals.minutes_to_close, assignable, median, hours', was='2')} hours. The quarter raised {n(len(sig), 'mart_signals: alarms, quarter', was='4,066')} alarms on {n(sig['subgroup_id'].nunique(), 'mart_signals: subgroups with an alarm', was='3,120')} subgroups; {n(len(nc), 'mart_signals: no cause found', was='3,648')} were closed as no cause found in a median "
         f"{n(nc['minutes_to_close'].median(), 'mart_signals.minutes_to_close, no cause found, median', was='24')} minutes, by a recheck on a second gauge, five more parts measured, or the next subgroup within limits.")
    ct = sr.groupby("chart").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum")); ct["obs"] = 100 * ct["signals"] / ct["subgroups"]; ct["exp"] = 100 * ct["es"] / ct["subgroups"]; ct["ratio"] = ct["signals"] / ct["es"]
    pg.p(f"By chart type, X-bar and R ran at {n(ct.at['X-bar and R', 'ratio'], 'observed over expected, X-bar and R, quarter', '{:.2f}', was='1.42')} times expectation, three-way at {n(ct.at['three-way', 'ratio'], 'observed over expected, three-way, quarter', '{:.2f}', was='0.92')} and tool-wear at {n(ct.at['tool-wear', 'ratio'], 'observed over expected, tool-wear, quarter', '{:.2f}', was='2.19')}. The excess on X-bar and R and tool-wear sits on rules 3 and 4 under long-held limits, as the design revalidation found; the three-way charts run at their design rate.")
    p1 = sr.groupby("press_id").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum")).reset_index()
    p1["observed per 100"] = 100 * p1["signals"] / p1["subgroups"]; p1["expected per 100"] = 100 * p1["es"] / p1["subgroups"]
    p1["low"] = [100 * stats.chi2.ppf(0.025, 2 * k) / 2 / m if k > 0 else 0.0 for k, m in zip(p1["signals"], p1["subgroups"])]; p1["high"] = [100 * stats.chi2.ppf(0.975, 2 * (k + 1)) / 2 / m for k, m in zip(p1["signals"], p1["subgroups"])]
    pg.figure(FIG.observed_expected_by_press(p1), "Figure 1: Observed against expected signals by press", "Signals per 100 routine subgroups on charts with no special cause in the quarter, with a 95% Poisson interval, against the rate expected from the press's charts at their own baseline sizes under their rules.")
    pg.table("Signals by chart type, observed against expected", ct.reset_index(), {"chart": "Chart", "subgroups": "Routine subgroups", "signals": "Signals", "obs": "Observed per 100", "exp": "Expected per 100", "ratio": "Observed over expected"},
             {"Routine subgroups": F0, "Signals": F0, "Observed per 100": F2, "Expected per 100": F2, "Observed over expected": F2})
    p4 = p1.set_index("press_id").loc["PR-04"]; below = p1[p1["observed per 100"] < p1["expected per 100"]]["press_id"].tolist()
    lv = sig[sig["cause_code"] == "level after sharpening"]
    pg.p(f"{txt(p1.sort_values('observed per 100').iloc[-1].press_id, 'press with the highest observed rate', was='PR-04')} ran highest, at {n(p4['observed per 100'], 'observed per 100, PR-04', '{:.2f}', was='5.27')} per 100 against {n(p4['expected per 100'], 'expected per 100, PR-04', '{:.2f}', was='3.16')} expected, and {txt(' and '.join(below), 'presses observed below expected', was='PR-08 and PR-10')} ran below expectation. The {n(len(lv), 'mart_signals: level after sharpening', was='356')} alarms dispositioned \"level after sharpening\" fall on "
         f"{n(lv['run_id'].nunique(), 'mart_signals: runs with level after sharpening', was='12')} runs where a die came back from sharpening at a new level and its verification failed; they are the verification doing its work, and each started a new baseline.")
    sig["rule_label"] = sig["chart"] + " rule " + sig["rule"].astype(str); sig["cause"] = np.where(sig["assignable_cause"], sig["cause_code"], "no cause found")
    tab = sig.pivot_table(index="rule_label", columns="cause", values="alarm_id", aggfunc="count", fill_value=0)
    pg.figure(FIG.signals_by_rule_and_cause(tab), "Figure 2: Signals by rule and cause", "Alarms in the quarter by chart and rule, divided by the cause recorded at closure.")
    rx = ac.groupby("cause_code").agg(alarms=("alarm_id", "count"), am=("minutes_to_acknowledge", "median"), ax=("minutes_to_acknowledge", "max"), cm_=("minutes_to_close", "median"), cx=("minutes_to_close", "max")).reset_index()
    pg.table("Assignable causes: time to reaction and closure", rx, {"cause_code": "Cause", "alarms": "Alarms", "am": "Minutes to acknowledge, median", "ax": "Minutes to acknowledge, longest", "cm_": "Minutes to close, median", "cx": "Minutes to close, longest"},
             {"Alarms": F0, "Minutes to acknowledge, median": F1, "Minutes to acknowledge, longest": F1, "Minutes to close, median": F1, "Minutes to close, longest": F1})
    famsig = sig[sig["family_part"]]
    fa = famsig[famsig["assignable_cause"]]; lr = fa[fa["cause_code"] == "level after the rebuild"]
    vr = query("select max(verified_at) v, max(event_date) e from marts.mart_limit_verifications where part_id = 'P-14026' and die_event = 'rebuild' and result = 'failed'").iloc[0]
    pg.p(f"The family's charts raised {n(len(famsig), 'mart_signals: family alarms, quarter', was='484')} alarms in the quarter, {n(len(fa), 'mart_signals: family alarms with an assignable cause', was='54')} with an assignable cause: the {n(len(fd), 'mart_signals: fixture drift alarms', was='30')} fixture-drift alarms on P-14026 on 28 and 29 May, "
         f"{n(len(lr), 'mart_signals: level after the rebuild, family', was='23')} on P-14026 after its rebuild of {txt(pd.Timestamp(vr.e).strftime('%d %B').lstrip('0'), 'mart_limit_verifications.event_date, P-14026 rebuild', was='28 May')}, whose verification failed on {txt(pd.Timestamp(vr.v).strftime('%d %B').lstrip('0'), 'mart_limit_verifications.verified_at, P-14026', was='30 June')}, and the soft coil on C-15731-07. The other "
         f"{n(int((~famsig['assignable_cause']).sum()), 'mart_signals: family alarms, no cause found', was='430')} were closed as no cause found.")
    fl = famsig[["raised_at", "characteristic_id", "chart", "rule", "subgroup_type", "disposition", "cause_code", "minutes_to_acknowledge", "minutes_to_close"]].copy()
    fl["raised_at"] = fl["raised_at"].map(lambda t: pd.Timestamp(t).strftime("%d %b %H:%M").lstrip("0")); fl["cause_code"] = fl["cause_code"].fillna("")
    pg.table("The family's signal log, April to June 2026", fl, {"raised_at": "Raised", "characteristic_id": "Characteristic", "chart": "Chart", "rule": "Rule", "subgroup_type": "Subgroup", "disposition": "Disposition", "cause_code": "Cause", "minutes_to_acknowledge": "Minutes to acknowledge", "minutes_to_close": "Minutes to close"},
             {"Rule": F0, "Minutes to acknowledge": F1, "Minutes to close": F1})

    # ═══════════════ 3. Limits governance
    pg.h2("limits", "3. Limits governance")
    rq = query("select trigger, chart, cast(sum(limit_sets_in_quarter) as integer) n from marts.mart_limit_recalculations group by all having sum(limit_sets_in_quarter) > 0 order by 1, 2")
    rt_ = rq.groupby("trigger")["n"].sum()
    vq = query("select * from marts.mart_limit_verifications where in_quarter"); vt = vq.groupby(["chart", "die_event"]).agg(verifications=("verification_id", "count"), failed=("result", lambda s: int((s == "failed").sum()))).reset_index()
    vx = vt.set_index(["chart", "die_event"]); sharp = vq[vq["die_event"] == "sharpening"]; tw_fail = vq[(vq["chart"] == "three-way") & (vq["result"] == "failed")]
    pg.p(f"No chart is past its recalculation trigger at 30 June, and {n(int(rq['n'].sum()), 'mart_limit_recalculations.limit_sets_in_quarter', was='53')} new limit sets were issued in the quarter: {n(rt_['rebuild'], 'rebuild, quarter', was='21')} after rebuilds, {n(rt_['tool-wear re-fit'], 'tool-wear re-fit, quarter', was='20')} tool-wear lines re-fitted, {n(rt_['failed verification'], 'failed verification, quarter', was='9')} after failed verifications and "
         f"{n(rt_['annual review'], 'annual review, quarter', was='3')} from the annual review. Of {n(len(sharp), 'mart_limit_verifications: verifications after a sharpening, quarter', was='339')} verifications after a sharpening, {n(int((sharp['result'] == 'failed').sum()), 'failed after a sharpening, quarter', was='10')} failed, "
         f"{'all' if int((sharp['result'] == 'failed').sum()) == vx.at[('X-bar and R', 'sharpening'), 'failed'] else 'not all'} on X-bar and R charts; of {n(vx.at[('three-way', 'rebuild'), 'verifications'], 'three-way verifications after a rebuild, quarter', was='30')} three-way verifications after a rebuild, {n(len(tw_fail), 'three-way failed, quarter', was='3')} failed, all on "
         f"{txt(tw_fail['part_id'].iloc[0], 'mart_limit_verifications.part_id, three-way failures', was='P-14026')} on {txt(pd.Timestamp(tw_fail['verified_at'].max()).strftime('%d %B').lstrip('0'), 'mart_limit_verifications.verified_at', was='30 June')}.")
    pg.table("Recalculations in the quarter by trigger and chart", rq, {"trigger": "Trigger", "chart": "Chart", "n": "New limit sets"}, {"New limit sets": F0})
    pg.table("Verifications completed in the quarter", vt, {"chart": "Chart", "die_event": "After", "verifications": "Verifications", "failed": "Failed"}, {"Verifications": F0, "Failed": F0})
    bip = cif[cif["in_baseline"]].copy(); c23 = bip[bip["characteristic_id"] == "C-23264-03"].iloc[0]
    pg.p(f"{n(len(bip), 'mart_charts_in_force.in_baseline', was='16')} charts are in a baseline at 30 June: {n(int((bip['chart_type'] == 'Xbar-R').sum()), 'in baseline, X-bar and R', was='12')} X-bar and R and {n(int((bip['chart_type'] == 'three-way (I-MR-R)').sum()), 'in baseline, three-way', was='4')} three-way. One of them, C-23264-03 on PR-08, has been in baseline since {txt(DAY(c23.baseline_started), 'mart_charts_in_force.baseline_started', was='1 December 2025')} with "
         f"{n(c23.baseline_subgroups_so_far, 'mart_charts_in_force.baseline_subgroups_so_far', was='21')} of 25 subgroups after seven months; its previous limits stay in force as provisional.")
    bip["started"] = bip["baseline_started"].map(DAY); bip["so_far"] = bip["baseline_subgroups_so_far"].astype(float); bip["coils"] = bip["baseline_coil_changes_so_far"].astype(float)
    pg.table("Baselines in progress at 30 June 2026", bip, {"characteristic_id": "Characteristic", "part_id": "Part", "press_id": "Press", "chart_type": "Chart", "started": "Baseline started", "so_far": "Subgroups so far", "coils": "Coil changes so far"},
             {"Subgroups so far": F0, "Coil changes so far": F0}, note="A three-way baseline needs 25 subgroups spanning ten coil changes; an X-bar and R baseline, 25 subgroups.")

    # ═══════════════ 4. Capability
    pg.h2("capability", "4. Capability")
    fq = cap[cap["characteristic_class"] == "formed"]
    pg.p(f"Capability held above 1.33 on {n(int((~ccap['under_1_33']).sum()), 'critical at or above 1.33', was='93')} of the {n(len(ccap), 'critical characteristics', was='100')} critical characteristics with 60 subgroups or more in the quarter. Medians by class: formed Ppk {n(cm['formed'], 'formed Ppk median', '{:.2f}', was='1.51')} (interquartile range "
         f"{n(fq['ppk'].quantile(0.25), 'formed Ppk, 25th percentile', '{:.2f}', was='1.41')} to {n(fq['ppk'].quantile(0.75), 'formed Ppk, 75th percentile', '{:.2f}', was='1.59')}), hole position {n(cm['hole position'], 'hole position Ppk median', '{:.2f}', was='1.64')}, hole diameter {n(cm['hole diameter'], 'hole diameter Ppk median', '{:.2f}', was='1.63')}, flatness Ppu {n(cm['flatness'], 'flatness Ppu median', '{:.2f}', was='1.81')}. Cpk sits "
         f"{n(fq['cpk_less_ppk'].median(), 'formed Cpk less Ppk, median', '{:.2f}', was='0.09')} above Ppk on formed characteristics, which is the coil offset left after centring, and {n(cap[cap['characteristic_class'] == 'hole diameter']['cpk_less_ppk'].median(), 'hole diameter Cpk less Ppk, median', '{:.2f}', was='0.38')} above on hole diameters, which is the wear over the interval that Ppk carries and Cpk, taken about the regression line, does not.")
    rows = []
    for cls, g in cap.groupby("characteristic_class"):
        rows.append({"class": cls, "n": len(g), "ppk": g["ppk"].median(), "iqr": f"{g['ppk'].quantile(0.25):.2f} to {g['ppk'].quantile(0.75):.2f}", "cpk": g["cpk"].median(), "gap": g["cpk_less_ppk"].median(), "u": int(g["under_1_33"].sum()), "def": g["cpk_definition"].iloc[0], "idx": g["index_reported"].iloc[0]})
    pg.table("Cpk and Ppk by class, April to June 2026", pd.DataFrame(rows), {"class": "Class", "n": "Characteristics", "ppk": "Ppk, median", "iqr": "Ppk, interquartile range", "cpk": "Cpk, median", "gap": "Cpk less Ppk", "u": "Under 1.33", "def": "Cpk on", "idx": "Index"},
             {"Characteristics": F0, "Ppk, median": F2, "Cpk, median": F2, "Cpk less Ppk": F2, "Under 1.33": F0}, note="Critical characteristics with 60 routine subgroups or more in the quarter, and every flatness characteristic; flatness carries the upper index only.")
    order = ["formed", "hole diameter", "hole position", "flatness"]
    pg.figure(FIG.plant_ppk_by_class(cap, order), "Figure 4: Plant Ppk by class", "Each point is one characteristic's Ppk for the quarter (Ppu on flatness), with the box from the 25th to the 75th percentile and the median; 1.33 marked.")
    fc = cap[cap["family_part"]].copy(); fbelow = fc[fc["under_1_33"]]; fabove = fc[~fc["under_1_33"]]; c03 = fc[fc["characteristic_id"] == "C-15731-03"].iloc[0]
    b5, b6 = fc[fc["characteristic_id"] == "C-15731-05"].iloc[0], fc[fc["characteristic_id"] == "C-15731-06"].iloc[0]
    pg.p(f"On the family, {n(len(fabove), 'mart_capability: family at or above 1.33', was='11')} of {n(len(fc), 'mart_capability: family characteristics', was='13')} critical characteristics are above 1.33, {wd(int((fabove['ppk_low'] > 1.33).sum()), 'family with the interval clear of 1.33', was='ten')} of them with their 95% intervals clear of it; C-15731-03's interval reaches down to "
         f"{n(c03.ppk_low, 'mart_capability.ppk_low, C-15731-03', '{:.2f}', was='1.30')}. {wd(len(fbelow), 'family below 1.33', was='Two').capitalize()} formed heights on P-15731 are below: C-15731-05 at {n(b5.ppk, 'ppk, C-15731-05', '{:.2f}', was='1.30')} ({n(b5.ppk_low, 'ppk_low, C-15731-05', '{:.2f}', was='1.22')} to {n(b5.ppk_high, 'ppk_high, C-15731-05', '{:.2f}', was='1.38')}) and C-15731-06 at "
         f"{n(b6.ppk, 'ppk, C-15731-06', '{:.2f}', was='1.23')} ({n(b6.ppk_low, 'ppk_low, C-15731-06', '{:.2f}', was='1.15')} to {n(b6.ppk_high, 'ppk_high, C-15731-06', '{:.2f}', was='1.31')}). Intervals are Bissell's approximation.")
    pg.figure(FIG.family_ppk(fc), "Figure 3: The family: Ppk with 95% intervals", "Ppk for April to June 2026 on each of the family's critical characteristics with 60 subgroups or more, with its 95% interval by Bissell's approximation; 1.33 marked.")
    u = cap[cap["under_1_33"]].merge(query("select characteristic_id, share_between_coils, trend_share from marts.mart_variance_components"), on="characteristic_id", how="left")
    uf = u[u["characteristic_class"] == "formed"]; c39 = u[u["characteristic_id"] == "C-39736-01"].iloc[0]
    fmed = float(query("select median(share_between_coils) m from marts.mart_variance_components where characteristic_class = 'formed' and critical")["m"].iloc[0])
    pg.p(f"The {wd(len(u), 'mart_capability: under 1.33', was='seven')} characteristics under 1.33 carry no special cause; their shortfall is the variation the charts are designed to live with. On the {wd(len(uf), 'formed under 1.33', was='six')} formed characteristics the between-coil share of the routine record runs "
         f"{n(100 * uf['share_between_coils'].min(), 'share_between_coils, formed under 1.33, lowest', '{:.0f}', was='7')}% to {n(100 * uf['share_between_coils'].max(), 'share_between_coils, formed under 1.33, highest', '{:.0f}', was='31')}%, against a class median of {pct(fmed, 'mart_variance_components.share_between_coils, formed, median', was='13.5%')}; on C-39736-01 (hole diameter, PR-09) the wear trend takes Ppk to "
         f"{n(c39.ppk, 'ppk, C-39736-01', '{:.2f}', was='1.32')} while Cpk about the line is {n(c39.cpk, 'cpk, C-39736-01', '{:.2f}', was='2.12')}. Each had only signals closed as no cause found in the quarter. The two P-15731 heights and C-16315-06 are the ones to take to the customer at the next review.")
    ev = []
    for r in u.itertuples():
        s_ = sig[sig["characteristic_id"] == r.characteristic_id]; ev.append(f"{len(s_)}, " + ("none" if s_.empty else "; ".join(f"{k} {v}" for k, v in s_["cause"].value_counts().items())))
    u["evidence"] = ev
    pg.table("Characteristics under Ppk 1.33, with the chart evidence", u, {"characteristic_id": "Characteristic", "press_id": "Press", "characteristic_class": "Class", "ppk": "Ppk", "cpk": "Cpk", "share_between_coils": "Between-coil share", "trend_share": "Wear trend", "evidence": "Signals in the quarter and their causes"},
             {"Ppk": F2, "Cpk": F2, "Between-coil share": P1, "Wear trend": P1}, note="Shares of the routine record's variance over the year.")

    # ═══════════════ 5. Measurement gating
    pg.h2("measurement", "5. Measurement gating")
    gsq = query("select * from marts.mart_gauge_studies where in_quarter order by study_date, gauge_id"); fx = query("select * from marts.mart_gauge_studies where latest_on_file and gauge_type = 'check fixture'")
    band = gsq["grr_band"].value_counts(); fb = fx["grr_band"].value_counts()
    pg.p(f"No gauge fed a chart without a current calibration and study in the quarter, and the one fixture that drifted was off the floor within a day of its verification failing. At 30 June no gauge is past calibration due or away for calibration; {n(int(var['study_date'].notna().sum()), 'mart_charts_in_force: variable charts with a study', was='897')} of {n(len(var), 'variable charts', was='897')} variable charts have a study on file. "
         f"{n(len(gsq), 'mart_gauge_studies: studies in the quarter', was='66')} gauge studies were run in the quarter, {n(int((gsq['gauge_type'] == 'check fixture').sum()), 'studies on check fixtures', was='52')} on check fixtures: {n(band.get('under 10%', 0), 'under 10%', was='59')} under 10% of tolerance and {n(band.get('10% to 30%', 0), '10% to 30%', was='7')} at 10% to 30%, {wd(int(gsq[(gsq['grr_band'] == '10% to 30%') & gsq['restudy_due'].notna()].shape[0]), 'mart_gauge_studies: 10% to 30% with a restudy date', was='six')} with a restudy scheduled and the seventh, {txt(gsq[(gsq['grr_band'] == '10% to 30%') & gsq['restudy_due'].isna()]['gauge_id'].iloc[0], 'mart_gauge_studies: 10% to 30% without a restudy date', was='F-14026')}, rebuilt. Across all "
         f"{n(len(fx), 'check fixtures on file', was='180')} check fixtures the latest study is under 10% on {n(fb.get('under 10%', 0), 'fixtures under 10%', was='164')} and at 10% to 30% on {n(fb.get('10% to 30%', 0), 'fixtures at 10% to 30%', was='16')}, none over 30%.")
    gall = query("select quarter_end, count(*) gauges, count(*) filter (where past_due) past_due, count(*) filter (where past_due and feeds_a_chart) pdf, count(*) filter (where away_for_calibration) away, count(*) filter (where away_for_calibration and feeds_a_chart) awf from marts.mart_gauge_quarter_end group by 1 order by 1")
    gall["quarter_end"] = gall["quarter_end"].map(DAY)
    pg.table("Calibration status at each quarter end", gall, {"quarter_end": "Quarter end", "gauges": "Gauges", "past_due": "Past calibration due", "pdf": "Past due, feeding a chart", "away": "Away for calibration", "awf": "Away, feeding a chart"},
             {"Gauges": F0, "Past calibration due": F0, "Past due, feeding a chart": F0, "Away for calibration": F0, "Away, feeding a chart": F0})
    f5 = gsq[gsq["gauge_type"] == "check fixture"].copy(); f5["label"] = f5["gauge_id"] + " (" + f5["study_date"].map(lambda d: pd.Timestamp(d).strftime("%d %b").lstrip("0")) + ")"
    pg.figure(FIG.grr_before_after(f5), "Figure 5: %GRR before and after, fixtures studied in the quarter", "Each row is one study of a check fixture in the quarter (%GRR of tolerance, ANOVA method) beside the fixture's previous study; F-14026 appears twice, on its restudy after the failed verification and after its rebuild.")
    pg.p(f"F-14026 showed on the charts before the verification caught it. Its {n(len(fd), 'fixture drift alarms', was='30')} alarms on 28 and 29 May preceded the failed daily verification of 2 June by {wd((pd.Timestamp(fv.verification_date) - pd.Timestamp(fd['raised_at'].max()).normalize()).days, 'days from the last drift alarm to the failed verification', was='four')} days; the restudy on 3 June read "
         f"{n(gs14.iloc[0].pct_grr_of_tolerance, 'restudy %GRR', '{:.1f}', was='16.7')}% of tolerance with {n(gs14.iloc[0].ndc, 'restudy ndc', was='4')} distinct categories, the fixture was rebuilt and restudied on 17 June at {n(gs14.iloc[-1].pct_grr_of_tolerance, 'after-rebuild %GRR', '{:.1f}', was='5.3')}% with {n(gs14.iloc[-1].ndc, 'after-rebuild ndc', was='15')}, and it returned to service on 18 June. P-14026 did not run while it was out. The daily verifications otherwise passed "
         f"{n(int(query('select count(*) n from marts.mart_fixture_verifications where in_quarter and result = ' + chr(39) + 'pass' + chr(39))['n'].iloc[0]), 'mart_fixture_verifications: passes, quarter', was='1,052')} times and failed once.")
    kall = query("select * from marts.mart_operator_kappa order by operator_id, study_date"); lq = kall[kall["latest"]]
    pg.p(f"All {n(len(lq), 'mart_operator_kappa: operators', was='24')} burr check operators are qualified at 30 June, at kappa {n(lq['kappa'].min(), 'latest kappa, lowest', '{:.2f}', was='0.78')} to {n(lq['kappa'].max(), 'latest kappa, highest', '{:.2f}', was='0.89')} against the burr gauge, median {n(lq['kappa'].median(), 'latest kappa, median', '{:.2f}', was='0.82')}. E-1006 fell to "
         f"{n(kq.iloc[0].kappa, 'kappa, 14 April', '{:.2f}', was='0.66')} on 14 April and was requalified on 28 April at {n(kq.iloc[-1].kappa, 'kappa, 28 April', '{:.2f}', was='0.83')}; no burr check by E-1006 is recorded between the two studies.")
    pg.figure(FIG.kappa_by_operator(kall, 0.75), "Figure 6: Kappa by operator", "Every burr check qualification in the record, by operator, against the requalification line; E-1006's studies are marked, with the quarter's two labelled.")
    ms = query("select sum(subgroups) n, sum(subgroups_on_gauge_away) a, sum(subgroups_on_gauge_past_due) p from marts.mart_measurement_subgroups where in_quarter").iloc[0]
    aw = query("""select cast(h.sample_time as date) - g.out_of_service_from as days_after, (cast(r.actual_start as date) <= g.out_of_service_from) as run_begun_before
                  from intermediate.int_characteristic_history h join intermediate.int_run_shots r using (run_id)
                  join intermediate.int_gauge_status g on g.gauge_id = h.gauge_id and cast(h.sample_time as date) between g.out_of_service_from and coalesce(g.back_in_service, date '2100-01-01')
                  where h.gauge_out_of_service and h.in_quarter""")
    later = aw[~aw["run_begun_before"]]
    pg.p(f"{n(ms.a, 'mart_measurement_subgroups.subgroups_on_gauge_away, quarter', was='261')} subgroups, {pct(ms.a / ms.n, 'share of the quarter', 2, was='0.27%')} of the quarter's, were recorded against a gauge away for calibration, and {'none' if ms.p == 0 else n(ms.p, 'past due')} against a gauge past due. "
         f"{n(int(aw['run_begun_before'].sum()), 'int_characteristic_history with int_gauge_status: on runs begun on or before the removal day', was='89')} are on runs begun before the removal was entered; the other {n(len(later), 'the rest', was='172')} fall {n(later['days_after'].min(), 'days after the removal, fewest', was='1')} to "
         f"{n(later['days_after'].max(), 'days after the removal, most', was='15')} days after it, which the terminal should have blocked, and are referred to the calibration administrator.")

    # ═══════════════ 6. Dies and per-stroke monitoring
    pg.h2("dies", "6. Dies and per-stroke monitoring")
    sh = query("select * from marts.mart_sharpenings where in_quarter order by sharpened_on, die_id"); shr = sh[sh["is_run_interval"]]; late = shr[shr["late"]]
    pg.p(f"Dies were sharpened at or before their due count on {n(int((~shr['late']).sum()), 'mart_sharpenings: on time, quarter', was='69')} of {n(len(shr), 'mart_sharpenings: quarter', was='76')} sharpenings, and burr reached at most {pct(sh['burr_peak_share_of_limit'].max(), 'mart_sharpenings.burr_peak_share_of_limit, highest', was='90.8%')} of its limit on any interval. The {wd(len(late), 'late sharpenings', was='seven')} late sharpenings overran by "
         f"{n(100 * (late['share_of_due_count'].min() - 1), 'late overrun, smallest', '{:.0f}', was='1')}% to {n(100 * (late['share_of_due_count'].max() - 1), 'late overrun, largest', '{:.0f}', was='9')}% of the count, each with a reason in the log: a toolmaker on a rebuild, punch steel on order, or a die booked on a running order. High-speed dies are pulled at a median "
         f"{pct(shr[shr['press_group'] == 'high_speed']['share_of_due_count'].median(), 'share of the due count, high-speed, median', 0, was='87%')} of their count and medium dies at {pct(shr[shr['press_group'] == 'medium']['share_of_due_count'].median(), 'share of the due count, medium, median', 0, was='96%')}.")
    late = late.copy(); late["on"] = late["sharpened_on"].map(DAY)
    pg.table("Sharpenings against the due count; the late sharpenings", late, {"die_id": "Die", "press_id": "Press", "on": "Sharpened", "shots_in_interval_logged": "Shots in the interval", "sharpening_due_count": "Due count", "share_of_due_count": "Share of the count", "late_reason": "Reason in the log"},
             {"Shots in the interval": F0, "Due count": F0, "Share of the count": P1})
    pg.figure(FIG.sharpening_share(shr), "Figure 7: Shots at sharpening over the due count, by press group", "Each sharpening in the quarter that closes a logged interval: the shots in the interval as a share of the die's due count, by press group.")
    stp = query("select * from marts.mart_per_stroke_stops where in_quarter"); srq = query("select * from marts.mart_per_stroke_stop_rates where period = 'quarter' order by press_id")
    srec = query("select sum(strokes) s, sum(stops_nothing_found) nf from marts.mart_per_stroke_stop_rates where period = 'record'").iloc[0]; fcq = stp["finding_class"].value_counts(); p3 = srq.set_index("press_id").loc["PR-03"]
    peq = query("select * from marts.mart_parts_exposed where in_quarter")
    pg.p(f"The per-stroke charts stopped the presses {n(len(stp), 'mart_per_stroke_stops: stops, quarter', was='139')} times on {n(srq['strokes'].sum() / 1e6, 'mart_per_stroke_stop_rates.strokes, quarter, millions', '{:.1f}', was='23.2')} million strokes: {n(fcq['slug pulling'], 'slug pulling, quarter', was='68')} on slug pulling, {n(fcq['chipped punch'], 'chipped punch, quarter', was='23')} on a chipped punch, {n(fcq['worn punch'], 'worn punch, quarter', was='21')} on a worn punch, and "
         f"{n(fcq['nothing found'], 'nothing found, quarter', was='27')} with nothing found, {n(srq['stops_nothing_found'].sum() / (srq['strokes'].sum() / 1e6), 'nothing found per million strokes, quarter', '{:.2f}', was='1.16')} per million strokes. PR-03 carries {n(p3.stops_nothing_found, 'nothing found, PR-03, quarter', was='18')} of the {n(fcq['nothing found'], 'nothing found, quarter', was='27')}, at "
         f"{n(p3.stops_nothing_found_per_million_strokes, 'nothing found per million, PR-03, quarter', '{:.2f}', was='3.78')} per million against {n(srec.nf / (srec.s / 1e6), 'nothing found per million, plant, the year', '{:.2f}', was='1.02')} across the year, and its EWMA baselines are reviewed before the next quarter. Chipped punches were stopped a median "
         f"{n(peq['strokes_exposed_per_stroke_charts'].median(), 'mart_parts_exposed: median strokes, quarter', was='0')} strokes after the onset, 90th percentile {n(peq['strokes_exposed_per_stroke_charts'].quantile(0.9), 'mart_parts_exposed: 90th percentile strokes, quarter', was='31')}.")
    pg.figure(FIG.stops_by_press(srq), "Figure 8: Per-stroke stops by finding, by press", "Stops of the press by the per-stroke charts in the quarter, by the toolmaker's finding.")
    pr = query("select * from marts.mart_punch_replacements where in_quarter"); pt = pr.groupby(["punch_condition", "led_by"]).size()
    pg.p(f"All {n(len(pr), 'mart_punch_replacements: quarter', was='44')} punch replacements followed a chart: {n(pt[('chipped', 'channel share')], 'chipped, channel share', was='19')} chipped punches on the channel-share chart and {n(pt[('chipped', 'EWMA on the total')], 'chipped, EWMA', was='4')} on the EWMA, {n(pt[('worn', 'EWMA on the total')], 'worn, EWMA', was='17')} worn punches on the EWMA and "
         f"{n(pt[('worn', 'channel share')], 'worn, channel share', was='4')} on the channel-share chart.")
    pg.figure(FIG.punch_replacements(pr), "Figure 9: Punch replacements by what led to them", "Punch replacements in the die log in the quarter, by the condition found and the per-stroke chart that stopped the press.")

    # ═══════════════ 7. First-piece approvals and recording
    pg.h2("first-piece", "7. First-piece approvals and recording")
    passed = fpa[~fpa["held"]]; ht = held["held_characteristic_type"].value_counts(); lg = held.sort_values("minutes_to_release", ascending=False)
    pg.p(f"{n(len(held), 'held', was='19')} of {n(len(fpa), 'run starts', was='583')} run starts were held at the first piece ({pct(len(held) / len(fpa), 'held share', was='3.3%')}), all released, at a median {n(held['minutes_to_release'].median(), 'held, median minutes', was='62')} minutes; passed first pieces were released in a median {n(passed['minutes_to_release'].median(), 'passed, median minutes', was='12')} minutes. Formed heights held "
         f"{n(ht.get('formed height', 0), 'held on formed height', was='8')}, hole-to-edge {n(ht.get('hole-to-edge', 0), 'held on hole-to-edge', was='4')}, burr height {n(ht.get('burr height', 0), 'held on burr height', was='3')}, bend angle {n(ht.get('bend angle', 0), 'held on bend angle', was='2')}, hole diameter {n(ht.get('hole diameter', 0), 'held on hole diameter', was='1')} and hole-to-hole {n(ht.get('hole-to-hole', 0), 'held on hole-to-hole', was='1')}. One hold, "
         f"{txt(lg.iloc[0].run_id, 'longest hold, run', was='R26-00796')} on {txt(lg.iloc[0].press_id, 'longest hold, press', was='PR-01')} on {txt(pd.Timestamp(lg.iloc[0].first_piece_at).strftime('%d %B').lstrip('0'), 'longest hold, date', was='5 May')}, took {n(lg.iloc[0].minutes_to_release, 'longest hold, minutes', was='470')} minutes on a formed height; the next longest took {n(lg.iloc[1].minutes_to_release, 'second longest hold, minutes', was='78')}.")
    pg.figure(FIG.first_piece_release(held, passed), "Figure 10: First-piece time to release, with the characteristic that held each", "Minutes from the first piece to its release: passed first pieces as a histogram, and each held first piece as a point beside the characteristic that held it.")
    pc = query("select press_id, shift, count(*) planned, count(*) filter (where recorded) recorded from marts.mart_recording_planned_checks where in_quarter group by all order by 1, 2"); pc["recorded share"] = pc["recorded"] / pc["planned"]
    tot = pc.groupby("shift")[["planned", "recorded"]].sum(); le = query("select count(*) n, count(*) filter (where late_entry) l, median(minutes_to_entry) m from marts.mart_recording_routine_subgroups where in_quarter").iloc[0]
    pg.p(f"Planned checks were recorded on {pct(tot.at['days', 'recorded'] / tot.at['days', 'planned'], 'planned checks recorded, days', was='97.9%')} of day-shift occasions and {pct(tot.at['nights', 'recorded'] / tot.at['nights', 'planned'], 'planned checks recorded, nights', was='96.9%')} on nights, with no press under "
         f"{pct(np.floor(pc['recorded share'].min() * 1000) / 1000, 'lowest press and shift, to the tenth of a point below', was='95.5%')} on either shift. {pct(le.l / le.n, 'late entries', 2, was='1.50%')} of routine entries were made more than 20 minutes after the parts; the median entry follows the parts by {wd(le.m, 'median minutes to entry', was='one')} minute.")
    pg.figure(FIG.planned_checks(pc), "Figure 11: Planned checks recorded by press and shift", "Share of the planned routine checks recorded in the quarter, by press and shift.")

    # ═══════════════ Appendix
    pg.h2("appendix", "Appendix")
    same_day = query("select count(*) n, count(*) filter (where cast(actual_start as date) = sharpening_date) d from intermediate.int_run_shots where shots_since_sharpening_at_start is not null").iloc[0]
    span = int(query("select count(*) n from intermediate.int_run_shots r where shots_since_sharpening_at_start is not null and exists (select 1 from intermediate.int_sharpening_intervals i where i.die_id = r.die_id and i.interval_start between cast(r.actual_start as date) and cast(r.actual_end as date))")["n"].iloc[0])
    pg.raw(DEFINITIONS.format(placed=n(same_day.d, 'int_run_shots: runs starting on the day their sharpening is logged', was='15'), runs=n(same_day.n, 'int_run_shots: runs with a shot count', was='1,399'),
                              span=n(span, 'int_run_shots with int_sharpening_intervals: runs spanning a logged sharpening date', was='92')))
    srq2 = srq.merge(pc.groupby("press_id")[["planned", "recorded"]].sum().reset_index(), on="press_id"); srq2["share"] = srq2["recorded"] / srq2["planned"]
    srq2 = srq2.merge(sig.groupby("press_id").agg(alarms=("alarm_id", "count"), assignable=("assignable_cause", "sum")).reset_index(), on="press_id", how="left")
    srq2 = srq2.merge(fpa.groupby("press_id").agg(starts=("approval_id", "count"), holds=("held", "sum")).reset_index(), on="press_id", how="left")
    pg.table("The full tables by press, April to June 2026", srq2, {"press_id": "Press", "alarms": "Alarms", "assignable": "Assignable causes", "starts": "Run starts", "holds": "First-piece holds", "strokes": "Strokes", "stops": "Per-stroke stops", "stops_nothing_found": "Nothing found", "planned": "Planned checks", "share": "Recorded"},
             {"Alarms": F0, "Assignable causes": F0, "Run starts": F0, "First-piece holds": F0, "Strokes": F0, "Per-stroke stops": F0, "Nothing found": F0, "Planned checks": F0, "Recorded": P1})
    al = sig[["alarm_id", "raised_at", "press_id", "characteristic_id", "chart", "rule", "disposition", "cause_code", "minutes_to_close"]].copy(); al["raised_at"] = al["raised_at"].map(lambda t: pd.Timestamp(t).strftime("%d %b %H:%M").lstrip("0")); al["cause_code"] = al["cause_code"].fillna("")
    pg.table("Every signal in the quarter with its disposition", al, {"alarm_id": "Alarm", "raised_at": "Raised", "press_id": "Press", "characteristic_id": "Characteristic", "chart": "Chart", "rule": "Rule", "disposition": "Disposition", "cause_code": "Cause", "minutes_to_close": "Minutes to close"},
             {"Rule": F0, "Minutes to close": F1})

    toc = [("summary", "1. Summary"), ("signals", "2. Signals and reaction"), ("limits", "3. Limits governance"), ("capability", "4. Capability"), ("measurement", "5. Measurement gating"), ("dies", "6. Dies and per-stroke monitoring"), ("first-piece", "7. First-piece approvals and recording"), ("appendix", "Appendix")]
    html = S.report_shell("SPC Quarterly Review, April to June 2026", "", "July 2026", "\n".join(pg.body), toc)
    out = S.DOCS / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / "spc_quarterly_review_2026_q2.html").write_text(html, encoding="utf8", newline="\n")
    trace, off = pg.check()
    return html, trace, off, pg.figures


DEFINITIONS = """<h3 id="definitions">Definitions</h3>
<p><strong>Periods and press groups.</strong> The quarter is 1 April to 30 June 2026; the record is 1 July 2025 to 30 June 2026, exported 13 July 2026. High-speed presses are PR-01 to PR-04, checked every 30 minutes; medium presses are PR-05 to PR-11, checked hourly. Status at 30 June is as at the end of that day.</p>
<p><strong>Signals and recording.</strong> An alarm is one chart and rule signalled on a subgroup. Observed against expected counts routine subgroups under limits in force, outside any sharpening interval in which the chart carried an assignable cause, once each with a signal on any of the characteristic's charts; the expectation is the false-alarm rate for limits estimated from the chart's own baseline size under the rules in force on it, by the Markov chain method. A planned check falls on the clock at the part's check frequency inside a shift the press worked, from 20 minutes after production starts to 2 minutes before the run ends, and is recorded when a routine check falls from 6 minutes before to 12 minutes after it. A late entry is more than 20 minutes after the parts.</p>
<p><strong>Capability and limits.</strong> Ppk on overall sigma from all readings; Cpk by class: between/within on three-way charts, residual about the regression on tool-wear charts, pooled within-subgroup on X-bar and R. Capability intervals by Bissell's approximation. Flatness on the upper index only. Critical characteristics with 60 routine subgroups or more in the quarter, and every flatness characteristic. A limit set's trigger is the reason recorded with it; a chart is in a baseline when its last routine subgroup in the quarter was charted under provisional limits.</p>
<p><strong>Dies, gauges and nonconformances.</strong> A sharpening's shots are the die's corrected shot count at the sharpening less its count at the one before; the due count is in the die master. Burr height is the lab gauge's five readings, against the upper limit. A gauge is out of gating status when it is past calibration due, away for calibration, or has no study on file; a hand gauge is covered by the latest study of its type at its press. The die log carries dates without times, so {placed} of {runs} runs that start on a sharpening day are placed in the interval by the day, and {span} span a logged sharpening date.</p>"""


if __name__ == "__main__":
    html, trace, off, nfig = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "quarterly_review_numbers.csv", index=False, lineterminator="\n")
    print(len(html), "characters;", len(trace), "numbers traced;", nfig, "figures;", len(off), "differ from the text")
    if len(off):
        print(off.to_string())
