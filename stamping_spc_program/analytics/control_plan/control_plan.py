"""Control plans and chart book: what is in force at 31 December 2025 on the parts that run on PR-03, PR-06 and PR-09.
Three control plans in the AIAG layout, the chart book, and an index of the other parts on those presses. Writes docs/control_plan/control_plan_and_chart_book.html
and returns the table of every number in the text lines, and of every table, with the mart each is read from."""
import pandas as pd

from analytics.data import query
from analytics.die_wear.die_wear import burr_by_die
from analytics.per_stroke.figures import L as EWMA_L, LAMBDA as EWMA_LAMBDA
from analytics.style import style as S

AS_AT = "2025-12-31"
FULL = [("P-20417", "PR-06"), ("P-31102", "PR-09"), ("P-10823", "PR-03")]
CHART_NAME = {"three-way chart": "three-way chart", "tool-wear chart": "tool-wear chart", "X-bar and R": "X-bar and R", "attribute check": "attribute check", "no limit set in force": "no chart: sharpening count"}
RECALCULATION = {"three-way chart": "After each sharpening, on a baseline of at least 25 subgroups spanning five coil changes", "tool-wear chart": "On a planned trigger, from the die's earlier sharpening intervals",
                 "X-bar and R": "After each sharpening, on a stable 25-subgroup baseline", "attribute check": "", "no limit set in force": ""}
SCHEME = "five consecutive parts"
BURR = "Burr height on the laboratory gauge has no chart. It is controlled by the die's burr line and by the sharpening count (next due in the sharpening table)."
ASSESSMENT_SECTION = 4          # the section of the assessment report on the record under the charts


def plan():
    return query("select * from marts.mart_control_plan order by press_id, part_id, characteristic_id")


def dies():
    """Each die's shot count at the end of the record, its last sharpening, and the burr line behind the sharpening count."""
    d = query(f"""
        with last as (select die_id, event_date as last_sharpening, shot_count as shot_count_at_last_sharpening
                      from intermediate.int_die_event_timeline where starts_interval and event_date <= date '{AS_AT}'
                      qualify row_number() over (partition by die_id order by event_date desc, shot_count desc) = 1),
             ran as (select die_id, shots_in_interval_logged as last_interval_run
                     from intermediate.int_sharpening_intervals where interval_end is not null and is_run_interval and shots_in_interval_logged is not null
                     qualify row_number() over (partition by die_id order by interval_end desc) = 1)
        select d.die_id, d.part_ids as part_id, d.stations, d.shot_count as shot_count_at_the_end_of_the_record, d.sharpening_interval_shots as master_interval,
               l.last_sharpening, l.shot_count_at_last_sharpening, d.shot_count - l.shot_count_at_last_sharpening as shots_since_sharpening, r.last_interval_run
        from staging.stg_erp__dies d left join last l using (die_id) left join ran r using (die_id)
        where d.die_id in (select die_id from marts.mart_control_plan) order by d.die_id""")
    b, _ = burr_by_die()
    d = d.merge(b[["die_id", "shots_at_80pct_of_limit", "low", "high"]], on="die_id", how="left")
    d["next_sharpening_due_at_shot_count"] = d["shot_count_at_last_sharpening"] + d["shots_at_80pct_of_limit"]
    d["shots_past_due"] = d["shot_count_at_the_end_of_the_record"] - d["next_sharpening_due_at_shot_count"]
    return d


def reaction_plan():
    return query("""select signal, step, action, owner, count(distinct characteristic_id) as characteristics from staging.stg_spc__reaction_plan_steps
                    where characteristic_id in (select characteristic_id from marts.mart_control_plan) group by 1, 2, 3, 4 order by 1, 2""")


def count_check(p):
    """Every characteristic against what controls it: a limit set in force, an attribute check, or the sharpening count."""
    g = p.assign(matched_to=p["chart_in_force"].map(lambda c: "an attribute check" if c == "attribute check" else ("the sharpening count (burr on the laboratory gauge)" if c == "no limit set in force" else "a limit set in force")))
    t = g.groupby(["press_id", "matched_to"]).agg(characteristics=("characteristic_id", "count"), parts=("part_id", "nunique")).reset_index()
    total = g.groupby("matched_to").agg(characteristics=("characteristic_id", "count"), parts=("part_id", "nunique")).reset_index().assign(press_id="all three presses")
    return pd.concat([t, total], ignore_index=True)[["press_id", "matched_to", "characteristics", "parts"]]


