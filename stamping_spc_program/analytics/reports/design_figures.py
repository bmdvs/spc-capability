"""Figures for the Control Chart Design report. Each function takes what the page has read from the marts and returns the
img tag of the figure written under docs/figures."""
import numpy as np
import pandas as pd

from analytics.style import style as S

CLASS_ORDER = ["cut geometry", "formed", "hole diameter", "flatness"]
COMPONENTS = [("share_within", "Within subgroup", S.BRAND_BLUE), ("share_between_subgroups_in_coil", "Between subgroups in a coil", S.ACCENT),
              ("share_between_coils", "Between coils", S.AMBER), ("share_between_intervals", "Between sharpening intervals", S.GREY)]


def variance_components(fig1):
    f, ax = S.fig(h=3.6)
    d = fig1.set_index("characteristic_class").reindex(CLASS_ORDER)
    left = np.zeros(len(d))
    for col, label, colour in COMPONENTS:
        v = S.sig(d[col].values * 100)
        ax.barh(range(len(d)), v, left=left, color=colour, label=label, height=0.6)
        left += v
    ax.set_yticks(range(len(d))); ax.set_yticklabels([CLASS_LABEL[c] for c in d.index]); ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xlabel("Share of variance, median across characteristics (%)")
    ax.legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    return S.save(f, "d1_variance_components_by_class", "Variance components by characteristic class")


def coil_fit(pts, tol_low, tol_high):
    f, ax = S.fig(h=4.2, w=6.4, grid="both")
    first = pts[pts["charted_point"]]; other = pts[~pts["charted_point"]]
    ax.scatter(S.sig(other["predicted"]), S.sig(other["observed"]), s=26, color=S.LIGHT_BLUE, label="Later coil-change subgroups on the coil", zorder=2)
    ax.scatter(S.sig(first["predicted"]), S.sig(first["observed"]), s=34, color=S.BRAND_BLUE, label="First on the coil (charted)", zorder=3)
    lo = float(min(pts["predicted"].min(), pts["observed"].min())); hi = float(max(pts["predicted"].max(), pts["observed"].max())); pad = (hi - lo) * 0.08
    x = np.array([lo - pad, hi + pad]); ax.plot(x, x, color=S.DARK_GREY, linewidth=1, label="Observed equals predicted")
    ax.set_xlim(*x); ax.set_ylim(*x)
    ax.set_xlabel("Predicted from certificate thickness and hardness (mm)"); ax.set_ylabel("Coil-change subgroup mean (mm)")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    return S.save(f, "d1_coil_means_against_certificate_fit", "Coil means against the certificate fit")


def phase1_baseline(b, centre, ucl, lcl, ucl_r):
    f, (a1, a2) = S.fig(h=5.0, nrows=2, sharex=True)
    x = b["baseline_subgroup_no"].values
    for a, y, c, u, l, lab in ((a1, b["subgroup_mean"], centre, ucl, lcl, "Subgroup mean (mm)"), (a2, b["subgroup_range"], None, ucl_r, None, "Subgroup range (mm)")):
        a.plot(x, S.sig(y), marker="o", markersize=4, color=S.BRAND_BLUE, linewidth=1)
        for v, style in ((c, "-"), (u, "--"), (l, "--")):
            if v is not None:
                a.axhline(v, color=S.RED if style == "--" else S.DARK_GREY, linestyle=style, linewidth=1)
        a.set_ylabel(lab)
    scr = b[b["screened"]]
    a2.scatter(scr["baseline_subgroup_no"], S.sig(scr["subgroup_range"]), s=90, facecolors="none", edgecolors=S.RED, linewidths=1.6, zorder=4)
    for _, r in scr.iterrows():
        a2.annotate(f"subgroup {int(r.baseline_subgroup_no)}: flagged, kept in the limits", (r.baseline_subgroup_no, r.subgroup_range), xytext=(-12, 0), textcoords="offset points", fontsize=9, color=S.RED, va="center", ha="right",
                    bbox=dict(boxstyle="square,pad=0.15", facecolor="white", edgecolor="none"))
    a2.set_xlabel("Baseline subgroup"); a2.set_xticks(range(1, len(x) + 1, 2))
    return S.save(f, "d1_phase1_baseline_c11333_02", "Phase I baseline after a rebuild, C-11333-02")


