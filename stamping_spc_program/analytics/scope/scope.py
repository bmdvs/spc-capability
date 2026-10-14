"""Scope and status of the assessment: what was assessed, the status of each characteristic class in each area of the
SPC program with the number that sets it, and the plant-wide items by shift.

Every measure is one of the analyses' own, on the assessment year, grouped by characteristic class. The thresholds
behind each status are in THRESHOLDS and are printed in the report's appendix.
"""
import re

import numpy as np
import pandas as pd

from analytics.data import ROOT, query
from analytics.stats import wilson

YEAR = 2025
STUDIES_TO = "2026-01-16"          # the end of the assessment's own studies
SHIFT_CHANGE_MINUTE = 870          # 14:30

CLASSES = ["formed heights and bend angles", "hole diameters", "other punched and dimensional", "flatness", "burr by limit sample", "burr on the lab gauge", "pin-gauge attribute checks"]
MATRIX_CLASSES = CLASSES[:6]
CLASS_SQL = """case when {t} in ('formed height', 'bend angle') then 'formed heights and bend angles'
                    when {t} = 'hole diameter' and {d} = 'variable' then 'hole diameters'
                    when {t} = 'hole diameter' then 'pin-gauge attribute checks'
                    when {t} = 'flatness' then 'flatness'
                    when {t} = 'burr height' and {d} = 'attribute' then 'burr by limit sample'
                    when {t} = 'burr height' then 'burr on the lab gauge'
                    else 'other punched and dimensional' end"""
HOLDS, PARTIAL, FAILS, NA = "Holds", "Partial", "Does not hold", "n/a"

# area -> (measure that sets the status, holds, partial, does not hold, basis)
THRESHOLDS = [
    ("Chart and limits: the chart fits the variation", "Rule 1 signals per 100 subgroups under limits computed from a stable baseline after each sharpening", "5 or fewer", "over 5 to 15", "over 15",
     "No standard reference. A stable process on correct limits gives 0.27; one signal in twenty subgroups is the rate taken here as one a press crew can answer."),
    ("Chart and limits: the limits as set", "Rule 1 signals per 100 subgroups under the limits as set, over the same under the computed limits", "0.67 to 1.5", "0.5 to 0.67, or 1.5 to 2", "under 0.5 or over 2",
     "No standard reference. Limits as set within a half of the computed rate either way are taken as holding to the baseline."),
    ("Capability", "Median production Ppk on critical characteristics, and the share of PPAP studies within 0.25 of the filed Ppk; median Ppu by the percentile method on bounded characteristics",
     "1.33 or more, and half or more of studies within 0.25", "1.33 or more, and under half of studies within 0.25", "under 1.33", "Ppk 1.33 (AIAG PPAP). The 0.25 band is the report's own."),
    ("Measurement: the study result", "Median %GRR of tolerance on the latest study on file of the gauges that measure the class; Fleiss' kappa against the burr gauge for the burr check",
     "under 10%, with no latest study over 30%; kappa 0.75 or more", "10% to 30%, or a latest study over 30%; kappa 0.40 to 0.75", "over 30%; kappa under 0.40", "AIAG MSA: 10% and 30% of tolerance; kappa 0.75 and 0.40."),
    ("Measurement: coverage", "Share of the class's gauges with a study on file; the cell takes the worse of the two parts", "90% or more", "50% to 90%", "under 50%", "No standard reference. The criterion is that every gauge in use is studied."),
    ("Sampling frequency", "Parts between two routine checks at the realised stroke rate, median over the class's characteristics",
     "no more than the median quantity sorted where a die-protection fault bounds the event", "between the two", "more than the median quantity sorted back to the check before",
     "No standard reference. The two quantities are the shop's own sorting record of 2024 and 2025."),
    ("Reaction", "Share of signals with an action recorded: paper signals with an action noted, software alarms acknowledged with a text; for classes adjusted at the press, the added variance",
     "90% or more on both media, and no added variance", "50% to 90% on the lower medium", "under 50% on the lower medium, or added variance with its interval above zero",
     "No standard reference. The criterion is that every signal is answered."),
]