def gauges_with_no_study(p):
    g = p[(p["data_type"] == "variable") & p["pct_grr_of_tolerance"].isna()]
    return g.groupby(["gauge_id", "gauge_type"]).agg(characteristics=("characteristic_id", "count"), parts=("part_id", "nunique")).reset_index().sort_values(["gauge_type", "gauge_id"]), len(g)


def fmt_value(v):
    if v != v or v is None:
        return ""
    s = f"{v:.4f}"          # specification limits are stated to four places; a trailing zero is dropped
    return s[:-1] if s.endswith("0") else s


def frequency(r):
    """The check frequency in force: as recorded, to the half hour, or the master's where none is recorded."""
    rec = r.frequency_minutes_as_recorded
    if rec != rec:
        return f"{int(r.frequency_minutes_in_the_master)} min"
    rec = int(round(rec / 30.0) * 30) if rec < 300 else int(round(rec / 60.0) * 60)
    return f"{rec} min"


def recalculation(r, last_sharpening):
    """The recalculation trigger; on a three-way chart whose limits predate the die's last sharpening, what they were set from."""
    if r.chart_in_force == "three-way chart" and pd.Timestamp(r.limits_in_force_from) < pd.Timestamp(last_sharpening):
        t = pd.Timestamp(last_sharpening)
        return f"Limits set from {int(r.coil_changes_spanned) + 1} coils before the sharpening of {t.day} {t.strftime('%B %Y')}; recalculation is due after six coil changes on the new edge."
    return RECALCULATION[r.chart_in_force]


def header(part_id):
    """The control plan header fields the record holds for a part."""
    return query("""select p.part_id, p.revision, c.customer_name, p.ppap_date, (select min(s.effective_from) from staging.stg_spc__reaction_plan_steps s join staging.stg_spc__characteristics k using (characteristic_id) where k.part_id = p.part_id) as revision_date
                    from staging.stg_erp__parts p join staging.stg_erp__customers c using (customer_id) where p.part_id = ?""", [part_id]).iloc[0]


def specification(r):
    if r.lsl != r.lsl:
        return f"{fmt_value(r.usl)} {r.unit} maximum"
    return f"{fmt_value(r.nominal)} ({fmt_value(r.lsl)} to {fmt_value(r.usl)}) {r.unit}"


def control_plan_table(p, part_id, die, steps):
    """The control plan of one part in the AIAG column order: coil load and feed, then stamping with its product and process characteristics."""
    g = p[p["part_id"] == part_id]; g0 = g.iloc[0]; machine = f"{g0.press_id}; die {g0.die_id}, {int(die.stations)} stations"
    step1 = steps[(steps["signal"] == "rule 1") & (steps["step"] == 1)]["action"].iloc[0]; rows = []

    def row(operation, mach, number="", product="", process="", special="", spec="", technique="", size="", freq="", method="", reaction=""):
        rows.append({"Process name or operation description": operation, "Machine, device, jig, tools for manufacturing": mach, "Characteristic number": number, "Product characteristic": product, "Process characteristic": process,
                     "Special characteristic classification": special, "Product or process specification and tolerance": spec, "Evaluation or measurement technique": technique, "Sample size": size, "Sample frequency": freq, "Control method": method, "Reaction plan": reaction})
    row("Coil load and feed", g0.press_id, process="Coil certificate thickness and hardness", spec="–", technique="Coil certificate", size="Each coil", freq="Each coil change",
        method=f"Coil-change subgroup on the three-way charts, with a centring step when its mean is outside one sigma of target (chart book, Section {SEC['charts']})", reaction=f"Chart book, Section {SEC['reaction']}")
    for r in g.itertuples():
        fixture = f"; {r.gauge_id}" if r.gauge_type == "check fixture" else ""
        study = f"{r.pct_grr_of_tolerance:.1f}% GRR of tolerance, ndc {int(r.ndc)}" if r.pct_grr_of_tolerance == r.pct_grr_of_tolerance else ("" if r.data_type == "attribute" else "no study on this gauge")
        gauge = r.gauge_id + ("" if r.gauge_type != r.gauge_type else f" ({r.gauge_type})")
        size = f"{int(r.subgroup_size)} consecutive parts" if r.data_type == "variable" else f"{int(r.subgroup_size)} parts, accept or reject"
        chart = CHART_NAME[r.chart_in_force]
        method = (f"{chart[0].upper() + chart[1:]} (chart book, Section {SEC['charts']})" if r.chart_in_force in ("three-way chart", "tool-wear chart", "X-bar and R") else
                  (f"Attribute check" if r.chart_in_force == "attribute check" else f"No chart: sharpening at the due count (chart book, Section {SEC['sharpening']})"))
        row("Stamping", machine + fixture, r.characteristic_id, r.characteristic_name, special=("Critical" + (", customer designated" if r.customer_designated else "")) if r.critical else "", spec=specification(r), technique=gauge + (f"; {study}" if study else ""), size=size,
            freq=f"{frequency(r)} ({r.parts_between_checks_at_run_speed:,.0f} parts at run speed)", method=method, reaction=f"Chart book, Section {SEC['reaction']}. Rule 1, step 1: {step1}" if r.reaction_plan_steps else "")
    row("Stamping", machine, process="Per-stroke total tonnage and channel shares", spec=f"EWMA limits at {EWMA_L} sigma of the EWMA about the level of the run's first 500 strokes; one channel share residual beyond {EWMA_L} sigma", technique=f"Press monitor, {int(g0.load_cell_channels)} load cell channels", size="Every stroke", freq="Continuous",
        method=f"EWMA on the total and channel share charts; the press stops on a signal (chart book, Section {SEC['per-stroke']})", reaction="Toolmaker inspects the die and records the finding; sorting runs back to the signal")
    due = "" if die.shots_at_80pct_of_limit != die.shots_at_80pct_of_limit else f"{die.shots_at_80pct_of_limit:,.0f} shots since sharpening (burr at 80% of its limit)"
    row("Stamping", machine, process="Die shots since sharpening", spec=due, technique="Die shot count, die maintenance log", size="Each run", freq="Each run", method=f"Sharpening at the due count (chart book, Section {SEC['sharpening']})", reaction="Pull the die at the count")
    return S.table(pd.DataFrame(rows), cls="data wide")


