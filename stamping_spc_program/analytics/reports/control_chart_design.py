"""Control Chart Design: revalidation on the July 2025 to June 2026 record. Reads the marts, computes the run lengths and
expected rates (analytics.chart_performance), builds the figures and writes docs/reports/control_chart_design.html and
the table of every number in the body with the mart it is read from and the value in the page text."""
import numpy as np
import pandas as pd
from scipy import stats

from analytics.chart_performance import arl as A
from analytics.chart_performance.coil_change import expectation as coil_change_expectation
from analytics.data import query
from analytics.reports import design_figures as FIG
from analytics.reports.page import DAY, F0, F1, F2, F3, F4, P1, Page, YN
from analytics.style import style as S

WEEKS = ((pd.Timestamp("2026-06-30") - pd.Timestamp("2025-07-01")).days + 1) / 7


def expected_rate(chart, n, cache={}):
    """Expected signals per routine subgroup at a chart's own baseline size under the rules in force on it."""
    key = (chart, int(n))
    if key not in cache:
        cache[key] = (A.expected_rate_xbar_r(int(n)) if chart == "X-bar and R" else A.expected_rate_tool_wear(int(n)) if chart == "tool-wear"
                      else A.expected_rate_three_way(min(int(n), 400)))
    return cache[key]


def build():
    pg = Page(); n, pct, txt = pg.num, pg.pct, pg.text
    design = query("select parameter, value from marts.mart_chart_design order by parameter").set_index("parameter")["value"]
    cif = query("select * from marts.mart_charts_in_force order by characteristic_id")
    vc = query("select * from marts.mart_variance_components order by characteristic_id")
    ls = query("select * from marts.mart_limit_sets order by characteristic_id, effective_from, limit_set_id")
    sr = query("select * from marts.mart_signal_rates where period = 'record' order by characteristic_id, press_id, chart, baseline_subgroups")
    sr["expected_rate"] = [expected_rate(c, b) for c, b in zip(sr["chart"], sr["baseline_subgroups"])]
    sr["es"] = sr["expected_rate"] * sr["subgroups_in_scope"]
    crit = vc[vc["critical"] | (vc["characteristic_class"] == "flatness")]
    med = crit.groupby("characteristic_class")[["share_within", "share_between_subgroups_in_coil", "share_between_coils", "share_between_intervals", "incoming_coil_share", "trend_share", "trend_within_share"]].median()
    cls_n = cif.groupby("chart_type").size()
    ch = query("select * from marts.mart_chart_changes order by changed_on").set_index("characteristic_id")
    load = sr.groupby("press_id").agg(routine_subgroups=("routine_subgroups", "sum"), es_all=("expected_rate", lambda s: 0.0)).reset_index()
    load["expected_signals"] = sr.assign(e=sr["expected_rate"] * sr["routine_subgroups"]).groupby("press_id")["e"].sum().values
    load["per_week"] = load["routine_subgroups"] / WEEKS; load["alarms_per_week"] = load["expected_signals"] / WEEKS
    scope = sr.groupby("chart").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum"))
    scope["observed per 100"] = 100 * scope["signals"] / scope["subgroups"]; scope["expected per 100"] = 100 * scope["es"] / scope["subgroups"]; scope["ratio"] = scope["signals"] / scope["es"]
    fam = vc[vc["family_part"]].merge(cif[["characteristic_id", "gauge_type"]], on="characteristic_id", how="left")
    fam_cif = cif[cif["family_part"]]

    # ═══════════════ 1. Summary
    pg.h2("summary", "1. Summary")
    pg.p(f"Every chart in force fits the variation it controls, and the year's record confirms the chart selection on all four characteristic classes. Formed heights and bend angles run on three-way charts with a coil-change chart beside them, because "
         f"{pct(med.at['formed', 'incoming_coil_share'], 'mart_variance_components.incoming_coil_share, formed, median', was='49.7%')} of their incoming variance lies between coils; hole diameters run on tool-wear charts, because "
         f"{pct(med.at['hole diameter', 'trend_share'], 'mart_variance_components.trend_share, hole diameter, median', was='36.2%')} of their variance is the wear trend within a sharpening interval; hole position, length, width and flatness run on X-bar and R, because "
         f"{pct(med.at['hole position', 'share_within'], 'mart_variance_components.share_within, hole position, median', was='97.4%')} to {pct(med.at['flatness', 'share_within'], 'mart_variance_components.share_within, flatness, median', was='97.5%')} of their variance lies within the subgroup. "
         f"At 30 June 2026 there are {n(len(cif), 'mart_charts_in_force: charts', was='1,380')} charts in force on {n(cif['press_id'].nunique(), 'mart_charts_in_force: presses', was='11')} presses: "
         f"{n(int(cif[(cif['chart_type'] == 'three-way (I-MR-R)') & (cif['characteristic_class'] == 'formed')].shape[0]), 'mart_charts_in_force: three-way, formed', was='399')} three-way, {n(int(cls_n.get('tool-wear', 0)), 'mart_charts_in_force: tool-wear', was='23')} tool-wear, "
         f"{n(int(cls_n.get('Xbar-R', 0)), 'mart_charts_in_force: X-bar and R', was='474')} X-bar and R, {n(int(cls_n.get('p', 0)), 'mart_charts_in_force: p', was='483')} p charts on the attribute checks, and "
         f"{pg.word(int(cif[(cif['chart_type'] == 'three-way (I-MR-R)') & (cif['characteristic_class'] == 'hole position')].shape[0]), 'mart_charts_in_force: three-way, hole position', was='one')} three-way chart on a hole position. "
         f"Burr height on the laboratory gauge is controlled by the sharpening count on {n(int(query('select count(*) n from staging.stg_spc__characteristics where chart_type = ' + chr(39) + 'none' + chr(39))['n'].iloc[0]), 'stg_spc__characteristics: chart none', was='180')} characteristics and carries no chart.")
    tw, mv = ch.loc["C-15731-02"], ch.loc["C-34479-05"]
    pg.p("Two charts changed in the year, both from the record.")
    pg.ul([f"<strong>C-15731-02 ({tw.die_id}, {tw.press_id}):</strong> the tool-wear recalculation trigger shortened from {n(tw.from_value, 'mart_chart_changes.from_value', was='30')} to {n(tw.to_value, 'mart_chart_changes.to_value', was='20')} subgroups, first applied "
           f"{txt(DAY(tw.changed_on), 'mart_chart_changes.changed_on', was='8 December 2025')}, after the die's intervals shortened under the burr line and the regression lagged them.",
           f"<strong>C-34479-05 ({mv.die_id}, {txt(mv.press_id, 'mart_chart_changes.press_id', was='PR-10')}):</strong> moved from X-bar and R to a three-way chart on {txt(DAY(mv.changed_on), 'mart_chart_changes.changed_on', was='9 March 2026')}, after "
           f"{pct(mv.evidence_value, 'mart_chart_changes.evidence_value', was='35.2%')} of its variance was found between coils."])
    tot_w = load["alarms_per_week"].sum(); sub_w = load["per_week"].sum(); p3 = load.set_index("press_id").loc["PR-03"]
    pg.p(f"The charts as designed raise {n(tot_w, 'mart_signal_rates with the expected rate per chart: false alarms per week, plant', was='133')} false alarms a week across the plant, {n(100 * tot_w / sub_w, 'false alarms per 100 routine subgroups, plant', '{:.1f}', was='3.1')} per 100 routine subgroups on "
         f"{n(sub_w, 'mart_signal_rates.routine_subgroups per week, plant', was='4,236')} subgroups a week. PR-03 carries {n(p3.alarms_per_week, 'false alarms per week, PR-03', '{:.1f}', was='23.7')} of them on {n(p3.per_week, 'routine subgroups per week, PR-03', was='750')} subgroups; the median press carries "
         f"{n(load['alarms_per_week'].median(), 'false alarms per week, median press', '{:.1f}', was='12.9')}.")
    t1 = cif.groupby(["characteristic_class", "chart_type"]).size().reset_index(name="charts")
    pg.table("Charts in force at 30 June 2026, by class and chart", t1, {"characteristic_class": "Characteristic class", "chart_type": "Chart", "charts": "Charts"}, {"Charts": F0})
    pg.table("False-alarm load as designed, per press per week", load, {"press_id": "Press", "per_week": "Routine subgroups a week", "alarms_per_week": "Expected false alarms a week"}, {"Routine subgroups a week": F0, "Expected false alarms a week": F1},
             note="Expected at each chart's own baseline size under the rules in force on it, times the chart's routine subgroups in the year, over 52.1 weeks.")
    rw = query("select * from marts.mart_limit_sets where issued_in_record and trigger = 'annual review' and chart = 'three-way'")
    rw["below_coil_change_minimum"] = rw["below_coil_change_minimum"].fillna(False).astype(bool)
    pg.p("Three findings call for action.")
    pg.ul([f"<strong>{n(int(rw['below_coil_change_minimum'].sum()), 'mart_limit_sets: three-way annual-review sets below the coil-change minimum', was='23')} of the {n(len(rw), 'mart_limit_sets: three-way sets at the annual review', was='45')} three-way limit sets issued at the annual review span fewer than ten coil changes.</strong> The review computed them on a trailing window rather than the baseline rule. They are re-issued as ten coil changes accrue.",
           f"<strong>Tool-wear charts signal at {n(scope.at['tool-wear', 'ratio'], 'mart_signal_rates with the expected rate: tool-wear observed over expected', '{:.2f}', was='1.79')} times their expected false-alarm rate</strong> on rules 3 and 4, from small level changes at sharpening that pass verification and from the regression line held between verifications. The verification criterion and the re-fit trigger are reviewed in Section 4.",
           f"<strong>Three-way charts signal at {n(scope.at['three-way', 'ratio'], 'mart_signal_rates with the expected rate: three-way observed over expected', '{:.2f}', was='0.83')} of expectation</strong>, because their individuals limits carry the residual coil offset left after centring. This is the design working as intended, and the shortfall is the price of it."])

    # ═══════════════ 2. Variance structure
    pg.h2("variance", "2. Variance structure by characteristic class")
    pg.p("The chart for each class follows from where its variance lies, and the four classes differ enough that no one chart serves them all.")
    pg.ul([f"<strong>Formed height and bend angle:</strong> {pct(med.at['formed', 'share_within'], 'mart_variance_components.share_within, formed', was='80.0%')} of the routine variance lies within the subgroup after centring, {pct(med.at['formed', 'share_between_subgroups_in_coil'], 'mart_variance_components.share_between_subgroups_in_coil, formed', was='5.2%')} between subgroups within a coil, and "
           f"{pct(med.at['formed', 'share_between_coils'], 'mart_variance_components.share_between_coils, formed', was='13.5%')} is the residual coil offset that centring leaves. Before centring, {pct(med.at['formed', 'incoming_coil_share'], 'mart_variance_components.incoming_coil_share, formed', was='49.7%')} of the incoming variance on coil-change subgroups lies between coils.",
           f"<strong>Hole diameter:</strong> {pct(med.at['hole diameter', 'trend_share'], 'mart_variance_components.trend_share, hole diameter', was='36.2%')} of the variance is the wear trend over a sharpening interval; {pct(med.at['hole diameter', 'trend_within_share'], 'mart_variance_components.trend_within_share, hole diameter', was='56.1%')} lies within the subgroup about the trend.",
           f"<strong>Hole position, length and width:</strong> {pct(med.at['hole position', 'share_within'], 'mart_variance_components.share_within, hole position', was='97.4%')} within the subgroup, {pct(med.at['hole position', 'share_between_coils'], 'mart_variance_components.share_between_coils, hole position', was='0.8%')} between coils.",
           f"<strong>Flatness:</strong> {pct(med.at['flatness', 'share_within'], 'mart_variance_components.share_within, flatness', was='97.5%')} within the subgroup."])
    fig1 = med.reset_index()
    pg.figure(FIG.variance_components(fig1), "Figure 1: Variance components by class", "Each bar is one class: the median share of variance in each component across its critical characteristics (all flatness characteristics) with 60 routine subgroups or more in the year, nested by the method of moments.")
    cf = query("select * from marts.mart_coil_fit order by characteristic_id")
    pg.p(f"The coil effect on formed characteristics is predictable from the coil certificate, which is why centring at the coil change removes it. Across {n(len(cf), 'mart_coil_fit: characteristics', was='242')} formed characteristics, thickness and hardness on the certificate explain the coil means with a median R squared of "
         f"{n(cf['r_squared'].median(), 'mart_coil_fit.r_squared, median', '{:.2f}', was='0.82')}; the residual about the fit is {pct(cf['residual_sigma_share_of_tolerance'].median(), 'mart_coil_fit.residual_sigma_share_of_tolerance, median', was='3.2%')} of tolerance, against coil means that spread "
         f"{pct(cf['coil_means_sigma_share_of_tolerance'].median(), 'mart_coil_fit.coil_means_sigma_share_of_tolerance, median', was='10.1%')} of tolerance.")
    rmed = float(cf["r_squared"].median()); fc = cf[cf["family_part"] & (cf["coil_change_subgroups"] >= 20)].copy(); fc["d"] = (fc["r_squared"] - rmed).abs(); pick = fc.sort_values(["d", "characteristic_id"]).iloc[0]
    pts = query("select sample_time, subgroup_id, certificate_thickness_mm, certificate_hardness_hrb, subgroup_mean as observed, charted_point from marts.mart_coil_change_points where characteristic_id = ? order by sample_time, subgroup_id", [pick.characteristic_id])
    pts["predicted"] = pick.intercept + pick.per_mm_thickness * pts["certificate_thickness_mm"] + pick.per_hrb * pts["certificate_hardness_hrb"]
    kp = query("select name, usl, lsl from staging.stg_spc__characteristics where characteristic_id = ?", [pick.characteristic_id]).iloc[0]
    pg.figure(FIG.coil_fit(pts, kp.lsl, kp.usl), f"Figure 2: Coil means against the certificate fit, {txt(pick.characteristic_id, 'mart_coil_fit: family characteristic with R squared nearest the plant median', was='C-11333-05')}",
              "Each point is one coil-change subgroup (10 pieces, before centring): its mean against the mean predicted from the coil's certificate thickness and hardness; the first subgroup on each coil is the point on the chart of coil-change means.")
    pg.p(f"On {pick.characteristic_id} ({kp['name']}, {pick.part_id}) the fit is {n(pick.per_mm_thickness, 'mart_coil_fit.per_mm_thickness', '{:.2f}', was='2.73')} mm of height per mm of certificate thickness and {n(pick.per_hrb, 'mart_coil_fit.per_hrb', '{:.4f}', was='-0.0094')} mm per HRB of hardness, R squared "
         f"{n(pick.r_squared, 'mart_coil_fit.r_squared', '{:.3f}', was='0.814')}, on {n(pick.coil_change_subgroups, 'mart_coil_fit.coil_change_subgroups', was='20')} coil-change subgroups over {n(pick.coils, 'mart_coil_fit.coils', was='9')} coils. The residual is "
         f"{pct(pick.residual_sigma_share_of_tolerance, 'mart_coil_fit.residual_sigma_share_of_tolerance', was='3.2%')} of tolerance and the coil means spread {pct(pick.coil_means_sigma_share_of_tolerance, 'mart_coil_fit.coil_means_sigma_share_of_tolerance', was='9.3%')}.")
    ff = fam[fam["characteristic_class"] == "formed"]; fh = fam[fam["characteristic_class"].isin(["hole position", "length and width"])]; fhd = fam[fam["characteristic_class"] == "hole diameter"].iloc[0]
    pg.p(f"The family's {n(len(fam), 'mart_variance_components: family variable characteristics', was='20')} variable characteristics show the same structure one at a time. The formed heights and bend angles carry between-coil shares of "
         f"{n(100 * ff['share_between_coils'].min(), 'mart_variance_components.share_between_coils, family formed, lowest', '{:.0f}', was='7')}% to {n(100 * ff['share_between_coils'].max(), 'mart_variance_components.share_between_coils, family formed, highest', '{:.0f}', was='31')}% on the routine record and "
         f"{n(100 * ff['incoming_coil_share'].min(), 'mart_variance_components.incoming_coil_share, family, lowest', '{:.0f}', was='22')}% to {n(100 * ff['incoming_coil_share'].max(), 'mart_variance_components.incoming_coil_share, family, highest', '{:.0f}', was='52')}% incoming; the hole positions carry "
         f"{n(100 * fh['share_between_coils'].min(), 'mart_variance_components.share_between_coils, family hole position and width, lowest', '{:.0f}', was='0')}% to {n(100 * fh['share_between_coils'].max(), 'mart_variance_components.share_between_coils, family hole position and width, highest', '{:.0f}', was='6')}%; the one variable hole diameter, {fhd.characteristic_id}, carries a "
         f"{pct(fhd.trend_share, 'mart_variance_components.trend_share, C-15731-02', was='23.5%')} wear trend.")
    pg.table("The family's characteristics: variance components, chart and gauge", fam,
             {"characteristic_id": "Characteristic", "characteristic_name": "Name", "routine_subgroups": "Routine subgroups", "coils": "Coils", "share_within": "Within", "share_between_subgroups_in_coil": "Between subgroups in a coil", "share_between_coils": "Between coils",
              "share_between_intervals": "Between intervals", "incoming_coil_share": "Incoming coil share", "trend_share": "Wear trend", "chart_type": "Chart", "gauge_id": "Gauge", "gauge_type": "Gauge type"},
             {"Routine subgroups": F0, "Coils": F0, "Within": P1, "Between subgroups in a coil": P1, "Between coils": P1, "Between intervals": P1, "Incoming coil share": P1, "Wear trend": P1},
             note="Shares of the routine record's variance over the year; the incoming coil share is on the coil-change subgroups before centring; the wear trend is on the hole diameter's subgroups with shots since sharpening known.")

    # ═══════════════ 3. Limit setting and governance
    pg.h2("limits", "3. Limit setting and governance")
    tc = ls["trigger"].value_counts()
    pg.p(f"Limits are set once from a baseline and then held across sharpenings under verification, so a chart's limits change only when the process has. The record holds {n(len(ls), 'mart_limit_sets: limit sets', was='1,216')} limit sets on {n(ls['characteristic_id'].nunique(), 'mart_limit_sets: charts', was='897')} variable charts: "
         f"{n(tc['baseline before the record'], 'mart_limit_sets.trigger: baseline before the record', was='855')} in force from before July 2025, {n(tc['rebuild'], 'mart_limit_sets.trigger: rebuild', was='171')} after a rebuild, {n(tc['tool-wear re-fit'], 'mart_limit_sets.trigger: tool-wear re-fit', was='77')} tool-wear lines re-fitted after a passed verification, "
         f"{n(tc['annual review'], 'mart_limit_sets.trigger: annual review', was='74')} from the annual review and {n(tc['failed verification'], 'mart_limit_sets.trigger: failed verification', was='39')} after a failed verification.")
    pb = query("select * from marts.mart_phase1_baselines order by effective_from, limit_set_id")
    pg.p(f"<strong>Phase I baselines.</strong> {n(len(pb), 'mart_phase1_baselines: baselines', was='244')} baselines were completed in the year: {n(int((pb['chart'] == 'X-bar and R').sum()), 'mart_phase1_baselines: X-bar and R', was='199')} X-bar and R and {n(int((pb['chart'] == 'three-way').sum()), 'mart_phase1_baselines: three-way', was='45')} three-way. A baseline is "
         f"{n(design['baseline_subgroups'], 'mart_chart_design.baseline_subgroups', was='25')} subgroups; a three-way baseline spans at least ten coil changes, and its individuals limits come from the spread of the baseline means rather than the moving range (Section 4). Subgroups beyond the baseline's own limits are screened: "
         f"{n(int(pb['screened_subgroups'].sum()), 'mart_phase1_baselines.screened_subgroups, total', was='94')} subgroups in {n(int((pb['screened_subgroups'] > 0).sum()), 'mart_phase1_baselines: baselines with a subgroup screened', was='64')} baselines. Anderson-Darling on the baseline means passes at 5% on "
         f"{pct(pb['normal_at_5pct'].mean(), 'mart_phase1_baselines.normal_at_5pct, share', was='92.9%')} of baselines; flatness baselines are tested after a Box-Cox transformation.")
    b = query("select * from marts.mart_phase1_baseline_subgroups where limit_set_id = 'LS-00074' order by baseline_subgroup_no")
    b0 = b.iloc[0]; pb74 = pb[pb["limit_set_id"] == "LS-00074"].iloc[0]
    rb_ = query("select event_date from intermediate.int_die_event_timeline where die_id = 'D-1333-C' and event_type = 'rebuild' and event_date between '2026-05-01' and '2026-05-11'").iloc[0]
    pg.figure(FIG.phase1_baseline(b, b0.centre_line, b0.ucl_mean, b0.lcl_mean, b0.ucl_range), "Figure 3: A Phase I baseline after a rebuild, C-11333-02, 11 May 2026",
              "The 25 routine subgroups of limit set LS-00074 on C-11333-02 (hole to edge B), run R26-00820: means against the computed centre line and limits, ranges against the range limit. Subgroup 18 is flagged on the range and kept in the limits, as the record has it.")
    scr = b[b["screened"]].iloc[0]; keep = b[~b["screened"]]; xb, rb = keep["subgroup_mean"].mean(), keep["subgroup_range"].mean()
    move = max(abs(xb - b0.centre_line), abs(xb + 0.577 * rb - b0.ucl_mean), abs(xb - 0.577 * rb - b0.lcl_mean))
    pg.p(f"The baseline on C-11333-02 after the rebuild of {txt(DAY(rb_.event_date), 'int_die_event_timeline: rebuild of D-1333-C', was='9 May 2026')} shows the procedure: {n(len(b), 'mart_phase1_baseline_subgroups: subgroups', was='25')} routine subgroups on one run, limits "
         f"{n(b0.lcl_mean, 'mart_phase1_baseline_subgroups.lcl_mean', '{:.3f}', was='24.381')} to {n(b0.ucl_mean, 'mart_phase1_baseline_subgroups.ucl_mean', '{:.3f}', was='24.435')} mm on the means and a range limit of {n(b0.ucl_range, 'mart_phase1_baseline_subgroups.ucl_range', '{:.4f}', was='0.0988')} mm, Anderson-Darling "
         f"{n(pb74.anderson_darling, 'mart_phase1_baselines.anderson_darling', '{:.2f}', was='0.53')} against a critical value of {n(pb74.anderson_darling_critical_5pct, 'mart_phase1_baselines.anderson_darling_critical_5pct', '{:.2f}', was='0.73')}. Subgroup "
         f"{n(scr.baseline_subgroup_no, 'mart_phase1_baseline_subgroups: screened subgroup', was='18')} carries a range of {n(scr.subgroup_range, 'mart_phase1_baseline_subgroups.subgroup_range, screened', '{:.3f}', was='0.106')} mm, beyond the range limit, and is flagged. The record keeps it in the limits; recomputed without it the mean limits move by under "
         f"{n(0.002 if move < 0.002 else move, 'mart_phase1_baseline_subgroups: largest move of the mean limits without the screened subgroup', '{:.3f}', was='0.002')} mm and the range limit by "
         f"{n(abs(2.114 * rb - b0.ucl_range), 'mart_phase1_baseline_subgroups: move of the range limit without the screened subgroup', '{:.3f}', was='0.005')} mm.")
    vf = query("select * from marts.mart_limit_verifications")
    vt = vf.groupby(["chart", "die_event"]).agg(verifications=("verification_id", "count"), failed=("result", lambda s: int((s == "failed").sum()))).reset_index(); vt["rate"] = vt["failed"] / vt["verifications"]; vtx = vt.set_index(["chart", "die_event"])
    shp = vf[(vf["die_event"] == "sharpening") & vf["chart"].isin(["X-bar and R", "tool-wear"])].groupby(["die_id", "event_date"])["result"].apply(lambda s: (s == "failed").any())
    pg.p(f"<strong>Verification.</strong> A sharpening does not reset the limits. The first {n(design['verification_subgroups'], 'mart_chart_design.verification_subgroups', was='25')} routine subgroups after it verify them: the verification passes when no rule 1 signal is confirmed and the mean of the 25 lies within "
         f"{n(design['verification_mean_within_sigma'], 'mart_chart_design.verification_mean_within_sigma', '{:.1f}', was='1.5')} sigma of the centre line. Formed charts are verified after a rebuild or a forming-station repair only, on 25 subgroups spanning at least "
         f"{pg.word(design['verification_formed_coil_changes'], 'mart_chart_design.verification_formed_coil_changes', was='two')} coil changes, since a sharpening does not touch the forming stations.")
    x1, x2, x3 = vtx.loc[("X-bar and R", "sharpening")], vtx.loc[("tool-wear", "sharpening")], vtx.loc[("three-way", "rebuild")]
    pg.ul([f"<strong>X-bar and R:</strong> {n(x1.verifications, 'mart_limit_verifications: X-bar and R after sharpening', was='1,100')} verifications after sharpening, {n(x1.failed, 'mart_limit_verifications: X-bar and R failed', was='34')} failed ({pct(x1.rate, 'X-bar and R failure rate', was='3.1%')}).",
           f"<strong>Tool-wear:</strong> {n(x2.verifications, 'mart_limit_verifications: tool-wear', was='67')} verifications, {n(x2.failed, 'mart_limit_verifications: tool-wear failed', was='2')} failed ({pct(x2.rate, 'tool-wear failure rate', was='3.0%')}).",
           f"<strong>Three-way after a rebuild:</strong> {n(x3.verifications, 'mart_limit_verifications: three-way after a rebuild', was='141')} verifications, {n(x3.failed, 'mart_limit_verifications: three-way failed', was='3')} failed ({pct(x3.rate, 'three-way failure rate', was='2.1%')}).",
           f"<strong>By sharpening:</strong> {n(int(shp.sum()), 'mart_limit_verifications: sharpenings with a failure on an X-bar and R or tool-wear chart', was='33')} of {n(len(shp), 'mart_limit_verifications: sharpenings', was='408')} sharpenings failed on at least one chart of the die ({pct(shp.mean(), 'share of sharpenings failed', was='8.1%')})."])
    ok = vf[vf["result"] == "passed"]
    cx, cw = A._normal_nodes(9); qx, qw = A._chi_ratio_nodes(3.8 * 25, 9)
    ff_rate = sum(a * w_ * (stats.norm.sf((1.5 * r - c / 5) * 5) + stats.norm.cdf((-1.5 * r - c / 5) * 5)) for c, a in zip(cx, cw) for r, w_ in zip(qx, qw))
    pg.p(f"The passes sit close to centre, at a median offset of {n(ok['mean_offset_sigma'].abs().median(), 'mart_limit_verifications.mean_offset_sigma, passes, median absolute', '{:.2f}', was='0.21')} sigma, and {n(int((ok['mean_offset_sigma'].abs() >= 1.0).sum()), 'mart_limit_verifications: passes at 1.0 to 1.5 sigma', was='19')} of the "
         f"{n(len(ok), 'mart_limit_verifications: passes', was='1,269')} passes lie between 1.0 and 1.5 sigma. On an unchanged process the mean criterion fails by chance on under {n(0.001 if ff_rate < 0.00001 else ff_rate * 100, 'analytics.chart_performance: false-failure rate of the mean criterion, limits from 25 subgroups', '{:.3f}', was='0.001')}% of verifications, so the failures are the dies that came back from the sharpening at a different level.")
    pg.table("Verifications of limits held across a die event", vt, {"chart": "Chart", "die_event": "After", "verifications": "Verifications", "failed": "Failed", "rate": "Failure rate"}, {"Verifications": F0, "Failed": F0, "Failure rate": P1},
             note="Verifications completed 1 July 2025 to 30 June 2026.")
    rc = query("select trigger, cast(sum(limit_sets) as integer) n from marts.mart_limit_recalculations group by 1").set_index("trigger")["n"]
    pg.p(f"<strong>Recalculations.</strong> {n(int(rc.sum()), 'mart_limit_recalculations: limit sets in the year', was='319')} new limit sets were issued in the year: {n(rc['rebuild'], 'mart_limit_recalculations: rebuild', was='146')} after rebuilds, {n(rc['annual review'], 'mart_limit_recalculations: annual review', was='74')} at the annual review on 19 January 2026, "
         f"{n(rc['tool-wear re-fit'], 'mart_limit_recalculations: tool-wear re-fit', was='65')} tool-wear lines re-fitted after a passed verification, and {n(rc['failed verification'], 'mart_limit_recalculations: failed verification', was='34')} after a failed verification. "
         f"{n(int(query("select sum(limit_sets) n from marts.mart_limit_recalculations where trigger = 'annual review' and issued_month between '2026-01' and '2026-03'")['n'].iloc[0]), 'mart_limit_recalculations: annual review, January to March', was='71')} of the annual review's {n(rc['annual review'], 'mart_limit_recalculations: annual review', was='74')} sets arrived in January to March.")
    by_month = query("select issued_month, trigger, cast(sum(limit_sets) as integer) n from marts.mart_limit_recalculations group by all").pivot(index="issued_month", columns="trigger", values="n").fillna(0).astype(int).reset_index()
    pg.figure(FIG.recalculations(by_month), "Figure 4: Recalculations by month and trigger", "New limit sets issued each month, July 2025 to June 2026, by the trigger that issued them.")
    below = rw[rw["below_coil_change_minimum"]]
    pg.p(f"<strong>The annual review's three-way sets.</strong> {n(len(below), 'mart_limit_sets: three-way annual-review sets below the minimum', was='23')} of the {n(len(rw), 'mart_limit_sets: three-way annual-review sets', was='45')} three-way limit sets issued at the review span "
         f"{pg.word(below['coil_changes_spanned'].min(), 'mart_limit_sets.coil_changes_spanned, lowest', was='one')} to {pg.word(below['coil_changes_spanned'].max(), 'mart_limit_sets.coil_changes_spanned, highest', was='nine')} coil changes, against the baseline rule of ten, because the review computed on a trailing window of "
         f"{n(below['subgroups_used'].min(), 'mart_limit_sets.subgroups_used, lowest', was='50')} to {n(below['subgroups_used'].max(), 'mart_limit_sets.subgroups_used, highest', was='978')} subgroups rather than on the baseline rule. Their centre lines are sound; their individuals limits understate the coil offset the design is meant to carry. They are re-issued as ten coil changes accrue on each chart.")
    t5 = ls[ls["characteristic_id"] == "C-15731-02"]; inforce = t5[t5["effective_to"].isna()].iloc[0]
    charted = t5[t5["routine_subgroups_charted"] >= 0]
    in_year = charted[(charted["effective_to"].isna()) | (charted["effective_to"] >= pd.Timestamp("2025-07-01"))]
    pg.p(f"<strong>Tool-wear charts.</strong> The centre line is the regression of diameter on shots since sharpening over the die's earlier intervals, re-fitted at each verification that passes with the limits' sigma held, so the line follows the die without a new baseline. On C-15731-02 the line in force ({txt(DAY(inforce.effective_from), 'mart_limit_sets.effective_from, C-15731-02 in force', was='27 May 2026')}) runs at "
         f"{n(inforce.slope_per_100k_shots, 'mart_limit_sets.slope_per_100k_shots', '{:.4f}', was='0.0058')} mm per 100,000 shots from {n(inforce.centre_line, 'mart_limit_sets.centre_line', '{:.4f}', was='9.4555')} mm with limits of plus and minus {n(3 * inforce.sigma_of_means, 'mart_limit_sets.sigma_of_means times 3', '{:.4f}', was='0.0060')} mm, and the chart ran on "
         f"{pg.word(len(in_year), 'mart_limit_sets: C-15731-02 sets in force in the year', was='ten')} limit sets in the year: {pg.word(int((in_year['trigger'] == 'tool-wear re-fit').sum()), 'mart_limit_sets: C-15731-02 re-fits in force in the year', was='eight')} re-fits, "
         f"{pg.word(int(((in_year['trigger'] == 'tool-wear re-fit') & ~in_year['issued_in_record']).sum()), 'mart_limit_sets: C-15731-02 re-fits issued before July 2025', was='one')} of them in force from {txt(in_year[~in_year['issued_in_record']]['effective_from'].min().strftime('%B %Y'), 'mart_limit_sets.effective_from, set in force on 1 July 2025', was='June 2025')}, "
         f"{pg.word(int((in_year['trigger'] == 'failed verification').sum()), 'mart_limit_sets: C-15731-02 failed verification', was='one')} failed verification and the annual review.")
    wp = query("select * from marts.mart_wear_points where characteristic_id = 'C-15731-02' and characteristic_type = 'hole diameter' and limit_set_id = ? order by sample_time", [inforce.limit_set_id])
    g5 = wp[wp["sharpening_interval_no"] == wp["sharpening_interval_no"].max()]
    pg.figure(FIG.tool_wear_chart(g5, inforce.centre_line, inforce.slope_per_100k_shots, 3 * inforce.sigma_of_means, g5["usl"].iloc[0], g5["lsl"].iloc[0]),
              f"Figure 5: The tool-wear chart on C-15731-02, interval from {txt(DAY(g5['sharpening_date'].iloc[0]), 'mart_wear_points.sharpening_date', was='1 May 2026')}",
              "The subgroups of hole diameter B on D-5731-A charted under the limit set in force at 30 June (from 27 May 2026), against shots since the sharpening, with its regression centre line and sloped limits.")
    ws = query("select characteristic_id, die_id, min(press_id) press_id, any_value(characteristic_rate_mm_per_100k_shots) rate, any_value(qualifying_intervals) intervals from marts.mart_wear_slopes group by characteristic_id, die_id order by rate, characteristic_id")
    pg.p(f"Wear rates by die run from {n(ws['rate'].min(), 'mart_wear_slopes.characteristic_rate_mm_per_100k_shots, lowest', '{:.4f}', was='0.0041')} to {n(ws['rate'].max(), 'mart_wear_slopes.characteristic_rate_mm_per_100k_shots, highest', '{:.4f}', was='0.0100')} mm per 100,000 shots on the "
         f"{n(len(ws), 'mart_wear_slopes: characteristics', was='19')} charted hole diameters. {pg.word(int((ws['intervals'] == 1).sum()), 'mart_wear_slopes.qualifying_intervals equal to 1', was='Six').capitalize()} of the rates rest on a single sharpening interval and are shown with that count.")
    pg.table("Hole diameter wear by die, with the intervals behind each rate", ws, {"characteristic_id": "Hole diameter", "die_id": "Die", "press_id": "Press", "rate": "Wear, mm per 100,000 shots", "intervals": "Intervals"}, {"Wear, mm per 100,000 shots": F4, "Intervals": F0},
             note="Each rate is the median slope of subgroup means on shots since sharpening over the die's intervals of 15 subgroups or more spanning 20,000 shots.")
    same_day = query("select count(*) n, count(*) filter (where cast(actual_start as date) = sharpening_date) d from intermediate.int_run_shots where shots_since_sharpening_at_start is not null").iloc[0]
    span = int(query("select count(*) n from intermediate.int_run_shots r where shots_since_sharpening_at_start is not null and exists (select 1 from intermediate.int_sharpening_intervals i where i.die_id = r.die_id and i.interval_start between cast(r.actual_start as date) and cast(r.actual_end as date))")["n"].iloc[0])
    pg.p(f"The die log carries dates without times, so a run is placed in the interval of the last sharpening dated on or before its start day. {n(same_day.d, 'int_run_shots: runs starting on the day their sharpening is logged', was='15')} of {n(same_day.n, 'int_run_shots: runs with a shot count', was='1,399')} runs start on the day their die's sharpening is logged, and "
         f"{n(span, 'int_run_shots with int_sharpening_intervals: runs spanning a logged sharpening date', was='92')} span a logged sharpening date, where the log date and the run times disagree; both enter the tool-wear shot counts and the wear rates above.")

    # ═══════════════ 4. Chart performance
    pg.h2("performance", "4. Chart performance")
    pg.p(f"The rules in force were chosen for the false-alarm load they carry as much as for the shifts they catch. Under rule 1 alone an X-bar chart signals once in {n(A.arl_rules(0, (1,)), 'analytics.chart_performance.arl_rules, rule 1, known', was='370')} in-control subgroups; with Western Electric rules 1 to 4 it signals once in "
         f"{n(A.arl_rules(0, (1, 2, 3, 4)), 'arl_rules, rules 1 to 4, known', was='92')}, and catches a one-sigma shift in {n(A.arl_rules(1, (1, 2, 3, 4)), 'arl_rules, rules 1 to 4 at 1 sigma', was='9')} subgroups instead of {n(A.arl_rules(1, (1,)), 'arl_rules, rule 1 at 1 sigma', was='44')}. Limits estimated from 25 subgroups move both figures: rule 1 to once in "
         f"{n(A.expected_arl_xbar(25, 0, (1,)), 'expected_arl_xbar, rule 1, baseline 25', was='407')}, rules 1 to 4 to once in {n(A.expected_arl_xbar(25, 0, (1, 2, 3, 4)), 'expected_arl_xbar, rules 1 to 4, baseline 25', was='74')}.")
    rows = [{"shift": sh, "a": A.arl_rules(sh, (1,)), "b": A.arl_rules(sh, (1, 2, 3, 4)), "c": A.expected_arl_xbar(25, sh, (1,)), "d": A.expected_arl_xbar(25, sh, (1, 2, 3, 4)),
             "e": A.three_way_arl(sh, with_moving_range=False, with_range=False), "f": A.three_way_arl(sh), "g": A.expected_arl_three_way(25, sh)} for sh in (0.0, 1.0, 1.5, 2.0)]
    pg.table("ARL by chart as designed", pd.DataFrame(rows), {"shift": "Shift (sigma)", "a": "X-bar, rule 1", "b": "X-bar, rules 1 to 4", "c": "X-bar, rule 1, baseline 25", "d": "X-bar, rules 1 to 4, baseline 25",
                                                                "e": "Three-way individuals, rule 1", "f": "Three-way, all three charts", "g": "Three-way, all three charts, baseline 25"},
             {"Shift (sigma)": F1, **{k: F1 for k in ("X-bar, rule 1", "X-bar, rules 1 to 4", "X-bar, rule 1, baseline 25", "X-bar, rules 1 to 4, baseline 25", "Three-way individuals, rule 1", "Three-way, all three charts", "Three-way, all three charts, baseline 25")}},
             note="Average run length in subgroups, by the Markov chain method: at known parameters, and averaged over the estimates from a baseline of 25 subgroups. Tool-wear charts run rules 1 to 4 about the regression line; their ARLs at known parameters are those of the X-bar columns.")
    f6 = pd.DataFrame([{"shift": sh, "X-bar rule 1": A.arl_rules(sh, (1,)), "X-bar rules 1 to 4": A.arl_rules(sh, (1, 2, 3, 4)), "three-way individuals rule 1": A.three_way_arl(sh, with_moving_range=False, with_range=False), "three-way all three charts": A.three_way_arl(sh)} for sh in np.arange(0, 2.01, 0.25)])
    pg.figure(FIG.arl_curves(f6), "Figure 6: ARL curves by chart type", "Average run length against a shift in the mean, known parameters, log scale. The three-way chart's curve with all three charts includes the moving-range and range charts.")
    fvc = vc[vc["characteristic_class"] == "formed"].copy(); fvc["means_var"] = fvc["share_between_subgroups_in_coil"] + fvc["share_between_coils"] + fvc["share_within"] / 5
    rho = float((fvc["share_between_coils"] / fvc["means_var"]).median())
    ppc = float(query("select median(k) n from (select characteristic_id, run_id, coil_id, count(*) k from intermediate.int_characteristic_history where characteristic_class = 'formed' and subgroup_type = 'routine' and in_record group by all)")["n"].iloc[0])
    mr_ratio = A.moving_range_sigma_ratio(rho, ppc)
    alts = pd.DataFrame([{"design": "Rule 1, limits from the standard deviation of the baseline means (in force)", "v": 100 * A.coil_block_rate(rho, (1,), 1.0)},
                         {"design": "Rules 1 to 4, limits from the standard deviation of the baseline means", "v": 100 * A.coil_block_rate(rho, (1, 2, 3, 4), 1.0)},
                         {"design": "Rule 1, limits from the average moving range", "v": 100 * A.coil_block_rate(rho, (1,), mr_ratio)},
                         {"design": "Rules 1 to 4, limits from the average moving range", "v": 100 * A.coil_block_rate(rho, (1, 2, 3, 4), mr_ratio)}])
    mr_rate = 100 * 2 * stats.norm.sf(A.D4[2] * A.D2[2] / np.sqrt(2)); r_rate = 100 * A.range_rate(1.0)
    pg.p(f"<strong>The three-way design.</strong> On formed characteristics the level resets at each coil, and centring on a 10-piece coil-change subgroup leaves each coil with a residual offset of {pct(rho, 'mart_variance_components: residual coil share of the variance of formed subgroup means, median', was='39.1%')} of the variance of the subgroup means. Limits from the average moving range do not carry that offset: with them rule 1 alone would signal on "
         f"{n(alts.v[2], 'coil_block_rate, rule 1, moving-range limits', '{:.2f}', was='1.57')} in-control points per 100, and rules 1 to 4 on {n(alts.v[3], 'coil_block_rate, rules 1 to 4, moving-range limits', '{:.1f}', was='20.5')}. The individuals limits in force therefore come from the standard deviation of the baseline means, and rules 2 to 4 are off on the individuals chart: rule 1 signals on "
         f"{n(alts.v[0], 'coil_block_rate, rule 1, limits in force', '{:.2f}', was='0.27')} per 100, the nominal rate. The range and moving-range charts run rule 1 at {n(r_rate, 'range_rate, known', '{:.2f}', was='0.46')} and {n(mr_rate, 'moving-range rule 1 rate, independent means', '{:.2f}', was='0.92')} per 100. A coil-level shift is the coil-change chart's job, not the routine chart's.")
    pg.table("The three-way design decision: false alarms per 100 points by design", alts, {"design": "Design", "v": "False alarms per 100 points"}, {"False alarms per 100 points": F2},
             note="Known parameters, with the residual coil share after centring and the median number of routine subgroups on a coil from the record; the rule history is taken within the coil.")
    lag = vc["lag_1_autocorrelation_within_coil"]; lo, hi = float(lag.quantile(0.1)), float(lag.quantile(0.9)); mp = float(lag.median())
    pg.p(f"<strong>Autocorrelation.</strong> Subgroup means within a coil carry a median lag-1 autocorrelation of {n(mp, 'mart_variance_components.lag_1_autocorrelation_within_coil, median', '{:.2f}', was='-0.07')} (10th to 90th percentile {n(lo, 'lag-1, 10th percentile', '{:.2f}', was='-0.19')} to {n(hi, 'lag-1, 90th percentile', '{:.2f}', was='0.02')}). Negative autocorrelation of that size lengthens the in-control ARL under rules 1 to 4 from "
         f"{n(A.arl_rules(0, (1, 2, 3, 4)), 'arl_rules, rules 1 to 4, independent', was='92')} to {n(A.arl_ar1_rules(mp, (1, 2, 3, 4), per_zone=3), 'arl_ar1_rules at the measured median', was='109')} and leaves rule 1 unchanged, so the limits need no adjustment for it.")
    f7 = pd.DataFrame([{"phi": phi, "rule 1": A.arl_ar1_rules(phi, (1,), per_zone=8), "rules 1 to 4": A.arl_ar1_rules(phi, (1, 2, 3, 4), per_zone=3)} for phi in (-0.3, -0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2, 0.3)])
    pg.figure(FIG.arl_autocorrelation(f7, lo, hi), "Figure 7: In-control ARL against lag-1 autocorrelation", "In-control average run length of a means chart on AR(1) subgroup means, by the Markov chain method, with the measured range of lag-1 autocorrelation shaded.")
    lv = query("select * from marts.mart_limit_verifications where result = 'passed' and chart in ('X-bar and R', 'tool-wear')")
    xr = sr[sr["chart"] == "X-bar and R"]; twr = sr[sr["chart"] == "tool-wear"]
    def rate(g, col):
        return 100 * g[col].sum() / g["subgroups_in_scope"].sum()
    known = {r: 100 * A.flag_rate_rules(A.zone_probs(), (r,)) for r in (1, 2, 3, 4)}
    cc = coil_change_expectation(); ccp = cc["points"]; cobs, cexp = int(ccp["observed_signal"].sum()), float(ccp["expected_rate"].sum())
    clo, chi = stats.chi2.ppf(0.025, 2 * cobs) / 2 / cexp, stats.chi2.ppf(0.975, 2 * (cobs + 1)) / 2 / cexp
    pg.p(f"<strong>Observed against expected.</strong> On charts with no special cause in the interval, the year's signals run at {n(scope.at['X-bar and R', 'ratio'], 'observed over expected, X-bar and R', '{:.2f}', was='1.30')} times expectation on X-bar and R, {n(scope.at['three-way', 'ratio'], 'observed over expected, three-way', '{:.2f}', was='0.83')} on three-way and "
         f"{n(scope.at['tool-wear', 'ratio'], 'observed over expected, tool-wear', '{:.2f}', was='1.79')} on tool-wear, with expectation set at each chart's own baseline size and rules.")
    pg.ul([f"<strong>X-bar and R and tool-wear</strong> run above expectation on rules 3 and 4: {n(rate(xr, 'signals_rule_3'), 'mart_signal_rates.signals_rule_3, X-bar and R, per 100', '{:.2f}', was='1.39')} and {n(rate(xr, 'signals_rule_4'), 'mart_signal_rates.signals_rule_4, X-bar and R, per 100', '{:.2f}', was='2.09')} per 100 against "
           f"{n(known[3], 'flag_rate_rules, rule 3, known', '{:.2f}', was='0.45')} and {n(known[4], 'flag_rate_rules, rule 4, known', '{:.2f}', was='0.78')} at known parameters on X-bar and R, {n(rate(twr, 'signals_rule_3'), 'mart_signal_rates.signals_rule_3, tool-wear, per 100', '{:.2f}', was='1.20')} and "
           f"{n(rate(twr, 'signals_rule_4'), 'mart_signal_rates.signals_rule_4, tool-wear, per 100', '{:.2f}', was='2.37')} on tool-wear. Two things in the record produce this. Limits are held across sharpenings, so small persistent offsets (operator reproducibility on the fixture, a part running on another press) accumulate rule 3 and 4 signals that a recomputed chart would absorb. And a level change at sharpening of up to 1.5 sigma passes verification and then runs under the old limits: "
           f"{n(int((lv['mean_offset_sigma'].abs() >= 1).sum()), 'mart_limit_verifications: X-bar and R and tool-wear passes at 1.0 to 1.5 sigma', was='14')} of {n(len(lv), 'mart_limit_verifications: X-bar and R and tool-wear passes', was='1,131')} passes lie between 1.0 and 1.5 sigma.",
           "<strong>Three-way</strong> runs below expectation because its individuals limits carry the residual coil offset, so rule 1 signals less often than an independent process would.",
           f"<strong>The coil-change chart</strong> raised {n(cobs, 'mart_coil_change_points: rule 1 signals on points with limits', was='18')} rule 1 signals on {n(len(ccp), 'mart_coil_change_points: points with limits', was='2,292')} coils against {n(cexp, 'analytics.chart_performance.coil_change: expected signals, Monte Carlo', '{:.1f}', was='12.1')} expected on the record's lot structure ("
           f"{n(cobs / cexp, 'observed over expected, coil-change chart', '{:.2f}', was='1.49')} times, with a 95% interval of {n(clo, 'Poisson interval, low', '{:.2f}', was='0.88')} to {n(chi, 'Poisson interval, high', '{:.2f}', was='2.35')}). The expectation is above the independent rate because coils arrive in lots of "
           f"{pg.word(int(query('select min(k) n from (select coil_lot, count(*) k from staging.stg_erp__coils group by 1)')['n'].iloc[0]), 'stg_erp__coils: fewest coils in a lot', was='one')} to {pg.word(int(query('select max(k) n from (select coil_lot, count(*) k from staging.stg_erp__coils group by 1)')['n'].iloc[0]), 'stg_erp__coils: most coils in a lot', was='four')} that share "
           f"{pct(cc['lot_share'], 'analytics.chart_performance.coil_change: lot share of coil variance', 0, was='76%')} of the coil variance."])
    st = scope.reset_index()
    pg.table("Observed against expected signals by chart", st, {"chart": "Chart", "subgroups": "Routine subgroups", "signals": "Signals", "observed per 100": "Observed per 100", "expected per 100": "Expected per 100", "ratio": "Observed over expected"},
             {"Routine subgroups": F0, "Signals": F0, "Observed per 100": F2, "Expected per 100": F2, "Observed over expected": F2},
             note="Routine subgroups under limits in force, outside any sharpening interval in which the chart carried an assignable cause; a subgroup counts once with a signal on any of its charts. Expected at each chart's own baseline size under its rules, by the Markov chain method.")
    rr = pd.DataFrame([{"chart": c, "rule": r, "obs": rate(g, f"signals_rule_{r}"), "exp": known[r]} for c, g in (("X-bar and R", xr), ("tool-wear", twr)) for r in (1, 2, 3, 4)])
    pg.table("Signals by rule on long-held limits", rr, {"chart": "Chart", "rule": "Rule", "obs": "Observed per 100", "exp": "Expected per 100, known parameters"}, {"Rule": F0, "Observed per 100": F2, "Expected per 100, known parameters": F2},
             note="A subgroup can carry more than one rule.")
    bp = sr.groupby("press_id").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum")).reset_index()
    bp["observed per 100"] = 100 * bp["signals"] / bp["subgroups"]; bp["expected per 100"] = 100 * bp["es"] / bp["subgroups"]
    bp["low"] = [100 * stats.chi2.ppf(0.025, 2 * k) / 2 / m if k > 0 else 0.0 for k, m in zip(bp["signals"], bp["subgroups"])]
    bp["high"] = [100 * stats.chi2.ppf(0.975, 2 * (k + 1)) / 2 / m for k, m in zip(bp["signals"], bp["subgroups"])]
    pg.figure(FIG.expected_observed_by_press(bp), "Figure 8: Expected against observed false alarms by press", "Observed signals per 100 routine subgroups on charts with no special cause in the year, with a 95% Poisson interval, against the rate expected from the press's charts at their own baseline sizes.")
    bp["d"] = bp["observed per 100"] - bp["expected per 100"]; bp["ratio"] = bp["observed per 100"] / bp["expected per 100"]
    t1_, t2_ = bp.sort_values("d", ascending=False).iloc[0], bp.sort_values("ratio", ascending=False).iloc[0]; bot = bp.sort_values("d").iloc[0]
    others = bp[~bp["press_id"].isin([t1_.press_id, t2_.press_id, bot.press_id])]
    pg.p(f"By press, {txt(t1_.press_id, 'mart_signal_rates: press furthest above expectation, by difference', was='PR-01')} and {txt(t2_.press_id, 'mart_signal_rates: press furthest above expectation, by ratio', was='PR-09')} run furthest above expectation ({n(t1_['observed per 100'], 'observed per 100, PR-01', '{:.2f}', was='3.91')} against {n(t1_['expected per 100'], 'expected per 100, PR-01', '{:.2f}', was='3.18')} per 100, and "
         f"{n(t2_['observed per 100'], 'observed per 100, PR-09', '{:.2f}', was='3.46')} against {n(t2_['expected per 100'], 'expected per 100, PR-09', '{:.2f}', was='2.81')}) and "
         f"{txt(bot.press_id, 'mart_signal_rates: press furthest below expectation', was='PR-10')} furthest below ({n(bot['observed per 100'], 'observed per 100, that press', '{:.2f}', was='2.60')} against {n(bot['expected per 100'], 'expected per 100, that press', '{:.2f}', was='3.26')}); the other eight sit within "
         f"{n(0.7 if others['d'].abs().max() < 0.7 else others['d'].abs().max(), 'bound on the gap between observed and expected per 100, the other eight presses (largest ' + format(others['d'].abs().max(), '.2f') + ')', '{:.1f}', was='0.7')} per 100 of expectation.")
    pg.p("Two changes are recommended for the tool-wear charts, where the excess is largest: the verification criterion tightened to 1.0 sigma, since the level change at sharpening is the larger part of it, and the regression re-fitted at each planned trigger as well as at each passed verification.")

    # ═══════════════ 5. Per-stroke monitoring design
    pg.h2("per-stroke", "5. Per-stroke monitoring design")
    pe = query("select * from marts.mart_parts_exposed order by fault_event_id"); rt = query("select * from marts.mart_per_stroke_run_tonnage order by run_id")
    px = pe.groupby("press_id").agg(chipped=("fault_event_id", "count"), per_stroke_median_parts=("parts_exposed_per_stroke_charts", "median"), per_stroke_median_strokes=("strokes_exposed_per_stroke_charts", "median"),
                                    hourly_up_to=("parts_exposed_hourly_check_up_to", "median"), hourly_average=("parts_exposed_hourly_check_average", "median")).reset_index()
    p3x = px.set_index("press_id").loc["PR-03"]
    lam, Lx, Lc = float(design["ewma_lambda"]), float(design["ewma_L"]), float(design["ewma_L_considered"])
    pg.p(f"The per-stroke charts catch a chipped punch on the stroke, where an hourly check would pass up to {n(p3x.hourly_up_to, 'mart_parts_exposed.parts_exposed_hourly_check_up_to, PR-03, median', was='11,773')} parts on PR-03 before seeing it. The EWMA on the per-stroke tonnage total runs with lambda "
         f"{n(lam, 'mart_chart_design.ewma_lambda', '{:.2f}', was='0.02')} and L {n(Lx, 'mart_chart_design.ewma_L', '{:.1f}', was='5.5')}, from a baseline of {n(design['ewma_baseline_strokes'], 'mart_chart_design.ewma_baseline_strokes', was='500')} production strokes at each run start; a residual chart on each channel's share of the total runs beside it at L "
         f"{n(design['channel_share_L'], 'mart_chart_design.channel_share_L', '{:.1f}', was='5.5')}.")
    phi_r = float(rt["baseline_lag_1_autocorrelation"].median()); cv_r = float((rt["baseline_total_kn_sd"] / rt["baseline_total_kn_mean"]).median())
    neff = float(design["ewma_baseline_strokes"]) * (1 - phi_r) / (1 + phi_r)
    nx, nw = A._normal_nodes(11); sx, sw = A._chi_ratio_nodes(neff - 1, 11)
    est = {Lv: 1 / sum(a * w_ / A.ewma_arl(lam, Lv * s, c / np.sqrt(neff), phi_r) for c, a in zip(nx, nw) for s, w_ in zip(sx, sw)) for Lv in (Lx, Lc)}
    a0, a0c = A.ewma_arl(lam, Lx, 0, phi_r), A.ewma_arl(lam, Lc, 0, phi_r)
    pg.p(f"<strong>The design.</strong> The total is autocorrelated at lag 1 by a median {n(phi_r, 'mart_per_stroke_run_tonnage.baseline_lag_1_autocorrelation, median', '{:.2f}', was='0.60')} and varies by {pct(cv_r, 'mart_per_stroke_run_tonnage: baseline sd over mean, median', 2, was='1.49%')} within a run, so the EWMA limits are set on the AR(1)-adjusted variance. At known parameters the in-control ARL is "
         f"{n(a0 / 1e6, 'ewma_arl, L 5.5, known, millions', '{:.1f}', was='77.8')} million strokes; with the parameters estimated from 500 strokes it is {n(est[Lx] / 1e6, 'ewma_arl averaged over the estimates, L 5.5, millions', '{:.2f}', was='2.64')} million. L is set at 5.5 for the estimated case: at L 4.9 the known-parameter ARL of "
         f"{n(a0c / 1e6, 'ewma_arl, L 4.9, known, millions', '{:.2f}', was='3.68')} million falls to {n(round(est[Lc], -3), 'ewma_arl averaged over the estimates, L 4.9, to the thousand', was='312,000')} strokes once estimation is allowed for, about one false stop in "
         f"{pg.word(round(est[Lc] / (float(query("select sum(strokes) s from intermediate.int_run_shots where press_id = 'PR-03' and cast(production_start as date) between '2026-04-01' and '2026-06-30'")['s'].iloc[0]) / float(query("select count(distinct (cast(sample_time as date), hour(sample_time) * 60 + minute(sample_time) >= 870)) n from intermediate.int_characteristic_history where press_id = 'PR-03' and in_quarter")['n'].iloc[0]))), 'strokes at L 4.9 over PR-03 strokes per worked shift in the quarter', was='eight')} shifts on PR-03.")
    shift_tot = float(pe["total_shift_at_onset"].abs().median()); shift_sh = float(pe["largest_channel_share_shift_points"].median())
    lams = (0.02, 0.05, 0.10); Ls = {l_: (Lx if l_ == lam else A.ewma_limit_for(l_, a0, phi_r)) for l_ in lams}
    pg.p(f"A chipped punch drops the total by a median {pct(shift_tot, 'mart_parts_exposed.total_shift_at_onset, median', 2, was='3.06%')} and moves the largest channel share by {n(shift_sh, 'mart_parts_exposed.largest_channel_share_shift_points, median', '{:.2f}', was='1.32')} points. At that shift the EWMA signals in "
         f"{n(A.ewma_arl(lam, Lx, shift_tot / cv_r, phi_r), 'ewma_arl at the median chipped-punch shift', was='38')} strokes; the channel-share chart signals first on most chips, because the share moves on the stroke of the break. Lambda 0.02 is the choice for shifts of 2% to 3%: at a 2% step it signals in "
         f"{n(A.ewma_arl(0.02, Ls[0.02], 0.02 / cv_r, phi_r), 'ewma_arl, lambda 0.02, 2% step', was='76')} strokes against {n(A.ewma_arl(0.05, Ls[0.05], 0.02 / cv_r, phi_r), 'ewma_arl, lambda 0.05, 2% step', was='117')} at lambda 0.05 and {n(A.ewma_arl(0.10, Ls[0.10], 0.02 / cv_r, phi_r), 'ewma_arl, lambda 0.10, 2% step', was='425')} at lambda 0.10, with the same in-control ARL.")
    f9 = pd.DataFrame([{"shift_value": d, **{f"lambda {l_:.2f}, L {Ls[l_]:.2f}": A.ewma_arl(l_, Ls[l_], d / cv_r, phi_r) for l_ in lams}} for d in (0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05)])
    pg.figure(FIG.ewma_arl1(f9, shift_tot), "Figure 9: EWMA ARL1 against shift size, three lambda values", "Strokes to signal against a step in the per-stroke total, by the Markov chain method on the AR(1)-adjusted variance at the measured autocorrelation and variation; each lambda's L gives the same in-control ARL.")
    stops = query("select * from marts.mart_per_stroke_stops where in_record order by fault_event_id"); fc_ = stops["finding_class"].value_counts()
    srate = query("select sum(strokes) s, sum(stops_nothing_found) nf from marts.mart_per_stroke_stop_rates where period = 'record'").iloc[0]
    nf_chart = stops[stops["finding_class"] == "nothing found"]["chart"].value_counts()
    pgc = pe.groupby("chart")["strokes_exposed_per_stroke_charts"].median(); chc = stops[stops["finding_class"] == "chipped punch"]["chart"].value_counts()
    pg.p(f"<strong>The record.</strong> The charts stopped the presses {n(len(stops), 'mart_per_stroke_stops: stops in the year', was='520')} times in the year: {n(fc_['slug pulling'], 'mart_per_stroke_stops: slug pulling', was='274')} on slug pulling, {n(fc_['worn punch'], 'mart_per_stroke_stops: worn punch', was='82')} on a worn punch, "
         f"{n(fc_['chipped punch'], 'mart_per_stroke_stops: chipped punch', was='71')} on a chipped punch and {n(fc_['nothing found'], 'mart_per_stroke_stops: nothing found', was='93')} with nothing found. The false-stop rate is {n(srate.nf / (srate.s / 1e6), 'mart_per_stroke_stop_rates: nothing found per million strokes', '{:.2f}', was='1.02')} per million strokes, "
         f"{n(nf_chart.get('EWMA on the total', 0), 'mart_per_stroke_stops: nothing found on the EWMA', was='82')} of the {n(fc_['nothing found'], 'mart_per_stroke_stops: nothing found', was='93')} on the EWMA. Strokes were kept for {n(int(stops['strokes_kept'].sum()), 'mart_per_stroke_stops.strokes_kept', was='204')} of the stops. On those, chipped punches were stopped at a median "
         f"{n(pe['strokes_exposed_per_stroke_charts'].median(), 'mart_parts_exposed.strokes_exposed_per_stroke_charts, median', was='0')} strokes from the onset, 90th percentile {n(pe['strokes_exposed_per_stroke_charts'].quantile(0.9), 'mart_parts_exposed.strokes_exposed_per_stroke_charts, 90th percentile', was='20')}; the EWMA caught "
         f"{n(chc.get('EWMA on the total', 0), 'mart_per_stroke_stops: chipped punches stopped by the EWMA', was='8')} chipped punches in the year and the channel-share chart {n(chc.get('channel share', 0), 'mart_per_stroke_stops: chipped punches stopped by the channel-share chart', was='63')}, at medians of "
         f"{n(pgc.get('EWMA on the total'), 'mart_parts_exposed: EWMA, median strokes', was='38')} and {n(pgc.get('channel share'), 'mart_parts_exposed: channel share, median strokes', was='0')} strokes on the {n(int((pe['chart'] == 'EWMA on the total').sum()), 'mart_parts_exposed: EWMA stops with strokes kept', was='4')} and "
         f"{n(int((pe['chart'] == 'channel share').sum()), 'mart_parts_exposed: channel-share stops with strokes kept', was='27')} with strokes kept.")
    t9 = stops.groupby(["finding_class", "chart"]).size().reset_index(name="stops")
    pg.table("Stops by the per-stroke charts, by finding and chart", t9, {"finding_class": "Finding", "chart": "Chart", "stops": "Stops"}, {"Stops": F0}, note="Stops in the year on every press.")
    s13 = stops[stops["run_id"] == "R26-00820"].iloc[0]
    st13 = query("select * from marts.mart_per_stroke_stop_strokes where fault_event_id = ? order by stroke_no", [s13.fault_event_id]); r13 = rt[rt["run_id"] == "R26-00820"].iloc[0]
    z = (st13["total_kn"].values - r13.baseline_total_kn_mean) / r13.baseline_total_kn_sd; e = 0.0; ew = []
    for v in z:
        e = lam * v + (1 - lam) * e; ew.append(e)
    lim = Lx * A.ewma_sd_factor(lam, r13.baseline_lag_1_autocorrelation)
    shares = [c for c in ("share_ch1", "share_ch2", "share_ch3", "share_ch4") if st13[c].notna().any()]
    pg.figure(FIG.stop_13_may(st13, ew, lim, shares), "Figure 10: The 13 May stop on D-1333-C", "The 300 production strokes before the stop of run R26-00820: the EWMA of the per-stroke total in the run's baseline sigmas, started at zero 300 strokes before, against its limits; and each channel's share of the total, less its level over the first 200 of those strokes.")
    pe13 = pe[pe["fault_event_id"] == s13.fault_event_id].iloc[0]
    pg.p(f"On 13 May 2026 the EWMA on PR-03 stopped run R26-00820 at stroke {n(s13.stop_stroke_no, 'mart_per_stroke_stops.stop_stroke_no', was='239,498')}, {n(pe13.strokes_exposed_per_stroke_charts, 'mart_parts_exposed.strokes_exposed_per_stroke_charts, the 13 May stop', was='34')} strokes after the estimated onset, on a punch found chipped and replaced; the press restarted at "
         f"{txt(pd.Timestamp(s13.cleared_at).strftime('%H:%M'), 'mart_per_stroke_stops.cleared_at', was='11:55')}.")
    pg.p(f"<strong>Parts exposed.</strong> Under the per-stroke charts the median chipped punch exposed {pg.word(pe['parts_exposed_per_stroke_charts'].median(), 'mart_parts_exposed.parts_exposed_per_stroke_charts, median', was='no')} parts. Under an hourly check the same failures would have exposed up to "
         f"{n(pe['parts_exposed_hourly_check_up_to'].median(), 'mart_parts_exposed.parts_exposed_hourly_check_up_to, median', was='6,499')} parts at the median press and up to {n(p3x.hourly_up_to, 'mart_parts_exposed.parts_exposed_hourly_check_up_to, PR-03', was='11,773')} on PR-03, with half that on average; the half-hourly check on the high-speed presses halves both.")
    pg.figure(FIG.parts_exposed(px), "Figure 11: Parts exposed per chipped punch, by press", "For each press, the parts made in an hour at its realised stroke rate (the bar, log scale), with the median parts exposed per chipped punch on the per-stroke charts (strokes from the estimated onset to the stop, times parts per stroke) written on it.")

    # ═══════════════ 6. The charts in force
    pg.h2("in-force", "6. The charts in force")
    vb = cif[cif["data_type"] == "variable"]["study_basis"].value_counts()
    pg.p(f"Every variable chart in force at 30 June 2026 has a current calibration and a gauge study on file: {n(vb.get('this gauge', 0), 'mart_charts_in_force.study_basis: this gauge', was='825')} on the gauge itself and {n(vb.get('gauge type at the press', 0), 'mart_charts_in_force.study_basis: gauge type at the press', was='72')} through the study of the gauge type at the press. "
         f"{n(int(cif['in_baseline'].sum()), 'mart_charts_in_force.in_baseline', was='16')} charts are in a baseline and {'none' if int(cif['past_trigger'].sum()) == 0 else n(int(cif['past_trigger'].sum()), 'mart_charts_in_force.past_trigger')} is past its recalculation trigger.")
    g11, g14, g15 = (fam_cif[fam_cif["gauge_id"] == g].iloc[0] for g in ("F-11333", "F-14026", "F-15731"))
    pg.p(f"The family's {n(len(fam_cif), 'mart_charts_in_force: family characteristics with a chart', was='27')} charted characteristics run on {n(int((fam_cif['data_type'] == 'variable').sum()), 'mart_charts_in_force: family variable charts', was='20')} variable charts and {n(int((fam_cif['chart_type'] == 'p').sum()), 'mart_charts_in_force: family p charts', was='7')} p charts. F-11333 stands at "
         f"{n(g11.pct_grr_of_tolerance, 'mart_charts_in_force.pct_grr_of_tolerance, F-11333', '{:.1f}', was='16.3')}% of tolerance on its {txt(DAY(g11.study_date), 'mart_charts_in_force.study_date, F-11333', was='5 May 2026')} study, with a restudy scheduled for {txt(DAY(g11.restudy_due), 'mart_charts_in_force.restudy_due, F-11333', was='17 August 2026')}; F-14026 at "
         f"{n(g14.pct_grr_of_tolerance, 'mart_charts_in_force.pct_grr_of_tolerance, F-14026', '{:.1f}', was='5.3')}% after its rebuild, F-15731 at {n(g15.pct_grr_of_tolerance, 'mart_charts_in_force.pct_grr_of_tolerance, F-15731', '{:.1f}', was='6.0')}%.")
    t6 = fam_cif.copy()
    t6["limits"] = [("" if pd.isna(bb) else f"{bb}, {DAY(ef)} ({tg})") for bb, ef, tg in zip(t6["basis"], t6["limits_effective_from"], t6["limits_trigger"])]
    t6["verified"] = t6["limits_annotation"].fillna("").map(lambda a: a.split("; ")[-1] if a else "")
    t6["coil-change chart"] = [("" if pd.isna(cc_) else f"{cc_:.4f} ({l_:.4f} to {u_:.4f}), {int(k_)} coils") for cc_, l_, u_, k_ in zip(t6["coil_change_centre"], t6["coil_change_lcl"], t6["coil_change_ucl"], t6["coil_change_chart_coils"])]
    t6["grr"] = t6["pct_grr_of_tolerance"].astype(float); t6["restudy"] = t6["restudy_due"].map(DAY); t6["study"] = t6["study_date"].map(DAY); t6["freq"] = t6["frequency_minutes"].astype(float)
    t6["plan"] = t6["reaction_plan_signals"].fillna("")
    pg.table("The family's charts in force at 30 June 2026", t6, {"characteristic_id": "Characteristic", "characteristic_name": "Name", "chart_type": "Chart", "limits": "Limits basis and date", "verified": "Last verification", "gauge_id": "Gauge",
                                                                  "study": "Study", "grr": "%GRR", "restudy": "Restudy due", "freq": "Check, minutes", "plan": "Reaction plan", "coil-change chart": "Coil-change chart"},
             {"%GRR": F1, "Check, minutes": F0}, note="The p charts on attribute checks carry no limit set of this kind. A hand gauge is covered by the latest study of its type at its press.")
    pw = cif.pivot_table(index="press_id", columns="characteristic_class", values="characteristic_id", aggfunc="count", fill_value=0).reset_index()
    cols = {"press_id": "Press", **{c: c.capitalize() for c in pw.columns if c != "press_id"}}
    pg.table("Charts in force by press and class", pw, cols, {v: F0 for k, v in cols.items() if k != "press_id"})

    # ═══════════════ Appendix
    pg.h2("appendix", "Appendix")
    pg.raw(APPENDIX_FORMULAS)
    ap = crit.groupby(["press_id", "characteristic_class"]).agg(n_=("characteristic_id", "count"), w=("share_within", "median"), s=("share_between_subgroups_in_coil", "median"), c=("share_between_coils", "median"), i=("share_between_intervals", "median")).reset_index()
    pg.table("Variance components by press", ap, {"press_id": "Press", "characteristic_class": "Class", "n_": "Characteristics", "w": "Within", "s": "Between subgroups in a coil", "c": "Between coils", "i": "Between intervals"},
             {"Characteristics": F0, "Within": P1, "Between subgroups in a coil": P1, "Between coils": P1, "Between intervals": P1}, note="Critical characteristics and all flatness characteristics with 60 routine subgroups or more; medians.")
    lh = ls[ls["family_part"]].copy(); lh["from"] = lh["effective_from"].map(DAY); lh["to"] = lh["effective_to"].map(DAY)
    for c_ in ("coil_changes_spanned",):
        lh[c_] = lh[c_].astype(float)
    pg.table("The limit history of every family chart", lh, {"characteristic_id": "Characteristic", "limit_set_id": "Limit set", "chart": "Chart", "from": "From", "to": "To", "trigger": "Trigger", "subgroups_used": "Subgroups used", "coil_changes_spanned": "Coil changes",
                                                             "verifications_passed": "Verified", "verifications_failed": "Failed", "routine_subgroups_charted": "Subgroups charted"},
             {"Subgroups used": F0, "Coil changes": F0, "Verified": F0, "Failed": F0, "Subgroups charted": F0})
    tb = cc["table"].rename(columns={"count": "coils"})
    pg.table("The coil-change chart's expectation by coils on record", tb, {"coils": "Coils on record", "points": "Points", "expected_per_100": "Expected per 100 coils", "observed_signals": "Signals", "observed_per_100": "Observed per 100 coils"},
             {"Coils on record": F0, "Points": F0, "Expected per 100 coils": F2, "Signals": F0, "Observed per 100 coils": F2},
             note="20 stands for 20 coils or more, on the previous 20. Expected by Monte Carlo on the record's lot structure (4,000 seeded replicates per point).")

    toc = [("summary", "1. Summary"), ("variance", "2. Variance structure"), ("limits", "3. Limit setting and governance"), ("performance", "4. Chart performance"), ("per-stroke", "5. Per-stroke monitoring design"), ("in-force", "6. The charts in force"), ("appendix", "Appendix")]
    html = S.report_shell("Control Chart Design", "Revalidation on the July 2025 to June 2026 record", "July 2026", "\n".join(pg.body), toc)
    out = S.DOCS / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / "control_chart_design.html").write_text(html, encoding="utf8", newline="\n")
    trace, off = pg.check()
    return html, trace, off, pg.figures