def _cls(t="characteristic_type", d="data_type"):
    return CLASS_SQL.format(t=t, d=d)


def classes_charted():
    """Characteristics charted in the assessment year by class, with the critical count and the subgroups by chart medium."""
    d = query(f"""
        select {_cls()} as characteristic_class, count(distinct characteristic_id) as characteristics,
               count(distinct characteristic_id) filter (where critical) as critical_characteristics, count(*) as subgroups,
               count(*) filter (where entry_method = 'keyed') as subgroups_keyed, count(*) filter (where entry_method = 'paper transcription') as subgroups_on_paper
        from intermediate.int_characteristic_history where year(sample_time) = {YEAR} group by 1""")
    return d.set_index("characteristic_class").reindex(CLASSES).reset_index()


def _count(table, column=None, where=None):
    cond = " and ".join(c for c in ((f"year({column}) = {YEAR}" if column else None), where) if c)
    return int(query(f"select count(*) as n from {table}" + (f" where {cond}" if cond else ""))["n"].iloc[0])


def sources():
    """Each source system with the tables used and their rows in the assessment year."""
    s = "staging.stg_"
    return [("SPC software", [("characteristics", _count(s + "spc__characteristics")), ("limit sets", _count(s + "spc__control_limits")), ("subgroups", _count("intermediate.int_characteristic_history", "sample_time")), ("alarms", _count(s + "spc__alarms", "raised_at"))]),
            ("Press monitors", [("fault events", _count(s + "press_monitor__fault_events", '"timestamp"')), ("tonnage windows", _count(s + "press_monitor__tonnage_windows", "run_start_monitor"))]),
            ("ERP", [("production runs", _count(s + "erp__production_runs", "production_start")), ("coils received", _count(s + "erp__coils", "received_date")), ("scrap transactions", _count(s + "erp__scrap_transactions", '"date"')), ("shipments", _count(s + "erp__shipments", "ship_date"))]),
            ("QMS", [("nonconformances", _count(s + "qms__nonconformances", "opened")), ("sorting events", _count(s + "qms__sorting_events", "started")), ("complaints", _count(s + "qms__complaints", "received")), ("dock audits", _count(s + "qms__dock_audits", "audit_date")),
                     ("PPAP studies on file", _count(s + "qms__ppap_studies", where=f"\"date\" <= date '{YEAR}-12-31'"))]),
            ("Die maintenance log", [("die events", _count(s + "die_room__die_events", '"date"'))]),
            ("Calibration system", [("gauges", _count(s + "calibration__gauges")), ("calibrations", _count(s + "calibration__calibrations", "done")), ("gauge studies on file", _count(s + "calibration__gauge_studies", where=f"\"date\" <= date '{STUDIES_TO}'"))]),
            ("Accounting", [("quality cost lines", _count(s + "accounting__quality_cost_lines", where=f"cast(period as varchar) like '{YEAR}%'"))])]


def assessment_studies(gauge_rr, attribute):
    """The studies the assessment ran itself: the three gauge studies and the burr attribute study, with their dates."""
    g = gauge_rr[gauge_rr["study"] == "redesign"].sort_values("study_date")
    head = (ROOT / "data" / "raw" / "studies" / "attribute_burr_redesign.csv").read_text(encoding="utf8").split("\n")[:4]
    date = re.search(r"Date: (\d{4}-\d{2}-\d{2})", "\n".join(head)).group(1); a = attribute[attribute["study"] == "at the redesign"].iloc[0]
    return g[["fixture", "characteristic_id", "study_date"]].reset_index(drop=True), {"date": date, "operators": int(a.operators), "parts": int(a.parts), "trials": int(a.trials)}