def charts_table(p, part_id, last_sharpening):
    g = p[p["part_id"] == part_id]; c = g[g["chart_in_force"] != "attribute check"]
    b = pd.DataFrame({
        "Characteristic": c["characteristic_id"], "Chart": c["chart_in_force"].map(CHART_NAME), "Limits in force from": c["limits_in_force_from"].map(lambda v: "" if v != v else str(v)[:10]),
        "Centre line": c["centre_line"].map(fmt_value), "LCL, means": c["lcl_mean"].map(fmt_value), "UCL, means": c["ucl_mean"].map(fmt_value), "UCL, range": c["ucl_range"].map(fmt_value),
        "Subgroups used": c["subgroups_used"].map(lambda v: "" if v != v else f"{int(v):,}"), "Coil changes spanned": c["coil_changes_spanned"].map(lambda v: "" if v != v or v is pd.NA else f"{int(v)}"),
        "Wear line, mm per 100,000 shots": c["slope_per_100k_shots"].map(lambda v: "" if v != v else f"{v:.4f}"),
        "Recalculation": [recalculation(r, last_sharpening) for r in c.itertuples()], "Reaction plan": c["reaction_plan_steps"].map(lambda n: f"{int(n)} steps" if n else "")})
    return S.table(b)


def die_table(d, die_ids):
    g = d[d["die_id"].isin(die_ids)].sort_values("shots_past_due", ascending=False)
    t = pd.DataFrame({"Die": g["die_id"], "Stations": g["stations"], "Shot count at the end of the record": g["shot_count_at_the_end_of_the_record"].map("{:,.0f}".format), "Last sharpening": g["last_sharpening"].map(lambda v: str(v)[:10]),
                      "Shot count at the last sharpening": g["shot_count_at_last_sharpening"].map("{:,.0f}".format), "Shots since": g["shots_since_sharpening"].map("{:,.0f}".format),
                      "Burr reaches 80% of its limit at, shots since sharpening (95% interval)": [("" if v != v else f"{v:,.0f} ({lo:,.0f} to {hi:,.0f})") for v, lo, hi in zip(g["shots_at_80pct_of_limit"], g["low"], g["high"])],
                      "Next due, shot count (burr at 80% of its limit)": [("" if v != v else f"{v:,.0f}" + (f", past due by {pd_:,.0f}" if pd_ > 0 else "")) for v, pd_ in zip(g["next_sharpening_due_at_shot_count"], g["shots_past_due"])],
                      "Last interval (strokes)": g["last_interval_run"].map(lambda v: "" if v != v else f"{v:,.0f}"), "Master interval (strokes)": g["master_interval"].map("{:,.0f}".format)})
    return S.table(t)


