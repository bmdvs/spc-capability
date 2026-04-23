"""Plant quality dashboard: one static page from the dashboard marts, monthly grain with a 12-month view and the 36-month
trend, December 2025 as the current month. Writes docs/dashboard/index.html and its figures."""
import numpy as np
import pandas as pd

from analytics.data import query
from analytics.style import style as S

VIEW = 12
PROGRAM_COLOR = {"formed": S.BRAND_BLUE, "punched": S.AMBER}
FOUND = [("press check", S.BRAND_BLUE), ("dock audit", S.ACCENT), ("customer", S.AMBER)]


def mlabel(ts):
    return pd.Timestamp(ts).strftime("%b %Y")


def month_axis(ax, months, every=3):
    ax.set_xticks(range(0, len(months), every)); ax.set_xticklabels([mlabel(months[i]) for i in range(0, len(months), every)], fontsize=8, rotation=45, ha="right")


def bar_colors(n):
    return [S.BRAND_BLUE if i >= n - VIEW else S.LIGHT_BLUE for i in range(n)]


def ppm_trend(m):
    months = list(m["month_start"]); v = S.sig((m["pieces_rejected"] / m["pieces_shipped"] * 1e6).values)
    roll = S.sig((m["pieces_rejected"].rolling(VIEW).sum() / m["pieces_shipped"].rolling(VIEW).sum() * 1e6).values)
    f, ax = S.fig(h=3.4)
    ax.bar(range(len(v)), v, 0.8, color=bar_colors(len(v)), label="Month"); ax.plot(range(len(v)), roll, color=S.AMBER, lw=1.8, label="12 months to the month")
    month_axis(ax, months); ax.set_ylabel("Customer PPM"); ax.legend(loc="upper right", frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "dashboard_ppm_trend", "Customer PPM by month, 36 months, with the 12-month figure")


def ppm_by_customer(c, months):
    cards = sorted(c[c["scorecard_frequency"] != "none"]["customer_id"].unique()); win = months[-VIEW:]
    f, axes = S.fig(h=5.2, ncols=2, nrows=2); axes = axes.ravel()
    for ax, cid in zip(axes, cards):
        g = c[(c["customer_id"] == cid)].set_index("month_start").reindex(win); v = S.sig((g["pieces_rejected"].fillna(0) / g["pieces_shipped"] * 1e6).fillna(0).values)
        ax.bar(range(VIEW), v, 0.75, color=S.BRAND_BLUE, label="Pieces rejected over pieces shipped")
        sc = g["scorecard_ppm"].values.astype(float); k = ~np.isnan(sc); freq = g["scorecard_frequency"].dropna().iloc[0]
        if freq == "quarterly":          # one figure a quarter: drawn as a line over the quarter's months, and not drawn where the record has none
            for q0 in range(0, VIEW, 3):
                if k[q0:q0 + 3].all():
                    ax.plot([q0 - 0.4, q0 + 2.4], [float(S.sig(sc[q0]))] * 2, color=S.AMBER, lw=2.4, zorder=3, label="Scorecard figure" if q0 == 0 else None)
        else:
            ax.scatter(np.arange(VIEW)[k], S.sig(sc[k]), s=30, color=S.AMBER, zorder=3, label="Scorecard figure")
        target = float(g["ppm_target"].dropna().iloc[0]); ax.axhline(target, color=S.DARK_GREY, ls="--", lw=1.0, label="PPM target")
        ax.set_title(f"{cid} ({g['program'].dropna().iloc[0]}, {freq} scorecard)", fontsize=10)
        ax.set_xticks(range(VIEW)); ax.set_xticklabels([pd.Timestamp(x).strftime("%b") for x in win], fontsize=7.5); ax.set_xlabel(str(pd.Timestamp(win[0]).year), fontsize=8); ax.tick_params(axis="y", labelsize=8)
    h_, l_ = axes[0].get_legend_handles_labels(); f.legend(h_, l_, loc="lower center", ncol=3, frameon=False, fontsize=8.5)          # the point (monthly) and the line (quarterly) share the label
    f.tight_layout(rect=(0, 0.06, 1, 1))
    return S.save(f, "dashboard_ppm_by_customer", "Customer PPM by month for the customers that issue a scorecard, twelve months, with the scorecard figure and the PPM target")