def scope(capability_summary, gauge_rr, attribute):
    presses = query("select press_id, press_group, spc_entry_at_install from staging.stg_erp__presses order by press_id")
    runs = query(f"select count(distinct part_id) as parts, count(distinct die_id) as dies, count(*) as runs from intermediate.int_run_shots where year(production_start) = {YEAR}").iloc[0]
    g, a = assessment_studies(gauge_rr, attribute); base = capability_summary.set_index("characteristic_class").loc["all critical"]
    return {"presses": presses, "parts": int(runs.parts), "dies": int(runs.dies), "runs": int(runs.runs), "classes": classes_charted(), "sources": sources(), "gauge_studies": g, "attribute_study": a,
            "base_characteristics": int(base.characteristics), "base_studies": int(base.studies)}


# -- the matrix ------------------------------------------------------------------

def _limits_by_class():
    d = query(f"""
        select limits_as_set_method, {_cls(d="'variable'")} as characteristic_class, count(distinct characteristic_id) as characteristics, count(*) as subgroups,
               count(*) filter (where signal_as_computed_rule_1) as signals_as_computed, count(*) filter (where signal_as_set_rule_1) as signals_as_set,
               count(*) filter (where signal_as_computed_rule_1 and signal_as_set_rule_1) as signals_by_both,
               count(*) filter (where signal_as_set_rule_1 and action_recorded) as signals_with_action_recorded
        from marts.mart_limits_subgroup_flags group by 1, 2 order by 1, 2""")
    d["as_set_per_100"] = d["signals_as_set"] / d["subgroups"] * 100; d["as_computed_per_100"] = d["signals_as_computed"] / d["subgroups"] * 100
    d["set_over_computed"] = d["as_set_per_100"] / d["as_computed_per_100"]; d["share_of_computed_also_set"] = d["signals_by_both"] / d["signals_as_computed"]
    d["action_share"] = d["signals_with_action_recorded"] / d["signals_as_set"]
    return d


def _limits_status(row):
    fit = HOLDS if row.as_computed_per_100 <= 5 else PARTIAL if row.as_computed_per_100 <= 15 else FAILS
    if row.signals_as_computed == 0 and row.signals_as_set == 0:
        return HOLDS, HOLDS, HOLDS
    r = row.set_over_computed; held = HOLDS if 0.67 <= r <= 1.5 else PARTIAL if 0.5 <= r <= 2 else FAILS
    return max((fit, held), key=[HOLDS, PARTIAL, FAILS].index), fit, held


def _capability_by_class(by_study, bounded_summary):
    s = by_study.assign(c=np.where(by_study["characteristic_class"] == "formed", CLASSES[0], np.where(by_study["characteristic_type"] == "hole diameter", CLASSES[1], CLASSES[2])))
    g = s.groupby("c").agg(studies=("study_id", "size"), filed_ppk=("filed_ppk", "median"), production_ppk=("ppk", "median"), production_cpk=("cpk", "median"),
                           within_0_25=("filed_less_production_ppk", lambda x: int((x.abs() <= 0.25).sum()))).reset_index().rename(columns={"c": "characteristic_class"})
    b = bounded_summary.set_index("characteristic_type")
    return g, {"flatness": float(b.loc["flatness", "ppu_percentile_median"]), "burr on the lab gauge": float(b.loc["burr height", "ppu_percentile_median"])}


def latest_gauge_studies():
    """Each gauge's latest study on file at the end of the assessment's studies. A check fixture carries its own study;
    a hand gauge is covered by the latest study of its family, the gauges of its type at its press, as the shop studies them."""
    return query(f"""
        with st as (select s.*, g."type" as gauge_type, g.location from staging.stg_calibration__gauge_studies s join staging.stg_calibration__gauges g using (gauge_id) where s."date" <= date '{STUDIES_TO}'),
        own as (select *, row_number() over (partition by gauge_id order by "date" desc, study_id desc) as recency from st),
        family as (select *, row_number() over (partition by gauge_type, location order by "date" desc, study_id desc) as recency from st where gauge_type <> 'check fixture')
        select g.gauge_id, g."type" as gauge_type, g.location, coalesce(o."date", f."date") as study_date, coalesce(o.trigger, f.trigger) as trigger,
               coalesce(o.pct_grr_of_tolerance, f.pct_grr_of_tolerance) as pct_grr_of_tolerance, coalesce(o.ndc, f.ndc) as ndc, (o.gauge_id is null and f.gauge_id is not null) as by_family
        from staging.stg_calibration__gauges g
        left join own o on o.gauge_id = g.gauge_id and o.recency = 1
        left join family f on f.gauge_type = g."type" and f.location = g.location and f.recency = 1 and g."type" <> 'check fixture'
        where g.status = 'active' order by g.gauge_id""")