def summary_table(p, d):
    rows = []
    full = {x for x, _ in FULL}
    for (press, part), g in p[~p["part_id"].isin(full)].groupby(["press_id", "part_id"], sort=True):
        v = g[g["limits_in_force_from"].notna()]; st = g["gauge_study_date"].dropna(); die = d[d["die_id"] == g["die_id"].iloc[0]].iloc[0]
        counts = g["chart_in_force"].value_counts()
        rows.append({"Press": press, "Part": part, "Die": g["die_id"].iloc[0], "Characteristics": len(g), "Critical": int(g["critical"].sum()),
                     "Three-way": int(counts.get("three-way chart", 0)), "Tool-wear": int(counts.get("tool-wear chart", 0)), "X-bar and R": int(counts.get("X-bar and R", 0)), "Attribute": int(counts.get("attribute check", 0)), "Sharpening count": int(counts.get("no limit set in force", 0)),
                     "Frequency, critical variable": " / ".join(sorted({frequency(r) for r in g[g["critical"] & (g["data_type"] == "variable")].itertuples()})) or "none critical",
                     "Limits in force from": f"{str(v['limits_in_force_from'].min())[:10]} to {str(v['limits_in_force_from'].max())[:10]}",
                     "Gauge studies": "none" if st.empty else f"{str(st.min())[:10]} to {str(st.max())[:10]}",
                     "Next due, shot count (burr at 80% of its limit)": f"{die.next_sharpening_due_at_shot_count:,.0f}" + (f", past due by {die.shots_past_due:,.0f}" if die.shots_past_due > 0 else ""),
                     "Last interval (strokes)": "" if die.last_interval_run != die.last_interval_run else f"{die.last_interval_run:,.0f}", "Master interval (strokes)": f"{die.master_interval:,.0f}"})
    return S.table(pd.DataFrame(rows))


SEC = {"charts": 5, "sharpening": 6, "reaction": 7, "per-stroke": 8, "index": 9, "count": 10, "gauges": 11}