def sorting(m):
    months = list(m["month_start"])
    f, axes = S.fig(h=3.4, ncols=2)
    axes[0].bar(range(len(m)), S.sig(m["sorting_events"].values.astype(float)), 0.8, color=bar_colors(len(m))); axes[0].set_ylabel("Sorting events"); axes[0].yaxis.get_major_locator().set_params(integer=True)
    axes[1].bar(range(len(m)), S.sig(m["quantity_sorted"].values.astype(float)), 0.8, color=bar_colors(len(m))); axes[1].set_ylabel("Quantity sorted"); axes[1].yaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    for ax in axes:
        month_axis(ax, months, 6)
    f.tight_layout()
    return S.save(f, "dashboard_sorting", "Sorting events and quantity sorted by month, 36 months")


def scrap(m):
    months = list(m["month_start"]); share = S.sig(((m["scrap_booked"] + m["rework_labor_booked"]) / m["revenue"] * 100).values)
    f, ax = S.fig(h=3.4)
    ax.bar(range(len(m)), share, 0.8, color=bar_colors(len(m)))
    month_axis(ax, months); ax.set_ylabel("Scrap and rework as booked,\n% of revenue")
    f.tight_layout()
    return S.save(f, "dashboard_scrap_and_rework", "Scrap and rework as booked as a share of revenue by month, 36 months")


def capability(k):
    g = k[k["ppap_ppk"].notna()]
    f, ax = S.fig(h=4.6, w=5.4); lim = (0.4, 2.6)
    ax.plot(lim, lim, color=S.DARK_GREY, ls="--", lw=1.0); ax.axhline(1.33, color=S.GREY, lw=1.0); ax.axvline(1.33, color=S.GREY, lw=1.0)
    for cls, color in PROGRAM_COLOR.items():
        d = g[g["characteristic_class"] == cls].sort_values("characteristic_id")
        ax.scatter(S.sig(d["ppap_ppk"].values), S.sig(d["production_ppk"].values), s=20, color=color, alpha=0.75, lw=0, label=f"{cls[0].upper() + cls[1:]} ({len(d)})")
    ax.set_xlim(*lim); ax.set_ylim(*lim); ax.set_aspect("equal"); ax.set_xlabel("Ppk of the latest PPAP study"); ax.set_ylabel("Production Ppk, 2025"); ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "dashboard_capability", "Production Ppk over 2025 against the Ppk of the latest PPAP study, by critical characteristic")


def signals(p, months):
    presses = sorted(p["press_id"].unique())
    rate = p.assign(v=p["alarm_signals"] / p["variable_subgroups"] * 100).pivot(index="press_id", columns="month_start", values="v").reindex(index=presses, columns=months)
    act = p.assign(v=p["signals_with_an_action_recorded"] / p["alarm_signals"] * 100).pivot(index="press_id", columns="month_start", values="v").reindex(index=presses, columns=months)
    f, axes = S.fig(h=5.6, nrows=2, sharex=True, grid="x")
    for ax, t, title, vmax in ((axes[0], rate, "Alarm signals per 100 subgroups", 30), (axes[1], act, "Signals with an acknowledgement or adjustment recorded, %", 100)):
        im = ax.imshow(S.sig(t.values.astype(float)), aspect="auto", cmap="Blues", vmin=0, vmax=vmax)
        ax.set_yticks(range(len(presses))); ax.set_yticklabels(presses, fontsize=8); ax.set_title(title, fontsize=10); ax.grid(False)
        f.colorbar(im, ax=ax, fraction=0.025, pad=0.01).ax.tick_params(labelsize=8)
    month_axis(axes[1], months)
    f.tight_layout()
    return S.save(f, "dashboard_signals", "Alarm signals per 100 subgroups and the share with an acknowledgement or adjustment recorded, by press and month, 36 months")


