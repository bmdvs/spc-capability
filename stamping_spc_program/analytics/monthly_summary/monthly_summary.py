"""SPC monthly summary: the SPC measures of one month across all eleven presses, against the month before and the
twelve months to the month, on the definitions of the two reports (planned check, alarm signal, action recorded,
capability, burr over the limit, gauge status)."""
import numpy as np
import pandas as pd

from analytics.data import query
from analytics.die_wear.die_wear import burr_by_die

MONTH = pd.Timestamp("2026-06-01")
MIN_SUBGROUPS = 60                 # a characteristic enters a capability figure with at least this many subgroups in the period
BASELINE_SUBGROUPS = 25            # the chart book's baseline after a sharpening
COIL_CHANGES = 6                   # coil changes on the new edge before a three-way chart is recalculated
FORMED = ("formed height", "bend angle")
R5 = ["r1", "r2", "r3", "r4", "r5"]


def periods(month=MONTH):
    """The month, the month before, the year to the end of the month and the calendar year before, as (start, end). The last two keep the names
    the tables were first built on."""
    end = month + pd.offsets.MonthBegin(1)
    return {"month": (month, end), "month_before": (month - pd.offsets.MonthBegin(1), month), "twelve_months": (pd.Timestamp(month.year, 1, 1), end), "twelve_months_before": (pd.Timestamp(month.year - 1, 1, 1), pd.Timestamp(month.year, 1, 1))}


def _d(t):
    return f"date '{pd.Timestamp(t).date()}'"


def _where(col, p):
    return f"{col} >= {_d(p[0])} and {col} < {_d(p[1])}"


# -- capability -----------------------------------------------------------------
def capability_by_characteristic(p):
    """Production Cpk and Ppk on each critical variable characteristic with at least 60 subgroups in the period."""
    d = query(f"""select characteristic_id, part_id, press_id, characteristic_name, characteristic_type, usl, lsl, r1, r2, r3, r4, r5 from intermediate.int_characteristic_history
                  where critical and data_type = 'variable' and r5 is not null and implausible_readings = 0 and lsl is not null and {_where('sample_time', p)}
                  order by characteristic_id, sample_time, subgroup_id""")
    rows = []
    for cid, g in d.groupby("characteristic_id", sort=True):
        if len(g) < MIN_SUBGROUPS:
            continue
        x = g[R5].values.astype(float); m = x.mean(); near = min(g["usl"].iloc[0] - m, m - g["lsl"].iloc[0])
        rows.append({"characteristic_id": cid, "part_id": g["part_id"].iloc[0], "press_id": g["press_id"].iloc[0], "characteristic_name": g["characteristic_name"].iloc[0],
                     "characteristic_class": "formed" if g["characteristic_type"].iloc[0] in FORMED else "punched", "subgroups": len(g), "cpk": near / (3 * np.sqrt(x.var(axis=1, ddof=1).mean())), "ppk": near / (3 * x.std(ddof=1))})
    return pd.DataFrame(rows)


def charts_in_force(as_at):
    """The chart in force on each variable characteristic at the date, by the limit set in force."""
    return query(f"""
        select l.characteristic_id, l.limit_set_id, l.press_id, l.part_id, l.die_id, l.method, l.effective_from, l.subgroups_used, l.coil_changes_spanned,
               case when l.method = 'tool-wear regression' then 'tool-wear chart' when l.method = 'PPAP study' then 'printed limits' when l.method = 'rolling 25 at entry' then 'rolling limits'
                    when l.characteristic_type in {FORMED} then 'three-way chart' else 'X-bar and R' end as chart
        from marts.mart_limits_as_set l where l.effective_from < {_d(as_at)} + interval 1 day and (l.effective_to is null or l.effective_to >= {_d(as_at)} + interval 1 day)
        qualify row_number() over (partition by l.characteristic_id order by l.effective_from desc) = 1""")


