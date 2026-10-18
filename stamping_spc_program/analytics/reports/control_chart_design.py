"""Control Chart Design: revalidation on the July 2025 to June 2026 record. Reads the marts, computes the run lengths and
expected rates (analytics.chart_performance), builds the figures and writes docs/reports/control_chart_design.html and
the table of every number in the body with the mart it is read from and the value in the page text."""
import re

import numpy as np
import pandas as pd
from scipy import stats

from analytics.chart_performance import arl as A
from analytics.chart_performance.coil_change import expectation as coil_change_expectation
from analytics.data import query
from analytics.reports import design_figures as FIG
from analytics.reports.page import DAY, F0, F1, F2, F4, P1, Page
from analytics.style import style as S

WEEKS = ((pd.Timestamp("2026-06-30") - pd.Timestamp("2025-07-01")).days + 1) / 7
WARN_TINT = "#FBEBD3"
# The page's characteristic classes, by characteristic type: the attribute checks fall in with what they check (burr
# against the limit sample under sheared edges, hole diameter by pin under hole diameter).
REPORT_CLASS = {"formed height": "formed", "bend angle": "formed", "hole-to-edge": "cut geometry", "hole-to-hole": "cut geometry", "length": "cut geometry",
                "width": "cut geometry", "hole diameter": "hole diameter", "flatness": "flatness", "burr height": "sheared edges"}
CLASS_ORDER = ["formed", "cut geometry", "hole diameter", "flatness", "sheared edges"]
REGRESSION_FIGURE = 24        # the tool-wear (regression) chart on C-15731-02 in page order; the wear-rate figure labels it
CHART_NAME = {"three-way (I-MR-R)": "three-way", "Xbar-R": "X-bar and R", "tool-wear": "regression", "p": "p chart"}
DISPLAY = {"tool-wear": "regression", "tool-wear re-fit": "regression re-fit", "tool-wear regression": "regression line"}     # the marts' names for the regression chart, as the page shows them


def report_class(df):
    out = df.assign(characteristic_class=df["characteristic_type"].map(REPORT_CLASS))
    assert out["characteristic_class"].notna().all(), "a characteristic type without a class"
    return out          # the page's warning tint, for a body-table row outside its design range


def expected_rate(chart, n, cache={}):
    """Expected signals per routine subgroup at a chart's own baseline size under the rules in force on it."""
    key = (chart, int(n))
    if key not in cache:
        cache[key] = (A.expected_rate_xbar_r(int(n)) if chart == "X-bar and R" else A.expected_rate_tool_wear(int(n)) if chart == "tool-wear"
                      else A.expected_rate_three_way(min(int(n), 400)))
    return cache[key]