def gauge_studies(g):
    v = S.sig(np.sort(g["pct_grr_of_tolerance"].dropna().values))
    f, ax = S.fig(h=3.2)
    ax.hist(v, bins=np.arange(0, 32, 1), color=S.BRAND_BLUE)
    for x, lab in ((10, "10%"), (30, "30%")):
        ax.axvline(x, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(x + 0.2, ax.get_ylim()[1] * 0.92, lab, fontsize=8.5, color=S.DARK_GREY)
    ax.set_xlabel("%GRR of tolerance, latest study on the check fixture"); ax.set_ylabel("Check fixtures")
    f.tight_layout()
    return S.save(f, "dashboard_gauge_studies", "Check fixtures by %GRR of tolerance on the latest gauge study")


def burr(b):
    f, ax = S.fig(h=3.6)
    for where, color in FOUND:
        d = b[(b["detected_at"] == where)].sort_values("ncr_id")
        ax.scatter(pd.to_datetime(d["opened"]).values, S.sig(d["position"].values), s=20, color=color, alpha=0.8, lw=0, label=f"Found at the {where}" if where != "customer" else "Found at the customer")
    ax.axhline(1.0, color=S.DARK_GREY, ls="--", lw=1.0)
    ax.set_ylabel("Shots since sharpening at the end of the run,\nmultiple of the die's stated interval"); ax.legend(loc="lower left", ncol=3, frameon=False, fontsize=8.5); ax.tick_params(axis="x", labelsize=8)
    f.tight_layout()
    return S.save(f, "dashboard_burr", "Burr nonconformances by date opened and the die's position in its stated sharpening interval, 36 months")


def tiles(items):
    return "<div class='kpis'>" + "".join(f"<div class='kpi'><div class='v'>{v}</div><div class='l'>{l}</div></div>" for v, l in items) + "</div>"


def panel(title, anchor, img, definition):
    return f'<h2 id="{anchor}">{title}</h2>{img}<div class="caption">{definition}</div>'


def build():
    m = query("select * from marts.mart_dashboard_monthly order by month_start"); m["month_start"] = pd.to_datetime(m["month_start"])
    c = query("select * from marts.mart_dashboard_ppm_by_customer order by customer_id, month_start"); c["month_start"] = pd.to_datetime(c["month_start"])
    p = query("select * from marts.mart_dashboard_by_press order by press_id, month_start"); p["month_start"] = pd.to_datetime(p["month_start"])
    k = query("select * from marts.mart_dashboard_capability order by characteristic_id")
    g = query("select * from marts.mart_dashboard_gauge_studies order by fixture_id")
    b = query("select *, shots_since_sharpening_at_run_end / sharpening_interval_practice as position from marts.mart_burr_nonconformances where defect_code = 'burr' and shots_since_sharpening_at_run_end is not null order by ncr_id")
    months = list(m["month_start"]); cur = m.iloc[-1]; win = m.iloc[-VIEW:]; before = m.iloc[-2 * VIEW:-VIEW]; cm = mlabel(cur.month_start); trace = []

    def T(section, value, src):
        trace.append((section, value, src)); return value

    ppm12 = win["pieces_rejected"].sum() / win["pieces_shipped"].sum() * 1e6; ppm12b = before["pieces_rejected"].sum() / before["pieces_shipped"].sum() * 1e6
    sr12 = (win["scrap_booked"].sum() + win["rework_labor_booked"].sum()) / win["revenue"].sum(); sr12b = (before["scrap_booked"].sum() + before["rework_labor_booked"].sum()) / before["revenue"].sum()
    kf = k[k["characteristic_class"] == "formed"]
    body = [tiles([
        (T("Tiles", f"{cur.pieces_rejected / cur.pieces_shipped * 1e6:,.0f}", "mart_dashboard_monthly: pieces_rejected over pieces_shipped, current month"), f"Customer PPM, {cm} ({int(cur.complaints)} complaints)"),
        (T("Tiles", f"{ppm12:,.0f}", "mart_dashboard_monthly: pieces_rejected over pieces_shipped, 12 months"), f"Customer PPM, 12 months to {cm}; {T('Tiles', f'{ppm12b:,.0f}', 'mart_dashboard_monthly: the 12 months before')} in the 12 months before"),
        (T("Tiles", f"{int(win['sorting_events'].sum())}", "mart_dashboard_monthly.sorting_events, 12 months"), f"Sorting events, 12 months to {cm}; {T('Tiles', str(int(before['sorting_events'].sum())), 'mart_dashboard_monthly.sorting_events, the 12 months before')} in the 12 months before"),
        (T("Tiles", f"{sr12 * 100:.2f}%", "mart_dashboard_monthly: scrap_booked and rework_labor_booked over revenue, 12 months"), f"Scrap and rework as booked, share of revenue, 12 months to {cm}; {T('Tiles', f'{sr12b * 100:.2f}%', 'mart_dashboard_monthly: the 12 months before')} before"),
        (T("Tiles", f"{kf['production_ppk'].median():.2f}", "mart_dashboard_capability.production_ppk, median, formed"), f"Production Ppk, median of {T('Tiles', str(len(kf)), 'mart_dashboard_capability: formed characteristics')} critical formed characteristics, 2025"),
        (T("Tiles", f"{cur.alarm_signals / cur.variable_subgroups * 100:.1f}", "mart_dashboard_monthly: alarm_signals over variable_subgroups, current month"), f"Alarm signals per 100 subgroups, {cm}; {T('Tiles', f'{cur.signals_with_an_action_recorded / cur.alarm_signals * 100:.0f}%', 'mart_dashboard_monthly: signals_with_an_action_recorded over alarm_signals, current month')} with an action recorded"),
    ])]

    body.append(panel("Customer PPM", "ppm", ppm_trend(m), "Pieces rejected on complaints received in the month over pieces shipped in the month, per million; the line is the same over the 12 months to each month. The last 12 months are in the darker shade."))
    body.append(ppm_by_customer(c, months) + '<div class="caption">For the customers that issue a scorecard: pieces rejected over pieces shipped by month, with the customer\'s scorecard figure (a point for a monthly figure, a line over the quarter for a quarterly one) and the customer\'s PPM target as a dashed line. Scorecard figures are the customer\'s own and are dated by the period in which the complaint was received; a period with no figure in the record is not drawn.</div>')
    cw = c[c["month_start"].isin(months[-VIEW:])].groupby(["customer_id", "program", "scorecard_frequency"], as_index=False).agg(complaints=("complaints", "sum"), pieces_rejected=("pieces_rejected", "sum"), pieces_shipped=("pieces_shipped", "sum"), scorecard_ppm=("scorecard_ppm", "mean"), ppm_target=("ppm_target", "first"))
    cw["ppm"] = cw["pieces_rejected"] / cw["pieces_shipped"] * 1e6; cw = cw[(cw["complaints"] > 0) | (cw["scorecard_frequency"] != "none")].sort_values("pieces_shipped", ascending=False)
    body.append(S.table(pd.DataFrame({"Customer": cw["customer_id"], "Program": cw["program"], f"Complaints, 12 months to {cm}": cw["complaints"].astype(int), "Pieces rejected": cw["pieces_rejected"].map("{:,.0f}".format), "Pieces shipped": cw["pieces_shipped"].map("{:,.0f}".format),
                                      "PPM": cw["ppm"].map("{:,.0f}".format), "Scorecard PPM, mean of the periods": cw["scorecard_ppm"].map(lambda v: "" if v != v else f"{v:,.0f}"), "PPM target": cw["ppm_target"].map(lambda v: "" if v != v else f"{v:,.0f}")})))
    T("Customer PPM", "table: PPM by customer, 12 months", "mart_dashboard_ppm_by_customer")

    body.append(panel("Sorting", "sorting", sorting(m), "Sorting events by the month the sorting started, and the quantity sorted. The last 12 months are in the darker shade."))
    pw = p[p["month_start"].isin(months[-VIEW:])]; sp = pw.pivot(index="press_id", columns="month_start", values="sorting_events").fillna(0).astype(int); sp.columns = [mlabel(x) for x in sp.columns]
    sp["12 months"] = sp.sum(axis=1); sp["Quantity sorted"] = pw.groupby("press_id")["quantity_sorted"].sum().map("{:,.0f}".format); body.append(S.table(sp.reset_index().rename(columns={"press_id": "Press"})))
    T("Sorting", "table: sorting events by press and month", "mart_dashboard_by_press.sorting_events, quantity_sorted")

    body.append(panel("Scrap and rework", "scrap", scrap(m), "Scrap and rework labor as booked in the month over the revenue of the runs ended in the month. The last 12 months are in the darker shade."))
    body.append(panel("Production capability", "capability", capability(k), f"Each point is one critical characteristic with {T('Production capability', '60', 'dbt variable dashboard_min_subgroups')} subgroups or more in 2025 and a PPAP study in the record: the Ppk of the latest PPAP study (300 consecutive pieces on the CMM) against the production Ppk on the check fixture over 2025. The dashed line is where the two agree; the grey lines are 1.33."))
    ks = k.groupby(["is_pilot_press", "characteristic_class"], as_index=False).agg(characteristics=("characteristic_id", "count"), ppap=("ppap_ppk", "median"), with_ppap=("ppap_ppk", "count"), ppk=("production_ppk", "median"), cpk=("production_cpk", "median"), under=("production_ppk", lambda x: int((x < 1.33).sum())))
    body.append(S.table(pd.DataFrame({"Presses": ks["is_pilot_press"].map({True: "PR-03, PR-06 and PR-09", False: "the other eight presses"}), "Class": ks["characteristic_class"], "Critical characteristics": ks["characteristics"], "With a PPAP study in the record": ks["with_ppap"],
                                      "Ppk of the latest PPAP study, median": ks["ppap"].map("{:.2f}".format), "Production Ppk, 2025, median": ks["ppk"].map("{:.2f}".format), "Production Cpk, median": ks["cpk"].map("{:.2f}".format), "Production Ppk under 1.33": ks["under"]})))
    T("Production capability", "table: capability by press set and class", "mart_dashboard_capability")

    body.append(panel("Alarm signals and recorded actions", "signals", signals(p, months), "By press and month: alarm signals per 100 variable subgroups, and the share of signals with an acknowledgement or an adjustment recorded. The redesign is in force on PR-03, PR-06 and PR-09 from 3 February 2025 and on the other presses from 2 September 2025."))
    lw = p[p["month_start"] == months[-1]]
    body.append(S.table(pd.DataFrame({"Press": lw["press_id"], f"Subgroups, {cm}": lw["variable_subgroups"].map("{:,.0f}".format), "Alarm signals": lw["alarm_signals"].map("{:,.0f}".format), "Per 100 subgroups": (lw["alarm_signals"] / lw["variable_subgroups"] * 100).map("{:.1f}".format),
                                      "With an action recorded": (lw["signals_with_an_action_recorded"] / lw["alarm_signals"] * 100).map("{:.0f}%".format)})))
    T("Alarm signals", "table: signals by press, current month", "mart_dashboard_by_press")

    body.append(panel("Gauge study status", "gauges", gauge_studies(g), "Each check fixture by the %GRR of tolerance of its latest gauge study (ANOVA method, 6 sigma). The dashed lines are at 10% and 30%."))
    gs = g.groupby("status", as_index=False).agg(fixtures=("fixture_id", "count"), earliest=("study_date", "min"), latest=("study_date", "max")).set_index("status").reindex(["under 10%", "10% to 30%", "over 30%", "no study"]).dropna(subset=["fixtures"]).reset_index()
    body.append(S.table(pd.DataFrame({"%GRR of tolerance, latest study": gs["status"], "Check fixtures": gs["fixtures"].astype(int), "Studies dated": [f"{str(a)[:10]} to {str(z)[:10]}" for a, z in zip(gs["earliest"], gs["latest"])]})))
    T("Gauge study status", "table: fixtures by status", "mart_dashboard_gauge_studies")

    body.append(panel("Burr nonconformances against shots since sharpening", "burr", burr(b), "Each point is a burr nonconformance by the date it was opened: the die's shots since sharpening at the end of the run as a multiple of the die's stated sharpening interval. The dashed line is the stated interval."))
    b["year"] = pd.to_datetime(b["opened"]).dt.year
    by = b.groupby("year", as_index=False).agg(n=("ncr_id", "count"), past=("position", lambda x: int((x > 1).sum())), dies=("die_id", "nunique"), med=("position", "median"))
    body.append(S.table(pd.DataFrame({"Year": by["year"], "Burr nonconformances with shots known": by["n"], "On runs ended past the stated interval": by["past"], "Dies": by["dies"], "Position, median": by["med"].map("{:.2f}".format)})))
    T("Burr nonconformances", "table: burr nonconformances by year", "mart_burr_nonconformances")
    body.append("<p class='glossary'>PPM is pieces rejected on complaints received in the period over pieces shipped in the period; a complaint entered a second time for the same customer, part, run, quantity and defect code is left out. Scrap and rework are the accounting lines as booked. "
                "Capability is within-subgroup sigma pooled across subgroups for Cpk and the standard deviation of all readings for Ppk, with readings that cannot be a measurement of the part set aside. An alarm signal is an alarm the SPC software raised or a point circled on a paper chart; an action is an acknowledgement or an adjustment recorded against it.</p>")

    meta = (f"Progressive-die metal stamper, about 110 employees, eleven presses, one plant; IATF 16949 certified. Current month {cur.month_start.strftime('%B %Y')}; monthly grain, 12-month view and 36-month trend, January 2023 to December 2025; SPC software, ERP, QMS, die maintenance log, calibration system and accounting.")
    toc = [("ppm", "Customer PPM"), ("sorting", "Sorting"), ("scrap", "Scrap and rework"), ("capability", "Capability"), ("signals", "Alarm signals"), ("gauges", "Gauge studies"), ("burr", "Burr")]
    html = S.shell("Plant Quality Dashboard", "Dashboard", meta, "\n".join(body), toc)
    links = "".join(f'<a href="{h}">{t}</a>' for h, t in (("../spc_board/pr_03.html", "SPC board PR-03"), ("../spc_board/pr_06.html", "SPC board PR-06"), ("../spc_board/pr_09.html", "SPC board PR-09"),
                                                           ("../control_plan/control_plan_and_chart_book.html", "Control plan and chart book"), ("../reports/spc_assessment.html", "SPC Assessment"), ("../reports/spc_redesign_and_results.html", "SPC Redesign and Results")))
    html = html.replace("</nav>", links + "</nav>", 1)
    out = S.DOCS / "dashboard"; out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf8", newline="\n")
    return html, pd.DataFrame(trace, columns=["section", "value_as_printed", "read_from"])


if __name__ == "__main__":
    html, trace = build()
    (S.ROOT / "analytics" / "reports" / "traces").mkdir(exist_ok=True)
    trace.to_csv(S.ROOT / "analytics" / "reports" / "traces" / "dashboard_numbers.csv", index=False, lineterminator="\n")
    print(len(html), len(trace))