def _measurement_by_class(latest):
    c = query(f"""select distinct {_cls('c."type"', 'c.data_type')} as characteristic_class, c.characteristic_id, c.gauge_id
                  from staging.stg_spc__characteristics c join intermediate.int_characteristic_history h using (characteristic_id) where year(h.sample_time) = {YEAR} order by 1, 2, 3""")
    m = c.merge(latest[["gauge_id", "pct_grr_of_tolerance", "study_date"]], on="gauge_id", how="left"); rows = []
    for k, g in m.groupby("characteristic_class"):
        gauges = g.drop_duplicates("gauge_id"); st = gauges["pct_grr_of_tolerance"].dropna()
        rows.append({"characteristic_class": k, "characteristics": len(g), "gauges": int(gauges["gauge_id"].notna().sum()), "gauges_with_a_study": len(st), "pct_grr_median": float(st.median()) if len(st) else np.nan,
                     "pct_grr_highest": float(st.max()) if len(st) else np.nan, "studies_over_30": int((st > 30).sum()), "characteristics_on_a_gauge_with_no_study": int(g["pct_grr_of_tolerance"].isna().sum())})
    return pd.DataFrame(rows)


def _sampling_by_class():
    return query(f"""
        with rate as (select part_id, press_id, parts_between_checks_at_the_realised_rate / plan_frequency_minutes as parts_a_minute, runs from marts.mart_risk_window),
        part as (select part_id, sum(parts_a_minute * runs) / sum(runs) as parts_a_minute from rate group by 1),
        ch as (select distinct characteristic_id, part_id, frequency_minutes, {_cls()} as characteristic_class from intermediate.int_characteristic_history
               where year(sample_time) = {YEAR} and subgroup_type = 'routine')
        select characteristic_class, count(*) as characteristics, median(frequency_minutes) as frequency_minutes_median,
               median(frequency_minutes * parts_a_minute) as parts_between_checks_median, quantile_cont(frequency_minutes * parts_a_minute, 0.9) as parts_between_checks_p90
        from ch join part using (part_id) group by 1 order by 1""")


def _reaction_by_class(variance_by_characteristic):
    soft = query(f"""
        select {_cls()} as characteristic_class, count(*) as alarms, count(*) filter (where acknowledgement_text is not null and acknowledgement_text <> '') as acknowledged_with_a_text,
               count(*) filter (where adjustment_recorded) as with_an_adjustment_recorded
        from intermediate.int_characteristic_history where year(sample_time) = {YEAR} and entry_method = 'keyed' and alarm_raised and not after_redesign group by 1 order by 1""")
    paper = query(f"""
        select {_cls(d="'variable'")} as characteristic_class, count(*) as signals, count(*) filter (where action_recorded) as with_an_action_recorded
        from marts.mart_limits_subgroup_flags where limits_as_set_method = 'PPAP study' and signal_as_set_rule_1 group by 1 order by 1""")
    ty = query(f"select characteristic_id, {_cls('\"type\"')} as characteristic_class from staging.stg_spc__characteristics")
    v = variance_by_characteristic.merge(ty, on="characteristic_id"); rows = []
    r = np.random.default_rng([20250105, 91])
    for k, g in v.groupby("characteristic_class"):
        x = g["added_variance"].values; boot = [np.median(x[r.integers(0, len(x), len(x))]) for _ in range(2000)]
        rows.append({"characteristic_class": k, "adjusted_characteristics": len(x), "added_variance_median": float(np.median(x)), "low": float(np.percentile(boot, 2.5)), "high": float(np.percentile(boot, 97.5)), "with_more_variance": int((x > 0).sum())})
    return soft, paper, pd.DataFrame(rows)