def build():
    pg = Page(); n, pct, txt, wd = pg.num, pg.pct, pg.text, pg.word

    keys, nxt = [], [0]

    class Body(list):
        def append(self, x):
            super().append(x); keys.append(nxt[0]); nxt[0] += 1

    class Trace(list):
        def append(self, row):
            super().append((row, nxt[0]))          # the block being built is the next one appended
    pg.body, pg.trace = Body(), Trace()
    _table, _body_table = pg.table, pg.body_table
    pg.table = lambda title, df, *a, **k: _table(title, df.replace(DISPLAY), *a, **k)
    pg.body_table = lambda title, df, *a, **k: _body_table(title, df.replace(DISPLAY), *a, **k)

    def mark():
        return None

    def take(m):
        return None

    def put(blk):
        return None
    pg.raw(f"<style>table.data tr.warn td {{ background: {WARN_TINT}; }}</style>")

    # ── read once ────────────────────────────────────────────────────────────
    design = query("select parameter, value from marts.mart_chart_design order by parameter").set_index("parameter")["value"]
    cif = report_class(query("select * from marts.mart_charts_in_force order by characteristic_id"))
    vc = report_class(query("select * from marts.mart_variance_components order by characteristic_id"))
    ls = query("select * from marts.mart_limit_sets order by characteristic_id, effective_from, limit_set_id")
    sr = query("select * from marts.mart_signal_rates where period = 'record' order by characteristic_id, press_id, chart, baseline_subgroups")
    sr["expected_rate"] = [expected_rate(c, b) for c, b in zip(sr["chart"], sr["baseline_subgroups"])]
    sr["es"] = sr["expected_rate"] * sr["subgroups_in_scope"]
    crit = vc[vc["critical"] | (vc["characteristic_class"] == "flatness")]
    med = crit.groupby("characteristic_class")[["share_within", "share_between_subgroups_in_coil", "share_between_coils", "share_between_intervals", "incoming_coil_share", "trend_share", "trend_within_share"]].median()
    ch = query("select * from marts.mart_chart_changes order by changed_on").set_index("characteristic_id")
    load = sr.groupby("press_id").agg(routine_subgroups=("routine_subgroups", "sum")).reset_index()
    load["expected_signals"] = sr.assign(e=sr["expected_rate"] * sr["routine_subgroups"]).groupby("press_id")["e"].sum().values
    load["per_week"] = load["routine_subgroups"] / WEEKS; load["alarms_per_week"] = load["expected_signals"] / WEEKS
    scope = sr.groupby("chart").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum"))
    scope["observed per 100"] = 100 * scope["signals"] / scope["subgroups"]; scope["expected per 100"] = 100 * scope["es"] / scope["subgroups"]; scope["ratio"] = scope["signals"] / scope["es"]
    fam = vc[vc["family_part"]].merge(cif[["characteristic_id", "gauge_type"]], on="characteristic_id", how="left")
    fam_cif = cif[cif["family_part"]]
    rw = query("select * from marts.mart_limit_sets where issued_in_record and trigger = 'annual review' and chart = 'three-way'")
    rw["below_coil_change_minimum"] = rw["below_coil_change_minimum"].fillna(False).astype(bool)
    tot_w = load["alarms_per_week"].sum(); sub_w = load["per_week"].sum(); p3 = load.set_index("press_id").loc["PR-03"]
    n_none = int(query("select count(*) n from staging.stg_spc__characteristics where chart_type = 'none'")["n"].iloc[0])

    # ═══════════════ 1. Summary
    pg.h2("summary", "1. Summary")
    ctn = cif["chart_type"].value_counts()
    pg.p(f"At 30 June 2026 there are {n(len(cif), 'mart_charts_in_force: charts', was='1,380')} active SPC charts on {n(cif['press_id'].nunique(), 'mart_charts_in_force: presses', was='11')} presses. The charts correspond to the "
         f"{wd(cif['characteristic_class'].nunique(), 'mart_charts_in_force: characteristic classes, by characteristic type', was='five')} characteristic classes: formed heights and bend angles, cut geometry (hole position and part length and width), hole diameter, flatness, and sheared edges. "
         f"By chart type: {n(int(((cif['chart_type'] == 'three-way (I-MR-R)') & (cif['characteristic_class'] == 'formed')).sum()), 'mart_charts_in_force: three-way, formed', was='399')} three-way charts, {n(int(ctn.get('tool-wear', 0)), 'mart_charts_in_force: tool-wear (regression) charts', was='23')} regression charts, "
         f"{n(int(ctn.get('Xbar-R', 0)), 'mart_charts_in_force: X-bar and R', was='474')} X-bar and R charts, {n(int(ctn.get('p', 0)), 'mart_charts_in_force: p', was='483')} p charts and "
         f"{wd(int(((cif['chart_type'] == 'three-way (I-MR-R)') & (cif['characteristic_class'] == 'cut geometry')).sum()), 'mart_charts_in_force: three-way, hole position', was='one')} three-way chart on a hole position. "
         "Section 2 covers the plant; Section 3 follows the C110 family on PR-03 through the same headings.")
    f1 = []
    for c in CLASS_ORDER:
        g = cif[cif["characteristic_class"] == c]
        f1.append({"characteristic_class": c, "measured": int((g["data_type"] == "variable").sum()), "attribute": int((g["data_type"] == "attribute").sum()),
                   "chart_label": ", ".join(CHART_NAME[t] for t in g["chart_type"].value_counts().sort_index().sort_values(ascending=False, kind="stable").index)})
    f1 = pd.DataFrame(f1)
    for r in f1.itertuples():
        pg.figval(1, f"{r.measured + r.attribute:,}", f"mart_charts_in_force: charts, {r.characteristic_class}")
        pg.figval(1, f"{r.measured:,}", f"mart_charts_in_force: measured charts, {r.characteristic_class}")
        pg.figval(1, f"{r.attribute:,}", f"mart_charts_in_force: attribute charts, {r.characteristic_class}")
    pg.figure(FIG.charts_by_class(f1), "Figure 1: Active SPC charts by characteristic class",
              f"{len(cif):,} charts on {cif['press_id'].nunique()} presses, measured and attribute by class; {n_none} burr characteristics on the sharpening count carry no chart. The one three-way chart on a hole position (C-34479-05) is counted with cut geometry.")
    sig = query("select * from marts.mart_signals where in_record order by alarm_id")
    rt_ = sig[(sig["subgroup_type"] == "routine") & (sig["chart"] != "coil-change means")]
    ac = rt_[rt_["assignable_cause"]]; lvl = ac[ac["cause_code"].isin(["level after sharpening", "level after the rebuild"])]
    vfail = query("select characteristic_id, limit_set_id from marts.mart_limit_verifications where result = 'failed'")
    lvl_failed = lvl.merge(vfail.drop_duplicates(), on=["characteristic_id", "limit_set_id"], how="inner")
    assert len(lvl_failed) == len(lvl), "a level-change alarm on a limit set whose verification passed"
    fx = ac[ac["cause_code"] == "fixture drift"]; oth = ac[ac["cause_code"].isin(["strip misfeed", "slug pulling", "gauge zero", "lubricant"])]
    wc = sig[(sig["cause_code"] == "sharpening logged at the wrong count")]; ccs = sig[sig["chart"] == "coil-change means"]; soft = ccs[ccs["assignable_cause"]]
    st_all = query("select * from marts.mart_per_stroke_stops where in_record order by fault_event_id"); fcs = st_all["finding_class"].value_counts()
    sr_st = query("select sum(strokes) s, sum(stops_nothing_found) nf from marts.mart_per_stroke_stop_rates where period = 'record'").iloc[0]
    pe_all = query("select * from marts.mart_parts_exposed order by fault_event_id")
    gauge_of = cif.set_index("characteristic_id")["gauge_id"]
    CH = {"Xbar-R": "X-bar and R", "three-way (I-MR-R)": "three-way", "tool-wear": "regression"}

    def charts_of(df):
        have = set(df["chart_type"])
        return ", ".join(CH[t] for t in ("Xbar-R", "three-way (I-MR-R)", "tool-wear") if t in have)
    n_slug, n_worn, n_chip = int(fcs["slug pulling"]), int(fcs["worn punch"]), int(fcs["chipped punch"])
    pg.p(f"<strong>How the charts performed.</strong> A chart has two jobs: signal when the process has changed, and stay quiet when it has not. On the first, every change the record holds was caught by the chart designed for it. A signal is closed either as no cause found, which is a false alarm, or with the cause that was found, which SPC calls a special cause. "
         f"{n(len(ac), 'mart_signals: routine alarms with an assignable cause', was='1,657')} routine alarms on {n(ac['run_id'].nunique(), 'mart_signals: runs with a routine assignable-cause alarm', was='58')} runs closed with a special cause, "
         f"{n(len(lvl), 'mart_signals: level after sharpening or rebuild, on a limit set whose verification failed', was='1,620')} of them on {n(lvl['run_id'].nunique(), 'mart_signals: runs with a level-change alarm', was='53')} runs where a die came back from sharpening or rebuild at a new level and its verification failed; "
         f"the coil-change chart caught the {wd(len(soft), 'mart_signals: coil-change chart, assignable cause', was='one')} soft coil; the regression chart on {txt(wc['press_id'].iloc[0], 'mart_signals.press_id, sharpening logged at the wrong count', was='PR-06')} caught a sharpening logged at the wrong count; "
         f"and the per-stroke charts stopped the presses on {n(n_slug, 'mart_per_stroke_stops: slug pulling', was='274')} slug pulls, {n(n_worn, 'mart_per_stroke_stops: worn punch', was='82')} worn punches and {n(n_chip, 'mart_per_stroke_stops: chipped punch', was='71')} chipped punches, the chipped punches at a median "
         f"{n(pe_all['strokes_exposed_per_stroke_charts'].median(), 'mart_parts_exposed.strokes_exposed_per_stroke_charts, median', was='0')} strokes after the onset. All were closed by {txt('30 June' if sig['closed_at'].max() < pd.Timestamp('2026-07-01') and sig['closed_at'].notna().all() else 'later', 'mart_signals.closed_at, latest', was='30 June')}.")
    pg.p("<strong>Takeaway: every special cause in the record was caught by the chart designed for it, and every alarm was closed by 30 June 2026.</strong>")
    t1 = pd.DataFrame([
        {"what": "Die at a new level after sharpening or rebuild", "chart": txt(charts_of(lvl) + ", with verification", 'mart_signals.chart_type, level-change alarms', was='X-bar and R, three-way, regression, with verification'),
         "events": n(lvl["run_id"].nunique(), 'mart_signals: runs, level change', was='53') + " runs", "alarms": n(len(lvl), 'mart_signals: alarms, level change', was='1,620')},
        {"what": f"Fixture drift ({txt(', '.join(sorted(set(gauge_of.reindex(fx['characteristic_id'])))), 'mart_charts_in_force.gauge_id, fixture drift alarms', was='F-14026')})", "chart": txt(charts_of(fx), 'mart_signals.chart_type, fixture drift', was='X-bar and R, three-way'),
         "events": n(fx["run_id"].nunique(), 'mart_signals: runs, fixture drift', was='1') + " run", "alarms": n(len(fx), 'mart_signals: alarms, fixture drift', was='30')},
        {"what": "Strip misfeed, slug pulling, gauge zero, lubricant", "chart": txt(charts_of(oth), 'mart_signals.chart_type, other causes', was='X-bar and R, three-way'),
         "events": n(oth["run_id"].nunique(), 'mart_signals: runs, strip misfeed, slug pulling, gauge zero, lubricant', was='6') + " runs", "alarms": n(len(oth), 'mart_signals: alarms, other causes', was='7')},
        {"what": f"Sharpening logged at the wrong count ({wc['press_id'].iloc[0]})", "chart": txt(charts_of(wc), 'mart_signals.chart_type, sharpening logged at the wrong count', was='regression'),
         "events": n(wc["run_id"].nunique(), 'mart_signals: runs, wrong count', was='1'), "alarms": n(len(wc), 'mart_signals: alarms, wrong count', was='1')},
        {"what": f"Soft coil ({txt(soft['characteristic_id'].iloc[0], 'mart_signals.characteristic_id, soft coil', was='C-15731-07')})", "chart": "coil-change",
         "events": n(len(soft), 'mart_signals: coils, soft coil', was='1'), "alarms": n(len(soft), 'mart_signals: alarms, soft coil', was='1')},
        {"what": "Slug pulling, worn and chipped punches", "chart": "per-stroke EWMA and channel share",
         "events": n(n_slug + n_worn + n_chip, 'mart_per_stroke_stops: stops on slug pulling, worn and chipped punches', was='427') + " stops", "alarms": n(n_slug + n_worn + n_chip, 'mart_per_stroke_stops: stops, as alarms', was='427')}])
    ncf = int((~rt_["assignable_cause"]).sum()); cc_ncf = int((~ccs["assignable_cause"]).sum())
    pg.body_table("Table 1: Special causes caught in the year, by the chart that caught them", t1, {"what": "What was caught", "chart": "Chart", "events": "Events", "alarms": "Alarms"}, bold_cols=("Events",),
                  caption=f"Routine, coil-change and per-stroke charts, 1 July 2025 to 30 June 2026; events are distinct runs, stops or coils. {n(ncf, 'mart_signals: routine alarms closed as no cause found', was='10,499')} routine alarms and "
                          f"{n(cc_ncf, 'mart_signals: coil-change signals closed as no cause found', was='27')} coil-change signals were closed as no cause found.")
    cc_x = coil_change_expectation(); ccp_x = cc_x["points"]; cobs_x, cexp_x = int(ccp_x["observed_signal"].sum()), float(ccp_x["expected_rate"].sum())
    clo_x, chi_x = stats.chi2.ppf(0.025, 2 * cobs_x) / 2 / cexp_x, stats.chi2.ppf(0.975, 2 * (cobs_x + 1)) / 2 / cexp_x
    cls_of = cif.set_index("characteristic_id")["characteristic_class"]
    sc = sr.assign(cls=sr["characteristic_id"].map(cls_of))
    assert sc["cls"].notna().all(), "a signal-rate row without a class"
    byc = sc.groupby("cls").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum"))
    byc["observed per 100"] = 100 * byc["signals"] / byc["subgroups"]; byc["expected per 100"] = 100 * byc["es"] / byc["subgroups"]; byc["ratio"] = byc["signals"] / byc["es"]
    pq = query("""select c.characteristic_type, count(*) subgroups, sum(s.attribute_count) nonconforming, sum(s.pieces) checked,
                         count(*) filter (where s.limit_set_id is not null or s.ucl_mean is not null) with_limits,
                         count(*) filter (where coalesce(trim(s.alarm_flags), '') <> '') with_flags
                  from staging.stg_spc__subgroups s join marts.mart_charts_in_force c on c.characteristic_id = s.characteristic_id
                  where c.chart_type = 'p' and s.sample_time >= '2025-07-01' and s.sample_time < '2026-07-01' group by 1""").set_index("characteristic_type")
    p_alarms = int(query("""select count(*) n from staging.stg_spc__alarms a join staging.stg_spc__subgroups s using (subgroup_id)
                            join marts.mart_charts_in_force c on c.characteristic_id = s.characteristic_id where c.chart_type = 'p'""")["n"].iloc[0])
    assert int(pq["with_limits"].sum()) == 0 and int(pq["with_flags"].sum()) == 0 and p_alarms == 0, "p-chart limits or alarms in the export"
    bu, pi = pq.loc["burr height"], pq.loc["hole diameter"]
    flat = byc.loc["flatness"]
    f_lo, f_hi = stats.chi2.ppf(0.025, 2 * flat.signals) / 2 / flat.es, stats.chi2.ppf(0.975, 2 * (flat.signals + 1)) / 2 / flat.es
    pg.p(f"On the second job, the charts signalled at close to their design rate. On charts with no special cause in the interval, signals ran at {n(byc.at['cut geometry', 'ratio'], 'observed over expected, cut geometry (X-bar and R)', '{:.2f}')} times expectation on cut geometry, "
         f"{n(byc.at['flatness', 'ratio'], 'observed over expected, flatness (X-bar and R)', '{:.2f}')} on flatness, {n(byc.at['formed', 'ratio'], 'observed over expected, formed (three-way)', '{:.2f}', was='0.83')} on formed heights and bend angles and "
         f"{n(byc.at['hole diameter', 'ratio'], 'observed over expected, hole diameter (regression)', '{:.2f}', was='1.79')} on hole diameter, with expectation set at each chart's own rules and baseline size. "
         f"Flatness, at {n(flat.ratio, 'observed over expected, flatness', '{:.2f}', was='0.88')} on {n(flat.subgroups, 'mart_signal_rates.subgroups_in_scope, flatness', was='5,738')} subgroups, sits just under its band and inside its chance interval of "
         f"{n(f_lo, 'Poisson interval on flatness signals over expectation, low', '{:.2f}')} to {n(f_hi, 'Poisson interval on flatness signals over expectation, high', '{:.2f}')}. The two departures beyond chance have reasons the record shows: the regression charts on hole diameters signal on small level changes at sharpening that pass verification, "
         f"and the three-way charts on formed characteristics carry the residual coil offset in their limits by design (Sections 3 and 4). The "
         f"{n(int((cif['chart_type'] == 'p').sum()), 'mart_charts_in_force: p charts', was='483')} p charts are outside the comparison: the SPC export carries their counts but no limits or alarm flags, so their signals cannot be assessed on this record. "
         f"The burr checks recorded {n(bu.nonconforming, 'stg_spc__subgroups.attribute_count, burr checks, in the year', was='268')} nonconforming pieces in {n(bu.checked, 'stg_spc__subgroups.pieces, burr checks, in the year', was='219,535')} checked "
         f"({pct(bu.nonconforming / bu.checked, 'burr checks: nonconforming share', 2, was='0.12%')}) and the pin checks {n(pi.nonconforming, 'stg_spc__subgroups.attribute_count, pin checks, in the year')} nonconforming in "
         f"{n(pi.checked, 'stg_spc__subgroups.pieces, pin checks, in the year')} checked.")
    f2 = byc.loc[["formed", "cut geometry", "hole diameter", "flatness"], ["observed per 100", "expected per 100", "ratio"]].reset_index()
    for r in f2.itertuples():
        pg.figval(2, f"{r[2]:.2f}", f"observed per 100, {r.cls}"); pg.figval(2, f"{r[3]:.2f}", f"expected per 100, {r.cls}"); pg.figval(2, f"{r.ratio:.2f}", f"observed over expected, {r.cls}")
    pg.figure(FIG.signals_by_class(f2, {"formed": (0.9, 1.4), "cut geometry": (0.9, 1.4), "hole diameter": (0.9, 1.5), "flatness": (0.9, 1.4)}),
              "Figure 2: Signals against expectation by characteristic class",
              "Charts with no special cause in the interval; expectation at each chart's own baseline size and rules; flatness's interval spans its band. The coil-change chart's comparison is in 2.3.")
    pg.p(f"<strong>False alarms.</strong> The price of the charts as designed is {n(tot_w, 'false alarms per week as designed, plant', was='133')} false alarms a week across the plant, {n(100 * tot_w / sub_w, 'false alarms per 100 routine subgroups, plant', '{:.1f}', was='3.1')} per 100 routine subgroups on "
         f"{n(sub_w, 'routine subgroups per week, plant', was='4,236')} subgroups a week, and in the year {n(ncf, 'mart_signals: routine alarms closed as no cause found', was='10,499')} routine alarms closed as no cause found. "
         f"The load falls where the subgroups are: PR-03 carries {n(p3.alarms_per_week, 'expected false alarms per week, PR-03', '{:.1f}', was='23.7')} a week on {n(p3.per_week, 'routine subgroups per week, PR-03', was='750')} subgroups, against a plant median of "
         f"{n(float(load['alarms_per_week'].median()), 'expected false alarms per week, median press', '{:.1f}', was='12.9')}.")
    for r in load.itertuples():
        pg.figval(3, f"{r.alarms_per_week:.1f}", f"expected false alarms per week, {r.press_id}")
    pg.figure(FIG.false_alarm_load(load, float(load["alarms_per_week"].median()), "PR-03", pg.figval(3, f"{p3.per_week:,.0f} subgroups a week", "routine subgroups per week, PR-03")),
              "Figure 3: False-alarm load as designed, per press per week",
              f"Expected false alarms a week at each chart's own baseline size under the rules in force, by press; plant total {tot_w:,.0f} on {sub_w:,.0f} routine subgroups a week, {100 * tot_w / sub_w:.1f} per 100; the dashed line is the plant median.")
    pg.p("<strong>Two actions.</strong>")
    pg.ul([f"{n(int(rw['below_coil_change_minimum'].sum()), 'mart_limit_sets: three-way annual-review sets below the coil-change minimum', was='23')} of the {n(len(rw), 'mart_limit_sets: three-way sets at the annual review', was='45')} three-way limit sets issued at the annual review span fewer than ten coil changes; they are re-issued as ten coil changes accrue (Section 3).",
           "The regression charts' verification criterion is tightened to 1.0 sigma, since the level change at sharpening is the larger part of their excess, and the line is re-fitted at each planned trigger as well as at each passed verification (2.3)."])

    # ═══════════════ 2. The charts in force and how they are run
    pg.h2("in-force", "2. The charts in force and how they are run")
    var = cif[cif["data_type"] == "variable"]; vb = var["study_basis"].value_counts()
    pg.p(f"Each class runs on the chart its variation calls for, and every variable chart runs on a gauge in gating status. Formed heights and bend angles run on three-way charts with a coil-change chart beside them; hole diameters on regression charts (tool-wear charts, with the centre line fitted on shots since sharpening); cut geometry and flatness on X-bar and R; sheared edges and the pin checks on hole diameters on p charts. "
         f"All {n(len(var), 'mart_charts_in_force: variable charts', was='897')} variable charts have a current calibration and a gauge study on file, {n(vb.get('this gauge', 0), 'mart_charts_in_force.study_basis: this gauge', was='825')} on the gauge itself and {n(vb.get('gauge type at the press', 0), 'mart_charts_in_force.study_basis: gauge type at the press', was='72')} through the study of the gauge type at the press. "
         f"{n(int(cif['in_baseline'].sum()), 'mart_charts_in_force.in_baseline', was='16')} charts are in a baseline and {'none' if int(cif['past_trigger'].sum()) == 0 else n(int(cif['past_trigger'].sum()), 'mart_charts_in_force.past_trigger')} is past its recalculation trigger.")
    order = CLASS_ORDER
    pw = cif.pivot_table(index="press_id", columns="characteristic_class", values="characteristic_id", aggfunc="count", fill_value=0).reset_index()
    for c in order:
        if c not in pw:
            pw[c] = 0
    for _, r in pw.iterrows():
        pg.figval(4, f"{int(sum(r[c] for c in order))}", f"mart_charts_in_force: charts, {r['press_id']}")
    pg.figure(FIG.charts_by_press_and_class(pw, order), "Figure 4: Active SPC charts by press and class", "Active charts at 30 June 2026 on each press, by characteristic class, with the press total at the end of each bar.")
    pg.p(f"Limits are set once from a baseline and held across sharpenings under verification, so a chart's limits change only when the process has. A baseline is {n(design['baseline_subgroups'], 'mart_chart_design.baseline_subgroups', was='25')} subgroups; a three-way baseline spans at least ten coil changes. A sharpening does not reset the limits: the first "
         f"{n(design['verification_subgroups'], 'mart_chart_design.verification_subgroups', was='25')} routine subgroups after it verify them, and a failed verification starts a new baseline. Formed charts are verified after a rebuild or a forming-station repair only, since a sharpening does not touch the forming stations. Regression lines are re-fitted at each verification that passes, with the limits' sigma held.")
    rc = query("select trigger, cast(sum(limit_sets) as integer) n from marts.mart_limit_recalculations group by 1").set_index("trigger")["n"]
    pb = query("select * from marts.mart_phase1_baselines order by effective_from, limit_set_id")
    pg.p(f"The record holds {n(len(ls), 'mart_limit_sets: limit sets', was='1,216')} limit sets on {n(ls['characteristic_id'].nunique(), 'mart_limit_sets: charts', was='897')} variable charts, and {n(int(rc.sum()), 'mart_limit_recalculations: limit sets in the year', was='319')} new sets were issued in the year: "
         f"{n(rc['rebuild'], 'mart_limit_recalculations: rebuild', was='146')} after rebuilds, {n(rc['annual review'], 'mart_limit_recalculations: annual review', was='74')} at the annual review on 19 January 2026, {n(rc['tool-wear re-fit'], 'mart_limit_recalculations: tool-wear re-fit', was='65')} regression lines re-fitted, and "
         f"{n(rc['failed verification'], 'mart_limit_recalculations: failed verification', was='34')} after a failed verification. {n(len(pb), 'mart_phase1_baselines: baselines', was='244')} Phase I baselines were completed, {n(int((pb['chart'] == 'X-bar and R').sum()), 'mart_phase1_baselines: X-bar and R', was='199')} X-bar and R and "
         f"{n(int((pb['chart'] == 'three-way').sum()), 'mart_phase1_baselines: three-way', was='45')} three-way; subgroups beyond the baseline's own limits are screened ({n(int(pb['screened_subgroups'].sum()), 'mart_phase1_baselines.screened_subgroups, total', was='94')} subgroups in "
         f"{n(int((pb['screened_subgroups'] > 0).sum()), 'mart_phase1_baselines: baselines with a subgroup screened', was='64')} baselines), and Anderson-Darling on the baseline means passes at 5% on {pct(pb['normal_at_5pct'].mean(), 'mart_phase1_baselines.normal_at_5pct, share', was='92.9%')} of them.")
    tw, mv = ch.loc["C-15731-02"], ch.loc["C-34479-05"]
    pg.p("Two charts changed in the year, both from the record.")
    pg.ul([f"<strong>C-15731-02 ({tw.die_id}, {tw.press_id}):</strong> the regression chart's recalculation trigger shortened from {n(tw.from_value, 'mart_chart_changes.from_value', was='30')} to {n(tw.to_value, 'mart_chart_changes.to_value', was='20')} subgroups, first applied "
           f"{txt(DAY(tw.changed_on), 'mart_chart_changes.changed_on', was='8 December 2025')}, after the die's intervals shortened under the burr line and the regression lagged them.",
           f"<strong>C-34479-05 ({mv.die_id}, {txt(mv.press_id, 'mart_chart_changes.press_id', was='PR-10')}):</strong> moved from X-bar and R to a three-way chart on {txt(DAY(mv.changed_on), 'mart_chart_changes.changed_on', was='9 March 2026')}, after "
           f"{pct(mv.evidence_value, 'mart_chart_changes.evidence_value', was='35.2%')} of its variance was found between coils."])
    by_month = query("select issued_month, trigger, cast(sum(limit_sets) as integer) n from marts.mart_limit_recalculations group by all").pivot(index="issued_month", columns="trigger", values="n").fillna(0).astype(int).reset_index()
    pg.figure(FIG.recalculations(by_month.rename(columns=DISPLAY)), "Figure 5: New limit sets by month and trigger", "New limit sets issued each month, July 2025 to June 2026, by the trigger that issued them; each trigger's year total is in the legend.")
    same_day = query("select count(*) n, count(*) filter (where cast(actual_start as date) = sharpening_date) d from intermediate.int_run_shots where shots_since_sharpening_at_start is not null").iloc[0]
    span = int(query("select count(*) n from intermediate.int_run_shots r where shots_since_sharpening_at_start is not null and exists (select 1 from intermediate.int_sharpening_intervals i where i.die_id = r.die_id and i.interval_start between cast(r.actual_start as date) and cast(r.actual_end as date))")["n"].iloc[0])
    pg.p(f"The die log carries dates without times, so a run is placed in the interval of the last sharpening dated on or before its start day. {n(same_day.d, 'int_run_shots: runs starting on the day their sharpening is logged', was='15')} of {n(same_day.n, 'int_run_shots: runs with a shot count', was='1,399')} runs start on the day their die's sharpening is logged, and "
         f"{n(span, 'int_run_shots with int_sharpening_intervals: runs spanning a logged sharpening date', was='92')} span a logged sharpening date, where the log date and the run times disagree; both enter the regression charts' shot counts and the wear rates in Section 4.")
    g11, g14, g15 = (fam_cif[fam_cif["gauge_id"] == g].iloc[0] for g in ("F-11333", "F-14026", "F-15731"))
    m_grr = mark()
    f5 = pd.DataFrame([{"gauge_id": "F-11333", "pct": float(g11.pct_grr_of_tolerance), "label": pg.figval(6, f"restudy {DAY(g11.restudy_due)}", "mart_charts_in_force.restudy_due, F-11333")},
                       {"gauge_id": "F-15731", "pct": float(g15.pct_grr_of_tolerance), "label": ""},
                       {"gauge_id": "F-14026", "pct": float(g14.pct_grr_of_tolerance), "label": pg.figval(6, f"after rebuild, {DAY(g14.study_date)}", "mart_charts_in_force.study_date, F-14026")}])
    pg.figure(FIG.fixture_grr(f5), "Figure 6: Gauge R&amp;R of the family's fixtures against the 10% and 30% lines",
              "%GRR of tolerance on the latest study; under 10% in service without restudy, 10% to 30% with a restudy scheduled.")
    mv_grr = take(m_grr)

    # ═══════════════ 3. How the charts performed
    pg.h2("performance", "3. How the charts performed")
    a_r1_0, a_r14_0, a_r1_1, a_r14_1 = A.arl_rules(0, (1,)), A.arl_rules(0, (1, 2, 3, 4)), A.arl_rules(1, (1,)), A.arl_rules(1, (1, 2, 3, 4))
    pg.p(f"The rules in force were chosen for the false-alarm load they carry as much as for the shifts they catch, and the year's signals ran close to that design on two chart types and above it on one. Under rule 1 alone an X-bar chart signals once in {n(a_r1_0, 'analytics.chart_performance.arl_rules, rule 1, known', was='370')} in-control subgroups; with Western Electric rules 1 to 4 it signals once in "
         f"{n(a_r14_0, 'arl_rules, rules 1 to 4, known', was='92')}, and catches a one-sigma shift in {n(a_r14_1, 'arl_rules, rules 1 to 4 at 1 sigma', was='9')} subgroups instead of {n(a_r1_1, 'arl_rules, rule 1 at 1 sigma', was='44')}. Limits estimated from 25 subgroups move both figures: rule 1 to once in "
         f"{n(A.expected_arl_xbar(25, 0, (1,)), 'expected_arl_xbar, rule 1, baseline 25', was='407')}, rules 1 to 4 to once in {n(A.expected_arl_xbar(25, 0, (1, 2, 3, 4)), 'expected_arl_xbar, rules 1 to 4, baseline 25', was='74')}.")
    pg.p(f"<strong>Takeaway: rules 1 to 4 catch a one-sigma shift {wd(a_r1_1 / a_r14_1, 'arl_rules: rule 1 over rules 1 to 4 at 1 sigma, rounded', was='five')} times faster than rule 1 alone, at {wd(a_r1_0 / a_r14_0, 'arl_rules: rule 1 over rules 1 to 4 in control, rounded', was='four')} times the false alarms.</strong>")
    rows = [{"shift": sh, "a": A.arl_rules(sh, (1,)), "b": A.arl_rules(sh, (1, 2, 3, 4)), "c": A.expected_arl_xbar(25, sh, (1,)), "d": A.expected_arl_xbar(25, sh, (1, 2, 3, 4)),
             "e": A.three_way_arl(sh, with_moving_range=False, with_range=False), "f": A.three_way_arl(sh), "g": A.expected_arl_three_way(25, sh)} for sh in (0.0, 1.0, 1.5, 2.0)]
    cols = {"shift": "Shift (sigma)", "a": "X-bar, rule 1", "b": "X-bar, rules 1 to 4", "c": "X-bar, rule 1, baseline 25", "d": "X-bar, rules 1 to 4, baseline 25", "e": "Three-way individuals, rule 1", "f": "Three-way, all three charts", "g": "Three-way, all three charts, baseline 25"}
    pg.body_table("Table 2: ARL by chart as designed", pd.DataFrame(rows), cols, {"Shift (sigma)": F1, **{v: F0 for v in list(cols.values())[1:]}},
                  bold_cells={(0, "X-bar, rule 1"), (1, "X-bar, rule 1"), (0, "X-bar, rules 1 to 4"), (1, "X-bar, rules 1 to 4")},
                  caption="Average run length in subgroups; known parameters and limits estimated from 25 subgroups.")
    f6 = pd.DataFrame([{"shift": sh, "X-bar rule 1": A.arl_rules(sh, (1,)), "X-bar rules 1 to 4": A.arl_rules(sh, (1, 2, 3, 4)), "three-way individuals rule 1": A.three_way_arl(sh, with_moving_range=False, with_range=False), "three-way all three charts": A.three_way_arl(sh)} for sh in np.arange(0, 2.01, 0.25)])
    pg.figure(FIG.arl_curves(f6), "Figure 7: ARL curves by chart type", "Average run length against a shift in the mean, known parameters, log scale. The three-way chart's curve with all three charts includes the moving-range and range charts.")
    vf = query("select * from marts.mart_limit_verifications")
    vt = vf.groupby(["chart", "die_event"]).agg(verifications=("verification_id", "count"), failed=("result", lambda s: int((s == "failed").sum()))).reset_index(); vt["rate"] = vt["failed"] / vt["verifications"]; vtx = vt.set_index(["chart", "die_event"])
    shp = vf[(vf["die_event"] == "sharpening") & vf["chart"].isin(["X-bar and R", "tool-wear"])].groupby(["die_id", "event_date"])["result"].apply(lambda s: (s == "failed").any())
    x1, x2, x3 = vtx.loc[("X-bar and R", "sharpening")], vtx.loc[("tool-wear", "sharpening")], vtx.loc[("three-way", "rebuild")]
    ok = vf[vf["result"] == "passed"]
    cx, cw = A._normal_nodes(9); qx, qw = A._chi_ratio_nodes(3.8 * 25, 9)
    ff_rate = sum(a * w_ * (stats.norm.sf((1.5 * r - c / 5) * 5) + stats.norm.cdf((-1.5 * r - c / 5) * 5)) for c, a in zip(cx, cw) for r, w_ in zip(qx, qw))
    pg.p(f"<strong>Verification.</strong> {n(len(vf), 'mart_limit_verifications: verifications', was='1,308')} verifications were completed in the year: {n(x1.verifications, 'mart_limit_verifications: X-bar and R after sharpening', was='1,100')} after sharpenings on X-bar and R charts, of which {n(x1.failed, 'mart_limit_verifications: X-bar and R failed', was='34')} failed ({pct(x1.rate, 'X-bar and R failure rate', was='3.1%')}); "
         f"{n(x2.verifications, 'mart_limit_verifications: tool-wear', was='67')} on regression charts, {n(x2.failed, 'mart_limit_verifications: tool-wear failed', was='2')} failed ({pct(x2.rate, 'tool-wear failure rate', was='3.0%')}); and {n(x3.verifications, 'mart_limit_verifications: three-way after a rebuild', was='141')} after rebuilds on three-way charts, "
         f"{n(x3.failed, 'mart_limit_verifications: three-way failed', was='3')} failed ({pct(x3.rate, 'three-way failure rate', was='2.1%')}). By sharpening, {n(int(shp.sum()), 'mart_limit_verifications: sharpenings with a failure on an X-bar and R or tool-wear chart', was='33')} of {n(len(shp), 'mart_limit_verifications: sharpenings', was='408')} failed on at least one chart of the die ({pct(shp.mean(), 'share of sharpenings failed', was='8.1%')}). "
         f"The passes sit close to centre, at a median offset of {n(ok['mean_offset_sigma'].abs().median(), 'mart_limit_verifications.mean_offset_sigma, passes, median absolute', '{:.2f}', was='0.21')} sigma, and {n(int((ok['mean_offset_sigma'].abs() >= 1.0).sum()), 'mart_limit_verifications: passes at 1.0 to 1.5 sigma', was='19')} of the "
         f"{n(len(ok), 'mart_limit_verifications: passes', was='1,269')} passes lie between 1.0 and 1.5 sigma. On an unchanged process the mean criterion fails by chance on under {n(0.001 if ff_rate < 0.00001 else ff_rate * 100, 'analytics.chart_performance: false-failure rate of the mean criterion, limits from 25 subgroups', '{:.3f}', was='0.001')}% of verifications, so the failures are the dies that came back from the sharpening at a different level.")
    pg.p(f"<strong>Takeaway: verification fails on {pct(vt['failed'].sum() / vt['verifications'].sum(), 'mart_limit_verifications: share of verifications failed', 0, was='3%')} of charts and {pct(shp.mean(), 'share of sharpenings failed, rounded', 0, was='8%')} of sharpenings, and almost every failure is a real level change.</strong>")
    t2 = pd.DataFrame([{"row": "X-bar and R, after sharpening", "v": x1.verifications, "f": x1.failed, "r": x1.rate}, {"row": "Regression, after sharpening", "v": x2.verifications, "f": x2.failed, "r": x2.rate},
                       {"row": "Three-way, after rebuild", "v": x3.verifications, "f": x3.failed, "r": x3.rate}, {"row": "By sharpening, any chart of the die", "v": len(shp), "f": int(shp.sum()), "r": float(shp.mean())}])
    pg.body_table("Table 3: Verifications of limits held across a die event", t2, {"row": "Verification", "v": "Verifications", "f": "Failed", "r": "Failure rate"}, {"Verifications": F0, "Failed": F0, "Failure rate": P1},
                  bold_cols=("Failure rate",), caption="Design range for the sharpening row 3% to 9%.")
    lv = query("select * from marts.mart_limit_verifications where result = 'passed' and chart in ('X-bar and R', 'tool-wear')")
    xr = sr[sr["chart"] == "X-bar and R"]; twr = sr[sr["chart"] == "tool-wear"]

    def rate(g, col):
        return 100 * g[col].sum() / g["subgroups_in_scope"].sum()
    known = {r: 100 * A.flag_rate_rules(A.zone_probs(), (r,)) for r in (1, 2, 3, 4)}
    cc = cc_x; ccp = cc["points"]; cobs, cexp = int(ccp["observed_signal"].sum()), float(ccp["expected_rate"].sum())
    clo, chi = stats.chi2.ppf(0.025, 2 * cobs) / 2 / cexp, stats.chi2.ppf(0.975, 2 * (cobs + 1)) / 2 / cexp
    pg.p(f"<strong>Observed against expected.</strong> On charts with no special cause in the interval, the year's signals run at {n(scope.at['X-bar and R', 'ratio'], 'observed over expected, X-bar and R', '{:.2f}', was='1.30')} times expectation on X-bar and R, {n(scope.at['three-way', 'ratio'], 'observed over expected, three-way', '{:.2f}', was='0.83')} on three-way and "
         f"{n(scope.at['tool-wear', 'ratio'], 'observed over expected, tool-wear', '{:.2f}', was='1.79')} on regression, with expectation set at each chart's own baseline size and rules.")
    pg.ul([f"<strong>X-bar and R and regression</strong> run above expectation on rules 3 and 4: {n(rate(xr, 'signals_rule_3'), 'mart_signal_rates.signals_rule_3, X-bar and R, per 100', '{:.2f}', was='1.39')} and {n(rate(xr, 'signals_rule_4'), 'mart_signal_rates.signals_rule_4, X-bar and R, per 100', '{:.2f}', was='2.09')} per 100 against "
           f"{n(known[3], 'flag_rate_rules, rule 3, known', '{:.2f}', was='0.45')} and {n(known[4], 'flag_rate_rules, rule 4, known', '{:.2f}', was='0.78')} at known parameters on X-bar and R, {n(rate(twr, 'signals_rule_3'), 'mart_signal_rates.signals_rule_3, tool-wear, per 100', '{:.2f}', was='1.20')} and "
           f"{n(rate(twr, 'signals_rule_4'), 'mart_signal_rates.signals_rule_4, tool-wear, per 100', '{:.2f}', was='2.37')} on regression. Two things in the record produce this. Limits are held across sharpenings, so small persistent offsets (operator reproducibility on the fixture, a part running on another press) accumulate rule 3 and 4 signals that a recomputed chart would absorb. And a level change at sharpening of up to 1.5 sigma passes verification and then runs under the old limits: "
           f"{n(int((lv['mean_offset_sigma'].abs() >= 1).sum()), 'mart_limit_verifications: X-bar and R and tool-wear passes at 1.0 to 1.5 sigma', was='14')} of {n(len(lv), 'mart_limit_verifications: X-bar and R and tool-wear passes', was='1,131')} passes on these charts lie between 1.0 and 1.5 sigma.",
           "<strong>Three-way</strong> runs below expectation because its individuals limits carry the residual coil offset left after centring (Section 4), so rule 1 signals less often than an independent process would.",
           f"<strong>The coil-change chart</strong> raised {n(len(ccs), 'mart_signals: coil-change chart, rule 1 signals in the year', was='28')} rule 1 signals in the year, {n(cc_ncf, 'mart_signals: coil-change chart, no cause found', was='27')} closed as no cause found and "
           f"{wd(len(soft), 'mart_signals: coil-change chart, assignable cause', was='one')} the soft coil on {txt(soft['characteristic_id'].iloc[0], 'mart_signals.characteristic_id, soft coil', was='C-15731-07')} on {txt(DAY(soft['raised_at'].iloc[0]), 'mart_signals.raised_at, soft coil', was='27 May 2026')}. "
           f"On the {n(len(ccp), 'mart_coil_change_points: points with six or more coils on record', was='2,292')} points with six or more coils on record, where the expectation can be set from the record's own lot structure, it raised "
           f"{n(cobs, 'mart_coil_change_points: rule 1 signals on points with six or more coils', was='18')} against {n(cexp, 'analytics.chart_performance.coil_change: expected signals, Monte Carlo', '{:.1f}', was='12.1')} expected ("
           f"{n(cobs / cexp, 'observed over expected, coil-change chart', '{:.2f}', was='1.49')} times, with a 95% interval of {n(clo, 'Poisson interval, low', '{:.2f}', was='0.88')} to {n(chi, 'Poisson interval, high', '{:.2f}', was='2.35')}); the expectation is above the independent rate because coils arrive in lots of "
           f"{wd(int(query('select min(k) n from (select coil_lot, count(*) k from staging.stg_erp__coils group by 1)')['n'].iloc[0]), 'stg_erp__coils: fewest coils in a lot', was='one')} to {wd(int(query('select max(k) n from (select coil_lot, count(*) k from staging.stg_erp__coils group by 1)')['n'].iloc[0]), 'stg_erp__coils: most coils in a lot', was='four')} that share "
           f"{pct(cc['lot_share'], 'analytics.chart_performance.coil_change: lot share of coil variance', 0, was='76%')} of the coil variance. The other {wd(len(ccs) - cobs, 'mart_signals less mart_coil_change_points: signals on points with fewer than six coils on record', was='ten')} signals sit on points whose limits rest on coils before the record."])
    pg.p("<strong>Takeaway: the excess on X-bar and R and regression charts is on rules 3 and 4, and comes from limits held across sharpenings.</strong>")
    st = scope.reset_index().set_index("chart").loc[["X-bar and R", "three-way", "tool-wear"]].reset_index()
    band = {"X-bar and R": (0.9, 1.4), "three-way": (0.9, 1.4), "tool-wear": (0.9, 1.5)}
    shade = {i for i, r in st.iterrows() if not band[r.chart][0] <= r.ratio <= band[r.chart][1]}
    pg.body_table("Table 4: Observed against expected signals by chart type", st, {"chart": "Chart", "subgroups": "Routine subgroups", "signals": "Signals", "observed per 100": "Observed per 100", "expected per 100": "Expected per 100", "ratio": "Observed over expected"},
                  {"Routine subgroups": F0, "Signals": F0, "Observed per 100": F2, "Expected per 100": F2, "Observed over expected": F2}, bold_cols=("Observed over expected",), shade_rows=shade,
                  caption="Charts with no special cause in the interval; expectation at each chart's own baseline size and rules; design band 0.9 to 1.4, regression 0.9 to 1.5.")
    rr = pd.DataFrame([{"chart": DISPLAY.get(c, c), "rule": r, "obs": rate(g, f"signals_rule_{r}"), "exp": known[r]} for c, g in (("X-bar and R", xr), ("tool-wear", twr)) for r in (1, 2, 3, 4)])
    for r in rr.itertuples():
        pg.figval(8, f"{r.obs:.2f}", f"mart_signal_rates.signals_rule_{r.rule}, {r.chart}, per 100")
        pg.figval(8, f"{r.exp:.2f}", f"flag_rate_rules, rule {r.rule}, known")
    pg.figure(FIG.signals_by_rule(rr), "Figure 8: Signals by rule on long-held limits, observed against the known-parameter expectation",
              "Signals per 100 routine subgroups on charts with no special cause in the interval, by rule: observed (filled) against the rate at known parameters (outlined). The excess is on rules 3 and 4.")
    bp = sr.groupby("press_id").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum")).reset_index()
    bp["observed per 100"] = 100 * bp["signals"] / bp["subgroups"]; bp["expected per 100"] = 100 * bp["es"] / bp["subgroups"]
    bp["low"] = [100 * stats.chi2.ppf(0.025, 2 * k) / 2 / m if k > 0 else 0.0 for k, m in zip(bp["signals"], bp["subgroups"])]
    bp["high"] = [100 * stats.chi2.ppf(0.975, 2 * (k + 1)) / 2 / m for k, m in zip(bp["signals"], bp["subgroups"])]
    pg.figure(FIG.expected_observed_by_press(bp), "Figure 9: Expected against observed false alarms by press", "Observed signals per 100 routine subgroups on charts with no special cause in the year, with a 95% Poisson interval, against the rate expected from the press's charts at their own baseline sizes.")
    bp["d"] = bp["observed per 100"] - bp["expected per 100"]; bp["ratio"] = bp["observed per 100"] / bp["expected per 100"]
    t1_, t2_ = bp.sort_values("d", ascending=False).iloc[0], bp.sort_values("ratio", ascending=False).iloc[0]; bot = bp.sort_values("d").iloc[0]
    others = bp[~bp["press_id"].isin([t1_.press_id, t2_.press_id, bot.press_id])]
    pg.p(f"By press, {txt(t1_.press_id, 'mart_signal_rates: press furthest above expectation, by difference', was='PR-01')} and {txt(t2_.press_id, 'mart_signal_rates: press furthest above expectation, by ratio', was='PR-09')} run furthest above expectation ({n(t1_['observed per 100'], 'observed per 100, PR-01', '{:.2f}', was='3.91')} against {n(t1_['expected per 100'], 'expected per 100, PR-01', '{:.2f}', was='3.18')} per 100, and "
         f"{n(t2_['observed per 100'], 'observed per 100, PR-09', '{:.2f}', was='3.46')} against {n(t2_['expected per 100'], 'expected per 100, PR-09', '{:.2f}', was='2.81')}) and "
         f"{txt(bot.press_id, 'mart_signal_rates: press furthest below expectation', was='PR-10')} furthest below ({n(bot['observed per 100'], 'observed per 100, that press', '{:.2f}', was='2.60')} against {n(bot['expected per 100'], 'expected per 100, that press', '{:.2f}', was='3.26')}); the other eight sit within "
         f"{n(0.7 if others['d'].abs().max() < 0.7 else others['d'].abs().max(), 'bound on the gap between observed and expected per 100, the other eight presses (largest ' + format(others['d'].abs().max(), '.2f') + ')', '{:.1f}', was='0.7')} per 100 of expectation.")
    lag = vc["lag_1_autocorrelation_within_coil"]; lo, hi = float(lag.quantile(0.1)), float(lag.quantile(0.9)); mp = float(lag.median())
    pg.p(f"<strong>Autocorrelation.</strong> Subgroup means within a coil carry a median lag-1 autocorrelation of {n(mp, 'mart_variance_components.lag_1_autocorrelation_within_coil, median', '{:.2f}', was='-0.07')} (10th to 90th percentile {n(lo, 'lag-1, 10th percentile', '{:.2f}', was='-0.19')} to {n(hi, 'lag-1, 90th percentile', '{:.2f}', was='0.02')}). Negative autocorrelation of that size lengthens the in-control ARL under rules 1 to 4 from "
         f"{n(a_r14_0, 'arl_rules, rules 1 to 4, independent', was='92')} to {n(A.arl_ar1_rules(mp, (1, 2, 3, 4), per_zone=3), 'arl_ar1_rules at the measured median', was='109')} and leaves rule 1 unchanged, so the limits need no adjustment for it.")
    f7 = pd.DataFrame([{"phi": phi, "rule 1": A.arl_ar1_rules(phi, (1,), per_zone=8), "rules 1 to 4": A.arl_ar1_rules(phi, (1, 2, 3, 4), per_zone=3)} for phi in (-0.3, -0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2, 0.3)])
    pg.figure(FIG.arl_autocorrelation(f7, lo, hi, mp), "Figure 10: In-control ARL against lag-1 autocorrelation", "In-control average run length of a means chart on AR(1) subgroup means, by the Markov chain method, with the measured 10th to 90th percentile of lag-1 autocorrelation shaded and the median marked.")
    below = rw[rw["below_coil_change_minimum"]]
    pg.p(f"<strong>The annual review's three-way sets.</strong> {n(len(below), 'mart_limit_sets: three-way annual-review sets below the minimum', was='23')} of the {n(len(rw), 'mart_limit_sets: three-way annual-review sets', was='45')} three-way limit sets issued at the review span "
         f"{wd(below['coil_changes_spanned'].min(), 'mart_limit_sets.coil_changes_spanned, lowest', was='one')} to {wd(below['coil_changes_spanned'].max(), 'mart_limit_sets.coil_changes_spanned, highest', was='nine')} coil changes, against the baseline rule of ten, because the review computed on a trailing window of "
         f"{n(below['subgroups_used'].min(), 'mart_limit_sets.subgroups_used, lowest', was='50')} to {n(below['subgroups_used'].max(), 'mart_limit_sets.subgroups_used, highest', was='978')} subgroups rather than on the baseline rule. Their centre lines are sound; their individuals limits understate the coil offset the design is meant to carry. They are re-issued as ten coil changes accrue on each chart.")
    pg.p("Two changes are recommended for the tool-wear charts, where the excess is largest: the verification criterion tightened to 1.0 sigma, since the level change at sharpening is the larger part of it, and the regression re-fitted at each planned trigger as well as at each passed verification.")

    # ═══════════════ 4. Variance structure and chart design
    pg.h2("variance", "4. Variance structure and chart design")
    pg.p("The chart for each class follows from where its variance lies, and the four measured classes differ enough that no one chart serves them all.")
    pg.ul([f"<strong>Formed height and bend angle:</strong> {pct(med.at['formed', 'share_within'], 'mart_variance_components.share_within, formed', was='80.0%')} of the routine variance lies within the subgroup after centring, {pct(med.at['formed', 'share_between_subgroups_in_coil'], 'mart_variance_components.share_between_subgroups_in_coil, formed', was='5.2%')} between subgroups within a coil, and "
           f"{pct(med.at['formed', 'share_between_coils'], 'mart_variance_components.share_between_coils, formed', was='13.5%')} is the residual coil offset that centring leaves. Before centring, {pct(med.at['formed', 'incoming_coil_share'], 'mart_variance_components.incoming_coil_share, formed, median', was='49.7%')} of the incoming variance on coil-change subgroups lies between coils.",
           f"<strong>Hole diameter:</strong> {pct(med.at['hole diameter', 'trend_share'], 'mart_variance_components.trend_share, hole diameter, median', was='36.2%')} of the variance is the wear trend over a sharpening interval; {pct(med.at['hole diameter', 'trend_within_share'], 'mart_variance_components.trend_within_share, hole diameter', was='56.1%')} lies within the subgroup about the trend.",
           f"<strong>Cut geometry:</strong> {pct(med.at['cut geometry', 'share_within'], 'mart_variance_components.share_within, cut geometry, median', was='97.4%')} within the subgroup, {pct(med.at['cut geometry', 'share_between_coils'], 'mart_variance_components.share_between_coils, cut geometry', was='0.8%')} between coils.",
           f"<strong>Flatness:</strong> {pct(med.at['flatness', 'share_within'], 'mart_variance_components.share_within, flatness, median', was='97.5%')} within the subgroup."])
    bi = float(med["share_between_intervals"].max())
    pg.figure(FIG.variance_components(med.reset_index()), "Figure 11: Variance components by class",
              f"Each bar is one class: the median share of variance in each component across its critical characteristics (all flatness characteristics) with 60 routine subgroups or more in the year, nested by the method of moments. Between-interval shares are under {pg.figval(11, '0.1%' if bi < 0.001 else f'{bi * 100:.1f}%', 'mart_variance_components.share_between_intervals, largest class median (bound)')} on every class; the wear on hole diameters is the trend share.")
    ff = fam[fam["characteristic_class"] == "formed"]; fh = fam[fam["characteristic_class"] == "cut geometry"]; fhd = fam[fam["characteristic_class"] == "hole diameter"].iloc[0]
    m_bc = mark()
    pg.p(f"The family's characteristics show the plant's structure one at a time: the formed heights and bend angles carry between-coil shares of {n(100 * ff['share_between_coils'].min(), 'mart_variance_components.share_between_coils, family formed, lowest', '{:.0f}', was='7')}% to "
         f"{n(100 * ff['share_between_coils'].max(), 'mart_variance_components.share_between_coils, family formed, highest', '{:.0f}', was='31')}% on the routine record and {n(100 * ff['incoming_coil_share'].min(), 'mart_variance_components.incoming_coil_share, family, lowest', '{:.0f}', was='22')}% to "
         f"{n(100 * ff['incoming_coil_share'].max(), 'mart_variance_components.incoming_coil_share, family, highest', '{:.0f}', was='52')}% incoming, the hole positions {n(100 * fh['share_between_coils'].min(), 'mart_variance_components.share_between_coils, family hole position and width, lowest', '{:.0f}', was='0')}% to "
         f"{n(100 * fh['share_between_coils'].max(), 'mart_variance_components.share_between_coils, family hole position and width, highest', '{:.0f}', was='6')}%, and the one measured hole diameter, {fhd.characteristic_id}, a {pct(fhd.trend_share, 'mart_variance_components.trend_share, C-15731-02', was='23.5%')} wear trend.")
    f11 = fam[["characteristic_id", "characteristic_class"]].copy(); f11["value"] = np.where(fam["characteristic_class"] == "hole diameter", fam["trend_share"], fam["share_between_coils"])
    for r in f11.itertuples():
        pg.figval(12, f"{r.value * 100:.1f}%", f"mart_variance_components.{'trend_share' if r.characteristic_class == 'hole diameter' else 'share_between_coils'}, {r.characteristic_id}")
    pg.figure(FIG.family_between_coil(f11, float(med.at["formed", "share_between_coils"]), float(med.at["cut geometry", "share_between_coils"])), "Figure 12: Between-coil share of variance by family characteristic",
              "One row per family variable characteristic, labelled by id: its between-coil share of the routine record's variance, coloured by class, against the plant's formed and cut geometry class medians. C-15731-02, the one variable hole diameter, is shown at its wear-trend share.")
    mv_bc = take(m_bc)
    cf = query("select * from marts.mart_coil_fit order by characteristic_id")
    rmed = float(cf["r_squared"].median()); fc = cf[cf["family_part"] & (cf["coil_change_subgroups"] >= 20)].copy(); fc["d"] = (fc["r_squared"] - rmed).abs(); pick = fc.sort_values(["d", "characteristic_id"]).iloc[0]
    pg.p(f"<strong>The coil effect and centring.</strong> The coil effect on formed characteristics is predictable from the coil certificate, which is why centring at the coil change removes it. Across {n(len(cf), 'mart_coil_fit: characteristics', was='242')} formed characteristics, thickness and hardness on the certificate explain the coil means with a median R squared of "
         f"{n(rmed, 'mart_coil_fit.r_squared, median', '{:.2f}', was='0.82')}; the residual about the fit is {pct(cf['residual_sigma_share_of_tolerance'].median(), 'mart_coil_fit.residual_sigma_share_of_tolerance, median', was='3.2%')} of tolerance, against coil means that spread "
         f"{pct(cf['coil_means_sigma_share_of_tolerance'].median(), 'mart_coil_fit.coil_means_sigma_share_of_tolerance, median', was='10.1%')} of tolerance.")
    m_cf = mark()
    pts = query("select sample_time, subgroup_id, certificate_thickness_mm, certificate_hardness_hrb, subgroup_mean as observed, charted_point from marts.mart_coil_change_points where characteristic_id = ? order by sample_time, subgroup_id", [pick.characteristic_id])
    pts["predicted"] = pick.intercept + pick.per_mm_thickness * pts["certificate_thickness_mm"] + pick.per_hrb * pts["certificate_hardness_hrb"]
    kp = query("select name, usl, lsl from staging.stg_spc__characteristics where characteristic_id = ?", [pick.characteristic_id]).iloc[0]
    pg.figure(FIG.coil_fit(pts, kp.lsl, kp.usl), f"Figure 13: Coil means against the certificate fit, {pick.characteristic_id}",
              "Each point is one coil-change subgroup (10 pieces, before centring): its mean against the mean predicted from the coil's certificate thickness and hardness; the first subgroup on each coil is the point on the chart of coil-change means. The line is observed equal to predicted.")
    mv_cf = take(m_cf)
    fvc = vc[vc["characteristic_class"] == "formed"].copy(); fvc["means_var"] = fvc["share_between_subgroups_in_coil"] + fvc["share_between_coils"] + fvc["share_within"] / 5
    rho = float((fvc["share_between_coils"] / fvc["means_var"]).median())
    ppc = float(query("select median(k) n from (select characteristic_id, run_id, coil_id, count(*) k from intermediate.int_characteristic_history where characteristic_class = 'formed' and subgroup_type = 'routine' and in_record group by all)")["n"].iloc[0])
    mr_ratio = A.moving_range_sigma_ratio(rho, ppc)
    r1_sd, r1_mr, r14_sd, r14_mr = (100 * A.coil_block_rate(rho, (1,), 1.0), 100 * A.coil_block_rate(rho, (1,), mr_ratio), 100 * A.coil_block_rate(rho, (1, 2, 3, 4), 1.0), 100 * A.coil_block_rate(rho, (1, 2, 3, 4), mr_ratio))
    mr_rate = 100 * 2 * stats.norm.sf(A.D4[2] * A.D2[2] / np.sqrt(2)); r_rate = 100 * A.range_rate(1.0)
    pg.p(f"<strong>The three-way design.</strong> On formed characteristics the level resets at each coil, and centring on a 10-piece coil-change subgroup leaves each coil with a residual offset of {pct(rho, 'mart_variance_components: residual coil share of the variance of formed subgroup means, median', was='39.1%')} of the variance of the subgroup means. Limits from the average moving range do not carry that offset: with them rule 1 alone would signal on "
         f"{n(r1_mr, 'coil_block_rate, rule 1, moving-range limits', '{:.2f}', was='1.57')} in-control points per 100, and rules 1 to 4 on {n(r14_mr, 'coil_block_rate, rules 1 to 4, moving-range limits', '{:.1f}', was='20.5')}. The individuals limits in force therefore come from the standard deviation of the baseline means, and rules 2 to 4 are off on the individuals chart: rule 1 signals on "
         f"{n(r1_sd, 'coil_block_rate, rule 1, limits in force', '{:.2f}', was='0.27')} per 100, the nominal rate. The range and moving-range charts run rule 1 at {n(r_rate, 'range_rate, known', '{:.2f}', was='0.46')} and {n(mr_rate, 'moving-range rule 1 rate, independent means', '{:.2f}', was='0.92')} per 100. A coil-level shift is the coil-change chart's job, not the routine chart's.")
    alts = pd.DataFrame([{"label": "rule 1, sd-of-means limits", "value": r1_sd, "in_force": True}, {"label": "rule 1, moving-range limits", "value": r1_mr, "in_force": False},
                         {"label": "rules 1 to 4, sd-of-means limits", "value": r14_sd, "in_force": False}, {"label": "rules 1 to 4, moving-range limits", "value": r14_mr, "in_force": False}])
    for r in alts.itertuples():
        pg.figval(14, f"{r.value:.2f}" if r.value < 10 else f"{r.value:.1f}", f"coil_block_rate, {r.label}")
    pg.figure(FIG.three_way_designs(alts), "Figure 14: False alarms per 100 points by three-way design",
              f"In-control false alarms per 100 points at known parameters, residual coil share {rho * 100:.1f}%; the filled bar is the design in force.")
    pb74 = pb[pb["limit_set_id"] == "LS-00074"].iloc[0]
    b = query("select * from marts.mart_phase1_baseline_subgroups where limit_set_id = 'LS-00074' order by baseline_subgroup_no"); b0 = b.iloc[0]
    rb_ = query("select event_date from intermediate.int_die_event_timeline where die_id = 'D-1333-C' and event_type = 'rebuild' and event_date between '2026-05-01' and '2026-05-11'").iloc[0]
    scr = b[b["screened"]].iloc[0]; keep = b[~b["screened"]]; xb, rbar = keep["subgroup_mean"].mean(), keep["subgroup_range"].mean()
    move = max(abs(xb - b0.centre_line), abs(xb + 0.577 * rbar - b0.ucl_mean), abs(xb - 0.577 * rbar - b0.lcl_mean))
    m_p1 = mark()
    pg.p(f"<strong>Phase I baselines.</strong> The baseline on C-11333-02 after the rebuild of {txt(DAY(rb_.event_date), 'int_die_event_timeline: rebuild of D-1333-C', was='9 May 2026')} shows the procedure: {n(len(b), 'mart_phase1_baseline_subgroups: subgroups', was='25')} routine subgroups on one run, limits "
         f"{n(b0.lcl_mean, 'mart_phase1_baseline_subgroups.lcl_mean', '{:.3f}', was='24.381')} to {n(b0.ucl_mean, 'mart_phase1_baseline_subgroups.ucl_mean', '{:.3f}', was='24.435')} mm on the means and a range limit of {n(b0.ucl_range, 'mart_phase1_baseline_subgroups.ucl_range', '{:.4f}', was='0.0988')} mm, Anderson-Darling "
         f"{n(pb74.anderson_darling, 'mart_phase1_baselines.anderson_darling', '{:.2f}', was='0.53')} against a critical value of {n(pb74.anderson_darling_critical_5pct, 'mart_phase1_baselines.anderson_darling_critical_5pct', '{:.2f}', was='0.73')}. Subgroup "
         f"{n(scr.baseline_subgroup_no, 'mart_phase1_baseline_subgroups: screened subgroup', was='18')} carries a range of {n(scr.subgroup_range, 'mart_phase1_baseline_subgroups.subgroup_range, screened', '{:.3f}', was='0.106')} mm, beyond the range limit, and is flagged. The record keeps it in the limits; recomputed without it the mean limits move by under "
         f"{n(0.002 if move < 0.002 else move, 'mart_phase1_baseline_subgroups: largest move of the mean limits without the screened subgroup', '{:.3f}', was='0.002')} mm and the range limit by {n(abs(2.114 * rbar - b0.ucl_range), 'mart_phase1_baseline_subgroups: move of the range limit without the screened subgroup', '{:.3f}', was='0.005')} mm.")
    pg.figure(FIG.phase1_baseline(b, b0.centre_line, b0.ucl_mean, b0.lcl_mean, b0.ucl_range), "Figure 15: A Phase I baseline after a rebuild, C-11333-02, 11 May 2026",
              "The 25 routine subgroups of limit set LS-00074 on C-11333-02 (hole to edge B), run R26-00820: means against the computed centre line and limits, ranges against the range limit. Subgroup 18 is flagged on the range and kept in the limits, as the record has it.")
    mv_p1 = take(m_p1)
    t5 = ls[ls["characteristic_id"] == "C-15731-02"]; inforce = t5[t5["effective_to"].isna()].iloc[0]
    in_year = t5[(t5["effective_to"].isna()) | (t5["effective_to"] >= pd.Timestamp("2025-07-01"))]
    ws = query("select characteristic_id, die_id, min(press_id) press_id, any_value(characteristic_rate_mm_per_100k_shots) rate, any_value(qualifying_intervals) intervals from marts.mart_wear_slopes group by characteristic_id, die_id order by rate, characteristic_id")
    pg.p(f"<strong>The regression chart.</strong> The centre line is the regression of diameter on shots since sharpening over the die's earlier intervals, re-fitted at each verification that passes with the limits' sigma held, so the line follows the die without a new baseline. Wear rates by die run from {n(ws['rate'].min(), 'mart_wear_slopes.characteristic_rate_mm_per_100k_shots, lowest', '{:.4f}', was='0.0041')} to "
         f"{n(ws['rate'].max(), 'mart_wear_slopes.characteristic_rate_mm_per_100k_shots, highest', '{:.4f}', was='0.0100')} mm per 100,000 shots on the {n(len(ws), 'mart_wear_slopes: characteristics', was='19')} charted hole diameters; {wd(int((ws['intervals'] == 1).sum()), 'mart_wear_slopes.qualifying_intervals equal to 1', was='six')} rest on a single sharpening interval.")
    m_tw = mark()
    pg.p(f"On C-15731-02 the line in force ({txt(DAY(inforce.effective_from), 'mart_limit_sets.effective_from, C-15731-02 in force', was='27 May 2026')}) runs at "
         f"{n(inforce.slope_per_100k_shots, 'mart_limit_sets.slope_per_100k_shots', '{:.4f}', was='0.0058')} mm per 100,000 shots from {n(inforce.centre_line, 'mart_limit_sets.centre_line', '{:.4f}', was='9.4555')} mm with limits of plus and minus {n(3 * inforce.sigma_of_means, 'mart_limit_sets.sigma_of_means times 3', '{:.4f}', was='0.0060')} mm; the chart ran on "
         f"{wd(len(in_year), 'mart_limit_sets: C-15731-02 sets in force in the year', was='ten')} limit sets in the year, listed in the appendix.")
    wp = query("select * from marts.mart_wear_points where characteristic_id = 'C-15731-02' and characteristic_type = 'hole diameter' and limit_set_id = ? order by sample_time", [inforce.limit_set_id])
    g5 = wp[wp["sharpening_interval_no"] == wp["sharpening_interval_no"].max()]
    pg.figure(FIG.tool_wear_chart(g5, inforce.centre_line, inforce.slope_per_100k_shots, 3 * inforce.sigma_of_means, g5["usl"].iloc[0], g5["lsl"].iloc[0]),
              f"Figure 16: The regression chart on C-15731-02, interval from {txt(DAY(g5['sharpening_date'].iloc[0]), 'mart_wear_points.sharpening_date', was='1 May 2026')}",
              "The subgroups of hole diameter B on D-5731-A charted under the limit set in force at 30 June (from 27 May 2026), against shots since the sharpening, with its regression centre line and sloped limits.")
    mv_tw = take(m_tw)
    for r in ws.itertuples():
        pg.figval(17, f"{r.rate:.4f}", f"mart_wear_slopes.characteristic_rate_mm_per_100k_shots, {r.characteristic_id}")
        pg.figval(17, f"{int(r.intervals)}", f"mart_wear_slopes.qualifying_intervals, {r.characteristic_id}")
    pg.figure(FIG.wear_rate_by_die(ws, 0.004, 0.010, "C-15731-02", f"(Figure {REGRESSION_FIGURE})"), "Figure 17: Hole diameter wear rate by die, with the intervals behind each rate",
              "Each charted hole diameter's wear rate: the median slope of subgroup means on shots since sharpening over its intervals of 15 subgroups or more spanning 20,000 shots. Marker area is the number of qualifying intervals (written beside it); hollow markers rest on one interval. The plant range, 0.004 to 0.010 mm per 100,000 shots, is shaded.")

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
    p3_strokes = float(query("select sum(strokes) s from intermediate.int_run_shots where press_id = 'PR-03' and cast(production_start as date) between '2026-04-01' and '2026-06-30'")["s"].iloc[0])
    p3_shifts = float(query("select count(distinct (cast(sample_time as date), hour(sample_time) * 60 + minute(sample_time) >= 870)) n from intermediate.int_characteristic_history where press_id = 'PR-03' and in_quarter")["n"].iloc[0])
    pg.p(f"<strong>The design.</strong> The total is autocorrelated at lag 1 by a median {n(phi_r, 'mart_per_stroke_run_tonnage.baseline_lag_1_autocorrelation, median', '{:.2f}', was='0.60')} and varies by {pct(cv_r, 'mart_per_stroke_run_tonnage: baseline sd over mean, median', 2, was='1.49%')} within a run, so the EWMA limits are set on the AR(1)-adjusted variance. At known parameters the in-control ARL is "
         f"{n(a0 / 1e6, 'ewma_arl, L 5.5, known, millions', '{:.1f}', was='77.8')} million strokes; with the parameters estimated from 500 strokes it is {n(est[Lx] / 1e6, 'ewma_arl averaged over the estimates, L 5.5, millions', '{:.2f}', was='2.64')} million. L is set at 5.5 for the estimated case: at L 4.9 the known-parameter ARL of "
         f"{n(a0c / 1e6, 'ewma_arl, L 4.9, known, millions', '{:.2f}', was='3.68')} million falls to {n(round(est[Lc], -3), 'ewma_arl averaged over the estimates, L 4.9, to the thousand', was='312,000')} strokes once estimation is allowed for, about one false stop in "
         f"{wd(round(est[Lc] / (p3_strokes / p3_shifts)), 'strokes at L 4.9 over PR-03 strokes per worked shift in the quarter', was='eight')} shifts on PR-03.")
    shift_tot = float(pe["total_shift_at_onset"].abs().median()); shift_sh = float(pe["largest_channel_share_shift_points"].median())
    lams = (0.02, 0.05, 0.10); Ls = {l_: (Lx if l_ == lam else A.ewma_limit_for(l_, a0, phi_r)) for l_ in lams}
    pg.p(f"A chipped punch drops the total by a median {pct(shift_tot, 'mart_parts_exposed.total_shift_at_onset, median', 2, was='3.06%')} and moves the largest channel share by {n(shift_sh, 'mart_parts_exposed.largest_channel_share_shift_points, median', '{:.2f}', was='1.32')} points. At that shift the EWMA signals in "
         f"{n(A.ewma_arl(lam, Lx, shift_tot / cv_r, phi_r), 'ewma_arl at the median chipped-punch shift', was='38')} strokes; the channel-share chart signals first on most chips, because the share moves on the stroke of the break. Lambda 0.02 is the choice for shifts of 2% to 3%: at a 2% step it signals in "
         f"{n(A.ewma_arl(0.02, Ls[0.02], 0.02 / cv_r, phi_r), 'ewma_arl, lambda 0.02, 2% step', was='76')} strokes against {n(A.ewma_arl(0.05, Ls[0.05], 0.02 / cv_r, phi_r), 'ewma_arl, lambda 0.05, 2% step', was='117')} at lambda 0.05 and {n(A.ewma_arl(0.10, Ls[0.10], 0.02 / cv_r, phi_r), 'ewma_arl, lambda 0.10, 2% step', was='425')} at lambda 0.10, with the same in-control ARL.")
    f9 = pd.DataFrame([{"shift_value": d, **{f"lambda {l_:.2f}, L {Ls[l_]:.2f}": A.ewma_arl(l_, Ls[l_], d / cv_r, phi_r) for l_ in lams}} for d in (0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05)])
    pg.figure(FIG.ewma_arl1(f9, shift_tot), "Figure 18: EWMA ARL1 against shift size, three lambda values", "Strokes to signal against a step in the per-stroke total, by the Markov chain method on the AR(1)-adjusted variance at the measured autocorrelation and variation; each lambda's L gives the same in-control ARL; the chipped-punch median shift is marked.")
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
    t18 = stops.groupby(["finding_class", "chart"]).size().to_dict()
    for (fd, chname), v in sorted(t18.items()):
        pg.figval(19, f"{v}", f"mart_per_stroke_stops: {fd}, {chname}")
    pg.figure(FIG.stops_by_finding(t18, ["slug pulling", "worn punch", "chipped punch", "nothing found"], ["EWMA on the total", "channel share", "both"]), "Figure 19: Stops by the per-stroke charts, by finding and chart",
              "Stops in the year on every press, by the toolmaker's finding and the chart that stopped the press; one worn punch was signalled by both charts at once.")
    s13 = stops[stops["run_id"] == "R26-00820"].iloc[0]
    st13 = query("select * from marts.mart_per_stroke_stop_strokes where fault_event_id = ? order by stroke_no", [s13.fault_event_id]); r13 = rt[rt["run_id"] == "R26-00820"].iloc[0]
    z = (st13["total_kn"].values - r13.baseline_total_kn_mean) / r13.baseline_total_kn_sd; e = 0.0; ew = []
    for v in z:
        e = lam * v + (1 - lam) * e; ew.append(e)
    lim = Lx * A.ewma_sd_factor(lam, r13.baseline_lag_1_autocorrelation)
    shares = [c for c in ("share_ch1", "share_ch2", "share_ch3", "share_ch4") if st13[c].notna().any()]
    m_13f = mark()
    pg.figure(FIG.stop_13_may(st13, ew, lim, shares), "Figure 20: The 13 May stop on D-1333-C", "The 300 production strokes before the stop of run R26-00820: the EWMA of the per-stroke total in the run's baseline sigmas, started at zero 300 strokes before, against its limits; and each channel's share of the total, less its level over the first 200 of those strokes.")
    mv_13f = take(m_13f)
    pe13 = pe[pe["fault_event_id"] == s13.fault_event_id].iloc[0]
    m_13p = mark()
    pg.p(f"On 13 May 2026 the EWMA on PR-03 stopped run R26-00820 at stroke {n(s13.stop_stroke_no, 'mart_per_stroke_stops.stop_stroke_no', was='239,498')}, {n(pe13.strokes_exposed_per_stroke_charts, 'mart_parts_exposed.strokes_exposed_per_stroke_charts, the 13 May stop', was='34')} strokes after the estimated onset, on a punch found chipped and replaced; the press restarted at "
         f"{txt(pd.Timestamp(s13.cleared_at).strftime('%H:%M'), 'mart_per_stroke_stops.cleared_at', was='11:55')}.")
    mv_13p = take(m_13p)
    pg.p(f"<strong>Parts exposed.</strong> Under the per-stroke charts the median chipped punch exposed {wd(pe['parts_exposed_per_stroke_charts'].median(), 'mart_parts_exposed.parts_exposed_per_stroke_charts, median', was='no')} parts. Under an hourly check the same failures would have exposed up to "
         f"{n(pe['parts_exposed_hourly_check_up_to'].median(), 'mart_parts_exposed.parts_exposed_hourly_check_up_to, median', was='6,499')} parts at the median press and up to {n(p3x.hourly_up_to, 'mart_parts_exposed.parts_exposed_hourly_check_up_to, PR-03', was='11,773')} on PR-03, with half that on average; the half-hourly check on the high-speed presses halves both.")
    pg.figure(FIG.parts_exposed(px), "Figure 21: Parts exposed per chipped punch, by press", "For each press, the parts an hourly check would expose: those made in an hour at its realised stroke rate (the bar, log scale), with the median parts exposed per chipped punch on the per-stroke charts (strokes from the estimated onset to the stop, times parts per stroke) written on it.")

    # ═══════════════ 6. The C110 family on PR-03
    pg.h2("family", "6. The C110 family on PR-03")
    pg.p("The three C110 copper parts on PR-03 (P-11333 on D-1333-C, P-15731 on D-5731-A, P-14026 on D-4026-A) are followed here through the same four headings as the plant: their charts and gauges, how the charts performed, the variance structure behind the chart choices, and the per-stroke charts on their press.")
    pg.h3("family-charts", "6.1 Charts and gauges")
    fc_ = fam_cif.assign(cls=fam_cif["characteristic_type"].map(REPORT_CLASS)); fcn = fc_.groupby(["cls", "chart_type"]).size()
    fls = ls[ls["family_part"] & ls["issued_in_record"]]["trigger"].value_counts()
    gs3 = query("select gauge_id, study_date, pct_grr_of_tolerance, study_trigger from marts.mart_gauge_studies where gauge_id = 'F-14026' and study_trigger = 'restudy after failed verification' order by study_date").iloc[-1]
    pg.p(f"The family's three parts carry {n(len(fam_cif), 'mart_charts_in_force: family charts', was='27')} of the plant's {n(len(cif), 'mart_charts_in_force: charts', was='1,380')} charts: "
         f"{n(int(fcn.get(('formed', 'three-way (I-MR-R)'), 0)), 'mart_charts_in_force: family formed, three-way', was='12')} formed heights and bend angles on three-way charts, {n(int(fcn.get(('cut geometry', 'Xbar-R'), 0)), 'mart_charts_in_force: family cut geometry, X-bar and R', was='7')} cut geometry on X-bar and R, "
         f"{n(int(fc_['cls'].eq('hole diameter').sum()), 'mart_charts_in_force: family hole diameter charts', was='5')} hole diameters (one on a regression chart, C-15731-02, and {wd(int(fcn.get(('hole diameter', 'p'), 0)), 'mart_charts_in_force: family pin checks', was='four')} on pin checks) and "
         f"{n(int(fcn.get(('sheared edges', 'p'), 0)), 'mart_charts_in_force: family burr checks', was='3')} sheared edges on burr checks. The register, with each chart's limits basis, gauge, study and status, is in the appendix.")
    pg.p(f"{n(int(fls.sum()), 'mart_limit_sets: family sets issued in the year', was='20')} limit sets were issued on the family's charts in the year: "
         f"{n(fls.get('rebuild', 0), 'mart_limit_sets: family, rebuild', was='9')} after rebuilds, {n(fls.get('tool-wear re-fit', 0), 'mart_limit_sets: family, tool-wear re-fit', was='7')} regression re-fits, {n(fls.get('annual review', 0), 'mart_limit_sets: family, annual review', was='3')} at the annual review and "
         f"{n(fls.get('failed verification', 0), 'mart_limit_sets: family, failed verification', was='1')} after a failed verification.")
    fvar = fam_cif[fam_cif["data_type"] == "variable"]
    own = fvar["gauge_id"] == "F-" + fvar["part_id"].str[2:]
    assert (own == (fvar["gauge_type"] == "check fixture")).all(), "a family chart on a fixture that is not its part's"
    other = fvar[~own].sort_values("characteristic_id")["gauge_type"].tolist()
    pg.p(f"{n(int(own.sum()), 'mart_charts_in_force: family measured charts on the part own check fixture', was='18')} of the family's {n(len(fvar), 'mart_charts_in_force: family measured charts', was='20')} measured charts run on the part's own check fixture; the other "
         f"{wd(len(other), 'mart_charts_in_force: family measured charts on another gauge', was='two')} run on {txt(' and '.join('an ' + t if t[0] in 'aeiou' else 'a ' + t for t in other), 'mart_charts_in_force.gauge_type, family measured charts not on a fixture', was='a caliper and an indicator')}. F-15731 stands at {n(g15.pct_grr_of_tolerance, 'mart_charts_in_force.pct_grr_of_tolerance, F-15731', '{:.1f}', was='6.0')}% of tolerance on its {txt(DAY(g15.study_date), 'mart_charts_in_force.study_date, F-15731', was='2 April 2026')} study and F-14026 at "
         f"{n(g14.pct_grr_of_tolerance, 'mart_charts_in_force.pct_grr_of_tolerance, F-14026', '{:.1f}', was='5.3')}% on {txt(DAY(g14.study_date), 'mart_charts_in_force.study_date, F-14026', was='17 June 2026')}, after the rebuild that followed its "
         f"{txt(DAY(gs3.study_date).rsplit(' ', 1)[0], 'mart_gauge_studies.study_date, F-14026 restudy after failed verification', was='3 June')} restudy at {n(gs3.pct_grr_of_tolerance, 'mart_gauge_studies.pct_grr_of_tolerance, F-14026 restudy', '{:.1f}', was='16.7')}%; "
         f"F-11333 stands at {n(g11.pct_grr_of_tolerance, 'mart_charts_in_force.pct_grr_of_tolerance, F-11333', '{:.1f}', was='16.3')}% on {txt(DAY(g11.study_date), 'mart_charts_in_force.study_date, F-11333', was='5 May 2026')}, in the band that keeps a gauge in service with a restudy, due "
         f"{txt(DAY(g11.restudy_due), 'mart_charts_in_force.restudy_due, F-11333', was='17 August 2026')}.")
    put(mv_grr)

    pg.h3("family-performance", "6.2 How the charts performed")
    fs = sig[sig["family_part"]]; frt = fs[(fs["subgroup_type"] == "routine") & (fs["chart"] != "coil-change means")]; fac = frt[frt["assignable_cause"]]
    f_lvl_s = fac[fac["cause_code"] == "level after sharpening"]; f_fx = fac[fac["cause_code"] == "fixture drift"]; f_lvl_r = fac[fac["cause_code"] == "level after the rebuild"]
    f_soft = fs[(fs["chart"] == "coil-change means") & fs["assignable_cause"]]
    fsr = sc[sc["family_part"]]
    fb = fsr.groupby("cls").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum"))
    fb.loc["total"] = fb.sum()
    fb["observed per 100"] = 100 * fb["signals"] / fb["subgroups"]; fb["expected per 100"] = 100 * fb["es"] / fb["subgroups"]; fb["ratio"] = fb["signals"] / fb["es"]
    fb["lo"] = [stats.chi2.ppf(0.025, 2 * k) / 2 / e if k > 0 else 0.0 for k, e in zip(fb["signals"], fb["es"])]
    fb["hi"] = [stats.chi2.ppf(0.975, 2 * (k + 1)) / 2 / e for k, e in zip(fb["signals"], fb["es"])]
    fvf = query("select * from marts.mart_limit_verifications where die_id in ('D-1333-C', 'D-5731-A', 'D-4026-A')")
    fvt = fvf.groupby(["chart", "die_event"]).agg(done=("verification_id", "count"), failed=("result", lambda x: int((x == "failed").sum())))
    fvd = fvf[fvf["result"] == "failed"].groupby("chart")["die_id"].agg(lambda x: ", ".join(sorted(set(x))))
    fshp = fvf[(fvf["die_event"] == "sharpening") & fvf["chart"].isin(["X-bar and R", "tool-wear"])].groupby(["die_id", "event_date"])["result"].apply(lambda x: (x == "failed").any())
    tw_4026 = int(((cif["die_id"] == "D-4026-A") & (cif["chart_type"] == "three-way (I-MR-R)")).sum())
    pg.p(f"The family's charts caught every special cause on the three parts in the year and ran at {n(fb.at['total', 'ratio'], 'family: observed over expected, total', '{:.2f}', was='1.13')} times expectation overall, with the excess on one class. "
         f"{n(len(fac), 'mart_signals: family routine alarms with an assignable cause', was='107')} routine alarms on {n(fac['run_id'].nunique(), 'mart_signals: family runs with an assignable cause', was='3')} runs closed with a special cause: "
         f"{n(len(f_lvl_s), 'mart_signals: family, level after sharpening', was='54')} on {wd(f_lvl_s['run_id'].nunique(), 'mart_signals: family runs, level after sharpening', was='one')} run where {txt(', '.join(sorted(set(f_lvl_s['die_id']))), 'mart_signals.die_id, level after sharpening', was='D-5731-A')} came back from sharpening at a new level and its verification failed, "
         f"{n(len(f_fx), 'mart_signals: family, fixture drift', was='30')} on {wd(f_fx['run_id'].nunique(), 'mart_signals: family runs, fixture drift', was='one')} run of {txt(', '.join(sorted(set(f_fx['part_id']))), 'mart_signals.part_id, fixture drift', was='P-14026')} as F-14026 drifted, and "
         f"{n(len(f_lvl_r), 'mart_signals: family, level after the rebuild', was='23')} on {wd(f_lvl_r['run_id'].nunique(), 'mart_signals: family runs, level after the rebuild', was='two')} runs of {txt(', '.join(sorted(set(f_lvl_r['part_id']))), 'mart_signals.part_id, level after the rebuild', was='P-14026')} after its rebuild, whose verification failed on "
         f"{wd(fvt.at[('three-way', 'rebuild'), 'failed'], 'mart_limit_verifications: three-way failed after the D-4026-A rebuild', was='three')} of the die's {wd(tw_4026, 'mart_charts_in_force: three-way charts on D-4026-A', was='four')} three-way charts. "
         f"The coil-change chart caught the soft coil on {txt(f_soft['characteristic_id'].iloc[0], 'mart_signals.characteristic_id, soft coil', was='C-15731-07')} on {txt(DAY(f_soft['raised_at'].iloc[0]), 'mart_signals.raised_at, soft coil', was='27 May 2026')}. "
         f"{n(int((~frt['assignable_cause']).sum()), 'mart_signals: family routine alarms closed as no cause found', was='657')} alarms on {n(frt.loc[~frt['assignable_cause'], 'run_id'].nunique(), 'mart_signals: family runs with a no-cause alarm', was='39')} runs closed as no cause found, and every alarm was closed by 30 June.")
    pg.p(f"Verifications on the three dies: {n(fvt.at[('X-bar and R', 'sharpening'), 'done'], 'mart_limit_verifications: family X-bar and R after sharpening', was='51')} X-bar and R after sharpening with {'none' if fvt.at[('X-bar and R', 'sharpening'), 'failed'] == 0 else fvt.at[('X-bar and R', 'sharpening'), 'failed']} failed, "
         f"{n(fvt.at[('tool-wear', 'sharpening'), 'done'], 'mart_limit_verifications: family tool-wear', was='8')} regression-chart with {n(fvt.at[('tool-wear', 'sharpening'), 'failed'], 'mart_limit_verifications: family tool-wear failed', was='1')} failed on {txt(fvd.get('tool-wear', ''), 'mart_limit_verifications.die_id, tool-wear failed', was='D-5731-A')}, "
         f"{n(fvt.at[('three-way', 'rebuild'), 'done'], 'mart_limit_verifications: family three-way after rebuild', was='16')} three-way after rebuild with {n(fvt.at[('three-way', 'rebuild'), 'failed'], 'mart_limit_verifications: family three-way failed', was='3')} failed, all on {txt(fvd.get('three-way', ''), 'mart_limit_verifications.die_id, three-way failed', was='D-4026-A')}; "
         f"by sharpening, {n(int(fshp.sum()), 'mart_limit_verifications: family sharpenings failed', was='1')} of {n(len(fshp), 'mart_limit_verifications: family sharpenings', was='23')}.")
    pg.p("<strong>Takeaway: the family's special causes in the year were one die at a new level, one fixture drifting and one rebuild, each caught by the chart designed for it.</strong>")
    CHX = {"Xbar-R": "X-bar and R", "three-way (I-MR-R)": "three-way", "tool-wear": "regression"}

    def charts_x(df):
        have = set(df["chart_type"])
        return " and ".join(CHX[t] for t in ("tool-wear", "Xbar-R", "three-way (I-MR-R)") if t in have)
    t5f = pd.DataFrame([
        {"what": "D-5731-A at a new level after sharpening", "chart": txt(charts_x(f_lvl_s) + ", with verification", 'mart_signals.chart_type, family level after sharpening', was='regression, with verification'),
         "events": n(f_lvl_s["run_id"].nunique(), 'mart_signals: runs, family level after sharpening', was='1') + " run", "alarms": n(len(f_lvl_s), 'mart_signals: alarms, family level after sharpening', was='54')},
        {"what": "F-14026 drifting", "chart": txt(", ".join(CHX[t] for t in ("Xbar-R", "three-way (I-MR-R)") if t in set(f_fx["chart_type"])), 'mart_signals.chart_type, family fixture drift', was='X-bar and R, three-way'),
         "events": n(f_fx["run_id"].nunique(), 'mart_signals: runs, family fixture drift', was='1') + " run", "alarms": n(len(f_fx), 'mart_signals: alarms, family fixture drift', was='30')},
        {"what": "P-14026 at a new level after rebuild", "chart": txt(charts_x(f_lvl_r) + ", with verification", 'mart_signals.chart_type, family level after the rebuild', was='three-way, with verification'),
         "events": n(f_lvl_r["run_id"].nunique(), 'mart_signals: runs, family level after the rebuild', was='2') + " runs", "alarms": n(len(f_lvl_r), 'mart_signals: alarms, family level after the rebuild', was='23')},
        {"what": "Soft coil on C-15731-07", "chart": "coil-change", "events": n(len(f_soft), 'mart_signals: coils, family soft coil', was='1') + " coil", "alarms": n(len(f_soft), 'mart_signals: alarms, family soft coil', was='1')}])
    pg.body_table("Table 105: Special causes caught on the family in the year", t5f, {"what": "What was caught", "chart": "Chart", "events": "Events", "alarms": "Alarms"}, bold_cols=("Events",),
                  caption=f"The family's 20 measured charts and coil-change chart, 1 July 2025 to 30 June 2026; {n(int((~frt['assignable_cause']).sum()), 'mart_signals: family routine alarms closed as no cause found', was='657')} routine alarms closed as no cause found.")
    cg_ = fsr[fsr["cls"] == "cut geometry"]
    kn = {r: A.flag_rate_rules(A.zone_probs(), (r,)) * cg_["subgroups_in_scope"].sum() for r in (1, 2, 3, 4)}
    ex = {r: cg_[f"signals_rule_{r}"].sum() - kn[r] for r in (1, 2, 3, 4)}
    assert ex[3] + ex[4] > 2 * (ex[1] + ex[2]), "the family's cut-geometry excess is not on rules 3 and 4"
    pg.p(f"On charts with no special cause in the interval, {n(fb.at['total', 'subgroups'], 'family: routine subgroups in scope', was='10,369')} routine subgroups raised {n(fb.at['total', 'signals'], 'family: signals', was='368')} signals against "
         f"{n(fb.at['total', 'es'], 'family: expected signals', was='327')} expected, {n(fb.at['total', 'ratio'], 'family: observed over expected', '{:.2f}', was='1.13')} times (95% interval {n(fb.at['total', 'lo'], 'family: interval low', '{:.2f}', was='1.01')} to {n(fb.at['total', 'hi'], 'family: interval high', '{:.2f}', was='1.25')}). "
         f"By class: formed {n(fb.at['formed', 'ratio'], 'family formed: observed over expected', '{:.2f}', was='0.80')} ({n(fb.at['formed', 'signals'], 'family formed: signals', was='151')} on {n(fb.at['formed', 'subgroups'], 'family formed: subgroups', was='6,313')}; interval "
         f"{n(fb.at['formed', 'lo'], 'family formed: interval low', '{:.2f}', was='0.68')} to {n(fb.at['formed', 'hi'], 'family formed: interval high', '{:.2f}', was='0.94')}), below its band for the reason the plant's three-way charts are (Section 3); "
         f"hole diameter {n(fb.at['hole diameter', 'ratio'], 'family hole diameter: observed over expected', '{:.2f}', was='0.40')} on {n(fb.at['hole diameter', 'subgroups'], 'family hole diameter: subgroups', was='296')} subgroups, inside chance "
         f"({n(fb.at['hole diameter', 'lo'], 'family hole diameter: interval low', '{:.2f}', was='0.08')} to {n(fb.at['hole diameter', 'hi'], 'family hole diameter: interval high', '{:.2f}', was='1.16')}); and cut geometry "
         f"{n(fb.at['cut geometry', 'ratio'], 'family cut geometry: observed over expected', '{:.2f}', was='1.64')} ({n(fb.at['cut geometry', 'signals'], 'family cut geometry: signals', was='214')} on {n(fb.at['cut geometry', 'subgroups'], 'family cut geometry: subgroups', was='3,760')}; interval "
         f"{n(fb.at['cut geometry', 'lo'], 'family cut geometry: interval low', '{:.2f}', was='1.43')} to {n(fb.at['cut geometry', 'hi'], 'family cut geometry: interval high', '{:.2f}', was='1.88')}), above its band beyond chance. "
         "The excess is on rules 3 and 4, as on the plant's X-bar and R charts.")
    ff2 = fb.loc[["formed", "cut geometry", "hole diameter", "total"]].reset_index().rename(columns={"index": "cls"})
    for r in ff2.itertuples():
        for col, lab in (("observed per 100", "observed per 100"), ("expected per 100", "expected per 100"), ("ratio", "observed over expected"), ("lo", "interval low"), ("hi", "interval high")):
            pg.figval(103, f"{ff2.at[r.Index, col]:.2f}", f"family {lab}, {r.cls}")
    pg.figure(FIG.family_signals(ff2, {"formed": (0.9, 1.4), "cut geometry": (0.9, 1.4), "hole diameter": (0.9, 1.5)}), "Figure 103: The family's signals against expectation by class",
              f"The family's 20 measured charts with no special cause in the interval, {fb.at['total', 'subgroups']:,.0f} of {int(fsr['routine_subgroups'].sum()):,} routine subgroups; expectation at each chart's own baseline size and rules.")

    pg.h3("family-variance", "6.3 Variance structure")
    put(mv_bc)
    fformed = fam_cif[fam_cif["characteristic_type"].isin(["formed height", "bend angle"])]
    fitted = fformed["characteristic_id"].isin(cf["characteristic_id"])
    ccn = query("select characteristic_id, part_id, count(*) n from marts.mart_coil_change_points where family_part and certificate_thickness_mm is not null and certificate_hardness_hrb is not null group by 1, 2").set_index("characteristic_id")
    unfit = ccn.reindex(fformed.loc[~fitted, "characteristic_id"])
    assert unfit["n"].max() < 20 and unfit["part_id"].nunique() == 1 and unfit["n"].nunique() == 1, "the formed characteristics without a fit differ from the stated reason"
    pg.p(f"The coil effect is predictable from the certificate on the {n(int(fitted.sum()), 'mart_coil_fit: family formed characteristics with a fit', was='7')} of the family's {n(len(fformed), 'mart_charts_in_force: family formed characteristics', was='12')} formed characteristics with a fit on record, as across the plant; the other "
         f"{wd(int((~fitted).sum()), 'mart_charts_in_force: family formed characteristics without a fit', was='five')}, all on {txt(unfit['part_id'].iloc[0], 'mart_coil_change_points.part_id, formed characteristics without a fit', was='P-15731')}, carry "
         f"{n(int(unfit['n'].iloc[0]), 'mart_coil_change_points: coil-change subgroups with a certificate, each formed characteristic without a fit', was='13')} coil-change subgroups in the year, fewer than the 20 the fit requires. On {txt(pick.characteristic_id, 'mart_coil_fit: family characteristic with R squared nearest the plant median', was='C-11333-05')} the fit is "
         f"{n(pick.per_mm_thickness, 'mart_coil_fit.per_mm_thickness', '{:.2f}', was='2.73')} mm of height per mm of certificate thickness and {n(pick.per_hrb, 'mart_coil_fit.per_hrb', '{:.4f}', was='-0.0094')} mm per HRB of hardness, R squared {n(pick.r_squared, 'mart_coil_fit.r_squared', '{:.3f}', was='0.814')}, on "
         f"{n(pick.coil_change_subgroups, 'mart_coil_fit.coil_change_subgroups', was='20')} coil-change subgroups over {n(pick.coils, 'mart_coil_fit.coils', was='9')} coils, with a residual of "
         f"{pct(pick.residual_sigma_share_of_tolerance, 'mart_coil_fit.residual_sigma_share_of_tolerance, C-11333-05', was='3.2%')} of tolerance against coil means that spread {pct(pick.coil_means_sigma_share_of_tolerance, 'mart_coil_fit.coil_means_sigma_share_of_tolerance, C-11333-05', was='9.3%')}.")
    put(mv_cf); put(mv_p1); put(mv_tw)

    pg.h3("family-per-stroke", "6.4 Per-stroke monitoring on PR-03")
    s3 = stops[stops["press_id"] == "PR-03"]; f3 = s3["finding_class"].value_counts()
    pe3 = pe[pe["press_id"] == "PR-03"]; sr3 = query("select sum(strokes) s, sum(stops_nothing_found) nf from marts.mart_per_stroke_stop_rates where period = 'record' and press_id = 'PR-03'").iloc[0]
    pg.p(f"The per-stroke charts stopped PR-03 {n(len(s3), 'mart_per_stroke_stops: PR-03 stops', was='97')} times in the year across every part it ran: {n(f3.get('slug pulling', 0), 'mart_per_stroke_stops: PR-03 slug pulling', was='34')} on slug pulling, "
         f"{n(f3.get('worn punch', 0), 'mart_per_stroke_stops: PR-03 worn punch', was='10')} on a worn punch, {n(f3.get('chipped punch', 0), 'mart_per_stroke_stops: PR-03 chipped punch', was='11')} on a chipped punch and {n(f3.get('nothing found', 0), 'mart_per_stroke_stops: PR-03 nothing found', was='42')} with nothing found. "
         f"The chipped punches were stopped at {n(pe3[pe3['chart'] == 'channel share']['strokes_exposed_per_stroke_charts'].max(), 'mart_parts_exposed: PR-03 channel-share chipped punches, strokes from onset (largest)', was='0')} strokes from the onset on "
         f"{n(int((pe3['chart'] == 'channel share').sum()), 'mart_parts_exposed: PR-03 chipped punches stopped by the channel-share chart', was='10')}, by the channel-share chart, and at {n(pe3[pe3['chart'] == 'EWMA on the total']['strokes_exposed_per_stroke_charts'].iloc[0], 'mart_parts_exposed: PR-03 EWMA chipped punch, strokes from onset', was='34')} strokes on the one the EWMA caught. "
         f"PR-03's nothing-found rate is {n(sr3.nf / (sr3.s / 1e6), 'mart_per_stroke_stop_rates: PR-03 nothing found per million strokes', '{:.2f}', was='2.21')} per million strokes against {n(sr_st.nf / (sr_st.s / 1e6), 'mart_per_stroke_stop_rates: nothing found per million strokes', '{:.2f}', was='1.02')} across the plant.")
    assert (pe3[pe3["chart"] == "channel share"]["strokes_exposed_per_stroke_charts"] == 0).all() and (pe3["chart"] == "EWMA on the total").sum() == 1
    t3s = s3.groupby(["finding_class", "chart"]).size().to_dict()
    for (fd, chname), v in sorted(t3s.items()):
        pg.figval(104, f"{v}", f"mart_per_stroke_stops: PR-03, {fd}, {chname}")
    pg.figure(FIG.stops_by_finding(t3s, ["slug pulling", "worn punch", "chipped punch", "nothing found"], ["EWMA on the total", "channel share"], name="d1_stops_pr03_by_finding_and_chart", alt="Stops on PR-03 by finding and chart", legend_above=True),
              "Figure 104: Stops on PR-03 by finding and chart", "Stops in the year on PR-03 across every part it ran, by the toolmaker's finding and the chart that stopped the press.")
    put(mv_13p); put(mv_13f)

    # ═══════════════ Appendix
    pg.h2("appendix", "Appendix")
    t6 = fam_cif.copy()
    t6["limits"] = [("" if pd.isna(bb) else f"{DISPLAY.get(bb, bb)}, {DAY(ef)} ({DISPLAY.get(tg, tg)})") for bb, ef, tg in zip(t6["basis"], t6["limits_effective_from"], t6["limits_trigger"])]
    t6["status"] = np.where(t6["in_baseline"], "in a baseline", np.where(t6["chart_type"] == "p", "", "in force"))
    t6["coil-change chart"] = [("" if pd.isna(cc_) else f"{cc_:.4f} ({l_:.4f} to {u_:.4f}), {int(k_)} coils") for cc_, l_, u_, k_ in zip(t6["coil_change_centre"], t6["coil_change_lcl"], t6["coil_change_ucl"], t6["coil_change_chart_coils"])]
    t6["grr"] = t6["pct_grr_of_tolerance"].astype(float); t6["restudy"] = t6["restudy_due"].map(DAY); t6["study"] = t6["study_date"].map(DAY); t6["freq"] = t6["frequency_minutes"].astype(float)
    t6["plan"] = t6["reaction_plan_signals"].fillna(""); t6["basis_"] = t6["study_basis"].fillna("")
    pg.table("A1. The family's charts in force at 30 June 2026", t6, {"characteristic_id": "Characteristic", "chart_type": "Chart", "limits": "Limits basis and date", "status": "Status", "gauge_id": "Gauge", "basis_": "Study basis", "study": "Study",
                                                                       "grr": "%GRR", "restudy": "Restudy due", "freq": "Check, minutes", "plan": "Reaction plan", "coil-change chart": "Coil-change chart"},
             {"%GRR": F1, "Check, minutes": F0}, note="The p charts carry no limit set of this kind. A hand gauge is covered by the latest study of its type at its press.")
    pg.table("A2. The family's characteristics: variance components, chart and gauge", fam,
             {"characteristic_id": "Characteristic", "characteristic_name": "Name", "routine_subgroups": "Routine subgroups", "coils": "Coils", "share_within": "Within", "share_between_subgroups_in_coil": "Between subgroups in a coil", "share_between_coils": "Between coils",
              "share_between_intervals": "Between intervals", "incoming_coil_share": "Incoming coil share", "trend_share": "Wear trend", "chart_type": "Chart", "gauge_id": "Gauge", "gauge_type": "Gauge type"},
             {"Routine subgroups": F0, "Coils": F0, "Within": P1, "Between subgroups in a coil": P1, "Between coils": P1, "Between intervals": P1, "Incoming coil share": P1, "Wear trend": P1},
             note="Shares of the routine record's variance over the year; the incoming coil share is on the coil-change subgroups before centring; the wear trend is on the hole diameter's subgroups with shots since sharpening known.")
    lh = ls[ls["family_part"]].copy(); lh["from"] = lh["effective_from"].map(DAY); lh["to"] = lh["effective_to"].map(DAY); lh["coil_changes_spanned"] = lh["coil_changes_spanned"].astype(float)
    pg.table("A3. The family's limit history, every limit set in the record", lh, {"characteristic_id": "Characteristic", "limit_set_id": "Limit set", "chart": "Chart", "from": "From", "to": "To", "trigger": "Trigger", "subgroups_used": "Subgroups used", "coil_changes_spanned": "Coil changes",
                                                                                   "verifications_passed": "Verified", "verifications_failed": "Failed", "routine_subgroups_charted": "Subgroups charted"},
             {"Subgroups used": F0, "Coil changes": F0, "Verified": F0, "Failed": F0, "Subgroups charted": F0})
    a4 = in_year.copy(); a4["from"] = a4["effective_from"].map(lambda v: pd.Timestamp(v).strftime("%d %B %Y %H:%M").lstrip("0")); a4["half"] = 3 * a4["sigma_of_means"]; a4["annotation"] = a4["annotation"].fillna("")
    a4["trigger_subgroups"] = a4["trigger_subgroups"].astype(float)
    pg.table("A4. C-15731-02's ten limit sets in the year", a4, {"limit_set_id": "Limit set", "from": "From", "trigger": "Trigger", "slope_per_100k_shots": "Slope, mm per 100,000 shots", "centre_line": "Centre at 0 shots, mm", "half": "Limits, plus and minus mm",
                                                                 "subgroups_used": "Subgroups used", "trigger_subgroups": "Recalculation trigger", "routine_subgroups_charted": "Subgroups charted", "annotation": "Verified"},
             {"Slope, mm per 100,000 shots": F4, "Centre at 0 shots, mm": F4, "Limits, plus and minus mm": F4, "Subgroups used": F0, "Recalculation trigger": F0, "Subgroups charted": F0},
             note="Every limit set in force on C-15731-02 between 1 July 2025 and 30 June 2026; LS-00292 was issued on 27 June 2025 and in force on 1 July.")
    ap = crit.groupby(["press_id", "characteristic_class"]).agg(n_=("characteristic_id", "count"), w=("share_within", "median"), s=("share_between_subgroups_in_coil", "median"), c=("share_between_coils", "median"), i=("share_between_intervals", "median")).reset_index()
    pg.table("A5. Variance components by press and class", ap, {"press_id": "Press", "characteristic_class": "Class", "n_": "Characteristics", "w": "Within", "s": "Between subgroups in a coil", "c": "Between coils", "i": "Between intervals"},
             {"Characteristics": F0, "Within": P1, "Between subgroups in a coil": P1, "Between coils": P1, "Between intervals": P1}, note="Critical characteristics and all flatness characteristics with 60 routine subgroups or more; medians.")
    tb = cc["table"].rename(columns={"count": "coils"})
    pg.table("A6. The coil-change chart's expectation by coils on record", tb, {"coils": "Coils on record", "points": "Points", "expected_per_100": "Expected per 100 coils", "observed_signals": "Signals", "observed_per_100": "Observed per 100 coils"},
             {"Coils on record": F0, "Points": F0, "Expected per 100 coils": F2, "Signals": F0, "Observed per 100 coils": F2},
             note="20 stands for 20 coils or more, on the previous 20. Expected by Monte Carlo on the record's lot structure (4,000 seeded replicates per point).")
    pg.raw(APPENDIX_FORMULAS)

    # ═══════════════ the page, assembled from the rendered blocks
    entries = dict(zip(keys, list(pg.body)))
    def find(snippet):
        hit = [k for k, v in entries.items() if snippet in v and k < appendix_key]
        assert len(hit) == 1, (snippet, len(hit))
        return hit[0]
    appendix_key = next(k for k, v in entries.items() if v.startswith('<h2 id="appendix"'))

    def new(html):
        pg.body.append(html); entries[keys[-1]] = html
        return keys[-1]

    def edit(k, old, new_):
        assert entries[k].count(old) == 1, (old, entries[k][:80]); entries[k] = entries[k].replace(old, new_)

    def h(level, anchor, title):
        return new(f'<h{level} id="{anchor}">{title}</h{level}>')
    B = {name: find(snip) for name, snip in {
        "overview": "active SPC charts on", "fig_classes": "Figure 1: Active SPC charts", "perf_special": "How the charts performed.</strong>",
        "perf_take": "Takeaway: every special cause in the record", "tab_special": "Special causes caught in the year, by the chart", "perf_class": "On the second job",
        "fig_class_signals": "Signals against expectation by characteristic class", "perf_false": "False alarms.</strong>", "fig_load": "False-alarm load as designed",
        "actions_head": "Two actions.</strong>", "actions_ul": "they are re-issued as ten coil changes accrue", "s2_open": "Each class runs on the chart its variation calls for",
        "fig_press_class": "Active SPC charts by press and class", "limits_gov": "Limits are set once from a baseline", "limits_counts": "The record holds",
        "two_charts_p": "Two charts changed in the year", "two_charts_ul": "the regression chart's recalculation trigger shortened", "fig_recalc": "New limit sets by month and trigger",
        "dielog": "The die log carries dates without times", "fam_grr": "Gauge R&amp;R of the family", "arl": "The rules in force were chosen", "arl_take": "Takeaway: rules 1 to 4 catch",
        "tab_arl": "ARL by chart as designed", "fig_arl": "ARL curves by chart type", "verif": "Verification.</strong>", "verif_take": "Takeaway: verification fails on",
        "tab_verif": "Verifications of limits held across a die event", "obs": "Observed against expected.</strong>", "obs_ul": "run above expectation on rules 3 and 4:",
        "obs_take": "Takeaway: the excess on X-bar and R", "tab_obs": "Observed against expected signals by chart type", "fig_rules": "Signals by rule on long-held limits",
        "fig_press_obs": "Expected against observed false alarms by press", "bypress": "By press, ", "autocorr": "Autocorrelation.</strong>", "fig_autocorr": "In-control ARL against lag-1",
        "annual": "The annual review's three-way sets.</strong>", "recs": "Two changes are recommended", "var_open": "The chart for each class follows from where its variance lies",
        "var_ul": "Formed height and bend angle:</strong>", "fig_var": "Variance components by class", "fam_bc_p": "The family's characteristics show the plant's structure",
        "fam_bc_fig": "Between-coil share of variance by family", "coil_plant": "The coil effect and centring.</strong>", "fam_cf_fig": "Coil means against the certificate fit",
        "threeway": "The three-way design.</strong>", "fig_threeway": "False alarms per 100 points by three-way design", "fam_p1_p": "Phase I baselines.</strong>",
        "fam_p1_fig": "A Phase I baseline after a rebuild", "tw_plant": "The regression chart.</strong>", "fam_tw_p": "On C-15731-02 the line in force", "fam_tw_fig": "The regression chart on C-15731-02",
        "fig_wear": "Hole diameter wear rate by die", "s5_open": "The per-stroke charts catch a chipped punch", "s5_design": "The design.</strong> The total is autocorrelated",
        "s5_chip": "A chipped punch drops the total", "fig_ewma": "EWMA ARL1 against shift size", "s5_record": "The record.</strong> The charts stopped",
        "fig_stops": "Stops by the per-stroke charts, by finding and chart", "fig_13": "The 13 May stop on D-1333-C", "p_13": "On 13 May 2026 the EWMA on PR-03",
        "s5_parts": "Parts exposed.</strong>", "fig_parts": "Parts exposed per chipped punch", "fam_intro": "are followed here through the same four headings",
        "fam_overview": "The family's three parts carry", "fam_limits": "limit sets were issued on the family's charts", "fam_fixtures": "measured charts run on the part's own check fixture",
        "fam_special": "The family's charts caught every special cause", "fam_verif": "Verifications on the three dies", "fam_take": "Takeaway: the family's special causes",
        "fam_table": "Special causes caught on the family", "fam_rates": "routine subgroups raised", "fam_fig": "The family's signals against expectation by class",
        "fam_coil": "The coil effect is predictable from the certificate on the", "fam_ps": "The per-stroke charts stopped PR-03", "fam_ps_fig": "Stops on PR-03 by finding and chart"}.items()}
    # cross-references to the new numbering, and the run-in heads
    edit(B["perf_class"], "(Sections 3 and 4)", "(2.3 and 2.4)")
    edit(B["dielog"], "the wear rates in Section 4", "the wear rates in 2.4")
    edit(B["obs_ul"], "(Section 4)", "(2.4)")
    edit(B["fam_rates"], "(Section 3)", "(2.3)")
    edit(B["actions_ul"], "accrue (Section 3).", "accrue (2.2).")
    edit(B["s5_open"], "<p>", "<p><strong>Per-stroke charts.</strong> ")
    edit(B["fam_p1_p"], "<strong>Phase I baselines.</strong> ", "")
    edit(B["fam_ps"], "<p>", "<p><strong>Per-stroke charts on PR-03.</strong> ")
    first = keys[0]; assert entries[first].startswith("<style>")
    first_new = nxt[0]
    order = [first]
    order += [h(2, "exec-summary", "1. Executive Summary")]
    n_sub = int(query("select count(*) n from staging.stg_spc__subgroups where sample_time >= '2025-07-01' and sample_time < '2026-07-01'")["n"].iloc[0])
    order.append(new(f"<p>This report revalidates the plant's SPC chart design on the 1 July 2025 to 30 June 2026 record: {n(len(cif), 'mart_charts_in_force: charts', was='1,380')} active charts on {n(cif['press_id'].nunique(), 'mart_charts_in_force: presses', was='11')} presses, "
                     f"{n(n_sub, 'stg_spc__subgroups: subgroups in the year')} subgroups, and the per-stroke tonnage charts on {n(sr_st.s / 1e6, 'mart_per_stroke_stop_rates.strokes, the year, millions', '{:.1f}')} million strokes. "
                     "It asks four questions of the charts, in the order of Section 2: what is charted and on what chart type; how limits are set, held and verified; whether each chart signalled when the process changed and stayed quiet when it did not; and whether the variance structure of each characteristic class is the one its chart type assumes. "
                     "Performance is tested by comparing each chart's signals with the false-alarm rate its own rules and baseline size predict, on intervals with no special cause, so a chart type on the wrong variance structure shows as a rate far from expectation. "
                     "Variation is tested by decomposing each class into within-subgroup, between-subgroup, between-coil and wear components and checking the chart type against where the variance lies.</p>"))
    order.append(new(f"<p>Section 3 asks the same four questions of one part family, the three C110 copper parts on PR-03: {n(len(fam_cif), 'mart_charts_in_force: family charts', was='27')} charts on {wd(fam_cif['die_id'].nunique(), 'mart_charts_in_force: family dies', was='three')} dies and "
                     f"{wd(int(fam_cif.loc[fam_cif['gauge_type'] == 'check fixture', 'gauge_id'].nunique()), 'mart_charts_in_force: family check fixtures', was='three')} check fixtures. The plant is reported at summary level because {n(len(cif), 'mart_charts_in_force: charts', was='1,380')} charts cannot be shown one at a time; "
                     "the family is where every chart, baseline, limit set, fit and stop is shown in full, so the plant-level rates can be read against the records that produce them.</p>"))
    order.append(new(f"<p>On both scopes the chart selection holds. Every special cause in the record was caught by the chart designed for it and every alarm was closed by 30 June: on the plant, {n(len(ac), 'mart_signals: routine alarms with an assignable cause', was='1,657')} routine alarms on "
                     f"{n(ac['run_id'].nunique(), 'mart_signals: runs with a routine assignable-cause alarm', was='58')} runs with a cause found, {wd(len(soft), 'mart_signals: coil-change chart, assignable cause', was='one')} soft coil, {wd(len(wc), 'mart_signals: sharpening logged at the wrong count', was='one')} mislogged sharpening and "
                     f"{n(n_slug + n_worn + n_chip, 'mart_per_stroke_stops: stops on slug pulling, worn and chipped punches', was='427')} die and punch events stopped on the stroke ({{TAB:Special causes caught in the year, by the chart that caught them}}); on the family, one die at a new level, one fixture drifting, one rebuild and the soft coil ({{TAB:Special causes caught on the family in the year}}). "
                     "On intervals with no special cause the charts signalled close to their design rate on both scopes, with the same departures for the same reasons: on the plant, regression charts above expectation on level changes at sharpening that pass verification; on both, three-way charts below it because their limits carry the residual coil offset by design; "
                     "and the family's cut-geometry charts above it on rules 3 and 4 under limits held across sharpenings.</p>"))
    pf = []
    for c_ in ("formed", "cut geometry", "hole diameter", "flatness"):
        k_, e_ = float(byc.at[c_, "signals"]), float(byc.at[c_, "es"])
        pf.append({"cls": c_, "scope": "plant", "ratio": k_ / e_, "lo": stats.chi2.ppf(0.025, 2 * k_) / 2 / e_, "hi": stats.chi2.ppf(0.975, 2 * (k_ + 1)) / 2 / e_})
        if c_ in fb.index:
            pf.append({"cls": c_, "scope": "family", "ratio": float(fb.at[c_, "ratio"]), "lo": float(fb.at[c_, "lo"]), "hi": float(fb.at[c_, "hi"])})
    pf = pd.DataFrame(pf)
    for r_ in pf.itertuples():
        for col in ("ratio", "lo", "hi"):
            pg.figval(100, f"{getattr(r_, col):.2f}", f"observed over expected{'' if col == 'ratio' else ', 95% interval ' + ('low' if col == 'lo' else 'high')}, {r_.scope}, {r_.cls}")
    pg.figure(FIG.plant_family_ratios(pf, {"formed": (0.9, 1.4), "cut geometry": (0.9, 1.4), "hole diameter": (0.9, 1.5), "flatness": (0.9, 1.4)}), "Figure 100: Signals against expectation by characteristic class, plant and family",
              "Charts with no special cause in the interval; expectation at each chart's own baseline size and rules. Plant: 2.3, {FIG:Signals against expectation by characteristic class}; family: 3.3, {FIG:The family's signals against expectation by class}.")
    entries[keys[-1]] = pg.body[-1]; order.append(keys[-1])
    order.append(new(f"<p>The variance structure is the one each chart assumes on every measured class ({{FIG:Variance components by class}}), and the family's characteristics show it one at a time ({{FIG:Between-coil share of variance by family characteristic}}). "
                     f"The design load is {n(tot_w, 'false alarms per week as designed, plant', was='133')} false alarms a week across the plant; verification of limits held across {n(len(shp), 'mart_limit_verifications: sharpenings', was='408')} sharpenings failed on "
                     f"{pct(shp.mean(), 'share of sharpenings failed', was='8.1%')}, each a real level change. PR-03's per-stroke charts stopped it {n(len(s3), 'mart_per_stroke_stops: PR-03 stops', was='97')} times with the chipped punches caught at a median "
                     f"{n(pe3['strokes_exposed_per_stroke_charts'].median(), 'mart_parts_exposed: PR-03 chipped punches, median strokes from onset', was='0')} strokes from the onset; its nothing-found rate, {n(sr3.nf / (sr3.s / 1e6), 'mart_per_stroke_stop_rates: PR-03 nothing found per million strokes', '{:.2f}', was='2.21')} per million strokes against "
                     f"{n(sr_st.nf / (sr_st.s / 1e6), 'mart_per_stroke_stop_rates: nothing found per million strokes', '{:.2f}', was='1.02')} for the plant, is the one family figure outside the plant's pattern.</p>"))
    order.append(new(f"<p>Two actions follow: the {n(int(rw['below_coil_change_minimum'].sum()), 'mart_limit_sets: three-way annual-review sets below the coil-change minimum', was='23')} three-way limit sets issued at the annual review on fewer than ten coil changes are re-issued as ten accrue, "
                     "and the regression charts' verification criterion is tightened to 1.0 sigma with the line re-fitted at each planned trigger.</p>"))
    order += [h(2, "chart-summary", "2. SPC Chart Summary"), h(3, "overview", "2.1 Overview"),
              B["overview"], B["fig_classes"], B["fig_press_class"]]
    order += [new(f"<p>The per-stroke charts on tonnage, an EWMA on the total and a residual chart on each channel's share, run on every press beside the {n(len(cif), 'mart_charts_in_force: charts', was='1,380')} and are covered in 2.3.</p>"), B["s2_open"]]
    order += [h(3, "limits", "2.2 Chart Limits"), B["limits_gov"], B["limits_counts"], B["fig_recalc"], B["two_charts_p"], B["two_charts_ul"], B["dielog"], B["verif"], B["verif_take"], B["tab_verif"], B["annual"]]
    order += [h(3, "performance", "2.3 Performance"), B["perf_special"], B["perf_take"], B["tab_special"], B["perf_class"], B["fig_class_signals"], B["perf_false"], B["fig_load"],
              B["arl"], B["arl_take"], B["tab_arl"], B["fig_arl"], B["obs"], B["obs_ul"], B["obs_take"], B["tab_obs"], B["fig_rules"], B["fig_press_obs"], B["bypress"], B["autocorr"], B["fig_autocorr"],
              B["s5_open"], B["s5_design"], B["s5_chip"], B["fig_ewma"], B["s5_record"], B["fig_stops"], B["s5_parts"], B["fig_parts"], new("<p><strong>Actions.</strong></p>"), B["actions_ul"]]
    order += [h(3, "variation", "2.4 Variation"), B["var_open"], B["var_ul"], B["fig_var"], B["coil_plant"], B["threeway"], B["fig_threeway"], B["tw_plant"], B["fig_wear"]]
    order += [h(2, "family", "3. Part Family"), new("<p>The three C110 copper parts on PR-03 (P-11333 on D-1333-C, P-15731 on D-5731-A, P-14026 on D-4026-A) are followed through the same four headings as the plant.</p>"),
              h(3, "family-overview", "3.1 Overview"), B["fam_overview"], B["fam_fixtures"], B["fam_grr"],
              h(3, "family-limits", "3.2 Chart Limits"), B["fam_limits"], B["fam_verif"], B["fam_p1_p"], B["fam_p1_fig"], B["fam_tw_p"],
              h(3, "family-performance", "3.3 Performance"), B["fam_special"], B["fam_take"], B["fam_table"], B["fam_rates"], B["fam_fig"], B["fam_ps"], B["fam_ps_fig"], B["p_13"], B["fig_13"],
              h(3, "family-variation", "3.4 Variation"), B["fam_bc_p"], B["fam_bc_fig"], B["fam_coil"], B["fam_cf_fig"], new("<p>C-15731-02's chart carries the wear trend as its centre line:</p>"), B["fam_tw_fig"]]
    order += [k for k in keys if appendix_key <= k < first_new]          # the appendix, as built
    dropped = {B["actions_head"], B["fam_intro"], B["recs"]} | {k for k in keys if k < appendix_key and entries[k].startswith(("<h2", "<h3"))}
    used = set(order)
    assert len(used) == len(order), "a block placed twice"
    lost = [k for k in keys if k not in used and k not in dropped]
    assert not lost, [entries[k][:80] for k in lost]
    rows = list(pg.trace)
    assert not [r for r, k in rows if k in dropped and k != B["recs"]], "a dropped block carries traced numbers"
    rows = [(r, k) for r, k in rows if k not in dropped]
    label, pos = {}, {}
    cur = ""
    for i, k in enumerate(order):
        m_ = re.match(r'<h[23] id="[^"]+">([^<]+)</h[23]>', entries[k])
        if m_:
            cur = m_.group(1)
        label[k], pos[k] = cur, i
    pg.body = [entries[k] for k in order]
    pg.trace = [((r[0] if r[0].startswith("Figure ") else label[k]),) + tuple(r[1:]) for r, k in sorted(rows, key=lambda x: pos[x[1]])]
    for kind in ("Figure", "Table"):
        mp = {}
        for blk in pg.body:
            for m_ in re.finditer(f"chart-title'>{kind} (\\d+):", blk):
                mp.setdefault(int(m_.group(1)), len(mp) + 1)
        pg.body = [re.sub(f"(chart-title'>{kind} )(\\d+)(:)", lambda m_: f"{m_.group(1)}{mp[int(m_.group(2))]}{m_.group(3)}", blk) for blk in pg.body]
        pg.trace = [((f"{kind} {mp[int(t[0].split()[1])]}" if t[0].startswith(kind + " ") else t[0]),) + tuple(t[1:]) for t in pg.trace]
        if kind == "Figure":
            assert mp[16] == REGRESSION_FIGURE, f"the regression chart is Figure {mp[16]}, not {REGRESSION_FIGURE}"
    def resolve(m_):
        kind, title = m_.group(1), m_.group(2)
        hits = {x for blk in pg.body for x in re.findall(f"chart-title'>{'Figure' if kind == 'FIG' else 'Table'} (\\d+): " + re.escape(title) + "</div>", blk)}
        assert len(hits) == 1, (title, hits)
        return f"{'Figure' if kind == 'FIG' else 'Table'} {hits.pop()}"
    pg.body = [re.sub(r"\{(FIG|TAB):([^}]+)\}", resolve, blk) for blk in pg.body]
    assert not any("{FIG:" in blk or "{TAB:" in blk for blk in pg.body)
    toc = [("exec-summary", "1. Executive Summary"), ("chart-summary", "2. SPC Chart Summary"), ("overview", "2.1 Overview", "sub"), ("limits", "2.2 Chart Limits", "sub"), ("performance", "2.3 Performance", "sub"), ("variation", "2.4 Variation", "sub"),
           ("family", "3. Part Family"), ("family-overview", "3.1 Overview", "sub"), ("family-limits", "3.2 Chart Limits", "sub"), ("family-performance", "3.3 Performance", "sub"), ("family-variation", "3.4 Variation", "sub"), ("appendix", "Appendix")]
    html = S.report_shell("Control Chart Design", "Revalidation on the July 2025 to June 2026 record", "July 2026", "\n".join(pg.body), toc)
    out = S.DOCS / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / "control_chart_design.html").write_text(html, encoding="utf8", newline="\n")
    trace, off = pg.check()
    return html, trace, off, pg.figures