TRIGGER_COLOURS = {"rebuild": S.BRAND_BLUE, "annual review": S.AMBER, "regression re-fit": S.ACCENT, "failed verification": S.RED, "repair": S.GREY, "chart change": S.GREEN}


def recalculations(by_month):
    f, ax = S.fig(h=3.8)
    months = list(by_month["issued_month"]); bottom = np.zeros(len(months))
    for t in [c for c in TRIGGER_COLOURS if c in by_month.columns]:
        v = by_month[t].values.astype(float); ax.bar(range(len(months)), v, bottom=bottom, color=TRIGGER_COLOURS[t], label=f"{t} ({int(v.sum())})", width=0.7); bottom += v
    ax.set_xticks(range(len(months))); ax.set_xticklabels([pd.Timestamp(m + "-01").strftime("%b %Y") for m in months], rotation=45, ha="right")
    ax.set_ylabel("New limit sets"); ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.14))
    return S.save(f, "d1_recalculations_by_month_and_trigger", "Recalculations by month and trigger")


def tool_wear_chart(g, centre, slope_per_100k, half_width, usl, lsl):
    f, ax = S.fig(h=4.0, grid="both")
    x = g["shots_since_sharpening"].values / 1000
    ax.scatter(S.sig(x), S.sig(g["subgroup_mean"]), s=18, color=S.BRAND_BLUE, zorder=3, label="Subgroup mean")
    xs = np.array([0, x.max() * 1.03]); line = centre + slope_per_100k * xs * 1000 / 1e5
    ax.plot(xs, line, color=S.DARK_GREY, linewidth=1.2, label="Regression centre line")
    ax.plot(xs, line + half_width, color=S.RED, linestyle="--", linewidth=1, label="Sloped limits")
    ax.plot(xs, line - half_width, color=S.RED, linestyle="--", linewidth=1)
    ax.set_xlabel("Shots since sharpening (thousands)"); ax.set_ylabel("Hole diameter (mm)")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    return S.save(f, "d1_tool_wear_chart_c15731_02", "The regression chart on C-15731-02")


def arl_curves(f6):
    f, ax = S.fig(h=4.0)
    for col, label, colour, style in (("X-bar rule 1", "rule 1 (X-bar; three-way individuals)", S.BRAND_BLUE, "-"), ("X-bar rules 1 to 4", "X-bar rules 1 to 4", S.ACCENT, "-"),
                                      ("X-bar rule 1, limits from 25 subgroups", "X-bar rule 1, limits from 25 subgroups", S.BRAND_BLUE, "--"), ("X-bar rules 1 to 4, limits from 25 subgroups", "X-bar rules 1 to 4, limits from 25 subgroups", S.ACCENT, "--"),
                                      ("three-way all three charts", "three-way all three charts", S.RED, "-")):
        ax.plot(f6["shift"], S.sig(f6[col]), color=colour, linestyle=style, marker="o", markersize=3, label=label)
    ax.set_yscale("log"); ax.set_xlabel("Shift in the mean (sigmas of the plotted statistic)"); ax.set_ylabel("Average run length (subgroups)")
    ax.legend(frameon=False, ncol=2, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.17))
    return S.save(f, "d1_arl_curves_by_chart_type", "ARL curves by chart type")


def arl_autocorrelation(f7, lo, hi, med=None):
    f, ax = S.fig(h=3.8)
    ax.axvspan(lo, hi, color=S.LIGHT_BLUE, alpha=0.4, label="Measured, 10th to 90th percentile")
    ax.plot(f7["phi"], S.sig(f7["rule 1"]), color=S.BRAND_BLUE, marker="o", markersize=3, label="Rule 1")
    ax.plot(f7["phi"], S.sig(f7["rules 1 to 4"]), color=S.AMBER, marker="o", markersize=3, label="Rules 1 to 4")
    if med is not None:
        ax.axvline(med, color=S.DARK_GREY, linestyle=":", linewidth=1.2, label=f"Measured median ({med:.2f})")
    ax.set_yscale("log"); ax.set_xlabel("Lag-1 autocorrelation of subgroup means"); ax.set_ylabel("In-control ARL (subgroups)")
    ax.legend(frameon=False)
    return S.save(f, "d1_in_control_arl_against_autocorrelation", "In-control ARL against lag-1 autocorrelation")


