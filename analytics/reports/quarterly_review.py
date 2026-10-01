"""Quarterly Capability & SPC Review, Q2 2026. Reads the marts, computes the expected rates with the method of the control
chart design study (analytics.chart_performance), builds the figures and writes docs/reports/spc_quarterly_review_2026_q2.html
and the table of every number in the body with the mart it is read from and the value in the page text."""
import numpy as np
import pandas as pd
from scipy import stats

from analytics.data import query
from analytics.chart_performance import arl as A
from analytics.reports import design_figures as DFIG
from analytics.reports import review_figures as FIG
from analytics.reports.control_chart_design import REPORT_CLASS, expected_rate
from analytics.reports.page import DAY, F0, F1, F2, P1, Page
from analytics.style import style as S

LV = ["level after sharpening", "level after the rebuild"]
D1_LINK = '<a href="control_chart_design.html">the control chart design study</a>'
CHART_ROW = {"Xbar-R": "X-bar and R", "three-way (I-MR-R)": "three-way", "tool-wear": "regression"}
SHORT = {"level after sharpening": "level change", "level after the rebuild": "level after rebuild", "fixture drift": "fixture drift", "strip misfeed": "strip misfeed",
         "slug pulling": "slug pull", "gauge zero": "gauge zero", "lubricant": "lubricant", "soft coil": "soft coil", "sharpening logged at the wrong count": "wrong count"}


def pci(k, e):
    return (stats.chi2.ppf(0.025, 2 * k) / 2 / e if k > 0 else 0.0), stats.chi2.ppf(0.975, 2 * (k + 1)) / 2 / e


