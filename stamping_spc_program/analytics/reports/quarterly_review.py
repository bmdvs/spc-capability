"""Quarterly Capability & SPC Review, April to June 2026. Reads the marts, computes the expected rates with the method of
the control chart design study (analytics.chart_performance), builds the figures and writes
docs/reports/spc_quarterly_review_2026_q2.html, the quarter's signal log as CSV, and the table of every number in the body
with the mart it is read from and the value in the page text."""
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

    # ═══════════════ 2. Capability Review (built first, the summary is written last)
    body_summary_at = len(pg.body)
    pg.h2("capability", "2. Capability Review")
    below = cap[cap["ppk"] < 1.33].copy()
    assert below["critical"].all() and set(below["cls"]) == {"formed", "hole diameter"}
    pg.p(f"Capability held through the quarter on all but {wd(len(below), 'mart_capability: below 1.33, quarter', was='seven')} critical characteristics, and none of those carries a special cause.")
    pg.h3("where", "2.1 Where capability stands")
    pg.p(f"{n(int((ccap['ppk'] >= 1.33).sum()), 'mart_capability: critical characteristics at or above 1.33, quarter', was='93')} of {n(len(ccap), 'mart_capability: critical characteristics with 60 routine subgroups or more, quarter', was='100')} critical characteristics ran above Ppk 1.33; "
         f"the {wd(len(below), 'mart_capability: below 1.33, quarter', was='seven')} below are {wd(int((below['cls'] == 'formed').sum()), 'below 1.33, formed', was='six')} formed characteristics and {wd(int((below['cls'] == 'hole diameter').sum()), 'below 1.33, hole diameter', was='one')} hole diameter. "
         f"The {n(int((cap['cls'] == 'flatness').sum()), 'mart_capability: flatness characteristics, quarter', was='11')} flatness characteristics, reported on Ppu, all ran above it.")
    assert (cap.loc[cap["cls"] == "flatness", "ppk"] >= 1.33).all()
    for r in cap.itertuples():
        pg.figval(fno[0] + 1, f"{r.ppk:.2f}", f"mart_capability.ppk, {r.characteristic_id}")
    pg.figure(FIG.ppk_by_class(cap[["characteristic_id", "cls", "ppk"]]), F("Ppk by class"))
    pg.h3("design-explains", "2.2 What the chart design explains")
    gap = cap.groupby("cls")["cpk_less_ppk"].median()
    assert abs(gap["cut geometry"]) < 0.02 and abs(gap["flatness"]) < 0.02
    pg.p(f"Cpk sits close to Ppk on cut geometry and flatness, {n(gap['formed'], 'mart_capability.cpk_less_ppk, formed, median', '{:.2f}', was='0.09')} above on formed characteristics and "
         f"{n(gap['hole diameter'], 'mart_capability.cpk_less_ppk, hole diameter, median', '{:.2f}', was='0.38')} above on hole diameters: the coil offset left after centering and the wear over the sharpening interval, which the three-way and regression charts carry by design.")
    pg.figure(FIG.cpk_against_ppk(cap), F("Cpk against Ppk"))
    pg.h3("year", "2.3 Across the year")
    QS = ["2025 Q3", "2025 Q4", "2026 Q1", "2026 Q2"]
    qmed = cap_all[cap_all["period"].isin(QS)].groupby(["period", "cls"])["ppk"].median().reset_index().rename(columns={"period": "quarter"})
    qcnt = cap_all[cap_all["period"].isin(QS)].groupby("period").agg(population=("ppk", "size"), above=("ppk", lambda s: int((s >= 1.33).sum()))).reindex(QS).reset_index().rename(columns={"period": "quarter"})
    qcnt["below"] = qcnt["population"] - qcnt["above"]
    hd = qmed[qmed["cls"] == "hole diameter"].set_index("quarter")["ppk"]; fm = qmed[qmed["cls"] == "formed"].set_index("quarter")["ppk"]
    earlier = qcnt[qcnt["quarter"] != "2026 Q2"]["below"]
    pg.p(f"Capability held across the year, with formed characteristics steady at {n(fm.min(), 'mart_capability: formed median Ppk, lowest quarter', '{:.2f}', was='1.49')} to {n(fm.max(), 'mart_capability: formed median Ppk, highest quarter', '{:.2f}', was='1.51')}, "
         f"but hole diameters eased from {n(hd['2025 Q3'], 'mart_capability: hole diameter median Ppk, 2025 Q3', '{:.2f}', was='1.73')} to {n(hd['2026 Q2'], 'mart_capability: hole diameter median Ppk, 2026 Q2', '{:.2f}', was='1.63')} in the review quarter, "
         f"and the count below 1.33 rose to {n(int(qcnt.set_index('quarter').at['2026 Q2', 'below']), 'mart_capability: below 1.33, 2026 Q2', was='7')}, from {n(int(earlier.min()), 'mart_capability: below 1.33, earlier quarters, fewest', was='3')} to {n(int(earlier.max()), 'mart_capability: below 1.33, earlier quarters, most', was='4')} in the earlier quarters.")
    for r in qcnt.itertuples():
        pg.figval(fno[0] + 1, f"{r.above} of {r.population}", f"mart_capability: at or above 1.33 over the population, {r.quarter}")
    for r in qmed.itertuples():
        pg.figval(fno[0] + 1, f"{r.ppk:.2f}", f"mart_capability: median Ppk, {r.cls}, {r.quarter}")
    pg.figure(FIG.capability_by_quarter(qmed, qcnt), F("Capability by quarter"))
    pg.h3("below", "2.4 Characteristics below 1.33")
    u = below.merge(vca[["characteristic_id", "within_share_wear_first", "between_subgroups_share_wear_first", "between_coils_share_wear_first", "wear_share"]], on="characteristic_id", how="left")
    COMP = {"within_share_wear_first": "within subgroup", "between_subgroups_share_wear_first": "between subgroups", "between_coils_share_wear_first": "between coils", "wear_share": "tool wear"}
    u["largest"] = u[[c_ for c_ in COMP if c_ != "within_share_wear_first"]].idxmax(axis=1)
    u["label"] = [f"{COMP[c]} {100 * r[c]:.0f}%" + (f"; Cpk {r.cpk:.2f}" if r.cls == "hole diameter" else "") for c, (_, r) in zip(u["largest"], u.iterrows())]
    u["customer"] = (u["ppk_high"] < 1.33) | (u["cpk"] < 1.33)
    cust = sorted(u.loc[u["customer"], "characteristic_id"]); assert cust == ["C-15731-06", "C-16315-06", "C-37007-06"], cust
    u_sig = sig[sig["characteristic_id"].isin(u["characteristic_id"])]; assert not u_sig["assignable_cause"].any()
    pg.p(f"None of the {wd(len(u), 'mart_capability: below 1.33, quarter', was='seven')} carries a special cause; each falls short on the variation its chart is built to carry. "
         f"Three go to the customer, those whose interval lies wholly below 1.33 or whose Cpk is also below it: {txt('C-15731-06, C-37007-06 and C-16315-06', 'mart_capability: ppk_high under 1.33 or cpk under 1.33, quarter', was='C-15731-06, C-37007-06 and C-16315-06')}.")
    for r in u.itertuples():
        pg.figval(fno[0] + 1, f"{r.ppk:.2f} ({r.ppk_low:.2f} to {r.ppk_high:.2f}); {r.label}", f"mart_capability and mart_variance_components, {r.characteristic_id}")
    pg.figure(FIG.below_133(u[["characteristic_id", "ppk", "ppk_low", "ppk_high", "label", "customer"]]), F("Characteristics below Ppk 1.33"))
    pg.h3("attribute", "2.5 Attribute features")
    at = query("""select c.characteristic_type t, s.sample_time, s.pieces, coalesce(s.attribute_count, 0) f from staging.stg_spc__subgroups s join marts.mart_charts_in_force c using (characteristic_id)
                  where c.chart_type = 'p' and s.sample_time >= '2025-07-01' and s.sample_time < '2026-07-01'""")
    at["quarter"] = pd.to_datetime(at["sample_time"]).dt.to_period("Q").astype(str)
    ag = at.groupby(["t", "quarter"]).agg(pieces=("pieces", "sum"), fails=("f", "sum")).reset_index()
    ag["per_million"] = 1e6 * ag["fails"] / ag["pieces"]; ag["lo"] = [1e6 * pci(k, m)[0] for k, m in zip(ag["fails"], ag["pieces"])]; ag["hi"] = [1e6 * pci(k, m)[1] for k, m in zip(ag["fails"], ag["pieces"])]
    for t_ in ("burr height", "hole diameter"):
        g_ = ag[ag["t"] == t_]; assert g_["lo"].max() <= g_["hi"].min(), f"{t_} quarters not overlapping"
    bq = ag[(ag["t"] == "burr height")].set_index("quarter"); pq = ag[(ag["t"] == "hole diameter")].set_index("quarter")
    pg.p(f"Burr and pin fails ran flat within chance across the year: burr at {n(bq.at['2026Q2', 'per_million'], 'stg_spc__subgroups: burr fails per million, 2026 Q2')} per million pieces checked this quarter against "
         f"{n(bq.drop('2026Q2')['per_million'].min(), 'burr fails per million, earlier quarters, lowest')} to {n(bq.drop('2026Q2')['per_million'].max(), 'burr fails per million, earlier quarters, highest')} before it, and pins at "
         f"{n(pq.at['2026Q2', 'per_million'], 'stg_spc__subgroups: pin fails per million, 2026 Q2')} against {n(pq.drop('2026Q2')['per_million'].min(), 'pin fails per million, earlier quarters, lowest')} to {n(pq.drop('2026Q2')['per_million'].max(), 'pin fails per million, earlier quarters, highest')}.")
    for r in ag.itertuples():
        pg.figval(fno[0] + 1, f"{r.per_million:.0f}", f"fails per million, {r.t}, {r.quarter} ({r.fails} of {r.pieces:,})")
    pg.figure(FIG.fails_by_quarter(ag), F("Burr and pin fails per million, by quarter"))
    pg.h3("by-press", "2.6 By press")
    pm = cap.pivot_table(index="press_id", columns="cls", values="ppk", aggfunc="median"); pcount = cap.pivot_table(index="press_id", columns="cls", values="ppk", aggfunc="size")
    low_cells = [(p_, c_) for p_ in pm.index for c_ in pm.columns if pm.at[p_, c_] == pm.at[p_, c_] and pm.at[p_, c_] < 1.33]
    assert low_cells == [("PR-11", "formed")] and int(pcount.loc["PR-11"].sum()) == 1
    pg.p(f"No press sits apart; PR-11's one characteristic in the population, {txt(cap[cap['press_id'] == 'PR-11']['characteristic_id'].iloc[0], 'mart_capability: the PR-11 characteristic, quarter', was='C-37007-06')}, is below 1.33.")

    # ═══════════════ 3. SPC Review
    pg.h2("spc", "3. SPC Review")
    assert sr["signals_rule_3"].sum() + sr["signals_rule_4"].sum() > sr["signals_rule_1"].sum() + sr["signals_rule_2"].sum()
    pg.p(f"The charts traced every special cause in the quarter; signals with no assignable cause ran {pct(tot_s / tot_e - 1, 'mart_signal_rates with the expected rate: observed over expected less one, quarter', 0, was='23%')} above the design rate, the excess on rules 3 and 4.")
    pg.h3("special-causes", "3.1 Special causes")
    evq = allc.groupby("event").agg(first=("raised_at", "min"), chart_type=("chart_type", "first"), panel=("chart", "first"), cause=("cause_code", "first"), die=("die_id", "first")).reset_index()
    evq["row"] = np.where(evq["panel"] == "coil-change means", "coil-change", evq["chart_type"].map(CHART_ROW))
    evq["label"] = evq["cause"].map(SHORT)
    cc_ = evq["cause"].value_counts()
    n_dies = int(cc_.get("level after sharpening", 0) + cc_.get("level after the rebuild", 0))
    assert n_dies == 9 and cc_.get("strip misfeed", 0) == 2 and cc_.get("slug pulling", 0) == 2
    pg.p(f"The charts traced {n(n_sc, 'mart_signals: special-cause events on the characteristic charts, quarter (die events for level changes, runs otherwise)', was='18')} special causes on the characteristic charts and "
         f"{n(len(stf), 'mart_per_stroke_stops: stops with a finding, quarter', was='112')} per-stroke stops with a finding, all closed by 30 June: "
         f"{wd(n_dies, 'mart_signals: level-change die events, quarter', was='nine')} times a die came back from sharpening or rebuild at a new level, a drifting fixture, a soft coil, a sharpening logged at the wrong count, "
         f"{wd(int(cc_['strip misfeed']), 'strip misfeed events', was='two')} strip misfeeds, {wd(int(cc_['slug pulling']), 'slug pulling events', was='two')} slug pulls, a gauge zero and a lubricant fault.")
    for r in evq.itertuples():
        pg.figval(fno[0] + 1, pd.Timestamp(r.first).strftime("%d %b"), f"mart_signals: first signal, {r.event}")
    pg.figure(FIG.special_cause_timeline(evq[["first", "row", "label"]]), F("Special causes in the quarter"))
    # F-14026, to the record's timeline
    fd = sig[sig["cause_code"] == "fixture drift"]; assert set(fd["action"]) == {"fixture removed from service on the failed verification"}
    rb = query("select event_date from intermediate.int_die_event_timeline where die_id = 'D-4026-A' and event_type = 'rebuild' and event_date between '2026-05-01' and '2026-05-31'").iloc[0]
    r938 = query("select actual_start, actual_end from intermediate.int_run_shots where run_id = 'R26-00938'").iloc[0]
    nxt = query("select min(actual_start) s from intermediate.int_run_shots where part_id = 'P-14026' and actual_start > ?", [r938.actual_end])["s"].iloc[0]
    fvs = query("select verification_date, result from marts.mart_fixture_verifications where gauge_id = 'F-14026' and verification_date between '2026-05-28' and '2026-06-05' order by verification_date")
    assert list(fvs["result"]) == ["pass", "pass", "fail"]
    gs14 = query("select study_date, pct_grr_of_tolerance from marts.mart_gauge_studies where gauge_id = 'F-14026' and in_quarter order by study_date")
    back = query("select back_in_service from intermediate.int_gauge_status where gauge_id = 'F-14026' and event_type = 'rebuild'")["back_in_service"].iloc[0]
    gap_days = (pd.Timestamp(fvs["verification_date"].iloc[2]).normalize() - pd.Timestamp(fd["closed_at"].max()).normalize()).days
    assert gap_days == 4
    D = lambda t_: pd.Timestamp(t_).strftime("%d %B").lstrip("0")
    pg.p(f"The fixture drift on P-14026 is the quarter's one cause traced to a fixture. D-4026-A was rebuilt on {txt(D(rb.event_date), 'int_die_event_timeline: D-4026-A rebuild', was='16 May')} and first ran on {txt(D(r938.actual_start), 'int_run_shots: R26-00938 start', was='28 May')}; "
         f"its charts raised {n(len(fd), 'mart_signals: fixture drift signals', was='30')} signals coded fixture drift on 28 and 29 May, while F-14026's daily verifications on both days passed. "
         f"P-14026 did not run again until {txt(D(nxt), 'int_run_shots: next P-14026 run', was='18 June')}. The fixture's verification failed on {txt(D(fvs['verification_date'].iloc[2]), 'mart_fixture_verifications: F-14026 fail', was='2 June')}, its restudy read "
         f"{n(gs14['pct_grr_of_tolerance'].iloc[0], 'mart_gauge_studies: F-14026 restudy', '{:.1f}', was='16.7')}%, and it was rebuilt, restudied at {n(gs14['pct_grr_of_tolerance'].iloc[1], 'mart_gauge_studies: F-14026 after rebuild', '{:.1f}', was='5.3')}% on "
         f"{txt(D(gs14['study_date'].iloc[1]), 'mart_gauge_studies: F-14026 after rebuild, date', was='17 June')} and back in service on {txt(D(back), 'int_gauge_status: F-14026 back in service', was='18 June')}. "
         f"The {n(len(fd), 'mart_signals: fixture drift signals', was='30')} signals' closures give the action as the fixture's removal on the failed verification, an event {wd(gap_days, 'days from the last closure to the failed verification', was='four')} days after they were closed.")
    rx = allc.groupby("cause_code").agg(ack_med=("minutes_to_acknowledge", "median"), ack_max=("minutes_to_acknowledge", "max"), close_med=("minutes_to_close", "median"), close_max=("minutes_to_close", "max")).reset_index().rename(columns={"cause_code": "cause"})
    longest = rx.sort_values("close_max").iloc[-1]
    pg.p(f"Signals with a special cause were acknowledged in a median {n(allc['minutes_to_acknowledge'].median(), 'mart_signals.minutes_to_acknowledge, special causes, median', '{:.1f}', was='3.1')} minutes and closed in a median "
         f"{n(allc['minutes_to_close'].median(), 'mart_signals.minutes_to_close, special causes, median', was='130')} minutes; the longest, {txt(longest.cause, 'mart_signals: cause with the longest close', was='fixture drift')}, in "
         f"{n(longest.close_max, 'mart_signals.minutes_to_close, longest', was='244')}.")
    for r in rx.itertuples():
        pg.figval(fno[0] + 1, f"{r.ack_med:.1f}, {r.ack_max:.1f}, {r.close_med:.0f}, {r.close_max:.0f}", f"mart_signals: minutes to acknowledge and close, median and longest, {r.cause}")
    pg.figure(FIG.reaction_times(rx), F("Time to acknowledge and close, by cause"))
    pg.h3("flagged", "3.2 What the charts flagged")
    pg.p(f"In the quarter the routine charts raised {n(len(rt), 'mart_signals: routine signals, quarter', was='3,385')} signals: {n(n_ev, 'mart_signals: special-cause events on the routine charts', was='16')} were the first signal of a special-cause event, "
         f"{n(n_fol, 'mart_signals: follow-on signals', was='400')} followed on from an event already found, and {n(n_nc, 'mart_signals: routine signals with no assignable cause', was='2,969')} had no assignable cause. "
         f"The coil-change chart raised {n(len(ccs), 'mart_signals: coil-change chart signals, quarter', was='10')}, and the per-stroke charts stopped the presses {n(len(stp), 'mart_per_stroke_stops: stops, quarter', was='139')} times, "
         f"{n(len(stf), 'mart_per_stroke_stops: stops with a finding, quarter', was='112')} on a finding. The {n(len(other), 'mart_signals: signals on coil-change and first-piece subgroups of the routine charts', was='671')} signals on coil-change and first-piece subgroups of the routine charts are not shown in the figure.")
    fl = pd.DataFrame([{"group": "Routine characteristic charts", "a": n_ev, "o": n_fol, "b": n_nc}, {"group": "Coil-change chart", "a": len(soft), "o": 0, "b": len(ccs) - len(soft)},
                       {"group": "Per-stroke charts", "a": len(stf), "o": 0, "b": len(stp) - len(stf)}])
    for r in fl.itertuples():
        pg.figval(fno[0] + 1, f"{r.a:,} / {r.o:,} / {r.b:,}", f"what the charts flagged: {r.group}")
    pg.figure(DFIG.flagged_bars(fl, "d2_charts_flagged", ("First signal of a special cause", "Follow-on signal", "No assignable cause")), F("What the charts flagged"))
    pg.h3("expectation", "3.3 Signals against expectation")
    byc = sr.groupby("cls").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum"))
    byc["observed per 100"] = 100 * byc["signals"] / byc["subgroups"]; byc["expected per 100"] = 100 * byc["es"] / byc["subgroups"]; byc["ratio"] = byc["signals"] / byc["es"]
    pg.p(f"On charts with no special cause, signals ran at {n(tot_s / tot_e, 'observed over expected, quarter', '{:.2f}', was='1.23')} times the expected rate, broadly across the plant; the excess is on rules 3 and 4 on the regression and X-bar and R charts, as in {D1_LINK}. "
         f"Cut geometry ran at {n(byc.at['cut geometry', 'ratio'], 'observed over expected, cut geometry', '{:.2f}', was='1.46')} and hole diameter at {n(byc.at['hole diameter', 'ratio'], 'observed over expected, hole diameter', '{:.2f}', was='2.19')}, "
         f"formed characteristics at {n(byc.at['formed', 'ratio'], 'observed over expected, formed', '{:.2f}', was='0.92')} and flatness at {n(byc.at['flatness', 'ratio'], 'observed over expected, flatness', '{:.2f}', was='0.92')}.")
    f2 = byc.loc[["formed", "cut geometry", "hole diameter", "flatness"], ["observed per 100", "expected per 100", "ratio"]].reset_index()
    for r in f2.itertuples():
        pg.figval(fno[0] + 1, f"{r.ratio:.2f}", f"observed over expected, {r.cls}")
    pg.figure(DFIG.signals_by_class(f2, {"formed": (0.9, 1.4), "cut geometry": (0.9, 1.4), "hole diameter": (0.9, 1.5), "flatness": (0.9, 1.4)}, name="d2_signals_against_expectation_by_class"), F("Signals against expectation by class"))
    p1 = sr.groupby("press_id").agg(subgroups=("subgroups_in_scope", "sum"), signals=("signals_any_rule", "sum"), es=("es", "sum")).reset_index()
    p1["observed per 100"] = 100 * p1["signals"] / p1["subgroups"]; p1["expected per 100"] = 100 * p1["es"] / p1["subgroups"]; p1["ratio"] = p1["signals"] / p1["es"]
    p1["low"] = [100 * pci(k, m)[0] for k, m in zip(p1["signals"], p1["subgroups"])]; p1["high"] = [100 * pci(k, m)[1] for k, m in zip(p1["signals"], p1["subgroups"])]
    top = p1.sort_values("ratio", ascending=False); assert list(top["press_id"].head(3)) == ["PR-04", "PR-11", "PR-03"] and list(top["press_id"].tail(2)) == ["PR-10", "PR-08"]
    pr_ = p1.set_index("press_id")["ratio"]
    pg.p(f"PR-04, PR-11 and PR-03 ran furthest above expectation, at {n(pr_['PR-04'], 'observed over expected, PR-04', '{:.2f}', was='1.67')}, {n(pr_['PR-11'], 'observed over expected, PR-11', '{:.2f}', was='1.48')} and "
         f"{n(pr_['PR-03'], 'observed over expected, PR-03', '{:.2f}', was='1.41')} times, and PR-08 and PR-10 below it, at {n(pr_['PR-08'], 'observed over expected, PR-08', '{:.2f}', was='0.71')} and {n(pr_['PR-10'], 'observed over expected, PR-10', '{:.2f}', was='0.79')}.")
    pg.figure(FIG.observed_expected_by_press(p1), F("Observed against expected signals by press"))
    pg.p(f"The quarter's signals by rule follow the year's pattern in {D1_LINK}: the causes were found mostly on rules 1 and 2.")
    pg.h3("per-stroke", "3.4 Per-stroke tonnage")
    fc = stf["finding_class"].value_counts(); nf_q = stp[stp["finding_class"] == "nothing found"]; n3 = nf_q[nf_q["press_id"] == "PR-03"]
    pg.p(f"The per-stroke charts stopped the presses {n(len(stp), 'mart_per_stroke_stops: stops, quarter', was='139')} times on {n(srq['strokes'].sum() / 1e6, 'mart_per_stroke_stop_rates.strokes, quarter, millions', '{:.1f}', was='23.2')} million strokes, "
         f"{n(len(stf), 'stops with a finding, quarter', was='112')} on a finding: {n(int(fc['slug pulling']), 'slug pulling, quarter', was='68')} slug pulling, {n(int(fc['chipped punch']), 'chipped punch, quarter', was='23')} chipped punches and "
         f"{n(int(fc['worn punch']), 'worn punch, quarter', was='21')} worn punches. PR-03 carried {n(len(n3), 'nothing found on PR-03, quarter', was='18')} of the {n(len(nf_q), 'nothing found, quarter', was='27')} stops with nothing found.")
    pg.figure(FIG.stops_by_press(srq), F("Per-stroke stops by finding, by press"))
    rtq = query("select * from marts.mart_per_stroke_run_tonnage")
    lam, Lx = float(design["ewma_lambda"]), float(design["ewma_L"]); phi = float(rtq["baseline_lag_1_autocorrelation"].median())
    neff = float(design["ewma_baseline_strokes"]) * (1 - phi) / (1 + phi); nx, nw = A._normal_nodes(11); sx, sw = A._chi_ratio_nodes(neff - 1, 11)
    est = 1 / sum(a * w / A.ewma_arl(lam, Lx * s, c / np.sqrt(neff), phi) for c, a in zip(nx, nw) for s, w in zip(sx, sw))
    phc = float(rtq["baseline_channel_share_lag_1_autocorrelation"].median()); nec = float(design["ewma_baseline_strokes"]) * (1 - phc) / (1 + phc)
    cx, cw = A._normal_nodes(15); sx2, sw2 = A._chi_ratio_nodes(nec - 1, 15); Lcs = float(design["channel_share_L"])
    r_cs = sum(a * w * (stats.norm.sf(Lcs * s - c / np.sqrt(nec)) + stats.norm.sf(Lcs * s + c / np.sqrt(nec))) for c, a in zip(cx, cw) for s, w in zip(sx2, sw2))
    sq = srq.merge(presses, on="press_id"); e_ew = float((sq["strokes"] / est).sum()); e_cs = float((sq["strokes"] * sq["load_cell_channels"] * r_cs).sum())
    r1066 = n3[n3["run_id"] == "R26-01066"]
    yr3 = query("select run_id, count(*) n from marts.mart_per_stroke_stops where in_record and press_id = 'PR-03' and finding_class = 'nothing found' and chart = 'EWMA on the total' group by 1 order by n desc")
    assert set(n3["chart"]) == {"EWMA on the total"} and list(yr3["run_id"].head(2)) == ["R26-01066", "R25-01992"]
    prr = query("select led_by, count(*) n from marts.mart_punch_replacements where in_quarter group by 1").set_index("led_by")["n"]
    pg.p(f"Stops with nothing found ran at {n(1e6 * len(nf_q) / srq['strokes'].sum(), 'nothing found per million strokes, quarter', '{:.2f}', was='1.16')} per million strokes: the EWMA stopped "
         f"{n(int((nf_q['chart'] == 'EWMA on the total').sum()), 'nothing found on the EWMA, quarter', was='24')} times against about {n(e_ew, 'design stops with nothing found on the EWMA, quarter', '{:.0f}', was='9')} expected by design, and the channel-share charts "
         f"{n(int((nf_q['chart'] == 'channel share').sum()), 'nothing found on the channel-share charts, quarter', was='3')} times against about {n(e_cs, 'design stops with nothing found on the channel-share charts, quarter', '{:.0f}', was='12')}. "
         f"{n(len(r1066), 'nothing found on PR-03 on run R26-01066', was='15')} of PR-03's {n(len(n3), 'nothing found on PR-03, quarter', was='18')} came on R26-01066, the first run after the D-4026-A rebuild, and two runs carry "
         f"{n(int(yr3['n'].head(2).sum()), 'PR-03 EWMA stops with nothing found on its two heaviest runs, the year', was='29')} of PR-03's {n(int(yr3['n'].sum()), 'PR-03 EWMA stops with nothing found, the year', was='41')} for the year. "
         f"All {n(int(prr.sum()), 'mart_punch_replacements: quarter', was='44')} punch replacements followed a chart: {n(int(prr.get('channel share', 0)), 'punch replacements after the channel-share chart', was='23')} on the channel-share chart and "
         f"{n(int(prr.get('EWMA on the total', 0)), 'punch replacements after the EWMA', was='21')} on the EWMA.")
    pg.h3("limits", "3.5 Limits")
    rq = query("select trigger, chart, cast(sum(limit_sets_in_quarter) as integer) n from marts.mart_limit_recalculations group by all having sum(limit_sets_in_quarter) > 0 order by 1, 2")
    rq["chart"] = rq["chart"].replace({"tool-wear": "regression"}); rq["trigger"] = rq["trigger"].replace({"tool-wear re-fit": "regression re-fit"})
    vq = query("select * from marts.mart_limit_verifications where in_quarter"); vq["chart"] = vq["chart"].replace({"tool-wear": "regression"})
    vt = vq.groupby("chart").agg(done=("verification_id", "size"), failed=("result", lambda s_: int((s_ == "failed").sum()))).reindex(["X-bar and R", "three-way", "regression"]).reset_index()
    assert int(cif["past_trigger"].sum()) == 0
    bip = cif[cif["in_baseline"]].copy(); bip["days"] = (pd.Timestamp("2026-06-30") - pd.to_datetime(bip["baseline_started"]).dt.normalize()).dt.days
    c23 = bip.set_index("characteristic_id").loc["C-23264-03"]; c34 = bip.set_index("characteristic_id").loc["C-34479-05"]
    assert set(bip.loc[bip["days"] > 60, "characteristic_id"]) == {"C-23264-03", "C-34479-05"}
    ls34 = query("select limit_set_id, chart, effective_from from marts.mart_limit_sets where characteristic_id = 'C-34479-05' and effective_to is null").iloc[0]
    ch34 = query("select changed_on from marts.mart_chart_changes where characteristic_id = 'C-34479-05'").iloc[0]
    assert ls34.chart == "X-bar and R"
    pg.p(f"No chart is past its recalculation trigger at 30 June; {n(int(rq['n'].sum()), 'mart_limit_recalculations.limit_sets_in_quarter', was='53')} new limit sets were issued and "
         f"{n(int(vt['failed'].sum()), 'mart_limit_verifications: failed, quarter', was='13')} of {n(int(vt['done'].sum()), 'mart_limit_verifications: quarter', was='369')} verifications failed. "
         f"Two baselines are stale: C-23264-03 has been in baseline for {n(int(c23.days), 'mart_charts_in_force: days in baseline, C-23264-03', was='211')} days with {n(int(c23.baseline_subgroups_so_far), 'baseline subgroups so far, C-23264-03', was='21')} of 25 subgroups, "
         f"and C-34479-05 for {n(int(c34.days), 'mart_charts_in_force: days in baseline, C-34479-05', was='103')} days with {n(int(c34.baseline_subgroups_so_far), 'baseline subgroups so far, C-34479-05', was='38')} subgroups but "
         f"{wd(int(c34.baseline_coil_changes_so_far), 'baseline coil changes so far, C-34479-05', was='three')} of its {wd(design['three_way_baseline_coil_changes'], 'mart_chart_design.three_way_baseline_coil_changes', was='ten')} coil changes. "
         f"C-34479-05 still runs on its X-bar and R limits from {txt(pd.Timestamp(ls34.effective_from).strftime('%B %Y'), 'mart_limit_sets.effective_from, C-34479-05 in force', was='April 2024')}, although it moved to a three-way chart on "
         f"{txt(DAY(ch34.changed_on), 'mart_chart_changes.changed_on, C-34479-05', was='9 March 2026')}.")
    for r in vt.itertuples():
        pg.figval(fno[0] + 1, f"{r.failed} of {r.done}", f"mart_limit_verifications: failed of done, {r.chart}")
    pg.figure(FIG.limits_and_verifications(rq, vt), F("Limit sets and verifications in the quarter"))
    pg.h3("measurement", "3.6 Measurement systems")
    gsq = query("select * from marts.mart_gauge_studies where in_quarter order by study_date, gauge_id")
    gend = query("select quarter_end, count(*) filter (where past_due) pd from marts.mart_gauge_quarter_end group by 1"); assert (gend["pd"] == 0).all()
    gg = var.groupby("gauge_id").agg(t=("gauge_type", "first"), pct=("pct_grr_of_tolerance", "first"))
    fx_ = gg[gg["t"] == "check fixture"]; assert set(gg["t"]) == {"check fixture", "caliper", "indicator"} and (gg[gg["t"] != "check fixture"]["pct"] < 10).all()
    pg.p(f"{meas_head[0].upper() + meas_head[1:]}.")
    pg.p(f"{meas_ret}. No gauge was past calibration due at any quarter end, and {n(len(gsq), 'mart_gauge_studies: studies in the quarter', was='66')} gauge studies were run in the quarter. "
         f"Of the {n(len(gg), 'mart_charts_in_force: gauges on variable charts', was='221')} gauges on variable charts, the {n(len(fx_), 'check fixtures on variable charts', was='180')} check fixtures have %GRR under 10% on "
         f"{n(int((fx_['pct'] < 10).sum()), 'check fixtures under 10%', was='164')} and 10% to 30% on {n(int(((fx_['pct'] >= 10) & (fx_['pct'] < 30)).sum()), 'check fixtures at 10% to 30%', was='16')}; the "
         f"{n(int((gg['t'] == 'caliper').sum()), 'calipers on variable charts', was='29')} calipers and {n(int((gg['t'] == 'indicator').sum()), 'indicators on variable charts', was='12')} indicators are all under 10%.")
    gfx = gsq[gsq["gauge_type"] == "check fixture"].copy()
    band = (((gfx["pct_grr_of_tolerance"] >= 10) & (gfx["pct_grr_of_tolerance"] < 30)) | ((gfx["previous_pct_grr"] >= 10) & (gfx["previous_pct_grr"] < 30))) | (gfx["gauge_id"] == "F-14026")
    rest = gfx[~band]
    pg.p(f"Of the {n(len(gfx), 'mart_gauge_studies: check fixture studies in the quarter', was='52')} fixture studies in the quarter, {n(len(rest), 'fixture studies in the quarter under 10% at both studies, F-14026 aside', was='44')} read under 10%, within "
         f"{n((rest['pct_grr_of_tolerance'] - rest['previous_pct_grr']).abs().max(), 'largest move of %GRR, those fixtures', '{:.1f}', was='2.8')} points of the fixture's previous study; the figure shows the other {wd(len(gfx) - len(rest), 'fixture studies shown in the figure', was='eight')}.")
    f5 = gfx[band].copy(); f5["label"] = f5["gauge_id"] + " (" + f5["study_date"].map(lambda d_: pd.Timestamp(d_).strftime("%d %b").lstrip("0")) + ")"
    for r in f5.itertuples():
        pg.figval(fno[0] + 1, f"{r.previous_pct_grr:.1f} to {r.pct_grr_of_tolerance:.1f}", f"mart_gauge_studies: previous and this study, {r.label}")
    pg.figure(FIG.grr_before_after(f5), F("%GRR before and after"))
    kall = query("select * from marts.mart_operator_kappa order by operator_id, study_date"); lq = kall[kall["latest"]]
    kq = kall[(kall["operator_id"] == "E-1006") & kall["in_quarter"]].sort_values("study_date")
    btw = query("""select count(*) n from staging.stg_spc__subgroups s join staging.stg_spc__characteristics c using (characteristic_id)
                   where s.operator_id = 'E-1006' and c.type = 'burr height' and cast(s.sample_time as date) > ? and cast(s.sample_time as date) < ?""", [kq.iloc[0].study_date, kq.iloc[-1].study_date])["n"].iloc[0]
    assert int(btw) == 0
    pg.p(f"All {n(len(lq), 'mart_operator_kappa: operators', was='24')} burr check operators are qualified at 30 June, at kappa {n(lq['kappa'].min(), 'latest kappa, lowest', '{:.2f}', was='0.78')} to "
         f"{n(lq['kappa'].max(), 'latest kappa, highest', '{:.2f}', was='0.89')}; E-1006 fell to {n(kq.iloc[0].kappa, 'kappa, E-1006, 14 April', '{:.2f}', was='0.66')} on {txt(D(kq.iloc[0].study_date), 'E-1006 below the line, date', was='14 April')} and was requalified on "
         f"{txt(D(kq.iloc[-1].study_date), 'E-1006 requalified, date', was='28 April')} at {n(kq.iloc[-1].kappa, 'kappa, E-1006, 28 April', '{:.2f}', was='0.83')}, with no burr check recorded between.")
    pg.figure(FIG.kappa_by_operator(kall, 0.75), F("Kappa by operator"))
    pg.h3("dies", "3.7 Dies, first piece and recording")
    sh = query("select * from marts.mart_sharpenings where in_quarter order by sharpened_on, die_id"); shr = sh[sh["is_run_interval"]]; late = shr[shr["late"]]
    assert late["late_reason"].notna().all()
    pg.p(f"{n(int((~shr['late']).sum()), 'mart_sharpenings: at or before the due count, quarter', was='69')} of {n(len(shr), 'mart_sharpenings: quarter', was='76')} sharpenings were at or before the due count, and burr reached at most "
         f"{pct(shr['burr_peak_share_of_limit'].max(), 'mart_sharpenings.burr_peak_share_of_limit, highest', was='90.8%')} of its limit; the {wd(len(late), 'late sharpenings', was='seven')} late ones overran by "
         f"{n(100 * (late['share_of_due_count'].min() - 1), 'late overrun, smallest', '{:.0f}', was='1')}% to {n(100 * (late['share_of_due_count'].max() - 1), 'late overrun, largest', '{:.0f}', was='9')}%, each with a reason in the log.")
    for r in late.itertuples():
        pg.figval(fno[0] + 1, f"{100 * r.share_of_due_count:.1f}%", f"mart_sharpenings.share_of_due_count, {r.die_id}, {DAY(r.sharpened_on)}")
    pg.figure(FIG.sharpening_share(shr, late), F("Shots at sharpening as a share of the due count, by press group"))
    ht = held["held_characteristic_type"].value_counts(); fp9 = fpa[fpa["run_id"] == "R26-01002"].iloc[0]
    rep9 = query("select event_date from intermediate.int_die_event_timeline where die_id = ? and event_type = 'repair' and event_date <= ? order by event_date desc", [fp9.die_id, fp9.first_piece_at]).iloc[0]
    pg.p(f"{n(held_n, 'mart_first_piece_approvals.held, quarter', was='19')} of {n(starts, 'mart_first_piece_approvals: run starts, quarter', was='583')} run starts were held at the first piece, released in a median "
         f"{n(held['minutes_to_release'].median(), 'minutes to release, held, median', was='62')} minutes against {n(passed['minutes_to_release'].median(), 'minutes to release, passed, median', was='12')} for a passed first piece; "
         f"formed heights held {n(int(ht.get('formed height', 0)), 'held on formed height', was='8')}, among them the PR-09 hold on {txt(D(fp9.first_piece_at), 'mart_first_piece_approvals: R26-01002 first piece', was='9 June')} after the die repair of "
         f"{txt(D(rep9.event_date), 'int_die_event_timeline: repair before R26-01002', was='8 June')}.")
    assert fp9.held_characteristic_type == "formed height" and fp9.press_id == "PR-09"
    lg = held.sort_values("minutes_to_release").iloc[-1]
    pg.figval(fno[0] + 1, f"{lg.minutes_to_release:.0f}", f"mart_first_piece_approvals.minutes_to_release, {lg.run_id}")
    pg.figure(FIG.first_piece_rows(held, passed), F("First-piece time to release"))
    pc = query("select press_id, shift, count(*) planned, count(*) filter (where recorded) recorded from marts.mart_recording_planned_checks where in_quarter group by all order by 1, 2"); pc["share"] = pc["recorded"] / pc["planned"]
    pv = pc.pivot(index="press_id", columns="shift", values="share"); tot = pc.groupby("shift")[["planned", "recorded"]].sum()
    hi_n = pv.index[pv["nights"] > pv["days"]].tolist(); assert hi_n == ["PR-09", "PR-10", "PR-11"]
    pg.p(f"Planned checks were recorded on {pct(tot.at['days', 'recorded'] / tot.at['days', 'planned'], 'planned checks recorded, days', was='97.9%')} of day-shift occasions and "
         f"{pct(tot.at['nights', 'recorded'] / tot.at['nights', 'planned'], 'planned checks recorded, nights', was='96.9%')} on nights; nights ran lower on {n(int((pv['nights'] < pv['days']).sum()), 'presses lower on nights', was='8')} presses, and higher on PR-09 to PR-11.")
    for p_ in pv.index:
        pg.figval(fno[0] + 1, f"{100 * pv.at[p_, 'days']:.1f}% / {100 * pv.at[p_, 'nights']:.1f}%", f"mart_recording_planned_checks: recorded share, days and nights, {p_}")
    pg.figure(FIG.planned_checks_heatmap(pv), F("Planned checks recorded, by press and shift"))

    # ═══════════════ 1. Summary, written last, placed first
    last_section = pg.section; pg.section = "1. Summary"
    summary = []
    summary.append('<h2 id="summary">1. Summary</h2>')
    sent = (f"The quarter ran in control: {n(int((ccap['ppk'] >= 1.33).sum()), 'critical at or above 1.33', was='93')} of {n(len(ccap), 'critical characteristics', was='100')} critical characteristics held above Ppk 1.33, "
            f"signals ran at {n(tot_s / tot_e, 'observed over expected, quarter', '{:.2f}', was='1.23')} times the expected rate with the excess on rules 3 and 4, every special cause was traced and closed by 30 June, "
            f"no chart took limits from a gauge out of service, and {n(held_n, 'held, quarter', was='19')} of {n(starts, 'run starts, quarter', was='583')} run starts were held at the first piece.")
    summary.append(f"<p>{sent}</p>")
    tiles = [(f"{n(int((ccap['ppk'] >= 1.33).sum()), 'critical at or above 1.33', was='93')} of {n(len(ccap), 'critical characteristics', was='100')}", "critical characteristics above Ppk 1.33"),
             (f"{n(tot_s / tot_e, 'observed over expected, quarter', '{:.2f}', was='1.23')}x", "signals against the expected rate, charts with no special cause"),
             (f"{n(n_sc, 'special causes on the characteristic charts', was='18')}", "special causes on the characteristic charts, all closed by 30 June"),
             (f"{n(len(stf), 'per-stroke stops with a finding', was='112')}", "per-stroke stops with a finding"),
             (f"{n(on_out, 'mart_charts_in_force with mart_gauge_quarter_end: charts on a gauge past due or away at 30 June', was='0')}", "charts on limits from a gauge out of service"),
             (f"{n(held_n, 'held', was='19')} of {n(starts, 'run starts', was='583')}", f"run starts held, median {n(held['minutes_to_release'].median(), 'minutes to release, held, median', was='62')} minutes to release")]
    summary.append('<div style="display:flex;flex-wrap:wrap;gap:12px;margin:14px 0 24px;">' + "".join(
        f'<div style="flex:1 1 120px;border:1px solid #DDE3E8;border-radius:8px;padding:12px 14px;"><div style="font-size:24px;font-weight:700;color:{S.BRAND_BLUE};line-height:1.2;">{big}</div>'
        f'<div style="font-size:12.5px;color:#555;margin-top:4px;">{lab}</div></div>' for big, lab in tiles) + "</div>")
    for k_, blk in enumerate(summary):
        pg.body.insert(body_summary_at + k_, blk)
    pg.section = last_section

    # ═══════════════ Appendix
    pg.h2("appendix", "Appendix")
    pg.raw(DEFINITIONS)
    srq2 = srq.merge(pc.groupby("press_id")[["planned", "recorded"]].sum().reset_index(), on="press_id"); srq2["share"] = srq2["recorded"] / srq2["planned"]
    srq2 = srq2.merge(sig.groupby("press_id").agg(signals=("alarm_id", "count"), special=("assignable_cause", "sum")).reset_index(), on="press_id", how="left")
    srq2 = srq2.merge(fpa.groupby("press_id").agg(starts=("approval_id", "count"), holds=("held", "sum")).reset_index(), on="press_id", how="left")
    pg.table("A1. The full tables by press, April to June 2026", srq2, {"press_id": "Press", "signals": "Signals", "special": "With a special cause", "starts": "Run starts", "holds": "First-piece holds", "strokes": "Strokes",
                                                                       "stops": "Per-stroke stops", "stops_nothing_found": "Nothing found", "planned": "Planned checks", "share": "Recorded"},
             {"Signals": F0, "With a special cause": F0, "Run starts": F0, "First-piece holds": F0, "Strokes": F0, "Per-stroke stops": F0, "Nothing found": F0, "Planned checks": F0, "Recorded": P1})
    rows = []
    for c_ in FIG.CLASS_ORDER:
        g_ = cap[cap["cls"] == c_]
        rows.append({"class": FIG.CLASS_LABEL[c_], "n": len(g_), "ppk": g_["ppk"].median(), "iqr": f"{g_['ppk'].quantile(0.25):.2f} to {g_['ppk'].quantile(0.75):.2f}", "cpk": g_["cpk"].median(), "gap": g_["cpk_less_ppk"].median(), "u": int((g_["ppk"] < 1.33).sum())})
    pg.table("A2. Cpk and Ppk by class, April to June 2026", pd.DataFrame(rows), {"class": "Class", "n": "Characteristics", "ppk": "Ppk, median", "iqr": "Ppk, interquartile range", "cpk": "Cpk, median", "gap": "Cpk less Ppk", "u": "Below 1.33"},
             {"Characteristics": F0, "Ppk, median": F2, "Cpk, median": F2, "Cpk less Ppk": F2, "Below 1.33": F0})
    bip["started"] = bip["baseline_started"].map(DAY); bip["so_far"] = bip["baseline_subgroups_so_far"].astype(float); bip["coils"] = bip["baseline_coil_changes_so_far"].astype(float)
    bip["chart"] = bip["chart_type"].map(lambda c_: CHART_ROW.get(c_, c_))
    pg.table("A3. Baselines in progress at 30 June 2026", bip.sort_values("days", ascending=False), {"characteristic_id": "Characteristic", "part_id": "Part", "press_id": "Press", "chart": "Chart", "started": "Baseline started", "days": "Days",
                                                                                                   "so_far": "Subgroups so far", "coils": "Coil changes so far"},
             {"Days": F0, "Subgroups so far": F0, "Coil changes so far": F0})
    log = sig[["alarm_id", "raised_at", "press_id", "characteristic_id", "chart", "rule", "subgroup_type", "assignable_cause", "cause_code", "minutes_to_acknowledge", "minutes_to_close"]].copy()
    log["outcome"] = np.where(log["assignable_cause"], "special cause", "no assignable cause"); log = log.drop(columns="assignable_cause")
    out = S.DOCS / "reports"; out.mkdir(parents=True, exist_ok=True)
    log.to_csv(out / "spc_quarterly_review_2026_q2_signals.csv", index=False, lineterminator="\n")
    pg.p(f'<strong>The quarter\'s signal log.</strong> Every one of the quarter\'s {n(len(sig), "mart_signals: signals, quarter", was="4,066")} signals with its chart, rule, outcome and cause is in '
         '<a href="spc_quarterly_review_2026_q2_signals.csv">the signal log (CSV)</a>.')

    toc = [("summary", "1. Summary"), ("capability", "2. Capability Review"), ("where", "2.1 Where capability stands", "sub"), ("design-explains", "2.2 What the chart design explains", "sub"),
           ("year", "2.3 Across the year", "sub"), ("below", "2.4 Characteristics below 1.33", "sub"), ("attribute", "2.5 Attribute features", "sub"), ("by-press", "2.6 By press", "sub"),
           ("spc", "3. SPC Review"), ("special-causes", "3.1 Special causes", "sub"), ("flagged", "3.2 What the charts flagged", "sub"), ("expectation", "3.3 Signals against expectation", "sub"),
           ("per-stroke", "3.4 Per-stroke tonnage", "sub"), ("limits", "3.5 Limits", "sub"), ("measurement", "3.6 Measurement systems", "sub"), ("dies", "3.7 Dies, first piece and recording", "sub"), ("appendix", "Appendix")]
    html = S.report_shell("Quarterly Capability &amp; SPC Review, April to June 2026", "", "July 2026", "\n".join(pg.body), toc)
    (out / "spc_quarterly_review_2026_q2.html").write_text(html, encoding="utf8", newline="\n")
    trace, off = pg.check()
    return html, trace, off, pg.figures