APPENDIX_FORMULAS = """<h3 id="formulas">A7. Formulas</h3>
<ul>
<li><strong>Pooled within-subgroup sigma:</strong> the square root of the mean of the subgroup variances. <strong>Between/within sigma</strong> on three-way charts: the within sigma from the average range (R-bar over d2, d2 = 2.326 for five pieces) combined with the between-subgroup sigma from the average moving range of subgroup means (MR-bar over 1.128, less the within share of a subgroup mean, not below zero).</li>
<li><strong>Three-way chart constants:</strong> individuals limits at the centre line plus and minus three times the standard deviation of the baseline subgroup means; moving-range limit at D4 = 3.267 times the average moving range; range limit at D4 = 2.114 times the average range; X-bar and R limits at the centre line plus and minus A2 = 0.577 times the average range.</li>
<li><strong>Regression chart (Mandel, 1969):</strong> centre line: the least-squares line of subgroup means on shots since sharpening, &#375;(s) = a + b&middot;s. A baseline fits the line on its 25 subgroups together with up to 200 of the die's earlier subgroups, and &sigma;<sub>e</sub> is the standard deviation of those subgroup means about the line. Limits: &#375;(s) &plusmn; 3&middot;&sigma;<sub>e</sub> on the means, and D4 times the average range on the ranges. At each passed verification a and b are re-fitted on the die's last four sharpening intervals (up to 400 subgroups) and &sigma;<sub>e</sub> is held; a failed verification starts a new baseline and a new &sigma;<sub>e</sub>. Cpk is taken on the standard deviation of the individual readings about a line fitted to the period's own subgroups with the shot count known, and on the period's mean against the nearer tolerance limit; Ppk carries the wear over the interval.</li>
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