APPENDIX_FORMULAS = """<h3 id="formulas">Formulas</h3>
<ul>
<li><strong>Pooled within-subgroup sigma:</strong> the square root of the mean of the subgroup variances. <strong>Between/within sigma</strong> on three-way charts: the within sigma from the average range (R-bar over d2, d2 = 2.326 for five pieces) combined with the between-subgroup sigma from the average moving range of subgroup means (MR-bar over 1.128, less the within share of a subgroup mean, not below zero).</li>
<li><strong>Three-way chart constants:</strong> individuals limits at the centre line plus and minus three times the standard deviation of the baseline subgroup means; moving-range limit at D4 = 3.267 times the average moving range; range limit at D4 = 2.114 times the average range; X-bar and R limits at the centre line plus and minus A2 = 0.577 times the average range.</li>
<li><strong>ARL by the Markov chain:</strong> the states carry the zone history the rules need (the last four points and the run on one side); the ARL is the first element of (I &minus; Q)<sup>&minus;1</sup>1, where Q holds the transitions among states that raise no signal. Limits estimated from a baseline enter as a centre offset, normal with variance 1/m, and a sigma ratio, scaled chi from the average range (3.8 degrees of freedom a subgroup of five), averaged by quadrature. Autocorrelated means carry the previous mean as a discretised state.</li>
<li><strong>Variance components:</strong> nested by the method of moments on the routine subgroups: within subgroup (pooled), between subgroups within a run and coil, between coils within a sharpening interval, between intervals, each net of the level below it and not below zero.</li>
<li><strong>EWMA on AR(1) data:</strong> the stationary sigma of the EWMA is the square root of lambda/(2 &minus; lambda) times (1 + a)/(1 &minus; a), with a = phi(1 &minus; lambda); the Brook and Evans chain with 301 states gives the ARL. Estimated parameters: the baseline mean with variance 1/n<sub>eff</sub>, n<sub>eff</sub> = n(1 &minus; phi)/(1 + phi), and a scaled chi sigma ratio; the in-control ARL is the reciprocal of the false-signal rate averaged over the estimates.</li>
<li><strong>Coil-change chart limits:</strong> from 6 to 19 coils, the mean of the coils on record plus and minus t(0.99865, n &minus; 1) times the square root of 1 + 1/n times their standard deviation; from 20 coils, three standard deviations of the previous 20.</li>
<li><strong>The coil-change expectation, Monte Carlo:</strong> each charted point is replicated 4,000 times on the lots its coils came from, a lot effect carrying the lot share of the coil variance estimated from the certificate-predicted coil means, plus the coil effect and the measurement of a 10-piece mean; the rate at a point is the share of replicates beyond its limits.</li>
</ul>"""


if __name__ == "__main__":
    html, trace, off, nfig = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "control_chart_design_numbers.csv", index=False, lineterminator="\n")
    print(len(html), "characters;", len(trace), "numbers traced;", nfig, "figures;", len(off), "differ from the text")
    if len(off):
        print(off.to_string())