def capability(P):
    now, before = capability_by_characteristic(P["twelve_months"]), capability_by_characteristic(P["twelve_months_before"])

    def by(c, keys):
        return c.groupby(keys).agg(characteristics=("characteristic_id", "count"), subgroups=("subgroups", "sum"), ppk_median=("ppk", "median"), cpk_median=("cpk", "median"), ppk_under_1_33=("ppk", lambda v: int((v < 1.33).sum()))).reset_index()
    press = by(now, ["press_id", "characteristic_class"]).merge(by(before, ["press_id", "characteristic_class"])[["press_id", "characteristic_class", "characteristics", "ppk_median", "ppk_under_1_33"]], on=["press_id", "characteristic_class"], how="outer", suffixes=("", "_twelve_months_before"))
    plant = by(now, ["characteristic_class"]).merge(by(before, ["characteristic_class"]), on="characteristic_class", suffixes=("", "_twelve_months_before"))
    ch = charts_in_force(P["month"][1] - pd.Timedelta(days=1))[["characteristic_id", "chart"]]
    under = now[now["ppk"] < 1.33].merge(ch, on="characteristic_id", how="left").sort_values(["ppk", "characteristic_id"])
    return {"capability_by_press": press, "capability_plant": plant, "capability_under_1_33": under, "capability_by_characteristic": now}


# -- alarms and reaction ----------------------------------------------------------
def alarms(P):
    rows = []
    for label, p in P.items():
        d = query(f"""select press_id, count(*) as variable_subgroups, count(*) filter (where alarm_raised) as alarm_signals,
                             count(*) filter (where alarm_raised and adjustment_recorded) as with_an_adjustment_recorded,
                             count(*) filter (where alarm_raised and (acknowledgement_text is not null or adjustment_recorded)) as with_an_acknowledgement_or_adjustment,
                             count(*) filter (where alarm_raised and acknowledgement_text is null and not adjustment_recorded) as with_nothing_recorded,
                             count(*) filter (where pattern_flags is not null) as subgroups_with_a_pattern_shown,
                             count(*) filter (where pattern_flags like '%2%') as rule_2, count(*) filter (where pattern_flags like '%3%') as rule_3, count(*) filter (where pattern_flags like '%4%') as rule_4
                      from intermediate.int_characteristic_history where data_type = 'variable' and subgroup_mean is not null and {_where('sample_time', p)} group by 1 order by 1""")
        tot = d.drop(columns="press_id").sum(); tot["press_id"] = "all presses"
        d = pd.concat([d, pd.DataFrame([tot])], ignore_index=True); d.insert(0, "period", label); rows.append(d)
    d = pd.concat(rows, ignore_index=True)
    d["alarm_signals_per_100_subgroups"] = d["alarm_signals"] / d["variable_subgroups"] * 100
    d["adjustment_share"] = d["with_an_adjustment_recorded"] / d["alarm_signals"]; d["acknowledgement_or_adjustment_share"] = d["with_an_acknowledgement_or_adjustment"] / d["alarm_signals"]
    nothing = query(f"""select press_id, part_id, characteristic_id, characteristic_name, sample_time, subgroup_type, operator_id, case when alarm_rule_1 then 'rule 1' else 'rule 2' end as rule, critical
                        from intermediate.int_characteristic_history where data_type = 'variable' and subgroup_mean is not null and alarm_raised and acknowledgement_text is null and not adjustment_recorded
                          and {_where('sample_time', P['month'])} order by press_id, sample_time, characteristic_id""")
    return {"alarms": d, "alarms_with_nothing_recorded": nothing}