def matrix(t_limits, t_capability, t_risk, t_measurement, t_adjustment):
    """The status of each class in each area, with the number that sets it. Returns the cells and the tables behind them."""
    lim = _limits_by_class(); cap, ppu = _capability_by_class(t_capability["by_study"], t_capability["bounded_summary"]); latest = latest_gauge_studies(); meas = _measurement_by_class(latest).set_index("characteristic_class")
    samp = _sampling_by_class().set_index("characteristic_class"); soft, paper, addv = _reaction_by_class(t_adjustment["variance_by_characteristic"])
    soft, paper, addv, cap = soft.set_index("characteristic_class"), paper.set_index("characteristic_class"), addv.set_index("characteristic_class"), cap.set_index("characteristic_class")
    sb = t_risk["sorting_by_basis"].set_index("sort_basis"); bounded_q = float(sb.loc["sorted from a logged die-protection fault", "quantity_sorted_median"]); back_q = float(sb.loc["sorted back to the check before, in-house", "quantity_sorted_median"])
    kappa = float(t_measurement["attribute_agreement"].set_index("study").loc["at the redesign", "fleiss_kappa"]); arl = t_limits["run_lengths"]
    arl = arl[(arl["limits_as_set_method"] == "PPAP study") & arl["limits"].str.startswith("as set")].set_index("characteristic_class")["arl_in_control"]
    cells = {}
    for k in MATRIX_CLASSES:
        short = {"formed heights and bend angles": "formed", "hole diameters": "hole diameter"}.get(k, "other punched and dimensional")
        for method, col in (("rolling 25 at entry", "software"), ("PPAP study", "paper")):
            r = lim[(lim["limits_as_set_method"] == method) & (lim["characteristic_class"] == k)]
            if len(r):
                r = r.iloc[0]; st, fit, held = _limits_status(r)
                if fit == st and fit != HOLDS:
                    why = f"{r.as_computed_per_100:.0f} of 100 subgroups signal under computed limits"
                elif held != HOLDS:
                    why = f"{r.as_set_per_100:.1f} signals per 100 as set, {r.as_computed_per_100:.1f} as computed"
                else:
                    why = f"{r.as_set_per_100:.1f} signals per 100 as set, {r.as_computed_per_100:.1f} as computed"
                if r.signals_as_computed == 0 and r.signals_as_set == 0:
                    why = f"no signal in {int(r.subgroups)} subgroups, as set or as computed"
                if col == "software" and st == FAILS and r.set_over_computed < 0.5:
                    why = f"{r.share_of_computed_also_set * 100:.1f}% of baseline signals flagged"
                cells[(k, col)] = (st, why)
            else:
                cells[(k, col)] = (NA, "not charted on limits" if k.startswith("burr by") else "no limits compared")
        if k in cap.index:
            c = cap.loc[k]; share = c.within_0_25 / c.studies
            st = FAILS if c.production_ppk < 1.33 else HOLDS if share >= 0.5 else PARTIAL
            cells[(k, "capability")] = (st, f"Ppk {c.production_ppk:.2f} against {c.filed_ppk:.2f} filed; {int(c.within_0_25)} of {int(c.studies)} within 0.25")
        elif k in ppu:
            cells[(k, "capability")] = (HOLDS if ppu[k] >= 1.33 else FAILS, f"Ppu {ppu[k]:.2f}")
        else:
            cells[(k, "capability")] = (NA, "attribute check")
        if k == "burr by limit sample":
            cells[(k, "measurement")] = (HOLDS if kappa >= 0.75 else PARTIAL if kappa >= 0.40 else FAILS, f"kappa {kappa:.2f} against the burr gauge")
        else:
            m = meas.loc[k]; cover = m.gauges_with_a_study / m.gauges; covered = HOLDS if cover >= 0.9 else PARTIAL if cover >= 0.5 else FAILS
            if m.gauges_with_a_study == 0:
                cells[(k, "measurement")] = (FAILS, f"no study on file for {int(m.gauges)} gauges")
            else:
                st = FAILS if m.pct_grr_median > 30 else PARTIAL if (m.pct_grr_median >= 10 or m.studies_over_30 > 0) else HOLDS
                why = f"%GRR {m.pct_grr_median:.1f} median on {int(m.gauges_with_a_study)} of {int(m.gauges)} gauges" + (f"; {int(m.studies_over_30)} over 30%" if m.studies_over_30 else "")
                if [HOLDS, PARTIAL, FAILS].index(covered) > [HOLDS, PARTIAL, FAILS].index(st):
                    st = covered; why = f"study on file for {int(m.gauges_with_a_study)} of {int(m.gauges)} gauges; %GRR {m.pct_grr_median:.1f} median on those"
                cells[(k, "measurement")] = (st, why)
        s = samp.loc[k]; q = float(s.parts_between_checks_median)
        cells[(k, "sampling")] = (HOLDS if q <= bounded_q else PARTIAL if q <= back_q else FAILS, f"{q:,.0f} parts between checks")
        p = paper.loc[k] if k in paper.index else None; sw = soft.loc[k] if k in soft.index else None; av = addv.loc[k] if k in addv.index else None
        if p is None and sw is None:
            cells[(k, "reaction")] = (NA, "no signals raised")
        else:
            shares = [x for x in ((p.with_an_action_recorded / p.signals) if p is not None else None, (sw.acknowledged_with_a_text / sw.alarms) if sw is not None else None) if x is not None]
            low = min(shares); st = HOLDS if low >= 0.9 else PARTIAL if low >= 0.5 else FAILS
            why = (f"{p.with_an_action_recorded / p.signals * 100:.0f}% of paper signals with an action" if p is not None else f"{sw.acknowledged_with_a_text / sw.alarms * 100:.0f}% of alarms acknowledged")
            if av is not None and av.low > 0:
                st = FAILS; why += f"; added variance {av.added_variance_median * 100:.1f}%"
            cells[(k, "reaction")] = (st, why)
    return {"cells": cells, "limits": lim, "capability": cap.reset_index(), "ppu": ppu, "measurement": meas.reset_index(), "sampling": samp.reset_index(), "software_alarms": soft.reset_index(), "paper_signals": paper.reset_index(),
            "added_variance": addv.reset_index(), "sorted_bounded_median": bounded_q, "sorted_back_median": back_q, "kappa": kappa, "printed_arl_in_control": arl, "latest_gauge_studies": latest}


