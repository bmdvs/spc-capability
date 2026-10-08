"""SPC boards: one page per pilot press as at the end of the last working day of the last complete week of December 2025.
Reads the board marts, draws the per-stroke charts and the manual-check charts of the run on the press, and writes
docs/spc_board/<press>.html."""
import numpy as np
import pandas as pd

from analytics.data import query
from analytics.die_wear.die_wear import burr_by_die
from analytics.per_stroke.figures import L, LAMBDA
from analytics.style import style as S

RULES = {"1": "rule 1", "2": "rule 2", "3": "rule 3", "4": "rule 4"}
SMOOTH = 200          # strokes in the moving mean of a channel share
TYPE_MARK = {"routine": "o", "first-piece": "s", "coil-change": "D", "last-piece": "^"}


def current_runs():
    return query("select * from marts.mart_board_current_run order by press_id")


def stops(run_id, as_at):
    return query("""select fault_event_id, "timestamp" as stopped_at, input, stroke_no, finding from staging.stg_press_monitor__fault_events
                    where run_id = ? and "timestamp" <= ? and input in ('EWMA signal', 'channel share signal') order by "timestamp" """, [run_id, as_at])


def tonnage_figure(r):
    """The EWMA of the per-stroke total with its limits, and each channel's share against its level at the start of the run."""
    d = query("select stroke_no, total_kn, share_ch1, share_ch2, share_ch3, share_ch4 from marts.mart_board_run_strokes where run_id = ? order by stroke_no", [r.run_id])
    y = d["total_kn"].values.astype(float); z = np.empty(len(y)); z[0] = r.baseline_total_kn_mean
    for i in range(1, len(y)):
        z[i] = LAMBDA * y[i] + (1 - LAMBDA) * z[i - 1]
    a = r.baseline_lag_1_autocorrelation * (1 - LAMBDA); sz = r.baseline_total_kn_sd * np.sqrt(LAMBDA / (2 - LAMBDA) * (1 + a) / (1 - a))
    x = np.arange(1, len(y) + 1); step = max(1, len(y) // 4000); st = stops(r.run_id, r.board_as_at); first = int(d["stroke_no"].iloc[0])
    f, axes = S.fig(h=5.0, nrows=2, sharex=True, gridspec_kw={"height_ratios": [1.25, 1]})
    ax = axes[0]
    edges = np.arange(0, len(y), step); lo = np.minimum.reduceat(z, edges); hi = np.maximum.reduceat(z, edges)          # the range of the EWMA in each bin of strokes, so no excursion is lost in the drawing
    ax.fill_between(x[edges], S.sig(lo), S.sig(hi), color=S.BRAND_BLUE, lw=0.6, label="EWMA of the per-stroke total")
    ax.axhline(float(S.sig(r.baseline_total_kn_mean)), color=S.DARK_GREY, lw=1.0, label="Level of the first 500 strokes")
    for sign in (1, -1):
        ax.axhline(float(S.sig(r.baseline_total_kn_mean + sign * L * sz)), color=S.AMBER, lw=1.2, ls="--", label="EWMA limits" if sign == 1 else None)
    ax.set_ylim(float(S.sig(r.baseline_total_kn_mean - 1.7 * L * sz)), float(S.sig(r.baseline_total_kn_mean + 1.7 * L * sz))); ax.set_ylabel("Total peak force, kN")
    ax2 = axes[1]; chans = [c for c in ("ch1", "ch2", "ch3", "ch4") if d[f"share_{c}"].notna().all()]; shades = [S.BRAND_BLUE, S.ACCENT, S.AMBER, S.GREY]
    for c, color in zip(chans, shades):
        s = d[f"share_{c}"].values * 100; level = s[:500].mean(); sm = pd.Series(s - level).rolling(SMOOTH).mean().values          # drawn from the first full window
        keep = np.arange(SMOOTH - 1, len(sm), step)
        ax2.plot(x[keep], S.sig(sm[keep]), color=color, lw=0.9, label=f"Channel {c[-1]}")
    ax2.axhline(0, color=S.DARK_GREY, lw=1.0); ax2.set_ylabel("Channel share less its level\nat the start of the run, points"); ax2.set_xlabel("Production stroke on the run")
    for s_ in st.itertuples():
        for a_ in axes:
            a_.axvline(s_.stroke_no - first + 1, color=S.RED, lw=0.8, ls=":")
        axes[0].scatter([s_.stroke_no - first + 1], [float(S.sig(z[s_.stroke_no - first]))], s=46, color=S.RED, zorder=5)
        axes[0].text(s_.stroke_no - first + 1, axes[0].get_ylim()[1], f" Stop: {s_.finding}", fontsize=8.5, color=S.RED, va="top")
    ax.legend(loc="lower left", ncol=3, frameon=False, fontsize=8.5); ax2.legend(loc="lower left", ncol=4, frameon=False, fontsize=8.5)
    ax2.xaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    f.tight_layout()
    name = f"board_{r.press_id.lower().replace('-', '_')}_tonnage"
    return S.save(f, name, f"EWMA of the per-stroke total and channel shares on run {r.run_id}, {r.press_id}"), len(y), st, float(z[-1] / r.baseline_total_kn_mean - 1), float(L * sz / r.baseline_total_kn_mean)


def checks(r):
    return query("""select h.characteristic_id, h.characteristic_name, h.characteristic_type, h.critical, h.data_type, h.unit, h.sample_time, h.subgroup_type, h.subgroup_mean, h.centre_line, h.ucl_mean, h.lcl_mean,
                           h.alarm_rule_1, h.pattern_flags, h.acknowledgement_text, h.adjustment_recorded, h.subgroup_id
                    from intermediate.int_characteristic_history h
                    where h.run_id = ? and h.sample_time <= ? and h.data_type = 'variable' and h.subgroup_mean is not null
                    order by h.characteristic_id, h.sample_time, h.subgroup_id""", [r.run_id, r.board_as_at])


def checks_figure(r, c):
    """Subgroup means of the critical characteristics on the run with the limits in force, rule 1 alarms and patterns marked."""
    g = c[c["critical"]]; ids = sorted(g["characteristic_id"].unique()); ncols = 3; nrows = int(np.ceil(len(ids) / ncols))
    f, axes = S.fig(h=2.7 * nrows, ncols=ncols, nrows=nrows); axes = np.atleast_1d(axes).ravel()
    for ax, cid in zip(axes, ids):
        d = g[g["characteristic_id"] == cid].reset_index(drop=True); x = np.arange(1, len(d) + 1); m = S.sig(d["subgroup_mean"].values)
        for col, color, ls in (("ucl_mean", S.DARK_GREY, "-"), ("lcl_mean", S.DARK_GREY, "-"), ("centre_line", S.LIGHT_BLUE, "-")):
            ax.step(x, S.sig(d[col].values.astype(float)), where="mid", color=color, lw=1.0, ls=ls)
        ax.plot(x, m, color=S.BRAND_BLUE, lw=1.0, zorder=2)
        for kind, mark in TYPE_MARK.items():
            k = (d["subgroup_type"] == kind).values
            ax.scatter(x[k], m[k], s=16 if kind == "routine" else 34, marker=mark, color=S.BRAND_BLUE, zorder=3, lw=0)
        pat = d["pattern_flags"].notna().values & ~d["alarm_rule_1"].values.astype(bool); r1 = d["alarm_rule_1"].values.astype(bool)
        ax.scatter(x[pat], m[pat], s=70, facecolors="none", edgecolors=S.AMBER, linewidths=1.5, zorder=4); ax.scatter(x[r1], m[r1], s=70, facecolors="none", edgecolors=S.RED, linewidths=1.7, zorder=5)
        ax.set_title(f"{cid} {d['characteristic_name'].iloc[0]} ({d['unit'].iloc[0]})", fontsize=9); ax.tick_params(labelsize=8)
    for ax in axes[len(ids):]:
        ax.set_visible(False)
    f.tight_layout()
    name = f"board_{r.press_id.lower().replace('-', '_')}_checks"
    return S.save(f, name, f"Subgroup means of the critical characteristics on run {r.run_id}, {r.press_id}, with the limits in force and the flags"), len(ids)


def flags_table(r, c):
    """The flagged subgroups on the run, latest first, with the first step of the reaction plan for the signal beside each."""
    steps = query("select characteristic_id, signal, action from staging.stg_spc__reaction_plan_steps where step = 1 and characteristic_id in (select characteristic_id from intermediate.int_characteristic_history where run_id = ?)", [r.run_id])
    step = {(a.characteristic_id, a.signal): a.action for a in steps.itertuples()}
    g = c[c["alarm_rule_1"].astype(bool) | c["pattern_flags"].notna()].sort_values(["sample_time", "characteristic_id"], ascending=[False, True])
    rows = []
    for a in g.itertuples():
        rule1 = bool(a.alarm_rule_1); signal = "rule 1" if rule1 else "rules 2 to 4"
        flag = "rule 1 alarm" if rule1 else "pattern shown: " + ", ".join(RULES[k] for k in str(a.pattern_flags).split())
        rows.append({"Time": str(a.sample_time)[:16], "Characteristic": f"{a.characteristic_id} {a.characteristic_name}", "Critical": "yes" if a.critical else "", "Check": a.subgroup_type, "Flag": flag,
                     "Reaction plan, step 1": step.get((a.characteristic_id, signal), ""), "Recorded": ("adjustment recorded" if a.adjustment_recorded else "") or (a.acknowledgement_text if isinstance(a.acknowledgement_text, str) else "")})
    return pd.DataFrame(rows), int(c["alarm_rule_1"].astype(bool).sum()), int((c["pattern_flags"].notna() & ~c["alarm_rule_1"].astype(bool)).sum())


def sharpening(press_id, as_at, current_run_id, strokes_on_current_run):
    """The dies of the press's parts as at the board: shots since the last sharpening against the count at which burr
    reaches 80% of its limit. Past due rows first, by the count past due."""
    d = query("""
        with dies as (select distinct die_id, part_id from marts.mart_control_plan where press_id = ?),
             iv as (select i.die_id, i.sharpening_interval_no, i.interval_start from intermediate.int_sharpening_intervals i
                    where i.interval_start <= cast(? as date) qualify row_number() over (partition by i.die_id order by i.interval_start desc, i.sharpening_interval_no desc) = 1),
             ran as (select r.die_id, sum(case when r.run_id = ? then ? else r.strokes end) as shots_since_sharpening
                     from intermediate.int_run_shots r join iv on iv.die_id = r.die_id and iv.sharpening_interval_no = r.sharpening_interval_no
                     where r.production_start <= ? group by 1)
        select dies.die_id, dies.part_id, iv.interval_start as last_sharpening, coalesce(ran.shots_since_sharpening, 0) as shots_since_sharpening, m.sharpening_interval_shots as master_interval
        from dies left join iv using (die_id) left join ran using (die_id) left join staging.stg_erp__dies m using (die_id) order by dies.die_id""", [press_id, as_at, current_run_id, strokes_on_current_run, as_at])
    b, _ = burr_by_die()
    d = d.merge(b[["die_id", "shots_at_80pct_of_limit"]], on="die_id", how="left")
    d["past_due_by"] = d["shots_since_sharpening"] - d["shots_at_80pct_of_limit"]
    return d.sort_values(["past_due_by", "die_id"], ascending=[False, True]).reset_index(drop=True)


def sharpening_table(d, current_die):
    t = pd.DataFrame({"Die": d["die_id"] + d["die_id"].map(lambda x: " (on the press)" if x == current_die else ""), "Part": d["part_id"], "Last sharpening": d["last_sharpening"].map(lambda v: str(v)[:10]),
                      "Shots since": d["shots_since_sharpening"].map("{:,.0f}".format), "Due at (burr at 80% of its limit)": d["shots_at_80pct_of_limit"].map("{:,.0f}".format),
                      "Status": [f"past due by {v:,.0f}" if v > 0 else f"{-v:,.0f} to go" for v in d["past_due_by"]], "Master interval (strokes)": d["master_interval"].map("{:,.0f}".format)})
    return S.table(t)


def tile(value, label):
    return f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div></div>'


def board(r):
    img_t, n_strokes, st, ewma_over, limit_over = tonnage_figure(r)
    c = checks(r); img_c, n_crit = checks_figure(r, c); flags, n_rule1, n_pattern = flags_table(r, c)
    freq = query("select min(frequency_minutes_as_recorded) as f from marts.mart_control_plan where part_id = ? and data_type = 'variable' and characteristic_type <> 'burr height'", [r.part_id])["f"].iloc[0]
    freq = int(round(float(freq) / 30.0) * 30); due = pd.Timestamp(r.last_routine_check) + pd.Timedelta(minutes=freq)
    dies = sharpening(r.press_id, r.board_as_at, r.run_id, n_strokes); past = int((dies["past_due_by"] > 0).sum())
    off = (r.certificate_thickness_mm / r.nominal_thickness_mm - 1) * 100
    last_piece = r.previous_run_last_piece_check == r.previous_run_last_piece_check
    fp = c[(c["subgroup_type"] == "first-piece") & c["alarm_rule_1"].astype(bool)]; fp_adjusted = int(fp["adjustment_recorded"].astype(bool).sum())
    first_piece_note = "" if fp.empty else ("; setup adjustment recorded" if fp_adjusted == len(fp) else ("; no adjustment recorded" if fp_adjusted == 0 else f"; setup adjustment recorded on {fp_adjusted}"))
    body = []
    body.append('<div class="kpis">'
                + tile(f"{r.part_id}", f"Run {r.run_id} on die {r.die_id}, in production from {str(r.production_start)[:16]}")
                + tile(f"{n_strokes:,}", f"Production strokes on the run; {len(st)} {'stop' if len(st) == 1 else 'stops'} by the per-stroke charts")
                + tile(str(r.first_piece_check)[11:16], f"First-piece check on {str(r.first_piece_check)[:10]}: {int(r.first_piece_characteristics)} characteristics, {int(r.first_piece_rule_1_signals)} beyond the limits in force" + first_piece_note)
                + tile(str(r.previous_run_last_piece_check)[:16] if last_piece else "not recorded", f"Last-piece check on the run before ({r.previous_run_id}, {r.previous_part_id})" + (": recorded" if last_piece else ""))
                + tile(f"{r.certificate_thickness_mm:.3f} mm", f"Coil in force {r.coil_in_force}, {r.coil_grade}: certificate thickness, {off:+.1f}% against the nominal {r.nominal_thickness_mm:.2f} mm")
                + tile(str(due)[11:16], f"Next routine check due, {freq} minutes after the last at {str(r.last_routine_check)[11:16]}")
                + "</div>")
    body.append('<h2 id="tonnage">Per-stroke tonnage</h2>')
    body.append(f'{img_t}<div class="caption">The upper panel is the EWMA of the per-stroke total peak force on the run with its limits, set on the first 500 production strokes; the lower panel is each channel\'s share of the total against its level at the start of the run, smoothed over {SMOOTH} strokes. '
                f'A stop by the per-stroke charts is a red point on the EWMA and a dotted line, with the toolmaker\'s finding. At the board the EWMA stands {ewma_over * 100:+.1f}% from the level of the first 500 strokes, with the limits at {limit_over * 100:.1f}% either side.</div>')
    if len(st):
        body.append(S.table(pd.DataFrame({"Stop": st["fault_event_id"], "Time": st["stopped_at"].map(lambda v: str(v)[:16]), "Chart": st["input"].map({"EWMA signal": "EWMA on the total", "channel share signal": "channel share"}),
                                          "Production stroke": (st["stroke_no"]).map("{:,.0f}".format), "Toolmaker's finding": st["finding"]})))
    body.append('<h2 id="checks">Manual checks, critical characteristics</h2>')
    body.append(f'{img_c}<div class="caption">Each panel is one critical characteristic on the run: subgroup means in order with the centre line and limits in force at each entry. Squares are first-piece checks and diamonds coil-change subgroups. '
                f'A red ring is a rule 1 alarm; an amber ring is a pattern on rules 2 to 4, shown for the weekly review and not alarmed at the press.</div>')
    body.append('<h2 id="flags">Flags on the run, with the reaction plan</h2>')
    body.append(f"<p>{n_rule1} rule 1 {'alarm' if n_rule1 == 1 else 'alarms'}, including {len(fp)} at first piece, and {n_pattern} patterns on the run's variable characteristics; the latest {min(len(flags), 12)} are listed, with the first step of the reaction plan for the signal.</p>")
    if len(flags):
        body.append(S.table(flags.head(12)))
    body.append('<h2 id="sharpening">Sharpening</h2>')
    body.append(f"<p>The dies of the parts that run on {r.press_id}, past due first; {past} past due at the board. A die is due when its burr line reaches 80% of the burr limit, counted from the last sharpening.</p>")
    body.append(sharpening_table(dies, r.die_id))
    meta = (f"{r.press_id}, as at {pd.Timestamp(r.board_as_at).day} {pd.Timestamp(r.board_as_at).strftime('%B %Y, %H:%M')}, the end of the last working day of the last complete week of December 2025; press monitor historian, SPC software, die maintenance log and ERP. "
            "Tonnage in kN, dimensions in millimetres, angles in degrees.")
    toc = [("tonnage", "Per-stroke tonnage"), ("checks", "Manual checks"), ("flags", "Flags"), ("sharpening", "Sharpening")] + [(f"../spc_board/{p_.lower().replace('-', '_')}.html", p_) for p_ in ("PR-03", "PR-06", "PR-09") if p_ != r.press_id]
    html = S.shell(f"SPC Board: {r.press_id}", "SPC board", meta, "\n".join(body), [(a, t) for a, t in toc if not a.startswith("..")])
    links = "".join(f'<a href="{p_.lower().replace("-", "_")}.html">{p_}</a>' for p_ in ("PR-03", "PR-06", "PR-09") if p_ != r.press_id)
    links += '<a href="../control_plan/control_plan_and_chart_book.html">Control plan and chart book</a>'
    html = html.replace("</nav>", links + "</nav>", 1)
    out = S.DOCS / "spc_board"; out.mkdir(parents=True, exist_ok=True)
    (out / f"{r.press_id.lower().replace('-', '_')}.html").write_text(html, encoding="utf8", newline="\n")
    sec = f"SPC board, {r.press_id}"
    trace = [(sec, r.part_id, "mart_board_current_run.part_id, run_id, die_id, production_start"), (sec, f"{n_strokes:,}", "mart_board_run_strokes: rows on the run"), (sec, str(len(st)), "stg_press_monitor__fault_events: per-stroke signals on the run to the board"),
             (sec, str(r.first_piece_check)[11:16], "mart_board_current_run.first_piece_check"), (sec, str(int(r.first_piece_characteristics)), "mart_board_current_run.first_piece_characteristics"), (sec, str(int(r.first_piece_rule_1_signals)), "mart_board_current_run.first_piece_rule_1_signals"),
             (sec, str(r.previous_run_last_piece_check)[:16] if last_piece else "not recorded", "mart_board_current_run.previous_run_last_piece_check"), (sec, f"{r.certificate_thickness_mm:.3f}", "mart_board_current_run.certificate_thickness_mm"),
             (sec, f"{off:+.1f}%", "mart_board_current_run: certificate_thickness_mm over nominal_thickness_mm"), (sec, f"{r.nominal_thickness_mm:.2f}", "mart_board_current_run.nominal_thickness_mm"), (sec, str(due)[11:16], "mart_board_current_run.last_routine_check plus the frequency as recorded"),
             (sec, str(freq), "mart_control_plan.frequency_minutes_as_recorded, shortest on the part's variable characteristics"), (sec, str(r.last_routine_check)[11:16], "mart_board_current_run.last_routine_check"),
             (sec, f"{ewma_over * 100:+.1f}%", "mart_board_run_strokes.total_kn: EWMA at the board over mart_board_current_run.baseline_total_kn_mean"), (sec, f"{limit_over * 100:.1f}%", "mart_board_current_run: baseline_total_kn_sd and baseline_lag_1_autocorrelation, with the chart parameters"),
             (sec, str(n_rule1), "int_characteristic_history.alarm_rule_1 on the run to the board"), (sec, str(len(fp)), "int_characteristic_history: first-piece subgroups with alarm_rule_1"), (sec, str(n_pattern), "int_characteristic_history.pattern_flags on the run to the board"),
             (sec, str(past), "sharpening table: dies with shots since sharpening over the count at 80% of the burr limit"),
             (sec, "figure: per-stroke tonnage", "mart_board_run_strokes; mart_board_current_run for the baseline"), (sec, "figure: manual checks", "int_characteristic_history on the run to the board: subgroup_mean, centre_line, ucl_mean, lcl_mean, alarm_rule_1, pattern_flags"),
             (sec, "table: flags with the reaction plan", "int_characteristic_history; stg_spc__reaction_plan_steps, step 1"), (sec, "table: sharpening", "mart_control_plan (dies of the press), int_sharpening_intervals, int_run_shots, stg_erp__dies; burr line from mart_wear_points")]
    if len(st):
        trace.append((sec, "table: stops", "stg_press_monitor__fault_events"))
    return {"trace": trace, "press_id": r.press_id, "run_id": r.run_id, "part_id": r.part_id, "strokes": n_strokes, "stops": len(st), "critical_characteristics_charted": n_crit, "rule_1_alarms": n_rule1, "patterns": n_pattern,
            "dies": len(dies), "dies_past_due": past, "first_past_due": (dies.iloc[0]["die_id"], float(dies.iloc[0]["past_due_by"])), "html": html}


def build():
    return [board(r) for r in current_runs().itertuples()]


if __name__ == "__main__":
    boards = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    pd.DataFrame([t for b in boards for t in b["trace"]], columns=["section", "value_as_printed", "read_from"]).to_csv(S.ROOT / "analytics" / "reports" / "traces" / "boards_numbers.csv", index=False, lineterminator="\n")
    for b in boards:
        print({k: v for k, v in b.items() if k not in ("html", "trace")}, len(b["html"]), len(b["trace"]))