def monthly_alarms(P):
    return query(f"""select date_trunc('month', sample_time)::date as month_start, count(*) as variable_subgroups, count(*) filter (where alarm_raised) as alarm_signals,
                            count(*) filter (where alarm_raised and adjustment_recorded) as with_an_adjustment_recorded,
                            count(*) filter (where alarm_raised and (acknowledgement_text is not null or adjustment_recorded)) as with_an_acknowledgement_or_adjustment
                     from intermediate.int_characteristic_history where data_type = 'variable' and subgroup_mean is not null and {_where('sample_time', P['twelve_months'])} group by 1 order by 1""")


# -- checks and recording --------------------------------------------------------
def checks(P):
    planned, first, late = [], [], []
    for label, p in P.items():
        d = query(f"""select press_id, shift, count(*) as planned_checks, count(*) filter (where recorded) as recorded from marts.mart_recording_planned_checks where {_where('planned_time', p)}
                      group by grouping sets ((1, 2), (1), (2), ()) order by 1, 2""")
        d["press_id"] = d["press_id"].fillna("all presses"); d["shift"] = d["shift"].fillna("both shifts"); d.insert(0, "period", label); planned.append(d)
        f = query(f"""with c as (select *, hour(planned_time) as h, min(hour(planned_time)) over (partition by shift) as first_hour from marts.mart_recording_planned_checks where {_where('planned_time', p)})
                      select press_id, shift, any_value(first_hour) as planned_hour, count(*) as planned_checks, count(*) filter (where recorded) as recorded from c where h = first_hour
                      group by grouping sets ((1, 2), (2)) order by 1, 2""")
        f["press_id"] = f["press_id"].fillna("all presses"); f.insert(0, "period", label); first.append(f)
        e = query(f"""select press_id, entry_method, count(*) as subgroups, count(*) filter (where minutes_to_entry > 20) as entered_more_than_20_minutes_after, median(minutes_to_entry) as minutes_to_entry_median
                      from marts.mart_recording_routine_subgroups where {_where('sample_time', p)} and entry_method <> 'paper transcription' group by grouping sets ((1, 2), (2)) order by 1, 2""")
        e["press_id"] = e["press_id"].fillna("all presses"); e.insert(0, "period", label); late.append(e)
    planned, first, late = pd.concat(planned, ignore_index=True), pd.concat(first, ignore_index=True), pd.concat(late, ignore_index=True)
    planned["recorded_share"] = planned["recorded"] / planned["planned_checks"]; first["recorded_share"] = first["recorded"] / first["planned_checks"]; late["share"] = late["entered_more_than_20_minutes_after"] / late["subgroups"]
    return {"planned_checks": planned, "first_check_of_the_shift": first, "entries_after_the_parts": late}


def monthly_checks(P):
    a = query(f"""select date_trunc('month', planned_time)::date as month_start, count(*) as planned_checks, count(*) filter (where recorded) as recorded from marts.mart_recording_planned_checks
                  where {_where('planned_time', P['twelve_months'])} group by 1 order by 1""")
    b = query(f"""select date_trunc('month', sample_time)::date as month_start, entry_method, count(*) as subgroups, count(*) filter (where minutes_to_entry > 20) as late from marts.mart_recording_routine_subgroups
                  where {_where('sample_time', P['twelve_months'])} and entry_method <> 'paper transcription' group by 1, 2 order by 1, 2""")
    return a, b