def found_after_the_press():
    """Nonconformances of the year by defect code and where they were found, with the share found after the press."""
    d = query(f"""select defect_code, count(*) filter (where detected_at in ('press check', 'first-piece')) as at_the_press, count(*) filter (where detected_at = 'dock audit') as at_the_dock_audit,
                         count(*) filter (where detected_at = 'customer') as at_the_customer, count(*) as nonconformances
                  from staging.stg_qms__nonconformances where year(opened) = {YEAR} group by 1 order by 5 desc, 1""")
    d["found_after_the_press_share"] = (d["at_the_dock_audit"] + d["at_the_customer"]) / d["nonconformances"]
    return d


# -- plant-wide ------------------------------------------------------------------

def _shift(col):
    return f"case when hour({col}) * 60 + minute({col}) < {SHIFT_CHANGE_MINUTE} then 'days' else 'nights' end"


def plant_wide(planned_checks_by_hour):
    """The items that do not vary by class, by shift: counts and shares with Wilson intervals. The first check of the
    shift is the first planned hour of each shift in the planned checks by hour."""
    ph = planned_checks_by_hour[planned_checks_by_hour["press_group"] == "all presses"]; first = ph.sort_values("hour_of_day").groupby("shift").head(1)
    q = {
        "Planned checks recorded": f"select shift, count(*) as n, count(*) filter (where recorded) as k from marts.mart_recording_planned_checks where planned_year = {YEAR} and not after_redesign group by 1",
        "First check of the shift recorded": None,
        "Keyed entries made more than 20 minutes after the parts": f"""
            select case when operator_shift = 1 then 'days' else 'nights' end as shift, count(*) as n, count(*) filter (where minutes_to_entry > 20) as k
            from marts.mart_recording_routine_subgroups where sample_year = {YEAR} and entry_method = 'keyed' and not after_redesign group by 1""",
        "Software alarms acknowledged": f"""
            select {_shift('sample_time')} as shift, count(*) as n, count(*) filter (where acknowledgement_text is not null and acknowledgement_text <> '') as k
            from intermediate.int_characteristic_history where year(sample_time) = {YEAR} and entry_method = 'keyed' and alarm_raised and not after_redesign group by 1""",
        "Paper signals with an action recorded": f"""
            select {_shift('sample_time')} as shift, count(*) as n, count(*) filter (where (acknowledgement_text is not null and acknowledgement_text <> '') or adjustment_recorded) as k
            from intermediate.int_characteristic_history
            where year(sample_time) = {YEAR} and entry_method = 'paper transcription' and alarm_rule_1 and limits_in_force and not after_redesign group by 1""",
        "Subgroups on a gauge in service and in calibration": f"""
            select {_shift('sample_time')} as shift, count(*) as n, count(*) filter (where not gauge_out_of_service and not gauge_past_due) as k
            from intermediate.int_characteristic_history where year(sample_time) = {YEAR} and gauge_id is not null group by 1""",
    }
    rows = []
    for name, sql in q.items():
        d = first.rename(columns={"planned_checks": "n", "recorded": "k"})[["shift", "n", "k"]] if sql is None else query(sql)
        d = d.set_index("shift").reindex(["days", "nights"]).fillna(0); tot = d.sum()
        for label, r in (("days", d.loc["days"]), ("nights", d.loc["nights"]), ("all", tot)):
            lo, hi = wilson(int(r.k), int(r.n)) if r.n else (np.nan, np.nan)
            rows.append({"measure": name, "shift": label, "count": int(r.n), "with": int(r.k), "share": r.k / r.n if r.n else np.nan, "low": lo, "high": hi})
    out = pd.DataFrame(rows); out.attrs["first_hours"] = {r.shift: int(r.hour_of_day) for r in first.itertuples()}
    return out