def expected_observed_by_press(bp):
    f, ax = S.fig(h=4.0)
    y = np.arange(len(bp))
    ax.errorbar(S.sig(bp["observed per 100"]), y, xerr=[S.sig(bp["observed per 100"] - bp["low"]), S.sig(bp["high"] - bp["observed per 100"])], fmt="o", color=S.BRAND_BLUE, capsize=3, label="Observed, 95% interval")
    ax.scatter(S.sig(bp["expected per 100"]), y, marker="|", s=260, color=S.AMBER, linewidths=2.4, label="Expected", zorder=4)
    ax.set_yticks(y); ax.set_yticklabels(bp["press_id"]); ax.invert_yaxis()
    ax.set_xlabel("Signals per 100 routine subgroups, charts with no special cause"); ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    return S.save(f, "d1_expected_against_observed_by_press", "Expected against observed false alarms by press")


def ewma_arl1(f9, marker):
    f, ax = S.fig(h=4.0)
    cols = [c for c in f9.columns if c != "shift_value"]
    for c, colour in zip(cols, (S.BRAND_BLUE, S.ACCENT, S.AMBER)):
        ax.plot(f9["shift_value"] * 100, S.sig(f9[c]), marker="o", markersize=3, color=colour, label=c)
    ax.axvline(marker * 100, color=S.RED, linestyle=":", linewidth=1.2, label="Chipped punch, median shift")
    ax.set_yscale("log"); ax.set_xlabel("Step in the per-stroke total (% of the total)"); ax.set_ylabel("ARL to signal (strokes)")
    ax.legend(frameon=False)
    return S.save(f, "d1_ewma_arl1_against_shift", "EWMA ARL1 against shift size")


def stop_13_may(st, ew, lim, shares):
    f, (a1, a2) = S.fig(h=5.0, nrows=2, sharex=True)
    x = -st["strokes_before_the_stop"].values
    a1.plot(x, S.sig(ew), color=S.BRAND_BLUE, linewidth=1.2, label="EWMA of the total (baseline sigmas)")
    a1.axhline(lim, color=S.RED, linestyle="--", linewidth=1); a1.axhline(-lim, color=S.RED, linestyle="--", linewidth=1, label="EWMA limits")
    a1.set_ylabel("EWMA"); a1.legend(frameon=False, fontsize=9, loc="lower left")
    for c, colour in zip(shares, (S.BRAND_BLUE, S.AMBER, S.ACCENT, S.GREY)):
        v = st[c].values * 100
        a2.plot(x, S.sig(v - v[:200].mean()), color=colour, linewidth=0.9, label=c.replace("share_ch", "channel "))
    a2.axhline(0, color=S.DARK_GREY, linewidth=0.8)
    a2.set_ylabel("Share less its level (points)"); a2.set_xlabel("Strokes before the stop"); a2.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
    return S.save(f, "d1_stop_13_may_d1333c", "The 13 May stop on D-1333-C")


def parts_exposed(px):
    f, ax = S.fig(h=4.0, grid="x")
    y = np.arange(len(px))
    ax.barh(y, S.sig(px["hourly_up_to"]), height=0.55, color=S.AMBER, label="Hourly check: parts made in an hour at the realised stroke rate")
    for i, r in px.reset_index(drop=True).iterrows():
        ax.text(1.2, i, f"per-stroke charts: {r.per_stroke_median_parts:,.0f} part{'' if round(r.per_stroke_median_parts) == 1 else 's'}", va="center", ha="left", fontsize=8.5, color="white")
    ax.set_xscale("log"); ax.set_xlim(1, px["hourly_up_to"].max() * 2); ax.set_yticks(y); ax.set_yticklabels(px["press_id"]); ax.invert_yaxis()
    ax.set_xlabel("Parts per chipped punch, median (log scale)"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12), fontsize=9)
    return S.save(f, "d1_parts_exposed_by_press", "Parts exposed per chipped punch by press")


# ── the restructured page's new figures ───────────────────────────────────────
CLASS_COLOURS = {"formed": S.BRAND_BLUE, "cut geometry": S.ACCENT, "hole diameter": S.AMBER, "flatness": S.GREY, "sheared edges": S.GREEN, "press tonnage": S.DARK_GREY}
CLASS_LABEL = {"formed": "Formed characteristics", "cut geometry": "Cut geometry", "hole diameter": "Hole diameter", "flatness": "Flatness", "sheared edges": "Sheared edges", "press tonnage": "Press tonnage"}