# -- limits ----------------------------------------------------------------------
def limits(P):
    m = P["month"]; as_at = m[1] - pd.Timedelta(days=1)
    recalculated = query(f"""select press_id, method, count(distinct characteristic_id) filter (where not first_limits_at_redesign) as charts_recalculated, count(distinct characteristic_id) filter (where first_limits_at_redesign) as charts_with_first_limits_under_the_redesign,
                                    count(distinct die_id) as dies from marts.mart_limits_as_set where {_where('effective_from', m)} group by grouping sets ((1, 2), (2)) order by 1, 2""")
    recalculated["press_id"] = recalculated["press_id"].fillna("all presses")
    monthly = query(f"""select date_trunc('month', effective_from)::date as month_start, count(distinct characteristic_id) as charts from marts.mart_limits_as_set
                        where {_where('effective_from', P['twelve_months'])} and method in ('baseline after sharpening', 'tool-wear regression') and not first_limits_at_redesign group by 1 order by 1""")
    c = charts_in_force(as_at); c = c[c["chart"].isin(["three-way chart", "X-bar and R"])]
    since = query(f"""
        with last as (select die_id, max(event_date) as last_sharpening from intermediate.int_die_event_timeline where starts_interval and event_date <= {_d(as_at)} group by 1)
        select h.characteristic_id, any_value(l.last_sharpening) as last_sharpening, count(*) as subgroups_since, count(distinct h.coil_id) - 1 as coil_changes_since
        from intermediate.int_characteristic_history h join last l using (die_id)
        where h.sample_time >= l.last_sharpening + interval 1 day and h.sample_time < {_d(as_at)} + interval 1 day and h.data_type = 'variable' and h.subgroup_mean is not null group by 1""")
    last = query(f"select die_id, max(event_date) as last_sharpening from intermediate.int_die_event_timeline where starts_interval and event_date <= {_d(as_at)} group by 1")
    c = c.merge(last, on="die_id", how="left").merge(since.drop(columns="last_sharpening"), on="characteristic_id", how="left"); c[["subgroups_since", "coil_changes_since"]] = c[["subgroups_since", "coil_changes_since"]].fillna(0).astype(int)
    c["set_before_the_last_sharpening"] = pd.to_datetime(c["effective_from"]) < pd.to_datetime(c["last_sharpening"]) + pd.Timedelta(days=1)
    need = np.where(c["chart"] == "three-way chart", (c["subgroups_since"] >= BASELINE_SUBGROUPS) & (c["coil_changes_since"] >= COIL_CHANGES), c["subgroups_since"] >= BASELINE_SUBGROUPS)
    c["status"] = np.where(~c["set_before_the_last_sharpening"], "set on the current edge", np.where(need, "due: baseline complete on the new edge", "baseline not yet complete on the new edge"))
    status = c.groupby(["press_id", "chart", "status"]).size().rename("charts").reset_index()
    return {"limits_recalculated": recalculated, "limits_recalculated_by_month": monthly, "limits_status": status, "limits_due": c[c["status"].str.startswith("due")].sort_values(["press_id", "part_id", "characteristic_id"])}


