"""The SPC terminal screen and the press monitor screen for PR-03 at one moment on one run: the press-side SPC software
as the operator and die setter see it, and the press monitor historian's display. Writes docs/screens/spc_terminal_pr_03.html
and docs/screens/press_monitor_pr_03.html, their figures, and the table of every value on each with what it is read from.

Usage: python -m analytics.screens.screens"""
import html as _html

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analytics.data import query
from analytics.die_wear.die_wear import burr_by_die
from analytics.per_stroke.figures import L, LAMBDA
from analytics.style import style as S

PRESS, RUN = "PR-03", "R25-01738"
AS_AT = pd.Timestamp("2025-10-07 09:45:00")          # the screen time; mart_screen_run_strokes is built to the same run and time
SHIFT_START, SHIFT_CHANGE = "06:00", "14:30"
FORMED = ("formed height", "bend angle")
R5 = ["r1", "r2", "r3", "r4", "r5"]
MR_FACTOR = 3.267 * 1.128 / 3          # upper limit of the moving range of the means, from the half-width of the individuals limits
BG, PANEL, GRID, TEXT, MUTED = "#0b1015", "#121a23", "#243140", "#dde6ee", "#8fa3b8"
OK, WARN, ALARM, LINE, LIMIT, SPEC = "#5fd38a", "#ffb300", "#ff5c5c", "#6fb1e8", "#c9d6e3", "#55687c"
DARK = {"figure.facecolor": PANEL, "axes.facecolor": PANEL, "savefig.facecolor": PANEL, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": TEXT, "font.size": 9, "axes.labelsize": 8.5,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8}
RULES = {"2": "rule 2", "3": "rule 3", "4": "rule 4"}

CSS = """
*{box-sizing:border-box} body{margin:0;background:#05080b;color:#dde6ee;font-family:"Segoe UI",Tahoma,sans-serif;font-size:12.5px}
.window{max-width:1600px;margin:14px auto 0;border:1px solid #263444;background:#0b1015}
.titlebar{background:#1c2a39;border-bottom:1px solid #263444;padding:6px 12px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;font-size:12px}
.titlebar .app{font-weight:700;letter-spacing:.3px} .titlebar .who{color:#c9d6e3;display:flex;gap:16px;flex-wrap:wrap}
.strip{background:#16202b;border-bottom:2px solid #263444;padding:8px 12px;display:flex;gap:8px 22px;flex-wrap:wrap;align-items:center}
.kv{display:flex;flex-direction:column} .kv .l{color:#8fa3b8;font-size:10px;text-transform:uppercase;letter-spacing:.8px} .kv .v{font-weight:600;font-size:13px}
.lamp{display:inline-block;padding:4px 12px;border-radius:3px;font-weight:700;letter-spacing:.6px;font-size:12px}
.lamp.ok{background:#1d6b3a} .lamp.warn{background:#9a6a12} .lamp.alarm{background:#a11b1b}
.grid{display:grid;gap:10px;padding:10px 12px} .g-spc{grid-template-columns:420px minmax(0,1fr) 320px} .g-pm{grid-template-columns:minmax(0,1.9fr) minmax(0,1fr)}
.col{display:flex;flex-direction:column;gap:10px;min-width:0}
.panel{background:#121a23;border:1px solid #243140;padding:8px 10px;min-width:0}
.panel h3{margin:0 0 6px;font-size:11px;color:#8fa3b8;text-transform:uppercase;letter-spacing:1px;display:flex;justify-content:space-between;gap:8px}
table{border-collapse:collapse;width:100%} td,th{padding:3px 6px;border-bottom:1px solid #1f2b38;text-align:left;vertical-align:top} th{color:#8fa3b8;font-weight:600;font-size:11px}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap} .muted{color:#6f8296} .tw{overflow-x:auto}
td.name{white-space:nowrap} tr.pick{cursor:pointer} tr.pick:hover td{background:#182330} tr.sel td{background:#1f3044} tr.sel td:first-child{box-shadow:inset 3px 0 0 #6fb1e8}
.chip{display:inline-block;padding:1px 7px;border-radius:2px;font-size:10.5px;font-weight:700;letter-spacing:.4px;white-space:nowrap}
.chip.acked{background:#3a2226;color:#d9a3a3} .chip.ok{background:#17402a;color:#7fe0a3} .chip.warn{background:#4a3608;color:#ffcf7a} .chip.alarm{background:#5a1414;color:#ff9c9c} .chip.info{background:#2a3a4c;color:#c9d6e3}
.crit{color:#ffcf7a;font-weight:700}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:6px} .tile{background:#0f161e;border:1px solid #243140;padding:6px 8px} .tile .v{font-size:19px;font-weight:700} .tile .l{font-size:10.5px;color:#8fa3b8}
.reads{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:6px} .reads div{background:#0f161e;border:1px solid #243140;padding:5px 4px;text-align:center;font-variant-numeric:tabular-nums;font-weight:600}
.bar{position:relative;height:14px;background:#0f161e;border:1px solid #243140;border-radius:2px} .bar .fill{position:absolute;left:0;top:0;bottom:0;background:#2E6FA7} .bar .due{position:absolute;top:-3px;bottom:-3px;width:2px;background:#ffb300}
img{max-width:100%;display:block} [hidden]{display:none!important}
.statusline{border-top:1px solid #263444;background:#16202b;color:#8fa3b8;padding:5px 12px;font-size:11.5px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.credit{max-width:1600px;margin:6px auto 16px;color:#6f8296;font-size:11px;padding:0 4px}
@media(max-width:1340px){.g-spc{grid-template-columns:420px minmax(0,1fr)} .g-spc .col.right{grid-column:1 / -1} .g-spc .col.right>.col{flex-direction:row;flex-wrap:wrap} .g-spc .col.right>.col>.panel{flex:1 1 260px}}
@media(max-width:820px){.g-spc,.g-pm{grid-template-columns:minmax(0,1fr)} .window{margin-top:0;border-left:0;border-right:0}}
"""


def page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body>{body}
<div class="credit">{S.CREDIT}</div></body></html>"""


def e(s):
    return _html.escape(str(s))


def hm(t):
    return pd.Timestamp(t).strftime("%H:%M")


def fmt(v, unit="mm"):
    return f"{v:.2f}" if unit == "deg" else f"{v:.3f}"


def save(f, name, alt):
    f.savefig(S.DOCS / "figures" / f"{name}.png", format="png", dpi=S.CHART_DPI)
    plt.close(f)
    return f'<img alt="{alt}" src="../figures/{name}.png">'


# -- the moment -----------------------------------------------------------------
def moment():
    """Everything the two screens show, read as at the screen time."""
    m = {}
    m["run"] = query("""select r.*, p.revision, p.material_grade, p.thickness_mm, c.customer_name from intermediate.int_run_shots r join staging.stg_erp__parts p using (part_id) join staging.stg_erp__customers c using (customer_id) where r.run_id = ?""", [RUN]).iloc[0]
    m["die"] = query("select * from staging.stg_erp__dies where die_id = ?", [m["run"].die_id]).iloc[0]
    h = query("""select h.*, k.chart_type from intermediate.int_characteristic_history h join staging.stg_spc__characteristics k using (characteristic_id)
                 where h.run_id = ? and h.sample_time <= ? order by h.sample_time, h.characteristic_id, h.subgroup_id""", [RUN, AS_AT])
    m["history"] = h
    m["characteristics"] = query("select characteristic_id, name, type, nominal, usl, lsl, unit, critical, customer_designated, gauge_id, data_type from staging.stg_spc__characteristics where part_id = ? and status = 'active' order by 1", [m["run"].part_id])
    m["limit_sets"] = query("""select characteristic_id, method from marts.mart_limits_as_set where part_id = ? and effective_from <= ? and (effective_to is null or effective_to > ?)
                               qualify row_number() over (partition by characteristic_id order by effective_from desc) = 1""", [m["run"].part_id, AS_AT, AS_AT]).set_index("characteristic_id")["method"]
    m["frequency"] = query("select characteristic_id, frequency_minutes_as_recorded, frequency_minutes_in_the_master from marts.mart_control_plan where part_id = ?", [m["run"].part_id]).set_index("characteristic_id")
    m["alarms"] = alarms = query("""select a.alarm_id, a.subgroup_id, a.rule, a.raised_at, a.acknowledged_at, a.acknowledged_by, a.text, s.characteristic_id from staging.stg_spc__alarms a join staging.stg_spc__subgroups s using (subgroup_id)
                           where s.run_id = ? and a.raised_at <= ? order by a.raised_at, a.alarm_id""", [RUN, AS_AT])
    open_alarms = set(alarms[pd.to_datetime(alarms["acknowledged_at"]) > AS_AT]["subgroup_id"])          # raised by the screen time and acknowledged after it
    h.loc[h["subgroup_id"].isin(open_alarms), ["adjustment_recorded", "acknowledgement_text"]] = [False, None]; m["open_alarms"] = open_alarms
    coil_id = h[h["coil_id"].notna()]["coil_id"].iloc[-1]
    m["coil"] = query("select * from staging.stg_erp__coils where coil_id = ?", [coil_id]).iloc[0]
    m["stops"] = query("""select f.fault_event_id, f."timestamp" as stopped_at, f.stroke_no, case when f.input = 'EWMA signal' then 'EWMA on the total' else 'channel share' end as chart, f.finding, f.cleared_at, f.cleared_by, f.die_event_id
                          from staging.stg_press_monitor__fault_events f where f.run_id = ? and f."timestamp" <= ? and f.input in ('EWMA signal', 'channel share signal') order by 2""", [RUN, AS_AT])
    m["strokes"] = query("select stroke_no, stroke_ts, total_kn, strokes_per_minute, peak_kn_ch1, peak_kn_ch2, peak_kn_ch3, peak_kn_ch4, share_ch1, share_ch2, share_ch3, share_ch4 from marts.mart_screen_run_strokes order by stroke_no")
    assert pd.Timestamp(query("select max(screen_as_at) as t from marts.mart_screen_run_strokes")["t"].iloc[0]) == AS_AT
    m["baseline"] = query("select baseline_total_kn_mean as mean, baseline_total_kn_sd as sd, baseline_lag_1_autocorrelation as phi, setup_strokes from marts.mart_per_stroke_run_tonnage where run_id = ?", [RUN]).iloc[0]
    m["last_sharpening"] = query("""select event_date, shot_count from intermediate.int_die_event_timeline where die_id = ? and starts_interval and event_date <= cast(? as date)
                                    qualify row_number() over (order by event_date desc, shot_count desc) = 1""", [m["run"].die_id, AS_AT]).iloc[0]
    m["punches"] = query("""select e.event_date, e.notes, e.toolmaker, e.fault_event_id, f."timestamp" as stopped_at from intermediate.int_die_event_timeline e left join staging.stg_press_monitor__fault_events f using (fault_event_id)
                            where e.die_id = ? and e.event_type = 'punch replacement' and e.event_date >= ? and coalesce(f."timestamp", cast(e.event_date as timestamp)) <= ? order by 1""", [m["run"].die_id, m["last_sharpening"].event_date, AS_AT])
    b, _ = burr_by_die(); m["due_count"] = float(b.set_index("die_id").loc[m["run"].die_id, "shots_at_80pct_of_limit"])
    m["shots_since_sharpening"] = float(m["run"].shots_since_sharpening_at_start) + float(m["strokes"]["stroke_no"].iloc[-1])
    return m


def chart_of(m, c):
    """The chart in force on a characteristic at the screen time."""
    if c.data_type == "attribute":
        return "attribute check"
    method = m["limit_sets"].get(c.characteristic_id)
    if method is None:
        return "no chart: sharpening count"
    return "tool-wear chart" if method == "tool-wear regression" else ("three-way chart" if c.type in FORMED else "X-bar and R")


# -- SPC terminal ----------------------------------------------------------------
def spc_chart(m, c, chart):
    """The selected characteristic over the run on its chart: means with the limits in force at each entry, the moving
    range of the means on a three-way chart, and the range chart."""
    d = m["history"]; d = d[(d["characteristic_id"] == c.characteristic_id) & d["subgroup_mean"].notna()].reset_index(drop=True); x = np.arange(1, len(d) + 1)
    mean, rng = S.sig(d["subgroup_mean"].values.astype(float)), S.sig(d["subgroup_range"].values.astype(float)); cl, ucl, lcl, ur = (S.sig(d[k].values.astype(float)) for k in ("centre_line", "ucl_mean", "lcl_mean", "ucl_range"))
    three = chart == "three-way chart"; rows = 3 if three else 2
    with plt.rc_context(DARK):
        f, axes = plt.subplots(rows, 1, figsize=(9.2, 5.6 if three else 4.6), sharex=True, gridspec_kw={"height_ratios": [2.2, 1, 1] if three else [2.2, 1]})
        for a in axes:
            a.grid(True, axis="y", color=GRID, lw=0.6); a.set_axisbelow(True)
            for sp in ("top", "right"):
                a.spines[sp].set_visible(False)
        ax = axes[0]
        for v, lab in ((c.usl, "USL"), (c.lsl, "LSL")):
            ax.axhline(v, color=SPEC, lw=1.0); ax.text(len(d) + 0.6, v, f" {lab} {fmt(v, c.unit)}", color=MUTED, fontsize=7.5, va="center", ha="left")
        ax.step(x, ucl, where="mid", color=LIMIT, lw=1.0, ls="--", label="Limits in force at entry"); ax.step(x, lcl, where="mid", color=LIMIT, lw=1.0, ls="--"); ax.step(x, cl, where="mid", color=LIMIT, lw=0.9, label="Centre line")
        ax.plot(x, mean, color=LINE, lw=1.2, zorder=3)
        r1 = d["alarm_rule_1"].values.astype(bool); pat = d["pattern_flags"].notna().values & ~r1; cc = (d["subgroup_type"] == "coil-change").values; adj = d["adjustment_recorded"].values.astype(bool)
        ax.scatter(x[~cc], mean[~cc], s=14, color=LINE, zorder=4, lw=0); ax.scatter(x[cc], mean[cc], s=42, marker="D", color="#ffffff", zorder=5, lw=0, label="Coil-change subgroup")
        ax.scatter(x[pat], mean[pat], s=90, facecolors="none", edgecolors=WARN, linewidths=1.5, zorder=6, label="Pattern, rules 2 to 4"); ax.scatter(x[r1], mean[r1], s=90, facecolors="none", edgecolors=ALARM, linewidths=1.8, zorder=7, label="Rule 1 alarm")
        span = float(c.usl - c.lsl)
        ax.scatter(x[adj & ~cc], mean[adj & ~cc] + 0.06 * span * np.where(mean[adj & ~cc] >= cl[adj & ~cc], 1, -1), s=34, marker="v", color=OK, zorder=6, lw=0, label="Adjustment recorded")
        ax.scatter(x[adj & cc], mean[adj & cc] + 0.06 * span * np.where(mean[adj & cc] >= cl[adj & cc], 1, -1), s=44, marker="P", color=OK, zorder=6, lw=0, label="Centring step")
        coil = d["coil_id"].ffill().values
        for i in range(1, len(d)):
            if coil[i] != coil[i - 1]:
                for a in axes:
                    a.axvline(x[i] - 0.5, color=MUTED, lw=1.0, ls=":")
                ax.text(x[i] - 0.4, c.usl + 0.03 * span, f"Coil change: {coil[i]}", color=MUTED, fontsize=8, va="bottom", ha="left")
        ax.set_ylim(c.lsl - 0.08 * span, c.usl + 0.34 * span); ax.set_ylabel(f"Subgroup mean, {c.unit}")
        ax.legend(loc="upper left", ncol=4, frameon=False, fontsize=7.5, handletextpad=0.4, columnspacing=1.0, borderaxespad=0.2)
        k = 1
        if three:
            mr = np.abs(np.diff(mean)); lim = MR_FACTOR * (ucl - cl)
            a = axes[1]; a.plot(x[1:], S.sig(mr), color=LINE, lw=1.0); a.scatter(x[1:], S.sig(mr), s=10, color=LINE, lw=0); a.step(x, S.sig(lim), where="mid", color=LIMIT, lw=1.0, ls="--"); a.set_ylabel("Moving range\nof means"); a.set_ylim(0, float(max(np.nanmax(lim), mr.max())) * 1.15); k = 2
        a = axes[k]; a.plot(x, rng, color=LINE, lw=1.0); a.scatter(x, rng, s=10, color=LINE, lw=0); a.step(x, ur, where="mid", color=LIMIT, lw=1.0, ls="--"); a.set_ylabel("Range"); a.set_ylim(0, float(max(np.nanmax(ur), rng.max())) * 1.15)
        ticks = [i for i in range(len(d)) if i % 4 == 0]; t = pd.to_datetime(d["sample_time"])
        a.set_xticks(x[ticks]); a.set_xticklabels([t.iloc[i].strftime("%d %b\n%H:%M") if (i == 0 or t.iloc[i].date() != t.iloc[ticks[max(ticks.index(i) - 1, 0)]].date()) else t.iloc[i].strftime("%H:%M") for i in ticks]); a.set_xlim(0.3, len(d) + 3.2)
        f.tight_layout(h_pad=0.4)
    return save(f, f"screen_spc_{c.characteristic_id.lower().replace('-', '_')}", f"{c.characteristic_id} {c.name} over run {RUN} on its {chart}")


def capability_on_the_run(d, c):
    g = d[d["r5"].notna() & (d["implausible_readings"] == 0)]; x = g[R5].values.astype(float); m = x.mean(); near = min(c.usl - m, m - c.lsl)
    return near / (3 * np.sqrt(x.var(axis=1, ddof=1).mean())), near / (3 * x.std(ddof=1)), len(g)


def spc_terminal(m, trace):
    run, coil, h, T = m["run"], m["coil"], m["history"], trace.append
    last_check = h[h["subgroup_type"].isin(["routine", "coil-change"])]["sample_time"].max(); freq = int(round(m["frequency"]["frequency_minutes_as_recorded"].min() / 30.0) * 30); due = pd.Timestamp(last_check) + pd.Timedelta(minutes=freq)
    operator = h["operator_id"].iloc[-1]; rows, blocks, default = [], [], None
    for c in m["characteristics"].itertuples():
        d = h[h["characteristic_id"] == c.characteristic_id]; chart = chart_of(m, c); lastrow = d.iloc[-1] if len(d) else None; variable = c.data_type == "variable"
        if lastrow is None:
            value, when, chip = "", "", '<span class="chip info">NO CHECK</span>'
        elif not variable:
            ok = int(lastrow.attribute_count) == 0; value = "pass" if ok else f"fail ({int(lastrow.attribute_count)})"; when = hm(lastrow.sample_time); chip = f'<span class="chip {"ok" if ok else "alarm"}">{"PASS" if ok else "FAIL"}</span>'
        else:
            value = fmt(lastrow.subgroup_mean, c.unit) if lastrow.subgroup_mean == lastrow.subgroup_mean else ""; when = hm(lastrow.sample_time) if pd.Timestamp(lastrow.sample_time).date() == AS_AT.date() else pd.Timestamp(lastrow.sample_time).strftime("%d %b %H:%M")
            f_c = m["frequency"].loc[c.characteristic_id]; f_min = f_c.frequency_minutes_as_recorded if f_c.frequency_minutes_as_recorded == f_c.frequency_minutes_as_recorded else None
            if chart.startswith("no chart"):
                chip = '<span class="chip info">LAB GAUGE</span>'
            elif bool(lastrow.alarm_rule_1):
                chip = '<span class="chip alarm">RULE 1 ALARM</span>' if lastrow.subgroup_id in m["open_alarms"] else '<span class="chip acked">ALARM &middot; ACK</span>'
            elif isinstance(lastrow.pattern_flags, str):
                chip = f'<span class="chip warn">PATTERN, RULE {" ".join(lastrow.pattern_flags.split())}</span>'
            elif f_min and AS_AT > pd.Timestamp(lastrow.sample_time) + pd.Timedelta(minutes=int(round(f_min / 30.0) * 30)):
                chip = '<span class="chip warn">CHECK DUE</span>'
            else:
                chip = '<span class="chip ok">IN CONTROL</span>'
        charted = variable and not chart.startswith("no chart")
        if charted and default is None and c.critical and c.type in FORMED and bool(lastrow.alarm_rule_1):
            default = c.characteristic_id
        rows.append((c, chart, value, when, chip, charted)); T(("Characteristic list", f"{c.characteristic_id}: {chart}; {value}; {when}", "int_characteristic_history: last subgroup to the screen time; mart_limits_as_set: limit set in force"))
        if not charted:
            continue
        img = spc_chart(m, c, chart); s = lastrow; cpk, ppk, n = capability_on_the_run(d, c)
        reads = "".join(f"<div>{fmt(getattr(s, k), c.unit) if c.unit != 'deg' else f'{getattr(s, k):.1f}'}</div>" for k in R5)
        al = m["alarms"]; al = al[(al["characteristic_id"] == c.characteristic_id) & (al["rule"].astype(str) == "1")]
        if len(al):
            a = al.iloc[-1]; sub = d[d["subgroup_id"] == a.subgroup_id].iloc[0]
            alarm = (f"<table><tbody><tr><th>Subgroup</th><td>{hm(sub.sample_time)}, {sub.subgroup_type}, mean {fmt(sub.subgroup_mean, c.unit)} {c.unit} (limits {fmt(sub.lcl_mean, c.unit)} to {fmt(sub.ucl_mean, c.unit)})</td></tr>"
                     f"<tr><th>Raised</th><td>{pd.Timestamp(a.raised_at).strftime('%H:%M:%S')}</td></tr>")
            acked = a.subgroup_id not in m["open_alarms"]
            if acked:
                alarm += (f"<tr><th>Acknowledged</th><td>{pd.Timestamp(a.acknowledged_at).strftime('%H:%M:%S')} by {e(a.acknowledged_by)}</td></tr>"
                          f"<tr><th>Text</th><td>{e(a.text) if isinstance(a.text, str) else '<span class=muted>none entered</span>'}</td></tr><tr><th>Adjustment</th><td>{'recorded' if bool(sub.adjustment_recorded) else 'none recorded'}</td></tr></tbody></table>")
            else:
                alarm += "<tr><th>Acknowledged</th><td>not yet acknowledged</td></tr></tbody></table>"
            head = '<span class="chip acked">ALARM &middot; ACK</span>' if acked else '<span class="chip alarm">RULE 1 ALARM</span>'
            T(("Alarm panel", f"{c.characteristic_id}: raised {pd.Timestamp(a.raised_at).strftime('%H:%M:%S')}, " + (f"acknowledged {pd.Timestamp(a.acknowledged_at).strftime('%H:%M:%S')} by {a.acknowledged_by}" if acked else "not acknowledged by the screen time"), "stg_spc__alarms; int_characteristic_history"))
        else:
            alarm, head = '<div class="muted">No rule 1 alarm on this run.</div>', ""
        T(("Last subgroup", f"{c.characteristic_id}: mean {fmt(s.subgroup_mean, c.unit)}, range {fmt(s.subgroup_range, c.unit)}, posted {pd.Timestamp(s.recorded_at).strftime('%H:%M:%S')}", "int_characteristic_history: r1 to r5, subgroup_mean, subgroup_range, recorded_at, gauge_id, entry_method"))
        T(("Capability tile", f"{c.characteristic_id}: Cpk {cpk:.2f}, Ppk {ppk:.2f}, {n} subgroups", "int_characteristic_history: readings on the run to the screen time; within-subgroup sigma pooled, overall sigma from all readings"))
        blocks.append((c, chart, img, f"""
<div class="panel"><h3>Last subgroup, {c.characteristic_id}</h3><div class="reads">{reads}</div>
 <table><tbody><tr><th>Mean</th><td class="n">{fmt(s.subgroup_mean, c.unit)} {c.unit}</td><th>Range</th><td class="n">{fmt(s.subgroup_range, c.unit)}</td></tr>
 <tr><th>Gauge</th><td>{e(s.gauge_id)}</td><th>Entry</th><td>{e(s.entry_method)}</td></tr><tr><th>Parts</th><td>{hm(s.sample_time)}</td><th>Posted</th><td>{pd.Timestamp(s.recorded_at).strftime('%H:%M:%S')}</td></tr></tbody></table></div>
<div class="panel"><h3>Most recent alarm{head}</h3>{alarm}</div>
<div class="panel"><h3>Capability on the run, {c.characteristic_id}</h3><div class="tiles"><div class="tile"><div class="v">{cpk:.2f}</div><div class="l">Cpk</div></div><div class="tile"><div class="v">{ppk:.2f}</div><div class="l">Ppk</div></div>
 <div class="tile"><div class="v">{n}</div><div class="l">subgroups</div></div></div></div>"""))
    default = default or blocks[0][0].characteristic_id
    lst = "".join(f'<tr class="{"pick" if charted else ""}{" sel" if c.characteristic_id == default else ""}"{f" data-c={chr(34)}{c.characteristic_id}{chr(34)}" if charted else ""}><td class="name">{c.characteristic_id}{" <span class=crit title=Critical>&#9670;</span>" if c.critical else ""} {e(c.name)}<br><span class="muted">{chart}</span></td>'
                  f'<td class="n">{value}<br><span class="muted">{when}</span></td><td>{chip}</td></tr>' for c, chart, value, when, chip, charted in rows)
    charts = "".join(f'<div data-view="{c.characteristic_id}"{"" if c.characteristic_id == default else " hidden"}><h3>{c.characteristic_id} {e(c.name)}{" (critical)" if c.critical else ""}: {chart}, run {RUN}<span>{fmt(c.nominal, c.unit)} ({fmt(c.lsl, c.unit)} to {fmt(c.usl, c.unit)}) {c.unit}</span></h3>{img}</div>' for c, chart, img, _ in blocks)
    side = "".join(f'<div class="col" data-view="{c.characteristic_id}"{"" if c.characteristic_id == default else " hidden"}>{b}</div>' for c, _, _, b in blocks)
    log = shift_log(m); T(("Shift event log", f"{len(log)} events from {SHIFT_START} to {hm(AS_AT)}", "int_characteristic_history, stg_spc__alarms, stg_press_monitor__fault_events"))
    logrows = "".join(f'<tr><td class="n">{t}</td><td><span class="chip {cls}">{kind}</span></td><td>{detail}</td></tr>' for t, cls, kind, detail in log)
    shots = m["shots_since_sharpening"]; mins = int((due - AS_AT).total_seconds() // 60)
    for k, v, src in (("Context strip", f"part {run.part_id} revision {run.revision}; die {run.die_id}; run {RUN}", "int_run_shots, stg_erp__parts"), ("Context strip", f"coil {coil.coil_id}, {coil.grade}, {coil.certificate_thickness_mm:.3f} mm, {coil.certificate_hardness_hrb:.1f} HRB", "stg_erp__coils; coil of the last subgroup"),
                      ("Context strip", f"{shots:,.0f} shots since sharpening", "int_run_shots.shots_since_sharpening_at_start plus the run's stroke count to the screen time (mart_screen_run_strokes)"),
                      ("Context strip", f"last check {hm(last_check)}; next due {hm(due)}", f"int_characteristic_history: last routine or coil-change check; frequency in force {freq} min (mart_control_plan.frequency_minutes_as_recorded)"), ("Title bar", f"operator {operator}", "int_characteristic_history.operator_id, last subgroup")):
        T((k, v, src))
    body = f"""<div class="window">
<div class="titlebar"><div class="app">SPC software &middot; gauge station, {PRESS}</div><div class="who"><span>Operator {e(operator)}</span><span>Day shift, {SHIFT_START} to {SHIFT_CHANGE}</span><span>{AS_AT.day} {AS_AT.strftime('%B %Y')}</span><span><b>{hm(AS_AT)}</b></span></div></div>
<div class="strip">
 <div class="kv"><span class="l">Part</span><span class="v">{run.part_id} rev {run.revision}</span></div><div class="kv"><span class="l">Die</span><span class="v">{run.die_id}</span></div><div class="kv"><span class="l">Run</span><span class="v">{RUN}</span></div>
 <div class="kv"><span class="l">Coil in force</span><span class="v">{coil.coil_id} &middot; {e(coil.grade)}</span></div><div class="kv"><span class="l">Certificate</span><span class="v">{coil.certificate_thickness_mm:.3f} mm &middot; {coil.certificate_hardness_hrb:.1f} HRB</span></div>
 <div class="kv"><span class="l">Shots since sharpening</span><span class="v">{shots:,.0f}</span></div><div class="kv"><span class="l">Last check</span><span class="v">{hm(last_check)}</span></div>
 <div class="kv"><span class="l">Next routine check</span><span class="v">{hm(due)} &middot; in {mins} min</span></div>
</div>
<div class="grid g-spc">
 <div class="col"><div class="panel"><h3>Characteristics, {run.part_id}<span><span class="crit">&#9670;</span> critical</span></h3><div class="tw"><table><thead><tr><th>Characteristic and chart</th><th class="n">Last</th><th>Status</th></tr></thead><tbody>{lst}</tbody></table></div></div></div>
 <div class="col"><div class="panel">{charts}</div></div>
 <div class="col right">{side}</div>
</div>
<div class="grid" style="padding-top:0"><div class="panel"><h3>Shift event log, {SHIFT_START} to {hm(AS_AT)}</h3><div class="tw"><table><thead><tr><th class="n">Time</th><th>Event</th><th>Detail</th></tr></thead><tbody>{logrows}</tbody></table></div></div></div>
<div class="statusline"><span>SPC software &middot; gauge station, {PRESS}</span><span>Limits as in force at each entry &middot; subgroups of five consecutive parts</span></div>
</div>
<script>
document.querySelectorAll('tr.pick').forEach(function(r){{r.addEventListener('click',function(){{
 document.querySelectorAll('tr.pick').forEach(function(x){{x.classList.remove('sel')}});r.classList.add('sel');
 document.querySelectorAll('[data-view]').forEach(function(v){{v.hidden=v.getAttribute('data-view')!==r.getAttribute('data-c')}});}});}});
</script>"""
    out = S.DOCS / "screens"; out.mkdir(parents=True, exist_ok=True)
    (out / "spc_terminal_pr_03.html").write_text(page(f"SPC Terminal Screen, {PRESS}", body), encoding="utf8", newline="\n")
    return default, len(blocks), len(log)


def shift_log(m):
    """The events of the shift on the run in the order they occurred: checks posted, alarms and their acknowledgement, patterns, coil changes, centring steps, adjustments and per-stroke stops."""
    h = m["history"]; start = pd.Timestamp(f"{AS_AT.date()} {SHIFT_START}"); d = h[h["sample_time"] >= start]; ev = []
    names = m["characteristics"].set_index("characteristic_id")
    coil_before = h[h["sample_time"] < start]["coil_id"].dropna(); prev = coil_before.iloc[-1] if len(coil_before) else None
    for t, g in d.groupby("sample_time", sort=True):
        kind = g["subgroup_type"].iloc[0]; var = g[g["subgroup_mean"].notna()]; att = g[g["subgroup_mean"].isna()]; coil = g["coil_id"].dropna().iloc[0] if g["coil_id"].notna().any() else prev
        if coil != prev and prev is not None:
            c = query("select grade, certificate_thickness_mm, certificate_hardness_hrb from staging.stg_erp__coils where coil_id = ?", [coil]).iloc[0]
            ev.append((pd.Timestamp(t), 0, "info", "COIL CHANGE", f"{coil} in force: certificate {c.certificate_thickness_mm:.3f} mm, {c.certificate_hardness_hrb:.1f} HRB (was {prev})"))
        prev = coil
        fails = int((att["attribute_count"] > 0).sum())
        ev.append((pd.Timestamp(t), 1, "info", f"{kind.upper()} CHECK", f"{len(var)} variable subgroups posted" + (f"; {len(att)} attribute checks, {'all pass' if fails == 0 else str(fails) + ' fail'}" if len(att) else "")))
        for r in g.itertuples():
            nm = f"{r.characteristic_id} {names.loc[r.characteristic_id, 'name']}"
            if bool(r.alarm_rule_1):
                ev.append((pd.Timestamp(t), 2, "alarm", "RULE 1 ALARM", f"{nm}: mean {fmt(r.subgroup_mean, r.unit)}, limits {fmt(r.lcl_mean, r.unit)} to {fmt(r.ucl_mean, r.unit)}"))
            elif isinstance(r.pattern_flags, str):
                ev.append((pd.Timestamp(t), 2, "warn", "PATTERN", f"{nm}: rule {' and '.join(r.pattern_flags.split())}"))
            if bool(r.adjustment_recorded):
                ev.append((pd.Timestamp(t), 3, "ok", "CENTRING STEP" if kind == "coil-change" else "ADJUSTMENT", f"{nm}: adjustment recorded"))
    for a in m["alarms"].itertuples():
        if pd.Timestamp(a.acknowledged_at) >= start and pd.Timestamp(a.acknowledged_at) <= AS_AT:
            ev.append((pd.Timestamp(a.acknowledged_at), 4, "info", "ACKNOWLEDGED", f"{a.characteristic_id}, by {a.acknowledged_by}" + (f": {e(a.text)}" if isinstance(a.text, str) else "")))
    for s in m["stops"].itertuples():
        if pd.Timestamp(s.stopped_at) >= start:
            ev.append((pd.Timestamp(s.stopped_at), 5, "alarm", "PER-STROKE STOP", f"{s.chart}, stroke {int(s.stroke_no):,}"))
            if pd.Timestamp(s.cleared_at) <= AS_AT:
                ev.append((pd.Timestamp(s.cleared_at), 5, "ok", "PRESS RESTARTED", f"{s.finding}; cleared by {s.cleared_by}"))
    ev.sort(key=lambda x: (x[0], x[1]))
    return [(t.strftime("%H:%M"), cls, kind, detail) for t, _, cls, kind, detail in ev]


# -- press monitor -----------------------------------------------------------------
def ewma(m):
    d, b = m["strokes"], m["baseline"]; y = d["total_kn"].values.astype(float); z = np.empty(len(y)); z[0] = b["mean"]
    for i in range(1, len(y)):
        z[i] = LAMBDA * y[i] + (1 - LAMBDA) * z[i - 1]
    a = b["phi"] * (1 - LAMBDA); sz = b["sd"] * np.sqrt(LAMBDA / (2 - LAMBDA) * (1 + a) / (1 - a))
    return z, float(sz)


def channels(m):
    return [c for c in ("ch1", "ch2", "ch3", "ch4") if m["strokes"][f"share_{c}"].notna().all()]


def monitor_figures(m, z, sz):
    d, b, st = m["strokes"], m["baseline"], m["stops"]; n = len(d); x = np.arange(1, n + 1); first = int(d["stroke_no"].iloc[0]); step = max(1, n // 3000); edges = np.arange(0, n, step)
    shades = [LINE, "#e8a25c", OK, "#c58be8"]
    with plt.rc_context(DARK):
        f, ax = plt.subplots(figsize=(10.4, 2.9)); ax.grid(True, axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
        ax.fill_between(x[edges], S.sig(np.minimum.reduceat(z, edges)), S.sig(np.maximum.reduceat(z, edges)), color=LINE, lw=0.7, label="EWMA of the per-stroke total")
        ax.axhline(float(S.sig(b["mean"])), color=MUTED, lw=1.0, label="Baseline level, first 500 strokes")
        for sign in (1, -1):
            ax.axhline(float(S.sig(b["mean"] + sign * L * sz)), color=WARN, lw=1.1, ls="--", label="EWMA limits" if sign == 1 else None)
        for s in st.itertuples():
            k = int(s.stroke_no) - first; ax.axvline(k + 1, color=ALARM, lw=1.0, ls=":"); ax.scatter([k + 1], [float(S.sig(z[k]))], s=44, color=ALARM, zorder=5)
            ax.text(k + 1, float(S.sig(b["mean"] + 1.62 * L * sz)), f"Stop {hm(s.stopped_at)}: {s.finding} ", color=ALARM, fontsize=8.5, va="top", ha="right")
        ax.set_ylim(float(S.sig(b["mean"] - 1.7 * L * sz)), float(S.sig(b["mean"] + 1.7 * L * sz))); ax.set_xlim(0, n * 1.01); ax.set_ylabel("Total peak force, kN"); ax.xaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
        ax.legend(loc="lower left", ncol=3, frameon=False)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        f.tight_layout(); total = save(f, "screen_monitor_total", f"EWMA of the per-stroke total on run {RUN}, {PRESS}, with its limits and the stop")
        ch = channels(m); f, axes = plt.subplots(len(ch), 1, figsize=(10.4, 1.45 * len(ch) + 0.5), sharex=True); axes = np.atleast_1d(axes); levels = {}
        for a, c, color in zip(axes, ch, shades):
            s = d[f"share_{c}"].values.astype(float) * 100; level, sd = s[:500].mean(), s[:500].std(ddof=1); levels[c] = (level, sd)
            a.fill_between(x[edges], S.sig(np.minimum.reduceat(s, edges)), S.sig(np.maximum.reduceat(s, edges)), color=color, lw=0.5, alpha=0.9)
            a.axhline(float(S.sig(level)), color=MUTED, lw=1.0); a.axhline(float(S.sig(level + L * sd)), color=WARN, lw=1.0, ls="--"); a.axhline(float(S.sig(level - L * sd)), color=WARN, lw=1.0, ls="--")
            a.set_ylim(float(S.sig(level - 1.6 * L * sd)), float(S.sig(level + 1.6 * L * sd))); a.set_ylabel(f"Channel {c[-1]}\nshare, %"); a.grid(True, axis="y", color=GRID, lw=0.6); a.set_axisbelow(True)
            for s_ in st.itertuples():
                a.axvline(int(s_.stroke_no) - first + 1, color=ALARM, lw=1.0, ls=":")
            for sp in ("top", "right"):
                a.spines[sp].set_visible(False)
        axes[-1].set_xlabel("Production stroke on the run"); axes[-1].xaxis.set_major_formatter(lambda v, _: f"{int(v):,}"); axes[-1].set_xlim(0, n * 1.01)
        f.tight_layout(h_pad=0.3); shares = save(f, "screen_monitor_channel_shares", f"Channel shares of the total on run {RUN}, {PRESS}, with their levels and limits")
        t = d.tail(300); f, ax = plt.subplots(figsize=(5.4, 2.6)); ax.grid(True, axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
        for c, color in zip(ch, shades):
            ax.plot(t["stroke_no"].values, t[f"peak_kn_{c}"].values.astype(float), color=color, lw=0.9, label=f"Channel {c[-1]}")
        ax.set_ylabel("Peak force, kN"); ax.set_xlabel("Stroke"); ax.xaxis.set_major_formatter(lambda v, _: f"{int(v):,}"); ax.legend(loc="lower left", ncol=4, frameon=False)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        f.tight_layout(); latest = save(f, "screen_monitor_latest_strokes", f"Peak force by channel over the last 300 strokes on run {RUN}, {PRESS}")
    return total, shares, latest, levels


def press_monitor(m, trace):
    run, d, b, st, T = m["run"], m["strokes"], m["baseline"], m["stops"], trace.append
    z, sz = ewma(m); total, shares, latest, levels = monitor_figures(m, z, sz); first = int(d["stroke_no"].iloc[0]); last = d.iloc[-1]
    open_stop = st[(st["cleared_at"].isna()) | (pd.to_datetime(st["cleared_at"]) > AS_AT)]; running = open_stop.empty
    shots = m["shots_since_sharpening"]; die_count = float(m["last_sharpening"].shot_count) + shots; to_go = m["due_count"] - shots; share = min(shots / m["due_count"], 1.0)
    rows = ""
    for s in st.itertuples():
        k = int(s.stroke_no) - first
        if s.chart == "EWMA on the total":
            signal = f"EWMA {z[k]:.1f} kN against the limit {b['mean'] + np.sign(z[k] - b['mean']) * L * sz:.1f} kN"
        else:
            best = max(levels, key=lambda c: abs(d[f"share_{c}"].values[k] * 100 - levels[c][0]) / levels[c][1]); signal = f"channel {best[-1]} share {(d[f'share_{best}'].values[k] * 100 - levels[best][0]) / levels[best][1]:+.1f} sigma"
        cleared = pd.Timestamp(s.cleared_at); restart = f"{(cleared - pd.Timestamp(s.stopped_at)).total_seconds() / 60:.0f}" if cleared <= AS_AT else "open"
        rows += (f'<tr><td class="n">{pd.Timestamp(s.stopped_at).strftime("%H:%M:%S")}</td><td class="n">{int(s.stroke_no):,}</td><td>{s.chart}</td><td>{signal}</td><td>{e(s.finding)}</td><td>{"yes" if "replaced" in str(s.finding) else "no"}</td><td class="n">{restart}</td></tr>')
        T(("Stop log", f"{pd.Timestamp(s.stopped_at).strftime('%H:%M:%S')}, stroke {int(s.stroke_no):,}, {s.chart}, {signal}, {s.finding}, {restart} min to restart", "stg_press_monitor__fault_events; EWMA from mart_screen_run_strokes with the baseline of mart_per_stroke_run_tonnage"))
    punches = "".join(f"<tr><td>{pd.Timestamp(p.stopped_at).strftime('%d %b %H:%M') if p.stopped_at == p.stopped_at else str(p.event_date)[:10]}</td><td>{e(p.notes)}</td><td>{e(p.toolmaker)}</td></tr>" for p in m["punches"].itertuples()) or '<tr><td colspan="3" class="muted">None since the last sharpening.</td></tr>'
    spm = int(last.strokes_per_minute); ls = pd.Timestamp(m["last_sharpening"].event_date)
    for k, v, src in (("Header", f"{spm} strokes a minute; run stroke count {int(last.stroke_no):,}; die shot count {die_count:,.0f}", "mart_screen_run_strokes: last stroke; int_die_event_timeline: shot count at the last sharpening plus shots since"),
                      ("Per-stroke total", f"baseline {b['mean']:.1f} kN; limits {b['mean'] - L * sz:.1f} to {b['mean'] + L * sz:.1f} kN; EWMA now {z[-1]:.1f} kN", "mart_per_stroke_run_tonnage: baseline of the first 500 strokes; EWMA lambda 0.02, limits at 5.5 sigma of the EWMA"),
                      ("Channel shares", "; ".join(f"channel {c[-1]} level {lv:.2f}%, limits {lv - L * sd:.2f}% to {lv + L * sd:.2f}%" for c, (lv, sd) in levels.items()), "mart_screen_run_strokes: share over the first 500 production strokes, 5.5 sigma"),
                      ("Die panel", f"{shots:,.0f} shots since sharpening of {ls.day} {ls.strftime('%B %Y')}; due count {m['due_count']:,.0f}; {to_go:,.0f} strokes to go", "int_run_shots, mart_screen_run_strokes; due count from the die's burr line (die wear analysis)"),
                      ("Die panel", f"{len(m['punches'])} punch replacements since the last sharpening", "int_die_event_timeline")):
        T((k, v, src))
    lamp = '<span class="lamp ok">RUNNING</span>' if running else f'<span class="lamp alarm">STOPPED: {e(open_stop.iloc[-1].chart)}</span>'
    body = f"""<div class="window">
<div class="titlebar"><div class="app">Press monitor historian &middot; {PRESS}</div><div class="who"><span>{AS_AT.day} {AS_AT.strftime('%B %Y')}</span><span><b>{hm(AS_AT)}</b></span></div></div>
<div class="strip">{lamp}
 <div class="kv"><span class="l">Press</span><span class="v">{PRESS}</span></div><div class="kv"><span class="l">Die</span><span class="v">{run.die_id}</span></div><div class="kv"><span class="l">Part</span><span class="v">{run.part_id}</span></div><div class="kv"><span class="l">Run</span><span class="v">{RUN}</span></div>
 <div class="kv"><span class="l">Strokes per minute</span><span class="v">{spm}</span></div><div class="kv"><span class="l">Run stroke count</span><span class="v">{int(last.stroke_no):,}</span></div><div class="kv"><span class="l">Die shot count</span><span class="v">{die_count:,.0f}</span></div>
</div>
<div class="grid g-pm">
 <div class="col">
  <div class="panel"><h3>Per-stroke total: EWMA since the first 500 production strokes<span>lambda {LAMBDA}, limits at {L} sigma</span></h3>{total}</div>
  <div class="panel"><h3>Channel shares of the total<span>level of the first 500 strokes, limits at {L} sigma</span></h3>{shares}</div>
 </div>
 <div class="col">
  <div class="panel"><h3>Now</h3><div class="tiles"><div class="tile"><div class="v">{z[-1]:.1f}</div><div class="l">EWMA, kN</div></div><div class="tile"><div class="v">{b['mean']:.1f}</div><div class="l">baseline, kN</div></div>
   <div class="tile"><div class="v">{b['mean'] - L * sz:.1f} to {b['mean'] + L * sz:.1f}</div><div class="l">EWMA limits, kN</div></div></div></div>
  <div class="panel"><h3>Latest strokes: peak force by channel, last 300</h3>{latest}</div>
  <div class="panel"><h3>Die {run.die_id}: shots since sharpening<span>sharpened {ls.day} {ls.strftime('%B %Y')}</span></h3>
   <div class="bar"><div class="fill" style="width:{share * 100:.1f}%"></div><div class="due" style="left:calc(100% - 2px)"></div></div>
   <table style="margin-top:6px"><tbody><tr><th>Shots since sharpening</th><td class="n">{shots:,.0f}</td></tr><tr><th>Sharpening due count (burr at 80% of the limit)</th><td class="n">{m['due_count']:,.0f}</td></tr><tr><th>Strokes to go</th><td class="n">{to_go:,.0f}</td></tr></tbody></table>
   <h3 style="margin-top:10px">Punch replacements since the last sharpening</h3><table><thead><tr><th>When</th><th>Entry</th><th>Toolmaker</th></tr></thead><tbody>{punches}</tbody></table></div>
 </div>
</div>
<div class="grid" style="padding-top:0"><div class="panel"><h3>Stop log, run {RUN}</h3><div class="tw"><table><thead><tr><th class="n">Time</th><th class="n">Stroke</th><th>Chart</th><th>Signal at the stop</th><th>Toolmaker's finding</th><th>Punch replaced</th><th class="n">Minutes to restart</th></tr></thead><tbody>{rows}</tbody></table></div></div></div>
<div class="statusline"><span>Press monitor historian &middot; {PRESS}</span><span>Signal stop: historian to press control external stop input.</span></div>
</div>"""
    out = S.DOCS / "screens"; out.mkdir(parents=True, exist_ok=True)
    (out / "press_monitor_pr_03.html").write_text(page(f"Press Monitor Screen, {PRESS}", body), encoding="utf8", newline="\n")
    return len(st), running


def build():
    m = moment(); t1, t2 = [], []
    a = spc_terminal(m, t1); b = press_monitor(m, t2)
    cols = ["panel", "value_as_shown", "read_from"]
    return a, b, pd.DataFrame(t1, columns=cols), pd.DataFrame(t2, columns=cols)


if __name__ == "__main__":
    a, b, t1, t2 = build()
    out = S.ROOT / "analytics" / "reports" / "traces"; out.mkdir(exist_ok=True)
    t1.to_csv(out / "spc_terminal_numbers.csv", index=False, lineterminator="\n"); t2.to_csv(out / "press_monitor_numbers.csv", index=False, lineterminator="\n")
    print(a, b, len(t1), len(t2))