def build():
    p, d, rp = plan(), dies(), reaction_plan()
    check = count_check(p); no_study, n_no_study = gauges_with_no_study(p)
    trace = []          # (section, value as printed or the table, read from)
    body = []
    body.append('<h2 id="in-force">1. In force at 31 December 2025</h2>')
    body.append(f"<p>{len(p)} characteristics on {p['part_id'].nunique()} parts on PR-03, PR-06 and PR-09: three control plans in full (Sections 2 to 4) and {p['part_id'].nunique() - len(FULL)} in the index (Section {SEC['index']}). {BURR} "
                f"{n_no_study} characteristics are measured on gauges with no measurement study; those gauges are listed in Section {SEC['gauges']}, and the gauge studies of the assessment are in the assessment report, Section {ASSESSMENT_SECTION}.</p>")
    trace += [("1. In force", str(len(p)), "mart_control_plan: rows"), ("1. In force", str(p["part_id"].nunique()), "mart_control_plan: distinct part_id"), ("1. In force", str(p["part_id"].nunique() - len(FULL)), "mart_control_plan: distinct part_id less the three in full"),
              ("1. In force", str(n_no_study), "mart_control_plan: variable characteristics with pct_grr_of_tolerance null")]
    key = p.groupby("chart_in_force").agg(characteristics=("characteristic_id", "count"), critical=("critical", "sum"), parts=("part_id", "nunique")).reindex(list(CHART_NAME)).reset_index()
    key["scheme"] = key["chart_in_force"].map({"three-way chart": f"Subgroup means on an individuals chart with limits from the moving range of the baseline means, and a range chart; {SCHEME}; a coil-change subgroup with a centring step when its mean is outside one sigma of target",
                                               "tool-wear chart": f"Centre line on the regression of diameter on shots since sharpening, limits about the line; {SCHEME}", "X-bar and R": f"Means and range charts; {SCHEME}",
                                               "attribute check": "Accept or reject against the limit sample (burr) or the pin gauge (hole diameter)", "no limit set in force": "Burr height on the laboratory gauge, a variable characteristic with no chart"})
    key["chart_in_force"] = key["chart_in_force"].map(CHART_NAME)
    body.append(S.table(key.rename(columns={"chart_in_force": "Chart", "characteristics": "Characteristics", "critical": "Critical", "parts": "Parts", "scheme": "Scheme"})[["Chart", "Scheme", "Characteristics", "Critical", "Parts"]]))
    trace.append(("1. In force", "table: charts in force", "mart_control_plan.chart_in_force, critical, part_id"))

    parts = []
    for n, (part, press) in enumerate(FULL, start=2):
        g = p[p["part_id"] == part].iloc[0]; die = d[d["die_id"] == g.die_id].iloc[0]; h = header(part); parts.append((part, press, g, die))
        steps = query("select signal, step, action from staging.stg_spc__reaction_plan_steps where characteristic_id in (select characteristic_id from marts.mart_control_plan where part_id = ?) group by all", [part])
        body.append(f'<h2 id="{part}">{n}. Control plan, {part} on {press}</h2>')
        rev = pd.Timestamp(h.revision_date); ppap = pd.Timestamp(h.ppap_date)
        head = pd.DataFrame([("Phase", "Production"), ("Part number and latest change level", f"{h.part_id}, revision {h.revision}"), ("Customer", h.customer_name), ("PPAP date", f"{ppap.day} {ppap.strftime('%B %Y')}"), ("Revision date", f"{rev.day} {rev.strftime('%B %Y')}"),
                             ("Press and die", f"{press}; die {g.die_id}, {int(die.stations)} stations; {int(g.parts_per_stroke)} per stroke at {g.run_speed_spm:.0f} strokes a minute; per-stroke monitoring on {int(g.load_cell_channels)} channels"),
                             ("Material", f"{g.material_grade}, {g.thickness_mm:.2f} mm")], columns=["Control plan", ""])
        body.append(S.table(head)); body.append(control_plan_table(p, part, die, steps))
        sec = f"{n}. Control plan, {part}"
        trace += [(sec, f"{g.thickness_mm:.2f}", "mart_control_plan.thickness_mm"), (sec, str(int(g.parts_per_stroke)), "mart_control_plan.parts_per_stroke"), (sec, f"{g.run_speed_spm:.0f}", "mart_control_plan.run_speed_spm"), (sec, str(int(g.load_cell_channels)), "mart_control_plan.load_cell_channels"),
                  (sec, "header: part, revision, customer, PPAP date, revision date", "stg_erp__parts, stg_erp__customers; stg_spc__reaction_plan_steps.effective_from, earliest on the part"),
                  (sec, "table: control plan", "mart_control_plan: specification, gauge, study, subgroup, frequency as recorded, parts_between_checks_at_run_speed, chart in force; stg_spc__reaction_plan_steps, rule 1 step 1; die due count from the burr line (die wear analysis)")]

    body.append(f'<h2 id="charts">{SEC["charts"]}. Chart book: charts in force</h2>')
    for part, press, g, die in parts:
        body.append(f"<h3>{part} on {press}</h3>" + charts_table(p, part, die.last_sharpening))
        trace.append((f"{SEC['charts']}. Charts in force", f"table: {part}", "mart_control_plan: limit set in force (mart_limits_as_set), reaction_plan_steps; int_die_event_timeline for the last sharpening"))
    body.append(f'<h2 id="sharpening">{SEC["sharpening"]}. Chart book: sharpening</h2>')
    body.append(f"<p>{BURR}</p>")
    body.append(die_table(d, [g.die_id for _, _, g, _ in parts]))
    trace.append((f"{SEC['sharpening']}. Sharpening", "table: sharpening", "stg_erp__dies, int_die_event_timeline, int_sharpening_intervals; burr line from mart_wear_points (die wear analysis)"))

    body.append(f'<h2 id="reaction">{SEC["reaction"]}. Chart book: reaction plan</h2>')
    body.append("<p>The steps on every variable characteristic with a limit set in force.</p>")
    body.append(S.table(rp.rename(columns={"signal": "Signal", "step": "Step", "action": "Action", "owner": "Owner", "characteristics": "Characteristics"})))
    trace.append((f"{SEC['reaction']}. Reaction plan", "table: reaction plan steps", "stg_spc__reaction_plan_steps on the characteristics of mart_control_plan"))

    body.append(f'<h2 id="per-stroke">{SEC["per-stroke"]}. Chart book: per-stroke monitoring</h2>')
    body.append("<p>On every die on the press, from 5 May 2025; the press stops on a signal. The press stops through the historian's signal to the press control's external stop input.</p>")
    ch = p.groupby("press_id")["load_cell_channels"].first().reset_index()
    ps = pd.DataFrame({"Press": ch["press_id"], "Channels": ch["load_cell_channels"].astype(int), "Chart on the total": f"EWMA, two-sided, lambda {EWMA_LAMBDA}, limits at {EWMA_L} sigma of the EWMA", "Chart on each channel": f"Channel share of the total, one residual beyond {EWMA_L} sigma",
                       "Baseline": "First 500 production strokes of the run, first-order autoregressive fit", "On a stop": "Toolmaker inspects the die and records the finding; sorting runs back to the signal"})
    body.append(S.table(ps))
    trace.append((f"{SEC['per-stroke']}. Per-stroke monitoring", "table: channels and chart parameters", "mart_control_plan.load_cell_channels; the chart parameters as designed (per-stroke analysis)"))

    body.append(f'<h2 id="index">{SEC["index"]}. Chart book: index of control plans, the other parts on PR-03, PR-06 and PR-09</h2>')
    body.append("<p>One row per part; frequency as in force.</p>")
    body.append(summary_table(p, d))
    trace.append((f"{SEC['index']}. Index of control plans", "table: one row per part", "mart_control_plan by part; dies as in the sharpening tables"))

    body.append(f'<h2 id="count">{SEC["count"]}. Chart book: count of characteristics</h2>')
    body.append("<p>Every characteristic against what controls it.</p>")
    body.append(S.table(check.rename(columns={"press_id": "Press", "matched_to": "Controlled by", "characteristics": "Characteristics", "parts": "Parts"})))
    body.append(f'<h2 id="gauges">{SEC["gauges"]}. Chart book: gauges with no measurement study</h2>')
    body.append(S.table(no_study.rename(columns={"gauge_id": "Gauge", "gauge_type": "Type", "characteristics": "Characteristics measured", "parts": "Parts"})))
    trace += [(f"{SEC['count']}. Count of characteristics", "table: count check", "mart_control_plan.chart_in_force by press_id"), (f"{SEC['gauges']}. Gauges with no measurement study", "table: gauges with no measurement study", "mart_control_plan: variable characteristics with pct_grr_of_tolerance null, by gauge_id")]
    body.append("<p class='glossary'>Limits are those in force at 31 December 2025. Frequency is as recorded from March to December 2025 (the median minutes between consecutive routine checks on a run, to the half hour). "
                "Parts between checks are at the part's median run speed in 2025. A gauge study is the latest on that gauge or check fixture; gauge R&amp;R is by the ANOVA method, %GRR of tolerance at 6 sigma. "
                "The next sharpening is due when the die's burr line reaches 80% of the burr limit, counted from the last sharpening; the burr line is the regression of burr height on shots since sharpening on the burr gauge readings of 2023 and 2024, with its 95% interval. The last interval is the last run interval; a sharpening followed within 20,000 shots by a rebuild is counted as the rebuild. Dimensions in millimetres, angles in degrees.</p>")

    toc = [("in-force", "1. In force")] + [(part, f"{n}. Control plan, {part}") for n, (part, _) in enumerate(FULL, start=2)] + [("charts", f"{SEC['charts']}. Charts in force"), ("sharpening", f"{SEC['sharpening']}. Sharpening"), ("reaction", f"{SEC['reaction']}. Reaction plan"),
           ("per-stroke", f"{SEC['per-stroke']}. Per-stroke monitoring"), ("index", f"{SEC['index']}. Index of control plans"), ("count", f"{SEC['count']}. Count of characteristics"), ("gauges", f"{SEC['gauges']}. Gauges with no study")]
    content = "\n".join(body).replace('<table class="data wide">', '<div style="overflow-x:auto"><table class="data" style="font-size:12px;min-width:1700px">').replace('<table class="data">','<div style="overflow-x:auto"><table class="data" style="font-size:12px">').replace("</table>", "</table></div>")          # a wide table scrolls inside the text column
    html = S.report_shell("Control Plans and Chart Book, PR-03, PR-06 and PR-09", "", "", content, toc)
    out = S.DOCS / "control_plan"; out.mkdir(parents=True, exist_ok=True)
    (out / "control_plan_and_chart_book.html").write_text(html, encoding="utf8", newline="\n")
    return html, p, d, check, pd.DataFrame(trace, columns=["section", "value_as_printed", "read_from"])


if __name__ == "__main__":
    html, p, d, check, trace = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "control_plan_numbers.csv", index=False, lineterminator="\n")
    print(len(html), len(trace)); print(check.to_string(index=False))