# -- die wear and per-stroke monitoring --------------------------------------------
def die_wear(P):
    m = P["month"]; as_at = m[1] - pd.Timedelta(days=1); b, _ = burr_by_die(); b = b[["die_id", "shots_at_80pct_of_limit"]]
    press = query("select die_id, mode(press_id) as press_id from intermediate.int_run_shots where production_start >= date '2025-01-01' group by 1")
    # the press of a sharpening interval is the press of the die's last run in it; a die with no run in the interval keeps its usual press
    last = query("""select i.die_id, i.sharpening_interval_no, arg_max(r.press_id, r.actual_start) as press_of_the_last_run
                    from intermediate.int_sharpening_intervals i join intermediate.int_run_shots r on r.die_id = i.die_id and r.sharpening_date = i.interval_start group by 1, 2""")

    def on_press(d):
        d = d.merge(press, on="die_id", how="left").merge(last, on=["die_id", "sharpening_interval_no"], how="left"); d["press_id"] = d["press_of_the_last_run"].fillna(d["press_id"])
        return d.drop(columns="press_of_the_last_run")

    def sharpenings(p):
        s = query(f"""select i.die_id, i.sharpening_interval_no, i.interval_end as sharpened, i.shots_in_interval_logged from intermediate.int_sharpening_intervals i
                      where i.is_run_interval and i.shots_in_interval_logged is not null and {_where('i.interval_end', p)} order by 3, 1""").merge(b, on="die_id", how="left"); s = on_press(s)
        s["against_the_due_count"] = np.where(s["shots_at_80pct_of_limit"].isna(), "no burr line on the die", np.where(s["shots_in_interval_logged"] <= s["shots_at_80pct_of_limit"], "at or before the due count", "after the due count"))
        return s
    sh = {k: sharpenings(P[k]) for k in ("month", "month_before", "twelve_months", "twelve_months_before")}
    counts = pd.concat([v.groupby("against_the_due_count").size().rename(k) for k, v in sh.items()], axis=1).fillna(0).astype(int).reset_index()

    def burr(p):
        return on_press(query(f"""with w as (select die_id, sharpening_interval_no, count(*) as subgroups, max(share_of_limit) as highest from marts.mart_wear_points where characteristic_type = 'burr height' group by 1, 2)
                         select s.die_id, s.sharpening_interval_no, s.interval_end, w.subgroups, w.highest from intermediate.int_sharpening_intervals s join w using (die_id, sharpening_interval_no)
                         where {_where('s.interval_end', p)} and w.subgroups >= 5 order by 3, 1"""))
    bu = {k: burr(P[k]) for k in sh}
    burr_counts = pd.DataFrame([{"period": k, "intervals_with_burr_gauge_subgroups": len(v), "intervals_with_burr_over_the_limit": int((v["highest"] > 1).sum())} for k, v in bu.items()])
    days = (m[1] - m[0]).days
    due = query(f"""
        with last as (select die_id, event_date as last_sharpening, shot_count as shot_count_at_last_sharpening from intermediate.int_die_event_timeline where starts_interval and event_date <= {_d(as_at)}
                      qualify row_number() over (partition by die_id order by event_date desc, shot_count desc) = 1),
             rate as (select die_id, sum(strokes) as strokes_in_the_month from intermediate.int_run_shots where {_where('actual_end', m)} group by 1),
             since as (select r.die_id, sum(r.strokes) as strokes_since from intermediate.int_run_shots r join last l on l.die_id = r.die_id and r.sharpening_date = l.last_sharpening
                       where r.actual_start < {_d(as_at)} + interval 1 day group by 1)
        -- shots since sharpening are the strokes on runs since the last sharpening, the run in process included: the die log rounds its shot
        -- counts and the die master leaves out the run in process, so the difference of the two can fall below zero
        select d.die_id, d.part_ids as part_id, d.shot_count as shot_count_at_the_end_of_the_month, l.last_sharpening, coalesce(s.strokes_since, 0) as shots_since_sharpening, coalesce(r.strokes_in_the_month, 0) as strokes_in_the_month
        from staging.stg_erp__dies d join last l using (die_id) left join rate r using (die_id) left join since s using (die_id) where d.status = 'active'""").merge(b, on="die_id").merge(press, on="die_id", how="left")
    due["shots_since_sharpening"] = due["shots_since_sharpening"].astype(float)          # a sharpening logged with no shot count leaves the shots since unknown
    due["shots_to_the_due_count"] = due["shots_at_80pct_of_limit"] - due["shots_since_sharpening"]; due["strokes_a_day"] = due["strokes_in_the_month"] / days
    due["days_to_the_due_count"] = np.where(due["shots_to_the_due_count"] <= 0, 0.0, np.where(due["strokes_a_day"] > 0, due["shots_to_the_due_count"] / due["strokes_a_day"].replace(0, np.nan), np.nan))
    nxt = (m[1] + pd.offsets.MonthBegin(1) - m[1]).days
    due_list = due[(due["shots_to_the_due_count"] <= 0) | (due["days_to_the_due_count"] <= nxt)].sort_values(["shots_to_the_due_count"]).reset_index(drop=True)
    due_list["status"] = np.where(due_list["shots_to_the_due_count"] <= 0, "past due", "due in the month after")
    due_list["run_in_the_month"] = due_list["strokes_in_the_month"] > 0

    def stops(p):
        d = query(f"""select f.press_id, x.is_pilot_press, f.finding, count(*) as stops from staging.stg_press_monitor__fault_events f join intermediate.int_press_redesign x using (press_id)
                      where f.input in ('EWMA signal', 'channel share signal') and {_where('f."timestamp"', p)} group by 1, 2, 3 order by 1, 3""")
        return d
    st = stops(m); st12 = stops(P["twelve_months"])
    stops_month = st.pivot_table(index=["press_id", "is_pilot_press"], columns="finding", values="stops", aggfunc="sum", fill_value=0).reset_index(); stops_month["stops"] = stops_month.drop(columns=["press_id", "is_pilot_press"]).sum(axis=1)
    stops_by_month = query(f"""select date_trunc('month', "timestamp")::date as month_start, count(*) as stops, count(*) filter (where finding = 'nothing found') as nothing_found from staging.stg_press_monitor__fault_events
                               where input in ('EWMA signal', 'channel share signal') and {_where('"timestamp"', P['twelve_months'])} group by 1 order by 1""")

    def punches(p):
        return query(f"""select case when fault_event_id is not null then 'after a stop by the per-stroke charts' when notes like '%sharpening%' then 'at a sharpening' when notes like '%nonconforming%' then 'after nonconforming parts' else notes end as led_by,
                                count(*) as punch_replacements from intermediate.int_die_event_timeline where event_type = 'punch replacement' and {_where('event_date', p)} group by 1""")
    pu = None
    for k in sh:
        t = punches(P[k]).rename(columns={"punch_replacements": k}); pu = t if pu is None else pu.merge(t, on="led_by", how="outer")
    pu = pu.fillna(0); pu[list(sh)] = pu[list(sh)].astype(int)
    sharp_month = query(f"""select date_trunc('month', interval_end)::date as month_start, count(*) as sharpenings from intermediate.int_sharpening_intervals where is_run_interval and shots_in_interval_logged is not null and {_where('interval_end', P['twelve_months'])} group by 1 order by 1""")
    s12 = sh["twelve_months"].assign(month_start=pd.to_datetime(sh["twelve_months"]["sharpened"]).dt.to_period("M").dt.to_timestamp()); s12 = s12[s12["against_the_due_count"] != "no burr line on the die"]
    on_time = s12.groupby("month_start").agg(sharpenings_on_a_die_with_a_burr_line=("die_id", "count"), at_or_before_the_due_count=("against_the_due_count", lambda v: int((v == "at or before the due count").sum()))).reset_index()
    b12 = bu["twelve_months"].assign(month_start=pd.to_datetime(bu["twelve_months"]["interval_end"]).dt.to_period("M").dt.to_timestamp())
    burr_month = b12.groupby("month_start").agg(intervals=("die_id", "count"), over_the_limit=("highest", lambda v: int((v > 1).sum()))).reset_index()
    return {"sharpenings_against_the_due_count": counts, "sharpenings_in_the_month": sh["month"], "burr_over_the_limit": burr_counts, "burr_intervals_in_the_month": bu["month"], "dies_due": due_list, "dies_with_a_burr_line": len(due),
            "stops_in_the_month": stops_month, "stops_twelve_months": st12.groupby(["is_pilot_press", "finding"])["stops"].sum().reset_index(), "stops_by_month": stops_by_month, "punch_replacements": pu,
            "sharpenings_by_month": on_time, "burr_by_month": burr_month, "sharpenings_all_by_month": sharp_month}