def compute(t_limits, t_capability, t_risk, t_measurement, t_adjustment, t_recording):
    return {"scope": scope(t_capability["capability_summary"], t_measurement["gauge_rr"], t_measurement["attribute_agreement"]), "matrix": matrix(t_limits, t_capability, t_risk, t_measurement, t_adjustment), "plant_wide": plant_wide(t_recording["planned_checks_by_hour"])}


if __name__ == "__main__":
    from analytics.limits import limits; from analytics.capability import capability; from analytics.risk_window import risk_window; from analytics.measurement import measurement; from analytics.adjustment import adjustment; from analytics.recording import recording
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_colwidth", 70)
    t = compute(limits.compute(), capability.compute(), risk_window.compute(), measurement.compute(), adjustment.compute(), recording.compute())
    s = t["scope"]; print({k: v for k, v in s.items() if not isinstance(v, (pd.DataFrame, list))}); print(s["classes"]); print(s["sources"]); print(s["gauge_studies"])
    m = t["matrix"]
    for k in MATRIX_CLASSES:
        print(k); [print("   ", c, m["cells"][(k, c)]) for c in ("software", "paper", "capability", "measurement", "sampling", "reaction")]
    for k in ("limits", "capability", "measurement", "sampling", "software_alarms", "paper_signals", "added_variance"):
        print(m[k])
    print(m["sorted_bounded_median"], m["sorted_back_median"], m["printed_arl_in_control"]); print(t["plant_wide"], t["plant_wide"].attrs)
