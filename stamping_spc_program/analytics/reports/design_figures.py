"""Figures for the Control Chart Design report. Each function takes what the page has read from the marts and returns the
img tag of the figure written under docs/figures."""
import numpy as np
import pandas as pd

from analytics.style import style as S

CLASS_ORDER = ["formed", "hole diameter", "hole position", "flatness"]
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
    ax.set_yticks(range(len(d))); ax.set_yticklabels(d.index); ax.invert_yaxis()
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


TRIGGER_COLOURS = {"rebuild": S.BRAND_BLUE, "failed verification": S.RED, "tool-wear re-fit": S.ACCENT, "annual review": S.AMBER, "repair": S.GREY, "chart change": S.GREEN}


def recalculations(by_month):
    f, ax = S.fig(h=3.8)
    months = list(by_month["issued_month"]); bottom = np.zeros(len(months))
    for t in [c for c in TRIGGER_COLOURS if c in by_month.columns]:
        v = by_month[t].values.astype(float); ax.bar(range(len(months)), v, bottom=bottom, color=TRIGGER_COLOURS[t], label=t, width=0.7); bottom += v
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
    return S.save(f, "d1_tool_wear_chart_c15731_02", "The tool-wear chart on C-15731-02")


def arl_curves(f6):
    f, ax = S.fig(h=4.0)
    for col, colour, style in (("X-bar rule 1", S.BRAND_BLUE, "-"), ("X-bar rules 1 to 4", S.BRAND_BLUE, "--"), ("three-way individuals rule 1", S.AMBER, "-"), ("three-way all three charts", S.AMBER, "--")):
        ax.plot(f6["shift"], S.sig(f6[col]), color=colour, linestyle=style, marker="o", markersize=3, label=col)
    ax.set_yscale("log"); ax.set_xlabel("Shift in the mean (sigmas of the plotted statistic)"); ax.set_ylabel("Average run length (subgroups)")
    ax.legend(frameon=False)
    return S.save(f, "d1_arl_curves_by_chart_type", "ARL curves by chart type")


def arl_autocorrelation(f7, lo, hi):
    f, ax = S.fig(h=3.8)
    ax.axvspan(lo, hi, color=S.LIGHT_BLUE, alpha=0.4, label="Measured, 10th to 90th percentile")
    ax.plot(f7["phi"], S.sig(f7["rule 1"]), color=S.BRAND_BLUE, marker="o", markersize=3, label="Rule 1")
    ax.plot(f7["phi"], S.sig(f7["rules 1 to 4"]), color=S.AMBER, marker="o", markersize=3, label="Rules 1 to 4")
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
    ax.barh(y, S.sig(px["hourly_up_to"]), height=0.55, color=S.AMBER, label="Parts made in an hour at the realised stroke rate")
    for i, r in px.reset_index(drop=True).iterrows():
        ax.text(1.2, i, f"per-stroke charts: {r.per_stroke_median_parts:,.0f} part{'' if round(r.per_stroke_median_parts) == 1 else 's'}", va="center", ha="left", fontsize=8.5, color="white")
    ax.set_xscale("log"); ax.set_xlim(1, px["hourly_up_to"].max() * 2); ax.set_yticks(y); ax.set_yticklabels(px["press_id"]); ax.invert_yaxis()
    ax.set_xlabel("Parts per chipped punch, median (log scale)"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.12), fontsize=9)
    return S.save(f, "d1_parts_exposed_by_press", "Parts exposed per chipped punch by press")