# -- measurement systems ------------------------------------------------------------
def measurement(P):
    m = P["month"]; as_at = m[1] - pd.Timedelta(days=1)
    status = query(f"""
        select g.gauge_id, g.type, g.location, c.due, c.done, c.removed_from_service,
               (c.due <= {_d(as_at)} and (c.done is null or c.done > {_d(as_at)})) as past_due, (c.removed_from_service is not null and c.removed_from_service <= {_d(as_at)} and (c.done is null or c.done > {_d(as_at)})) as out_of_service
        from staging.stg_calibration__calibrations c join staging.stg_calibration__gauges g using (gauge_id)
        where (c.due <= {_d(as_at)} and (c.done is null or c.done > {_d(as_at)})) or (c.removed_from_service is not null and c.removed_from_service <= {_d(as_at)} and (c.done is null or c.done > {_d(as_at)})) order by c.due""")
    lost = query("select gauge_id, type, location, status from staging.stg_calibration__gauges where status <> 'active'")
    sub = []
    for label in ("month", "month_before", "twelve_months", "twelve_months_before"):
        # past due on the subgroup's date with no calibration done by then, calibrations still open included; out of service by the flag of the characteristic history
        d = query(f"""
            with h as (select subgroup_id, press_id, gauge_id, cast(sample_time as date) as d, gauge_out_of_service from intermediate.int_characteristic_history where {_where('sample_time', P[label])}),
                 late as (select distinct h.subgroup_id from h join staging.stg_calibration__calibrations c on c.gauge_id = h.gauge_id and c.due < h.d and (c.done is null or c.done > h.d))
            select h.press_id, count(*) as subgroups, count(late.subgroup_id) as on_a_gauge_past_due, count(*) filter (where h.gauge_out_of_service) as on_a_gauge_out_of_service,
                   count(*) filter (where late.subgroup_id is not null or h.gauge_out_of_service) as on_a_gauge_past_due_or_out_of_service
            from h left join late using (subgroup_id) group by grouping sets ((1), ()) order by 1""")
        d["press_id"] = d["press_id"].fillna("all presses"); d.insert(0, "period", label); sub.append(d)
    sub = pd.concat(sub, ignore_index=True)
    fixtures = query("select status, count(*) as check_fixtures from marts.mart_dashboard_gauge_studies group by 1 order by 1")
    fixtures_over = query("select fixture_id, part_id, press_id, study_date, study_trigger, pct_grr_of_tolerance, ndc from marts.mart_dashboard_gauge_studies where pct_grr_of_tolerance >= 10 order by pct_grr_of_tolerance desc")
    no_study = query("""select p.primary_press as press_id, g.type as gauge_type, count(*) as characteristics, count(*) filter (where c.critical) as critical_characteristics, count(distinct c.gauge_id) as gauges, count(distinct c.part_id) as parts
                        from staging.stg_spc__characteristics c join staging.stg_erp__parts p using (part_id) left join staging.stg_calibration__gauges g on g.gauge_id = c.gauge_id
                        where c.data_type = 'variable' and c.status = 'active' and c.gauge_id not in (select gauge_id from staging.stg_calibration__gauge_studies) group by grouping sets ((1, 2), (2)) order by 1, 2""")
    no_study["press_id"] = no_study["press_id"].fillna("all presses")
    return {"gauges_past_due_or_out_of_service": status, "gauges_not_active": lost, "subgroups_on_gauges": sub, "check_fixtures_by_grr": fixtures, "check_fixtures_at_10pct_or_more": fixtures_over, "characteristics_on_a_gauge_with_no_study": no_study}