DEFINITIONS = """<h3 id="definitions">Definitions</h3>
<p><strong>Periods.</strong> The quarter is 1 April to 30 June 2026; the record is 1 July 2025 to 30 June 2026, exported 13 July 2026. High-speed presses are PR-01 to PR-04; medium presses PR-05 to PR-11.</p>
<p><strong>Signals.</strong> A signal is a point beyond a control limit or a run-rule pattern on one panel of a chart. A special cause is a specific, identifiable source of variation found behind a signal; a die back from sharpening or rebuild at a new level is one special cause however many runs it signals on, and every other cause is one per run. The first signal of a special cause is the earliest signal of that event; the signals after it are follow-on signals. A signal with no assignable cause is one where the investigation finds nothing.</p>
<p><strong>Expected rate.</strong> For each characteristic chart, at its own rules and the size of the baseline its limits came from, the chance that a routine subgroup carries at least one signal on any of its panels, with the estimation error of the baseline allowed for; summed over the chart's routine subgroups under limits in force, outside any interval with a special cause, and set against the subgroups observed to carry at least one signal. The per-stroke charts' design rate is the EWMA's in-control run length with its parameters estimated from the run's baseline strokes, and each channel-share chart's rate at its limit, summed over each press's charts and strokes.</p>
<p><strong>Capability.</strong> The population is the critical characteristics with 60 routine subgroups or more in the period, reported on Ppk, and every flatness characteristic, reported on Ppu. Ppk is on the overall sigma of all readings; Cpk is on the short-term sigma of each chart type: between and within subgroups on three-way charts, the residual about the wear line on regression charts, pooled within subgroups on X-bar and R charts. Intervals are 95%, by Bissell's approximation. The variance shares behind each characteristic are those of the control chart design study, with tool wear fitted first.</p>
<p><strong>Gauges.</strong> A gauge's removal and return are dated without a time; a subgroup recorded on either day cannot be placed before or after it.</p>"""


if __name__ == "__main__":
    html, trace, off, nfig = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "quarterly_review_numbers.csv", index=False, lineterminator="\n")
    print(len(html), "characters;", len(trace), "numbers traced;", nfig, "figures;", len(off), "differ from the text")
    if len(off):
        print(off.to_string())