def charts_by_class(rows, inside=("hole diameter",)):
    """rows: characteristic_class, measured, attribute, chart_label; in page order. Stacked columns, variable charts below
    attribute, the total on top with the chart types in parentheses below it; a white count inside the variable segment of
    the classes named in inside."""
    f, ax = S.fig(h=3.9)
    x = np.arange(len(rows)); tot = (rows["measured"] + rows["attribute"]).values
    ax.bar(x, rows["measured"], width=0.6, color=S.BRAND_BLUE, label="Variable charts")
    ax.bar(x, rows["attribute"], bottom=rows["measured"], width=0.6, color=S.LIGHT_BLUE, label="Attribute charts")
    for i, r in rows.reset_index(drop=True).iterrows():
        ax.text(i, tot[i] + tot.max() * 0.02, f"{tot[i]:,}\n({r.chart_label})", ha="center", va="bottom", fontsize=8.5, linespacing=1.3)
        if r.characteristic_class in inside and r.measured > 0:
            ax.text(i, r.measured / 2, f"{int(r.measured)}", ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([CLASS_LABEL[c].replace(" ", "\n") for c in rows["characteristic_class"]])
    ax.set_ylim(0, tot.max() * 1.3); ax.set_ylabel("Active SPC charts")
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    return S.save(f, "d1_charts_in_force_by_class", "Active SPC charts by control target")


def false_alarm_load(load, median, label_press, label_text):
    f, ax = S.fig(h=3.6)
    x = np.arange(len(load))
    ax.bar(x, S.sig(load["alarms_per_week"]), color=[S.BRAND_BLUE if p == label_press else S.ACCENT for p in load["press_id"]], width=0.65)
    ax.axhline(median, color=S.AMBER, linestyle="--", linewidth=1.2, label=f"Plant median, {median:.1f} a week")
    i = list(load["press_id"]).index(label_press)
    ax.text(i, load["alarms_per_week"].iloc[i] + 0.5, label_text, ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels(load["press_id"]); ax.set_ylabel("Expected false alarms a week"); ax.legend(frameon=False, loc="upper right")
    ax.set_ylim(0, load["alarms_per_week"].max() * 1.2)
    return S.save(f, "d1_false_alarm_load_by_press", "False-alarm load as designed, per press per week")


def charts_by_press_and_class(pw, order, labels=None, min_label=6):
    labels = labels or {}
    f, ax = S.fig(h=4.6, grid="x")
    y = np.arange(len(pw)); left = np.zeros(len(pw))
    for c in order:
        v = pw[c].values.astype(float); ax.barh(y, v, left=left, color=CLASS_COLOURS[c], label=labels.get(c, CLASS_LABEL[c]), height=0.65)
        for i, (l_, vv) in enumerate(zip(left, v)):
            if vv >= min_label:
                ax.text(l_ + vv / 2, i, f"{int(vv)}", ha="center", va="center", fontsize=7.5, color="white")
        left += v
    for i, t in enumerate(left):
        ax.text(t + 2, i, f"{int(t)}", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(pw["press_id"]); ax.invert_yaxis(); ax.set_xlim(0, left.max() * 1.1); ax.set_xlabel("Active SPC Charts")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.13), fontsize=9)
    return S.save(f, "d1_charts_in_force_by_press_and_class", "Active SPC charts by press and control target")


def fixture_grr(rows):
    """rows: gauge_id, pct, label; in page order."""
    f, ax = S.fig(h=2.6, grid="x")
    y = np.arange(len(rows))
    ax.barh(y, rows["pct"], color=[S.AMBER if v >= 10 else S.BRAND_BLUE for v in rows["pct"]], height=0.55)
    ax.axvline(10, color=S.AMBER, linestyle="--", linewidth=1.2, label="10%"); ax.axvline(30, color=S.RED, linestyle="--", linewidth=1.2, label="30%")
    for i, r in rows.reset_index(drop=True).iterrows():
        ax.text(r.pct + 0.4, i, f"{r.pct:.1f}%" + (f"  {r.label}" if r.label else ""), va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(rows["gauge_id"]); ax.invert_yaxis(); ax.set_xlim(0, 32); ax.set_xlabel("%GRR of tolerance, latest study")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    return S.save(f, "d1_family_fixture_grr", "Gauge R&R of the family's fixtures")


def signals_by_rule(rr):
    f, axes = S.fig(h=3.6, ncols=2, sharey=True)
    for ax, chart in zip(axes, ("X-bar and R", "regression")):
        g = rr[rr["chart"] == chart]; x = np.arange(4); w = 0.38
        ax.bar(x - w / 2, S.sig(g["obs"]), width=w, color=S.BRAND_BLUE, label="Observed per 100")
        ax.bar(x + w / 2, S.sig(g["exp"]), width=w, facecolor="none", edgecolor=S.BRAND_BLUE, linewidth=1.4, label="Expected, known parameters")
        ax.set_xticks(x); ax.set_xticklabels([f"rule {r}" for r in g["rule"]]); ax.set_title(chart, fontsize=11)
    axes[0].set_ylabel("Signals per 100 routine subgroups"); axes[0].legend(frameon=False, loc="upper left", fontsize=9)
    return S.save(f, "d1_signals_by_rule_long_held_limits", "Signals by rule on long-held limits")


def family_between_coil(fam, med_formed, med_hp):
    """fam: characteristic_id, characteristic_class, value (between-coil share; the trend share on the hole diameter).
    One row per characteristic, grouped by class and ordered by share within the class, labelled by id."""
    order = ["formed", "cut geometry", "hole diameter"]
    d = fam.assign(k=fam["characteristic_class"].map(order.index)).sort_values(["k", "value", "characteristic_id"]).reset_index(drop=True)
    f, ax = S.fig(h=5.6, grid="x")
    y, labels, prev = [], [], None
    pos = 0.0
    for _, r in d.iterrows():
        if prev is not None and r.k != prev:
            pos += 0.6
        y.append(pos); pos += 1; prev = r.k
        labels.append(r.characteristic_id + ("  (wear-trend share)" if r.characteristic_class == "hole diameter" else ""))
    d["y"] = y
    for cls in order:
        g = d[d["characteristic_class"] == cls]
        if len(g):
            ax.hlines(g["y"], 0, g["value"] * 100, color=S.GREY, linewidth=0.8, zorder=1)
            ax.scatter(g["value"] * 100, g["y"], s=40, color=CLASS_COLOURS[cls], zorder=3, label=CLASS_LABEL[cls])
    ax.axvline(med_formed * 100, color=CLASS_COLOURS["formed"], linestyle="--", linewidth=1, label=f"formed class median ({med_formed * 100:.1f}%)")
    ax.axvline(med_hp * 100, color=CLASS_COLOURS["cut geometry"], linestyle="--", linewidth=1, label=f"cut geometry class median ({med_hp * 100:.1f}%)")
    ax.set_yticks(d["y"]); ax.set_yticklabels(labels, fontsize=8); ax.invert_yaxis()
    ax.set_xlim(left=0); ax.set_xlabel("Between-coil share of the routine record's variance (%)")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    return S.save(f, "d1_family_between_coil_share", "Between-coil share of variance by family characteristic")


def three_way_designs(alts):
    """alts: label, value, in_force; in page order."""
    f, ax = S.fig(h=2.8, grid="x")
    y = np.arange(len(alts))
    for i, r in alts.reset_index(drop=True).iterrows():
        ax.barh(i, r.value, height=0.55, color=S.BRAND_BLUE if r.in_force else "none", edgecolor=S.BRAND_BLUE, linewidth=1.4)
        ax.text(r.value * 1.12, i, (f"{r.value:.2f}" if r.value < 10 else f"{r.value:.1f}") + ("  design in force" if r.in_force else ""), va="center", fontsize=9)
    ax.set_xscale("log"); ax.set_xlim(0.1, 100); ax.set_yticks(y); ax.set_yticklabels(alts["label"]); ax.invert_yaxis()
    ax.set_xlabel("In-control false alarms per 100 points (log scale)")
    return S.save(f, "d1_three_way_design_false_alarms", "False alarms per 100 points by three-way design")


def wear_rate_by_die(ws, lo, hi, label_id, label_ref):
    f, ax = S.fig(h=5.4, grid="x")
    d = ws.sort_values(["rate", "characteristic_id"]).reset_index(drop=True); y = np.arange(len(d))
    ax.axvspan(lo, hi, color=S.LIGHT_BLUE, alpha=0.25, label=f"Plant range {lo:.3f} to {hi:.3f}")
    ax.hlines(y, 0.0, S.sig(d["rate"]), color=S.GREY, linewidth=1)
    for i, r in d.iterrows():
        single = int(r.intervals) == 1
        ax.scatter(r.rate, i, s=30 * int(r.intervals), facecolors="none" if single else S.AMBER, edgecolors=S.AMBER, linewidths=1.5, zorder=3)
        ax.text(r.rate + 0.00025, i, f"{int(r.intervals)}", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels([c + ("  " + label_ref if c == label_id else "") for c in d["characteristic_id"]], fontsize=8.5)
    ax.set_xlim(0.003, 0.011); ax.set_xlabel("Wear rate, mm per 100,000 shots (marker area: qualifying intervals; hollow: one interval)")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    return S.save(f, "d1_wear_rate_by_die", "Hole diameter wear rate by die")


def stops_by_finding(t, order, charts, name="d1_stops_by_finding_and_chart", alt="Stops by the per-stroke charts, by finding and chart", legend_above=False):
    f, ax = S.fig(h=3.0, grid="x")
    y = np.arange(len(order)); left = np.zeros(len(order))
    for ch_, colour in zip(charts, (S.BRAND_BLUE, S.AMBER, S.GREY)):
        v = np.array([t.get((fd, ch_), 0) for fd in order], dtype=float)
        ax.barh(y, v, left=left, color=colour, label=ch_, height=0.6)
        for i, (l_, vv) in enumerate(zip(left, v)):
            if vv >= 8:
                ax.text(l_ + vv / 2, i, f"{int(vv)}", va="center", ha="center", fontsize=8.5, color="white")
        left += v
    for i, tot in enumerate(left):
        ax.text(tot + 3, i, f"{int(tot)}", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(order); ax.invert_yaxis(); ax.set_xlim(0, left.max() * 1.12); ax.set_xlabel("Stops in the year")
    ax.legend(frameon=False, ncol=3, fontsize=9, **({"loc": "lower center", "bbox_to_anchor": (0.5, 1.0)} if legend_above else {"loc": "lower right"}))
    return S.save(f, name, alt)


def signals_by_class(f2, bands):
    """f2: cls, observed per 100, expected per 100, ratio, in page order. Grouped bars per class with the design band (the
    observed rate the band allows) shaded behind the pair and the ratio above it; a column whose ratio is outside its band
    sits on the warning tint, as a body-table row would; a fifth column for sheared edges carries no bar."""
    f, ax = S.fig(h=3.8)
    w = 0.36; shaded = False
    for i, r in f2.reset_index(drop=True).iterrows():
        lo, hi = bands[r.cls]; e = float(r["expected per 100"]); o = float(r["observed per 100"])
        if not lo <= r.ratio <= hi:
            ax.axvspan(i - 0.47, i + 0.47, color="#FBEBD3", zorder=0, linewidth=0, label=None if shaded else "Outside its band"); shaded = True
        ax.fill_between([i - 0.45, i + 0.45], e * lo, e * hi, color=S.LIGHT_BLUE, alpha=0.35, linewidth=0, label="Design band" if i == 0 else None)
        ax.bar(i - w / 2, S.sig(o), width=w, color=S.BRAND_BLUE, label="Observed" if i == 0 else None)
        ax.bar(i + w / 2, S.sig(e), width=w, color="white", edgecolor=S.BRAND_BLUE, linewidth=1.4, label="Expected" if i == 0 else None)
        ax.text(i, max(o, e * hi) + 0.15, f"{r.ratio:.2f}x", ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    k = len(f2)
    ax.text(k, 0.25, "no limits in\nthe export;\nsee text", ha="center", va="bottom", fontsize=8.5, color=S.DARK_GREY, linespacing=1.3)
    ax.set_xticks(range(k + 1)); ax.set_xticklabels([CLASS_LABEL[c].replace(" characteristics", "\ncharacteristics") for c in list(f2["cls"]) + ["sheared edges"]])
    ax.set_xlim(-0.6, k + 0.6); ax.set_ylabel("Signals per 100 routine subgroups")
    ax.set_ylim(0, max(f2["observed per 100"].max(), (f2["expected per 100"] * 1.5).max()) * 1.25)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=3)
    return S.save(f, "d1_signals_against_expectation_by_class", "Signals against expectation by characteristic class")


def family_signals(ff2, bands):
    """ff2: cls, observed per 100, expected per 100, ratio, lo, hi; the classes then a total. Grouped bars with the design
    band shaded behind each class's pair, a class outside its band on the warning tint, the ratio above each pair and its
    95% interval as a whisker on the observed bar."""
    f, ax = S.fig(h=3.8)
    w = 0.36; shaded = False
    for i, r in ff2.reset_index(drop=True).iterrows():
        e = float(r["expected per 100"]); o = float(r["observed per 100"])
        if r.cls in bands:
            lo, hi = bands[r.cls]
            if not lo <= r.ratio <= hi:
                ax.axvspan(i - 0.47, i + 0.47, color="#FBEBD3", zorder=0, linewidth=0, label=None if shaded else "Outside its band"); shaded = True
            ax.fill_between([i - 0.45, i + 0.45], e * lo, e * hi, color=S.LIGHT_BLUE, alpha=0.35, linewidth=0, label="Design band" if i == 0 else None)
        ax.bar(i - w / 2, S.sig(o), width=w, color=S.BRAND_BLUE, label="Observed" if i == 0 else None)
        ax.errorbar(i - w / 2, o, yerr=[[o - e * r.lo], [e * r.hi - o]], color=S.DARK_GREY, capsize=4, linewidth=1.2, label="95% interval" if i == 0 else None)
        ax.bar(i + w / 2, S.sig(e), width=w, color="white", edgecolor=S.BRAND_BLUE, linewidth=1.4, label="Expected" if i == 0 else None)
        top = max(e * r.hi, e * bands.get(r.cls, (0, 0))[1])
        ax.text(i, top + 0.15, f"{r.ratio:.2f}x", ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    labels = [CLASS_LABEL.get(c, "Total").replace(" characteristics", "\ncharacteristics") for c in ff2["cls"]]
    ax.set_xticks(range(len(ff2))); ax.set_xticklabels(labels); ax.set_ylabel("Signals per 100 routine subgroups")
    ax.set_ylim(0, float((ff2["expected per 100"] * ff2["hi"]).max()) * 1.3)
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=3)
    return S.save(f, "d1_family_signals_against_expectation", "The family's signals against expectation by class")


def plant_family_ratios(pf, bands):
    """pf: cls, scope (plant or family), ratio, lo, hi. Per class the plant's and the family's observed-over-expected
    ratio as columns with the 95% interval as a whisker, the class's design band shaded behind both, the ratio above
    each column; a class the family does not chart has the plant column only."""
    f, ax = S.fig(h=3.8)
    classes = list(dict.fromkeys(pf["cls"])); w = 0.34
    for i, c in enumerate(classes):
        lo, hi = bands[c]
        ax.fill_between([i - 0.45, i + 0.45], lo, hi, color=S.LIGHT_BLUE, alpha=0.35, linewidth=0, label="Design band" if i == 0 else None)
        for j, (scope, colour) in enumerate((("plant", S.BRAND_BLUE), ("family", S.AMBER))):
            g = pf[(pf["cls"] == c) & (pf["scope"] == scope)]
            if not len(g):
                continue
            r = g.iloc[0]; x = i + (j - 0.5) * w
            ax.bar(x, S.sig(r.ratio), width=w * 0.92, color=colour, label=("Plant" if scope == "plant" else "Family") if i == 0 else None)
            ax.errorbar(x, r.ratio, yerr=[[r.ratio - r.lo], [r.hi - r.ratio]], color=S.DARK_GREY, capsize=3, linewidth=1.1, label="95% interval" if i == 0 and scope == "plant" else None)
            ax.text(x, r.hi + 0.06, f"{r.ratio:.2f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax.axhline(1.0, color=S.GREY, linewidth=0.8, linestyle=":")
    ax.set_xticks(range(len(classes))); ax.set_xticklabels([CLASS_LABEL[c].replace(" characteristics", "\ncharacteristics") for c in classes])
    ax.set_ylabel("Observed over expected signals"); ax.set_ylim(0, float(pf["hi"].max()) * 1.18)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    return S.save(f, "d1_signals_against_expectation_plant_and_family", "Signals against expectation by characteristic class, plant and family")


def subgroups_by_press(ld, high_speed, total):
    """ld: press_id, per_week. Bars by press, the high-speed presses dark, the weekly total in the plot."""
    f, ax = S.fig(h=3.6)
    x = np.arange(len(ld)); hs = [p in high_speed for p in ld["press_id"]]
    ax.bar(x, S.sig(ld["per_week"]), color=[S.BRAND_BLUE if h_ else S.LIGHT_BLUE for h_ in hs], width=0.65)
    for i, v in enumerate(ld["per_week"]):
        ax.text(i, v + 8, f"{v:,.0f}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels(ld["press_id"], fontsize=8.5)
    ax.set_ylabel("Weekly subgroup measurements"); ax.set_ylim(0, float(ld["per_week"].max()) * 1.22)
    ax.text(0.99, 0.95, f"Weekly total: {total:,.0f}", transform=ax.transAxes, ha="right", va="top", fontsize=9.5)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=S.BRAND_BLUE, label="High-speed press, 30 minute intervals"), Patch(color=S.LIGHT_BLUE, label="60 minute intervals")],
              frameon=False, fontsize=8.5, loc="upper right", bbox_to_anchor=(0.99, 0.86))
    return S.save(f, "d1_routine_subgroups_by_press", "Subgroup measurements per week by press")


def program_by_class(pv, parts, min_label=12):
    """pv: programs (rows, in descending chart count) by class (columns, in legend order). Stacked horizontal bars with a
    count inside each segment wide enough to hold one and the chart and part counts at the end of each bar."""
    f, ax = S.fig(h=3.8, grid="x")
    y = np.arange(len(pv)); left = np.zeros(len(pv))
    for c in pv.columns:
        v = pv[c].values.astype(float); ax.barh(y, v, left=left, color=CLASS_COLOURS[c], label=CLASS_LABEL[c], height=0.62)
        for i, (l_, vv) in enumerate(zip(left, v)):
            if vv >= min_label:
                ax.text(l_ + vv / 2, i, f"{int(vv)}", ha="center", va="center", fontsize=7.5, color="white")
        left += v
    for i, (t, n_) in enumerate(zip(left, parts.values)):
        ax.text(t + 4, i, f"{int(t)} charts, {int(n_)} parts", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels(pv.index); ax.invert_yaxis(); ax.set_xlim(0, left.max() * 1.35); ax.set_xlabel("Active SPC Charts")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.17), fontsize=8.5)
    return S.save(f, "d1_charts_by_program_and_class", "Active SPC charts by program and control target")


def flagged_bars(rows, name, labels=("Special cause", "No assignable cause")):
    """rows: group, a (special cause), b (no assignable cause). One 100% stacked horizontal bar per group, counts in the
    segments, the total at the bar's end."""
    f, ax = S.fig(h=3.2, grid="x")
    y = np.arange(len(rows)); tot = (rows["a"] + rows["b"]).values.astype(float); fa = np.where(tot > 0, rows["a"] / tot, 0); fb_ = 1 - fa
    ax.barh(y, 100 * fa, color=S.BRAND_BLUE, height=0.6, label=labels[0]); ax.barh(y, 100 * fb_, left=100 * fa, color=S.LIGHT_BLUE, height=0.6, label=labels[1])
    for i, r in rows.reset_index(drop=True).iterrows():
        if r.a > 0:
            ax.text(100 * fa[i] / 2, i, f"{int(r.a):,}", ha="center", va="center", fontsize=8.5, color="white")
        if r.b > 0:
            ax.text(100 * fa[i] + 100 * fb_[i] / 2, i, f"{int(r.b):,}", ha="center", va="center", fontsize=8.5, color=S.TEXT)
        ax.text(102, i, f"{int(tot[i]):,}", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(rows["group"]); ax.invert_yaxis(); ax.set_xlim(0, 112); ax.set_xlabel("Share of what was flagged (%)")
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.45, -0.2), fontsize=9)
    return S.save(f, name, "What the charts flagged in the year")


def oot_by_class(rows, name):
    """rows: group, sc, nsc (per million, on runs with and without a special cause). Stacked horizontal bars with the total written at the end."""
    f, ax = S.fig(h=3.2, grid="x")
    y = np.arange(len(rows)); tot = (rows["sc"] + rows["nsc"]).values
    ax.barh(y, S.sig(rows["sc"]), color=S.BRAND_BLUE, height=0.6, label="On a run with a special cause"); ax.barh(y, S.sig(rows["nsc"]), left=S.sig(rows["sc"]), color=S.LIGHT_BLUE, height=0.6, label="On a run without one")
    for i, t in enumerate(tot):
        ax.text(t + max(tot) * 0.01, i, f"{t:,.0f}", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(rows["group"]); ax.invert_yaxis(); ax.set_xlim(0, max(tot) * 1.12); ax.set_xlabel("Pieces outside tolerance or failed, per million checked")
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.45, -0.2), fontsize=9)
    return S.save(f, name, "Out-of-tolerance pieces per million by class")