# -- nonconformances ----------------------------------------------------------------
def nonconformances(P):
    rows = []
    for label in ("month", "month_before", "twelve_months", "twelve_months_before"):
        p = P[label]
        s = query(f"select press_id, count(*) as sorting_events, sum(quantity_sorted) as quantity_sorted from marts.mart_sorting_events where {_where('sort_started', p)} group by 1")
        b = query(f"select press_id, count(*) as burr_nonconformances from marts.mart_burr_nonconformances where defect_code = 'burr' and {_where('opened', p)} group by 1")
        d = query("select press_id from intermediate.int_press_redesign order by 1").merge(s, on="press_id", how="left").merge(b, on="press_id", how="left").fillna(0)
        tot = d.drop(columns="press_id").sum(); tot["press_id"] = "all presses"; d = pd.concat([d, pd.DataFrame([tot])], ignore_index=True); d.insert(0, "period", label); rows.append(d)
    d = pd.concat(rows, ignore_index=True); d[["sorting_events", "quantity_sorted", "burr_nonconformances"]] = d[["sorting_events", "quantity_sorted", "burr_nonconformances"]].astype(int)
    b, _ = burr_by_die()
    burr = query(f"""select ncr_id, opened, press_id, part_id, die_id, detected_at, quantity_affected, shots_since_sharpening_at_run_end, sharpening_interval_practice from marts.mart_burr_nonconformances
                     where defect_code = 'burr' and {_where('opened', P['twelve_months'])} order by opened, ncr_id""").merge(b[["die_id", "shots_at_80pct_of_limit"]], on="die_id", how="left")
    burr["position_in_the_stated_interval"] = burr["shots_since_sharpening_at_run_end"] / burr["sharpening_interval_practice"]; burr["position_against_the_due_count"] = burr["shots_since_sharpening_at_run_end"] / burr["shots_at_80pct_of_limit"]
    sort = query(f"""select sorting_event_id, sort_started, press_id, part_id, die_id, defect_code, quantity_sorted, quantity_rejected, sort_basis from marts.mart_sorting_events where {_where('sort_started', P['twelve_months'])} order by 2""")
    monthly = query(f"""select m.month_start, coalesce(s.n, 0) as sorting_events, coalesce(b.n, 0) as burr_nonconformances from (select unnest(range({_d(P['twelve_months'][0])}, {_d(P['twelve_months'][1])}, interval 1 month))::date as month_start) m
                        left join (select date_trunc('month', sort_started)::date as month_start, count(*) as n from marts.mart_sorting_events group by 1) s using (month_start)
                        left join (select date_trunc('month', opened)::date as month_start, count(*) as n from marts.mart_burr_nonconformances where defect_code = 'burr' group by 1) b using (month_start) order by 1""")
    return {"nonconformances_by_press": d, "burr_nonconformances": burr, "sorting_events": sort, "nonconformances_by_month": monthly}