def build():
    pg = Page(); n, pct, txt, wd = pg.num, pg.pct, pg.text, pg.word
    fno = [0]

    def F(title):
        fno[0] += 1
        return f"Figure {fno[0]}: {title}"

    # ═══════════════ read once
    sig = query("select * from marts.mart_signals where in_quarter order by raised_at, alarm_id")
    cif = query("select * from marts.mart_charts_in_force order by characteristic_id"); cif["cls"] = cif["characteristic_type"].map(REPORT_CLASS)
    var = cif[cif["data_type"] == "variable"]
    sr = query("select * from marts.mart_signal_rates where period = 'quarter' order by characteristic_id, press_id, chart, baseline_subgroups")
    sr["es"] = [expected_rate(c, b) * s for c, b, s in zip(sr["chart"], sr["baseline_subgroups"], sr["subgroups_in_scope"])]
    sr["cls"] = sr["characteristic_id"].map(cif.set_index("characteristic_id")["cls"]); assert sr["cls"].notna().all()
    cap_all = query("select * from marts.mart_capability order by period, characteristic_id"); cap_all["cls"] = cap_all["characteristic_type"].map(REPORT_CLASS)
    crit_ids = set(query("select characteristic_id from staging.stg_spc__characteristics where critical")["characteristic_id"]); cap_all["critical"] = cap_all["characteristic_id"].isin(crit_ids)
    cap = cap_all[cap_all["period"] == "quarter"].copy(); ccap = cap[cap["critical"]]
    assert set(cap.loc[~cap["critical"], "cls"]) == {"flatness"}
    vca = query("select * from marts.mart_variance_components")
    stp = query("select * from marts.mart_per_stroke_stops where in_quarter order by stopped_at"); stf = stp[stp["finding_class"] != "nothing found"]
    srq = query("select * from marts.mart_per_stroke_stop_rates where period = 'quarter' order by press_id")
    fpa = query("select * from marts.mart_first_piece_approvals where in_quarter order by first_piece_at"); held = fpa[fpa["held"]]; passed = fpa[~fpa["held"]]
    design = query("select parameter, value from marts.mart_chart_design").set_index("parameter")["value"]
    presses = query("select press_id, load_cell_channels from staging.stg_erp__presses order by press_id")

    # the routine charts' signals on the control chart design study's basis
    rt = sig[(sig["subgroup_type"] == "routine") & (sig["chart"] != "coil-change means")]
    ac = rt[rt["assignable_cause"]].copy()
    ac["event"] = np.where(ac["cause_code"].isin(LV), ac["die_id"] + "|" + ac["sharpening_interval_no"].astype(int).astype(str) + "|" + ac["cause_code"], ac["run_id"] + "|" + ac["cause_code"])
    ac = ac.sort_values(["raised_at", "alarm_id"]); ac["first"] = ac["subgroup_id"] == ac["event"].map(ac.groupby("event")["subgroup_id"].first())
    n_ev = ac["event"].nunique(); n_fol = len(ac) - n_ev; n_nc = int((~rt["assignable_cause"]).sum())
    ccs = sig[sig["chart"] == "coil-change means"]; soft = ccs[ccs["assignable_cause"]]
    other = sig[(sig["subgroup_type"] != "routine") & (sig["chart"] != "coil-change means")]; wc = other[other["assignable_cause"]]
    assert list(wc["cause_code"]) == ["sharpening logged at the wrong count"] and len(soft) == 1
    allc = sig[sig["assignable_cause"]].copy()
    allc["event"] = np.where(allc["cause_code"].isin(LV), allc["die_id"] + "|" + allc["sharpening_interval_no"].fillna(-1).astype(int).astype(str) + "|" + allc["cause_code"], allc["run_id"] + "|" + allc["cause_code"])
    n_sc = allc["event"].nunique(); assert n_sc == n_ev + len(soft) + len(wc)
    assert sig["closed_at"].notna().all() and pd.Timestamp(sig["closed_at"].max()) < pd.Timestamp("2026-07-01") and pd.Timestamp(stp["cleared_at"].max()) < pd.Timestamp("2026-07-01")
    tot_s, tot_e = sr["signals_any_rule"].sum(), sr["es"].sum()
    held_n, starts = len(held), len(fpa)

    # measurement gating: where each subgroup recorded against a gauge away falls against the gauge's dates out and back
    aw = query("""select h.subgroup_id, h.gauge_id, h.characteristic_id, h.sample_time, g.out_of_service_from o, g.back_in_service b, cast(r.actual_start as date) rs
                  from intermediate.int_characteristic_history h join intermediate.int_run_shots r using (run_id)
                  join intermediate.int_gauge_status g on g.gauge_id = h.gauge_id and cast(h.sample_time as date) between g.out_of_service_from and coalesce(g.back_in_service, date '2100-01-01')
                  where h.gauge_out_of_service and h.in_quarter""")
    dd = pd.to_datetime(aw["sample_time"]).dt.normalize()
    aw["where"] = np.where(dd == pd.to_datetime(aw["o"]), "removal day", np.where(dd == pd.to_datetime(aw["b"]), "return day", "between"))
    between = aw[aw["where"] == "between"]; retday = aw[aw["where"] == "return day"]
    assert (pd.to_datetime(between["rs"]) <= pd.to_datetime(between["o"])).all() and not between["subgroup_id"].isin(query("select subgroup_id from marts.mart_signals")["subgroup_id"]).any()
    assert not aw["subgroup_id"].isin(query("select subgroup_id from marts.mart_phase1_baseline_subgroups")["subgroup_id"]).any()
    gq = query("select * from marts.mart_gauge_quarter_end where quarter_end = cast('2026-06-30' as date)")
    out_now = set(gq[gq["past_due"] | gq["away_for_calibration"]]["gauge_id"])
    on_out = int(var["gauge_id"].isin(out_now).sum())
    meas_head = (f"{n(len(between), 'int_characteristic_history with int_gauge_status: subgroups recorded strictly between a gauge removal and its return', was='9')} subgroups, on "
                 f"{wd(between['gauge_id'].nunique(), 'gauges with a subgroup recorded while away', was='two')} gauges, were recorded while the gauge was away, all on runs begun before the removal, and none signaled; "
                 "no chart took limits from a gauge out of service")
    meas_ret = f"The record dates a gauge's return without a time, so {n(len(retday), 'subgroups on the return day of a gauge', was='252')} subgroups on return days cannot be placed before or after it"

    pg.raw("<style>.subsection { margin: 34px 0 14px; border-left: 3px solid #54C0E8; padding-left: 12px; } "
           ".subsection-label { font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: #8093A4; font-weight: 700; margin-bottom: 2px; } "
           ".subsection h3 { font-size: 16px; font-weight: 600; letter-spacing: .2px; margin: 0; } "
           "main.content > h2#summary { margin-top: 0; }</style>")

    # ═══════════════ 2. Capability Review (built first, the summary is written last)
    body_summary_at = len(pg.body)
    pg.h2("capability", "2. Capability Review")
    below = cap[cap["ppk"] < 1.33].copy()
    assert below["critical"].all() and set(below["cls"]) == {"formed", "hole diameter"}
    pg.p(f"Capability held through the quarter on all but {wd(len(below), 'mart_capability: below 1.33, quarter', was='seven')} critical characteristics. "
         f"{n(len(ccap), 'mart_capability: critical characteristics with 60 routine subgroups or more, quarter', was='100')} critical characteristics had 60 or more routine subgroups in the quarter; "
         f"{n(int((ccap['ppk'] >= 1.33).sum()), 'mart_capability: critical characteristics at or above 1.33, quarter', was='93')} ran at or above Ppk 1.33, and the other {wd(len(below), 'mart_capability: below 1.33, quarter', was='seven')}, "
         f"{wd(int((below['cls'] == 'formed').sum()), 'below 1.33, formed', was='six')} formed characteristics and {wd(int((below['cls'] == 'hole diameter').sum()), 'below 1.33, hole diameter', was='one')} hole diameter, ran between "
         f"{n(below['ppk'].min(), 'mart_capability.ppk, below 1.33, lowest', '{:.2f}', was='1.23')} and {n(below['ppk'].max(), 'mart_capability.ppk, below 1.33, highest', '{:.2f}', was='1.32')}.")
    for r in cap.itertuples():
        pg.figval(fno[0] + 1, f"{r.ppk:.2f}", f"mart_capability.ppk, {r.characteristic_id}")
    pg.figure(FIG.ppk_by_class(cap[["characteristic_id", "cls", "ppk"]]), F("Ppk by class, Q2 '26"))
    gap = cap.groupby("cls")["cpk_less_ppk"].median()
    assert abs(gap["cut geometry"]) < 0.02 and abs(gap["flatness"]) < 0.02
    lowc = cap[cap["cpk"] < 1.33]; assert len(lowc) == 1 and float(lowc["ppk"].iloc[0]) < 1.33
    pg.p(f"Cpk sits close to Ppk on cut geometry and flatness, and above it by {n(gap['formed'], 'mart_capability.cpk_less_ppk, formed, median', '{:.2f}', was='0.09')} on formed characteristics and "
         f"{n(gap['hole diameter'], 'mart_capability.cpk_less_ppk, hole diameter, median', '{:.2f}', was='0.38')} on hole diameters, as expected given the coil offset left after centering and the wear across the sharpening interval. "
         f"One characteristic, {txt(lowc['characteristic_id'].iloc[0], 'mart_capability: the characteristic with Cpk under 1.33, quarter', was='C-16315-06')}, ran below 1.33 on Cpk, at "
         f"{n(float(lowc['cpk'].iloc[0]), 'mart_capability.cpk, that characteristic', '{:.2f}', was='1.31')}.")
    pg.figval(fno[0] + 1, f"{float(lowc['cpk'].iloc[0]):.2f}", f"mart_capability.cpk, {lowc['characteristic_id'].iloc[0]}, marked")
    pg.figure(FIG.cpk_against_ppk(cap), F("Cpk against Ppk by class, Q2 '26"))
    # each characteristic's largest variance component other than within subgroup, with Cpk where it is also below 1.33
    u = below.merge(vca[["characteristic_id", "within_share_wear_first", "between_subgroups_share_wear_first", "between_coils_share_wear_first", "wear_share"]], on="characteristic_id", how="left")
    COMP = {"between_subgroups_share_wear_first": "between subgroups", "between_coils_share_wear_first": "between coils", "wear_share": "tool wear"}
    assert u[list(COMP)].notna().all().all()
    u["largest"] = u[list(COMP)].idxmax(axis=1)
    u["label"] = [f"{COMP[c]} {100 * r[c]:.0f}%" + (f"; Cpk {r.cpk:.2f}" if r.cpk < 1.33 else "") for c, (_, r) in zip(u["largest"], u.iterrows())]
    u["customer"] = (u["ppk_high"] < 1.33) | (u["cpk"] < 1.33)
    cust = sorted(u.loc[u["customer"], "characteristic_id"]); assert cust == ["C-15731-06", "C-16315-06", "C-37007-06"], cust
    assert sorted(u.loc[u["ppk_high"] < 1.33, "characteristic_id"]) == ["C-15731-06", "C-37007-06"] and list(u.loc[u["cpk"] < 1.33, "characteristic_id"]) == ["C-16315-06"]
    u_sig = sig[sig["characteristic_id"].isin(u["characteristic_id"])]; assert not u_sig["assignable_cause"].any()
    pg.p(f"The {wd(len(u), 'mart_capability: below 1.33, quarter', was='seven')} characteristics that ran below 1.33 Ppk in Q2 are shown below, along with their 95% confidence intervals (the estimate of the true Ppk, given the small sample size in Q2). "
         "None carries a special cause: each is stable and falls short on its normal variation, so raising its Ppk takes a change to the process.")
    pg.p(f"{txt('Three', 'mart_capability: ppk_high under 1.33 or cpk under 1.33, quarter (3)', was='Three')} of these characteristics are flagged as needing to be reported to the customer: "
         f"{txt('C-15731-06, C-37007-06', 'mart_capability: ppk_high under 1.33, quarter', was='C-15731-06, C-37007-06')}, whose Q2 confidence intervals lie wholly below 1.33 Ppk, and "
         f"{txt('C-16315-06', 'mart_capability: cpk under 1.33, quarter', was='C-16315-06')}, whose Cpk is also below 1.33.")
    for r in u.itertuples():
        pg.figval(fno[0] + 1, f"{r.ppk:.2f} ({r.ppk_low:.2f} to {r.ppk_high:.2f}); {r.label}", f"mart_capability and mart_variance_components, {r.characteristic_id}")
    pg.figure(FIG.below_133(u[["characteristic_id", "ppk", "ppk_low", "ppk_high", "label", "customer"]]), F("Characteristics below Ppk 1.33"))
    at = query("""select c.characteristic_type t, s.sample_time, s.pieces, coalesce(s.attribute_count, 0) f from staging.stg_spc__subgroups s join marts.mart_charts_in_force c using (characteristic_id)
                  where c.chart_type = 'p' and s.sample_time >= '2025-07-01' and s.sample_time < '2026-07-01'""")
    at["quarter"] = pd.to_datetime(at["sample_time"]).dt.to_period("Q").astype(str)
    ag = at.groupby(["t", "quarter"]).agg(pieces=("pieces", "sum"), fails=("f", "sum")).reset_index()
    ag["per_million"] = 1e6 * ag["fails"] / ag["pieces"]; ag["lo"] = [1e6 * pci(k, m)[0] for k, m in zip(ag["fails"], ag["pieces"])]; ag["hi"] = [1e6 * pci(k, m)[1] for k, m in zip(ag["fails"], ag["pieces"])]
    for t_ in ("burr height", "hole diameter"):
        g_ = ag[ag["t"] == t_]; assert g_["lo"].max() <= g_["hi"].min(), f"{t_} quarters not overlapping"
    bq = ag[(ag["t"] == "burr height")].set_index("quarter"); pq = ag[(ag["t"] == "hole diameter")].set_index("quarter")
    pg.p(f"Burr and pin fail rates in Q2 ran within the yearly interval: burr at {n(bq.at['2026Q2', 'per_million'], 'stg_spc__subgroups: burr fails per million, 2026 Q2', was='1,346')} per million pieces checked this quarter against "
         f"{n(bq.drop('2026Q2')['per_million'].min(), 'burr fails per million, earlier quarters, lowest', was='1,160')} to {n(bq.drop('2026Q2')['per_million'].max(), 'burr fails per million, earlier quarters, highest', was='1,203')} before it, and pins at "
         f"{n(pq.at['2026Q2', 'per_million'], 'stg_spc__subgroups: pin fails per million, 2026 Q2', was='845')} against {n(pq.drop('2026Q2')['per_million'].min(), 'pin fails per million, earlier quarters, lowest', was='734')} to {n(pq.drop('2026Q2')['per_million'].max(), 'pin fails per million, earlier quarters, highest', was='1,062')}.")
    for r in ag.itertuples():
        pg.figval(fno[0] + 1, f"{r.per_million:.0f}", f"fails per million, {r.t}, {r.quarter} ({r.fails} of {r.pieces:,})")
    pg.figure(FIG.fails_by_quarter(ag), F("Burr and Pin Fail Rates, By Quarter"))

    # ═══════════════ 3. SPC Review
    def sub(anchor, title):
        num, name = title.split(" ", 1); pg.section = title
        pg.body.append(f'<div class="subsection" id="{anchor}"><div class="subsection-label">Section {num}</div><h3>{name}</h3></div>')
    pg.h2("spc", "3. SPC Review")
    sub("signals", "3.1 Signals and Causes")
    VT = {"Xbar-R": "X-bar and R", "three-way (I-MR-R)": "Three-way", "tool-wear": "Regression"}
    assert set(rt["chart_type"]) <= set(VT) and len(wc) == 1 and wc["chart_type"].iloc[0] == "tool-wear" and len(ccs[ccs["assignable_cause"]]) == len(soft)
    ev_type = ac.groupby("event").head(1)["chart_type"].value_counts()
    fl = []
    for t_, lab_ in VT.items():
        g_ = rt[rt["chart_type"] == t_]; a_ = int(ev_type.get(t_, 0))
        row_ = {"group": lab_, "a": a_, "o": int(g_["assignable_cause"].sum()) - a_, "b": int((~g_["assignable_cause"]).sum())}
        if t_ == "three-way (I-MR-R)":
            row_["a"] += len(soft); row_["b"] += len(ccs) - len(soft)
        if t_ == "tool-wear":
            row_["a"] += len(wc)
        fl.append(row_)
    fl.append({"group": "Per-stroke tonnage", "a": len(stf), "o": 0, "b": len(stp) - len(stf)})
    fl = pd.DataFrame(fl); fv = fl.iloc[:3]
    q_first, q_fol, q_nc = int(fv["a"].sum()), int(fv["o"].sum()), int(fv["b"].sum()); q_var = q_first + q_fol + q_nc
    assert q_first == n_sc and q_fol == n_fol and q_var == len(rt) + len(ccs) + len(wc)
    pg.p(f"In Q2, the variable characteristic charts (X-bar and R, three-way, and regression) raised {n(q_var, 'mart_signals: routine signals, coil-change chart signals and the wrong-count signal, quarter', was='3,396')} signals: "
         f"{n(q_first, 'mart_signals: first signals of a special-cause event on the variable charts, quarter', was='18')} were the first signal of a special-cause event, "
         f"{n(q_fol, 'mart_signals: follow-on signals, quarter', was='400')} followed on from those {n(q_first, 'mart_signals: first signals of a special-cause event on the variable charts, quarter', was='18')} events "
         f"(i.e., the charts kept producing signals from the same special cause event), and {n(q_nc, 'mart_signals: routine and coil-change signals with no assignable cause, quarter', was='2,978')} had no assignable cause. "
         f"The per-stroke tonnage charts signaled {n(len(stp), 'mart_per_stroke_stops: stops, quarter', was='139')} times, stopping the press each time, {n(len(stf), 'mart_per_stroke_stops: stops with a finding, quarter', was='112')} with a special cause finding and "
         f"{n(len(stp) - len(stf), 'mart_per_stroke_stops: nothing found, quarter', was='27')} with no assignable cause.")
    for r in fl.itertuples():
        pg.figval(fno[0] + 1, f"{r.a:,} / {r.o:,} / {r.b:,}", f"what the charts flagged: {r.group}")
    pg.figure(DFIG.flagged_bars(fl, "d2_charts_flagged", ("First signal of a special cause", "Follow-on signal", "No assignable cause"), alt="SPC chart signals and causes, Q2 2026", legend_y=-0.17), F("SPC Chart Signals and Causes, Q2 '26"))
    evq = allc.groupby("event").agg(first=("raised_at", "min"), chart_type=("chart_type", "first"), panel=("chart", "first"), cause=("cause_code", "first"), die=("die_id", "first")).reset_index()
    evq["row"] = evq["chart_type"].map(CHART_ROW); assert evq["row"].notna().all()
    evq["label"] = evq["cause"].map(SHORT)
    pg.p(f"The variable characteristic charts traced {n(n_sc, 'mart_signals: special-cause events on the variable charts, quarter (die events for level changes, runs otherwise)', was='18')} special causes across Q2, with their timeline laid out below.")
    for r in evq.itertuples():
        pg.figval(fno[0] + 1, pd.Timestamp(r.first).strftime("%d %b"), f"mart_signals: first signal, {r.event}")
    pg.figure(FIG.special_cause_timeline(evq[["first", "row", "label"]]), F("Special Causes Found at Variable Characteristic Charts"))
    cc_ = evq["cause"].value_counts()
    lvl_q = ac[ac["cause_code"].isin(LV)]; fx_q = ac[ac["cause_code"] == "fixture drift"]; oth_q = ac[ac["cause_code"].isin(["strip misfeed", "slug pulling", "gauge zero", "lubricant"])]
    e_lvl, e_fx, e_oth = lvl_q["event"].nunique(), fx_q["event"].nunique(), oth_q["event"].nunique()
    assert e_lvl + e_fx + e_oth + len(soft) + len(wc) == n_sc and e_lvl > e_oth > max(e_fx, len(soft), len(wc))
    gauge_of = cif.set_index("characteristic_id")["gauge_id"]

    def charts_of(df):
        have = set(df["chart_type"])
        return ", ".join(CHART_ROW[t_] for t_ in ("Xbar-R", "three-way (I-MR-R)", "tool-wear") if t_ in have)
    pg.p(f"{n(n_sc + len(stf), 'special-cause events on the variable charts and per-stroke stops with a finding, quarter', was='130')} signals were traced to a special cause over the quarter. "
         f"The variable characteristic charts most commonly found special causes related to a die at a new level after sharpening or rebuild ({n(e_lvl, 'mart_signals: level-change die events, quarter', was='9')}) "
         f"and faults related to strip misfeed, slug pull, gauge zeroing, or lubricant issues ({n(e_oth, 'mart_signals: runs, strip misfeed, slug pulling, gauge zero, lubricant, quarter', was='6')}).")
    ts_ = pd.DataFrame([
        {"what": "Die at a new level after sharpening or rebuild", "chart": txt(charts_of(lvl_q), 'mart_signals.chart_type, level-change signals, quarter'),
         "events": n(e_lvl, 'mart_signals: level-change die events, quarter', was='9'), "alarms": n(len(lvl_q), 'mart_signals: level-change signals, quarter')},
        {"what": f"Fixture drift ({txt(', '.join(sorted(set(gauge_of.reindex(fx_q['characteristic_id'])))), 'mart_charts_in_force.gauge_id, fixture drift signals', was='F-14026')})", "chart": txt(charts_of(fx_q), 'mart_signals.chart_type, fixture drift, quarter'),
         "events": n(e_fx, 'mart_signals: runs, fixture drift, quarter', was='1'), "alarms": n(len(fx_q), 'mart_signals: fixture drift signals, quarter', was='30')},
        {"what": "Strip misfeed, slug pulling, gauge zeroing, lubricant", "chart": txt(charts_of(oth_q), 'mart_signals.chart_type, other causes, quarter'),
         "events": n(e_oth, 'mart_signals: runs, strip misfeed, slug pulling, gauge zero, lubricant, quarter', was='6'), "alarms": n(len(oth_q), 'mart_signals: other-cause signals, quarter')},
        {"what": f"Soft coil ({txt(soft['characteristic_id'].iloc[0], 'mart_signals.characteristic_id, soft coil', was='C-15731-07')})", "chart": "three-way",
         "events": n(len(soft), 'mart_signals: soft coil, quarter', was='1'), "alarms": n(len(soft), 'mart_signals: soft coil signals, quarter', was='1')},
        {"what": f"Sharpening logged at the wrong count ({txt(wc['press_id'].iloc[0], 'mart_signals.press_id, sharpening logged at the wrong count', was='PR-06')})", "chart": txt(charts_of(wc), 'mart_signals.chart_type, wrong count', was='regression'),
         "events": n(len(wc), 'mart_signals: wrong count, quarter', was='1'), "alarms": n(len(wc), 'mart_signals: wrong-count signals, quarter', was='1')},
        {"what": "Slug pulling, worn and chipped punches", "chart": "per-stroke EWMA and channel share",
         "events": n(len(stf), 'mart_per_stroke_stops: stops with a finding, quarter', was='112'), "alarms": n(len(stf), 'mart_per_stroke_stops: stops with a finding, as signals, quarter', was='112')}])
    pg.body_table("Table 1: Special Causes With the Charts that Signaled Them", ts_, {"what": "What was caught", "chart": "Chart", "events": "Events", "alarms": "Alarms"}, bold_cols=("Events",))
    fc = stf["finding_class"].value_counts(); nf_q = stp[stp["finding_class"] == "nothing found"]; n3 = nf_q[nf_q["press_id"] == "PR-03"]
    pg.p(f"The per-stroke charts stopped the presses on {n(len(stp), 'mart_per_stroke_stops: stops, quarter', was='139')} signals across {n(srq['strokes'].sum() / 1e6, 'mart_per_stroke_stop_rates.strokes, quarter, millions', '{:.1f}', was='23.2')} million strokes in the quarter. "
         f"{n(len(stf), 'stops with a finding, quarter', was='112')} of these signals were found to have a special cause: {n(int(fc['slug pulling']), 'slug pulling, quarter', was='68')} ({pct(fc['slug pulling'] / len(stf), 'slug pulling share of stops with a finding, quarter', 0)}) due to slug pulling, "
         f"{n(int(fc['chipped punch']), 'chipped punch, quarter', was='23')} ({pct(fc['chipped punch'] / len(stf), 'chipped punch share of stops with a finding, quarter', 0)}) due to chipped punches and "
         f"{n(int(fc['worn punch']), 'worn punch, quarter', was='21')} ({pct(fc['worn punch'] / len(stf), 'worn punch share of stops with a finding, quarter', 0)}) due to worn punches. "
         f"PR-03 carried {n(len(n3), 'nothing found on PR-03, quarter', was='18')} of the {n(len(nf_q), 'nothing found, quarter', was='27')} ({pct(len(n3) / len(nf_q), 'nothing found on PR-03, share of the quarter', 0)}) signals with no assignable cause.")
    for r in srq.itertuples():
        pg.figval(fno[0] + 1, f"{int(r.stops)}", f"mart_per_stroke_stop_rates.stops, quarter, {r.press_id}")
    pg.figure(FIG.stops_by_press(srq), F("Per-stroke tonnage stops by finding, by press"))
    sub("expected", "3.2 Observed vs. Expectations")
    assert sr["signals_rule_3"].sum() + sr["signals_rule_4"].sum() > sr["signals_rule_1"].sum() + sr["signals_rule_2"].sum()
    sch = sr.groupby("chart").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum"))
    sch["observed per 100"] = 100 * sch["signals"] / sch["subgroups"]; sch["expected per 100"] = 100 * sch["es"] / sch["subgroups"]; sch["ratio"] = sch["signals"] / sch["es"]
    BAND = {"X-bar and R": (0.9, 1.4), "three-way": (0.9, 1.4), "tool-wear": (0.9, 1.5)}
    assert BAND["three-way"][0] <= sch.at["three-way", "ratio"] < 1.0 and sch.at["tool-wear", "ratio"] > BAND["tool-wear"][1]
    pg.p(f"Signals with no assignable cause ran at {n(tot_s / tot_e, 'observed over expected, quarter', '{:.2f}', was='1.23')} times the expected rate, broadly across the plant. "
         "The excess in the quarter was on rules 3 and 4 on the regression and X-bar and R charts. "
         "The three-way chart signals were at the bottom of the expected range, and the regression chart signals well above it, as expected and detailed in the "
         '<a href="control_chart_design.html">SPC Chart Design &amp; Performance</a> report.')
    sct = sch.loc[["X-bar and R", "three-way", "tool-wear"], ["observed per 100", "expected per 100", "ratio"]].reset_index()
    for r in sct.itertuples():
        pg.figval(fno[0] + 1, f"{r.ratio:.2f}", f"observed over expected, {r.chart}, quarter")
    pg.figure(DFIG.signals_by_chart(sct, {"X-bar and R": (0.9, 1.4), "three-way": (0.9, 1.4), "tool-wear": (0.9, 1.5)}, {"X-bar and R": "X-bar and R", "three-way": "Three-way", "tool-wear": "Regression"},
                                    name="d2_signals_against_expectation_by_chart"), F("Signals against expectation by chart type"))
    p1 = sr.groupby("press_id").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum")).reset_index()
    p1["observed per 100"] = 100 * p1["signals"] / p1["subgroups"]; p1["expected per 100"] = 100 * p1["es"] / p1["subgroups"]; p1["ratio"] = p1["signals"] / p1["es"]
    p1["low"] = [100 * pci(k, m)[0] for k, m in zip(p1["signals"], p1["subgroups"])]; p1["high"] = [100 * pci(k, m)[1] for k, m in zip(p1["signals"], p1["subgroups"])]
    top = p1.sort_values("ratio", ascending=False); assert list(top["press_id"].head(3)) == ["PR-04", "PR-11", "PR-03"] and list(top["press_id"].tail(2)) == ["PR-10", "PR-08"]
    pr_ = p1.set_index("press_id")["ratio"]
    pg.p(f"By press, signals with no assignable cause at PR-04, PR-11 and PR-03 ran furthest above expectation, at {n(pr_['PR-04'], 'observed over expected, PR-04', '{:.2f}', was='1.67')}, {n(pr_['PR-11'], 'observed over expected, PR-11', '{:.2f}', was='1.48')} and "
         f"{n(pr_['PR-03'], 'observed over expected, PR-03', '{:.2f}', was='1.41')} times, and PR-08 and PR-10 below it, at {n(pr_['PR-08'], 'observed over expected, PR-08', '{:.2f}', was='0.71')} and {n(pr_['PR-10'], 'observed over expected, PR-10', '{:.2f}', was='0.79')}.")
    pg.figure(FIG.observed_expected_by_press(p1), F("Signals with no assignable cause, observed vs. expected, by press"))
    sub("limits", "3.3 Control Limits")
    rq = query("select trigger, chart, cast(sum(limit_sets_in_quarter) as integer) n from marts.mart_limit_recalculations group by all having sum(limit_sets_in_quarter) > 0 order by 1, 2")
    rq["chart"] = rq["chart"].replace({"tool-wear": "regression"}); rq["trigger"] = rq["trigger"].replace({"tool-wear re-fit": "regression re-fit"})
    vq = query("select * from marts.mart_limit_verifications where in_quarter"); vq["chart"] = vq["chart"].replace({"tool-wear": "regression"})
    vt = vq.groupby("chart").agg(done=("verification_id", "size"), failed=("result", lambda s_: int((s_ == "failed").sum()))).reindex(["X-bar and R", "three-way", "regression"]).reset_index()
    bip = cif[cif["in_baseline"]].copy(); bip["days"] = (pd.Timestamp("2026-06-30") - pd.to_datetime(bip["baseline_started"]).dt.normalize()).dt.days
    c23 = bip.set_index("characteristic_id").loc["C-23264-03"]; c34 = bip.set_index("characteristic_id").loc["C-34479-05"]
    assert set(bip.loc[bip["days"] > 60, "characteristic_id"]) == {"C-23264-03", "C-34479-05"}
    pg.p(f"In Q2, {n(int(rq['n'].sum()), 'mart_limit_recalculations.limit_sets_in_quarter', was='53')} new limit sets were issued and "
         f"{n(int(vt['failed'].sum()), 'mart_limit_verifications: failed, quarter', was='13')} of {n(int(vt['done'].sum()), 'mart_limit_verifications: quarter', was='369')} verifications failed. "
         f"Two baselines are stale: C-23264-03 has been in baseline for {n(int(c23.days), 'mart_charts_in_force: days in baseline, C-23264-03', was='211')} days with {n(int(c23.baseline_subgroups_so_far), 'baseline subgroups so far, C-23264-03', was='21')} of 25 subgroups, "
         f"and C-34479-05 for {n(int(c34.days), 'mart_charts_in_force: days in baseline, C-34479-05', was='103')} days with {n(int(c34.baseline_subgroups_so_far), 'baseline subgroups so far, C-34479-05', was='38')} subgroups but "
         f"{wd(int(c34.baseline_coil_changes_so_far), 'baseline coil changes so far, C-34479-05', was='three')} of its {wd(design['three_way_baseline_coil_changes'], 'mart_chart_design.three_way_baseline_coil_changes', was='ten')} coil changes.")
    for r in rq.itertuples():
        pg.figval(fno[0] + 1, f"{r.n}", f"mart_limit_recalculations.limit_sets_in_quarter, {r.trigger}, {r.chart}")
    for r in vt.itertuples():
        pg.figval(fno[0] + 1, f"{r.failed} of {r.done}", f"mart_limit_verifications: failed of done, {r.chart}")
    pg.figure(FIG.limits_and_verifications(rq, vt), F("Control Limit Sets and Verifications, Q2 '26"))
    sub("measurement", "3.4 Measurement Systems")
    gsq = query("select * from marts.mart_gauge_studies where in_quarter order by study_date, gauge_id")
    gfx = gsq[gsq["gauge_type"] == "check fixture"].copy()
    band = (((gfx["pct_grr_of_tolerance"] >= 10) & (gfx["pct_grr_of_tolerance"] < 30)) | ((gfx["previous_pct_grr"] >= 10) & (gfx["previous_pct_grr"] < 30))) | (gfx["gauge_id"] == "F-14026")
    rest = gfx[~band]
    assert (rest["pct_grr_of_tolerance"] < 10).all()
    pg.p(f"There were {n(len(gfx), 'mart_gauge_studies: check fixture studies in the quarter', was='52')} fixture studies in the quarter. "
         f"{n(len(rest), 'fixture studies in the quarter under 10% at both studies, F-14026 aside', was='44')} ({pct(len(rest) / len(gfx), 'fixture studies under 10%, share', 0)}) had a gauge R&amp;R (%GRR) under the 10% threshold and were within "
         f"{n((rest['pct_grr_of_tolerance'] - rest['previous_pct_grr']).abs().max(), 'largest move of %GRR, those fixtures', '{:.1f}', was='2.8')} points of their previous study. "
         f"The {wd(len(gfx) - len(rest), 'fixture studies shown in the figure', was='eight')} studies that were above the 10% threshold are shown below.")
    f5 = gfx[band].copy(); f5["label"] = f5["gauge_id"] + " (" + f5["study_date"].map(lambda d_: pd.Timestamp(d_).strftime("%d %b").lstrip("0")) + ")"
    for r in f5.itertuples():
        pg.figval(fno[0] + 1, f"{r.previous_pct_grr:.1f} to {r.pct_grr_of_tolerance:.1f}", f"mart_gauge_studies: previous and this study, {r.label}")
    pg.figure(FIG.grr_before_after(f5), F("%GRR by Gauge, Studies Over 10% in Q2 '26"))

    # ═══════════════ 1. Summary, written last, placed first
    last_section = pg.section; pg.section = "1. Summary"
    summary = []
    summary.append('<h2 id="summary">1. Summary</h2>')
    mon = u[(u["ppk_high"] >= 1.33) & ~u["customer"]]; wholly = u[u["ppk_high"] < 1.33]; both = u[u["cpk"] < 1.33]
    assert len(mon) == 4 and len(wholly) == 2 and len(both) == 1 and len(mon) + len(wholly) + len(both) == len(u)
    g10 = gsq[gsq["pct_grr_of_tolerance"] >= 10]
    summary.append(f"<p>In Q2 2026, {n(int((ccap['ppk'] >= 1.33).sum()), 'critical at or above 1.33', was='93')} of {n(len(ccap), 'critical characteristics', was='100')} critical characteristics held above the Ppk threshold of 1.33. "
                   f"Of the {wd(len(u), 'mart_capability: below 1.33, quarter', was='seven')} that were below the Ppk threshold, {wd(len(mon), 'mart_capability: below 1.33 with ppk_high at or above 1.33 and cpk at or above 1.33, quarter', was='four')} had confidence intervals that extended over the threshold, and are flagged for monitoring. "
                   f"{txt('Three', 'mart_capability: ppk_high under 1.33 or cpk under 1.33, quarter (3)', was='Three')} were flagged as needing to be reported to the customers: {wd(len(wholly), 'mart_capability: ppk_high under 1.33, quarter', was='two')} had confidence intervals wholly under the Ppk threshold, "
                   f"and {wd(len(both), 'mart_capability: ppk and cpk under 1.33, quarter', was='one')} was under both the Ppk and Cpk threshold.</p>")
    summary.append(f"<p>Signals with no assignable cause ran slightly above expectations at {n(tot_s / tot_e, 'observed over expected, quarter', '{:.2f}', was='1.23')}x. "
                   f"100% of the {n(n_sc, 'special causes on the characteristic charts, all closed by 30 June', was='18')} special causes found on the characteristic chart signals were closed by the end of the quarter. "
                   f"{n(len(stf), 'per-stroke stops with a finding', was='112')} of the {n(len(stp), 'per-stroke stops, quarter', was='139')} ({pct(len(stf) / len(stp), 'per-stroke stops with a finding, share', 0)}) stops on the per-stroke tonnage charts found a special cause. "
                   f"{pct(len(g10) / len(gsq), 'mart_gauge_studies: studies in the quarter at or above 10% of tolerance, share (7 of 66)', 0, was='11%')} of gauge studies were above the 10% GRR threshold, all flagged for studies. "
                   f"{'No' if on_out == 0 else n(on_out, 'charts on a gauge out of service')} charts in the quarter set limits from a gauge that was out of service.</p>")
    tiles = [(f"{n(int((ccap['ppk'] >= 1.33).sum()), 'critical at or above 1.33', was='93')} of {n(len(ccap), 'critical characteristics', was='100')}", "critical characteristics above Ppk 1.33"),
             (f"{n(len(u[u['customer']]), 'mart_capability: ppk_high under 1.33 or cpk under 1.33, quarter', was='3')}", "characteristics flagged for reporting to customers"),
             (f"{n(tot_s / tot_e, 'observed over expected, quarter', '{:.2f}', was='1.23')}x", "signals without assignable cause against the expected rate"),
             (f"{n(n_sc, 'special causes on the characteristic charts', was='18')}", "special causes on the characteristic charts closed by end of quarter"),
             (f"{n(len(stf), 'per-stroke stops with a finding', was='112')} of {n(len(stp), 'per-stroke stops, quarter', was='139')}", "per-stroke tonnage stops with a special cause finding"),
             (f"{n(on_out, 'mart_charts_in_force with mart_gauge_quarter_end: charts on a gauge past due or away at 30 June', was='0')}", "charts on limits from an out of service gauge")]
    summary.append('<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:14px 0 24px;">' + "".join(
        f'<div style="border:1px solid #DDE3E8;border-radius:8px;padding:12px 14px;"><div style="font-size:24px;font-weight:700;color:{S.BRAND_BLUE};line-height:1.2;">{big}</div>'
        f'<div style="font-size:12.5px;color:#555;margin-top:4px;">{lab}</div></div>' for big, lab in tiles) + "</div>")
    for k_, blk in enumerate(summary):
        pg.body.insert(body_summary_at + k_, blk)
    pg.section = last_section

    toc = [("summary", "1. Summary"), ("capability", "2. Capability Review"),
           ("spc", "3. SPC Review"), ("signals", "3.1 Signals and Causes", "sub"), ("expected", "3.2 Observed vs. Expectations", "sub"), ("limits", "3.3 Control Limits", "sub"), ("measurement", "3.4 Measurement Systems", "sub")]
    import re
    ftitle = {}
    for blk in pg.body:
        for m_ in re.finditer(r"chart-title'>Figure (\d+): ([^<]+)</div>", blk):
            ftitle[int(m_.group(1))] = m_.group(2)
    pg.body = [re.sub(r"(chart-title'>)(?:Figure|Table) \d+: ", r"\1", blk) for blk in pg.body]
    assert not any(re.search(r"chart-title'>(?:Figure|Table) \d+", blk) for blk in pg.body)
    pg.trace[:] = [((f"Figure: {ftitle[int(t[0].split()[1])]}" if re.fullmatch(r"Figure \d+", t[0]) else t[0]),) + tuple(t[1:]) for t in pg.trace]
    html = S.report_shell("Quarterly Capability &amp; SPC Review, Q2 2026", "", "", "\n".join(pg.body), toc)
    out = S.DOCS / "reports"; out.mkdir(parents=True, exist_ok=True)
    (out / "spc_quarterly_review_2026_q2.html").write_text(html, encoding="utf8", newline="\n")
    trace, off = pg.check()
    return html, trace, off, pg.figures


if __name__ == "__main__":
    html, trace, off, nfig = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "quarterly_review_numbers.csv", index=False, lineterminator="\n")
    print(len(html), "characters;", len(trace), "numbers traced;", nfig, "figures;", len(off), "differ from the text")
    if len(off):
        print(off.to_string())