def alarms_by_press_in_the_month(P):
    """Alarm signals of the month by press with what was recorded: nothing, a text of one word, an adjustment."""
    return query(f"""
        select press_id, count(*) as alarm_signals,
               count(*) filter (where (acknowledgement_text is null or acknowledgement_text = '') and not coalesce(adjustment_recorded, false)) as with_nothing_recorded,
               count(*) filter (where acknowledgement_text is not null and acknowledgement_text <> '' and position(' ' in trim(acknowledgement_text)) = 0) as with_a_one_word_text,
               count(*) filter (where coalesce(adjustment_recorded, false)) as with_an_adjustment_recorded
        from intermediate.int_characteristic_history where {_where('sample_time', P['month'])} and data_type = 'variable' and (alarm_raised or alarm_rule_1) group by 1 order by 1""")


def compute(month=MONTH):
    P = periods(month); out = {"periods": P}
    for part in (capability(P), alarms(P), checks(P), limits(P), die_wear(P), measurement(P), nonconformances(P)):
        out.update(part)
    out["alarms_by_press_in_the_month"] = alarms_by_press_in_the_month(P)
    out["alarms_by_month"] = monthly_alarms(P); out["planned_checks_by_month"], out["entries_by_month"] = monthly_checks(P)
    for v in out.values():
        if isinstance(v, pd.DataFrame) and "month_start" in v.columns:
            v["month_start"] = pd.to_datetime(v["month_start"])
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60); pd.set_option("display.max_colwidth", 60); pd.set_option("display.max_rows", 400)
    for name, table in compute().items():
        print(f"\n== {name}")
        print(table.round(4).to_string(index=False) if isinstance(table, pd.DataFrame) else table)
