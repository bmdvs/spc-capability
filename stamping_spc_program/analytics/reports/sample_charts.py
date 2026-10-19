"""Sample charts for D1 2.2, drawn in the style of the press-side SPC terminal: one chart of each type, from a non-family
part and the record as it stands. Each function takes the rows it plots and returns the img tag of the figure written
under docs/figures."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analytics.screens.screens import ALARM, DARK, GRID, LIMIT, LINE, MUTED, OK, TEXT, WARN
from analytics.style import style as S

SHADES = [LINE, "#e8a25c", OK, "#c58be8"]


def _style(axes):
    for a in axes:
        a.grid(True, axis="y", color=GRID, lw=0.6); a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)


def _header(f, left, right):
    f.text(0.01, 0.985, left, color=TEXT, fontsize=9.5, fontweight="bold", va="top", ha="left")
    f.text(0.99, 0.985, right, color=MUTED, fontsize=8.5, va="top", ha="right")


def _limit(ax, x_end, y, label, fmt, colour=LIMIT):
    ax.text(x_end, y, f" {label} {fmt.format(y)}", color=colour, fontsize=7.5, va="center", ha="left")


def _times(ax, t, every=6):
    """The date once at the first subgroup of each day, and a time at every few subgroups between."""
    t = pd.to_datetime(pd.Series(t)).reset_index(drop=True); n = len(t)
    days = []
    for i in range(n):
        if (i == 0 or t.iloc[i].date() != t.iloc[i - 1].date()) and (not days or i - days[-1] >= 3):
            days.append(i)
    ticks = sorted(set(days) | {i for i in range(n) if i % every == 0 and min(abs(i - j) for j in days) >= 3})
    ax.set_xticks(np.array(ticks) + 1)
    ax.set_xticklabels([t.iloc[i].strftime("%H:%M") + (f"\n{t.iloc[i].day} {t.iloc[i].strftime('%b')}" if i in days else "") for i in ticks])


def _save(f, name, alt):
    f.savefig(S.DOCS / "figures" / f"{name}.png", format="png", dpi=S.CHART_DPI)
    plt.close(f)
    return f'<img alt="{alt}" src="../figures/{name}.png">'


def xbar_r(d, meta, fmt="{:.3f}"):
    """d: sample_time, subgroup_mean, subgroup_range, centre_line, ucl_mean, lcl_mean, ucl_range, in order."""
    x = np.arange(1, len(d) + 1); n = len(d)
    with plt.rc_context(DARK):
        f, (a, b) = plt.subplots(2, 1, figsize=(9.2, 4.1), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]}); _style((a, b))
        for col, ls_ in (("ucl_mean", "--"), ("lcl_mean", "--"), ("centre_line", "-")):
            a.step(x, S.sig(d[col]), where="mid", color=LIMIT, lw=1.0 if ls_ == "--" else 0.9, ls=ls_)
        a.plot(x, S.sig(d["subgroup_mean"]), color=LINE, lw=1.2); a.scatter(x, S.sig(d["subgroup_mean"]), s=14, color=LINE, lw=0, zorder=4)
        for col, lab in (("ucl_mean", "UCL"), ("centre_line", "CL"), ("lcl_mean", "LCL")):
            _limit(a, n + 0.4, float(d[col].iloc[-1]), lab, fmt)
        a.set_ylabel(f"Subgroup mean, {meta['unit']}")
        b.step(x, S.sig(d["ucl_range"]), where="mid", color=LIMIT, lw=1.0, ls="--"); b.plot(x, S.sig(d["subgroup_range"]), color=LINE, lw=1.0); b.scatter(x, S.sig(d["subgroup_range"]), s=10, color=LINE, lw=0)
        _limit(b, n + 0.4, float(d["ucl_range"].iloc[-1]), "UCL", fmt); b.set_ylabel("Range"); b.set_ylim(0, float(max(d["ucl_range"].max(), d["subgroup_range"].max())) * 1.2)
        _times(b, d["sample_time"]); b.set_xlim(0.3, n + 4.5)
        _header(f, f"{meta['chart_id']}   {meta['part']}   {meta['name']}", "X-bar and R   rules 1 to 4 on the means")
        f.tight_layout(rect=(0, 0, 1, 0.94), h_pad=0.4)
    return _save(f, "d1_sample_xbar_r", f"X-bar and R chart, {meta['chart_id']}")


def three_way(d, meta, fmt="{:.3f}"):
    """d: sample_time, coil, subgroup_mean, subgroup_range, centre_line, ucl_mean, lcl_mean, ucl_moving_range, ucl_range, in order (routine subgroups)."""
    x = np.arange(1, len(d) + 1); n = len(d); mean = d["subgroup_mean"].values.astype(float); mr = np.r_[np.nan, np.abs(np.diff(mean))]
    with plt.rc_context(DARK):
        f, (a, m, b) = plt.subplots(3, 1, figsize=(9.2, 6.0), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1]}); _style((a, m, b))
        for col, ls_ in (("ucl_mean", "--"), ("lcl_mean", "--"), ("centre_line", "-")):
            a.step(x, S.sig(d[col]), where="mid", color=LIMIT, lw=1.0 if ls_ == "--" else 0.9, ls=ls_)
        a.plot(x, S.sig(mean), color=LINE, lw=1.2); a.scatter(x, S.sig(mean), s=14, color=LINE, lw=0, zorder=4)
        for col, lab in (("ucl_mean", "UCL"), ("centre_line", "CL"), ("lcl_mean", "LCL")):
            _limit(a, n + 0.4, float(d[col].iloc[-1]), lab, fmt)
        coil = d["coil"].values; lo = float(d["lcl_mean"].min()); hi = float(d["ucl_mean"].max()); span = hi - lo
        k_ = 0
        for i in range(n):
            if i == 0 or coil[i] != coil[i - 1]:
                if i > 0:
                    for ax_ in (a, m, b):
                        ax_.axvline(x[i] - 0.5, color=MUTED, lw=1.0, ls=":")
                a.text(x[i] - 0.4, hi + (0.04 if k_ % 2 == 0 else 0.14) * span, f"Coil {coil[i]}", color=MUTED, fontsize=7.5, va="bottom", ha="left"); k_ += 1
        a.set_ylim(lo - 0.12 * span, hi + 0.3 * span); a.set_ylabel(f"Individuals, {meta['unit']}")
        m.step(x, S.sig(d["ucl_moving_range"]), where="mid", color=LIMIT, lw=1.0, ls="--"); m.plot(x, S.sig(mr), color=LINE, lw=1.0); m.scatter(x, S.sig(mr), s=10, color=LINE, lw=0)
        _limit(m, n + 0.4, float(d["ucl_moving_range"].iloc[-1]), "UCL", fmt); m.set_ylabel("Moving\nrange"); m.set_ylim(0, float(max(d["ucl_moving_range"].max(), np.nanmax(mr))) * 1.2)
        b.step(x, S.sig(d["ucl_range"]), where="mid", color=LIMIT, lw=1.0, ls="--"); b.plot(x, S.sig(d["subgroup_range"]), color=LINE, lw=1.0); b.scatter(x, S.sig(d["subgroup_range"]), s=10, color=LINE, lw=0)
        _limit(b, n + 0.4, float(d["ucl_range"].iloc[-1]), "UCL", fmt); b.set_ylabel("Range"); b.set_ylim(0, float(max(d["ucl_range"].max(), d["subgroup_range"].max())) * 1.2)
        _times(b, d["sample_time"], every=8); b.set_xlim(0.3, n + 5)
        _header(f, f"{meta['chart_id']}   {meta['part']}   {meta['name']}", "Three-way   rule 1 only; coil changes dotted")
        f.tight_layout(rect=(0, 0, 1, 0.955), h_pad=0.4)
    return _save(f, "d1_sample_three_way", f"Three-way chart, {meta['chart_id']}")


def regression(d, meta, refits, fmt="{:.4f}"):
    """d: sample_time, sharpening_interval_no, limit_set_id, subgroup_mean, centre_line, ucl_mean, lcl_mean, in order; refits: positions where a re-fitted line takes effect."""
    x = np.arange(1, len(d) + 1); n = len(d)
    with plt.rc_context(DARK):
        f, a = plt.subplots(figsize=(9.2, 3.8)); _style((a,))
        seg = (d["sharpening_interval_no"].astype(str) + "|" + d["limit_set_id"]).values
        for s_ in pd.unique(seg):
            k = np.flatnonzero(seg == s_)
            for col, ls_ in (("ucl_mean", "--"), ("lcl_mean", "--"), ("centre_line", "-")):
                a.plot(x[k], S.sig(d[col].values[k]), color=LIMIT, lw=1.0 if ls_ == "--" else 0.9, ls=ls_)
        a.plot(x, S.sig(d["subgroup_mean"]), color=LINE, lw=1.1); a.scatter(x, S.sig(d["subgroup_mean"]), s=14, color=LINE, lw=0, zorder=4)
        for col, lab in (("ucl_mean", "UCL"), ("centre_line", "CL"), ("lcl_mean", "LCL")):
            _limit(a, n + 0.4, float(d[col].iloc[-1]), lab, fmt)
        top = float(d["ucl_mean"].max()); bot = float(d["lcl_mean"].min()); span = top - bot
        iv = d["sharpening_interval_no"].values
        for i in range(1, n):
            if iv[i] != iv[i - 1]:
                a.axvline(x[i] - 0.5, color=WARN, lw=1.1, ls=":"); a.text(x[i] - 0.4, top + 0.06 * span, "Sharpened", color=WARN, fontsize=7.5, va="bottom", ha="left")
        for i in refits:
            a.axvline(x[i] - 0.5, color=MUTED, lw=0.9, ls=":"); a.text(x[i] - 0.4, bot - 0.04 * span, "Line re-fitted", color=MUTED, fontsize=7.5, va="top", ha="left")
        a.set_ylim(bot - 0.16 * span, top + 0.22 * span); a.set_ylabel(f"Subgroup mean, {meta['unit']}")
        _times(a, d["sample_time"], every=8); a.set_xlim(0.3, n + 5.5)
        _header(f, f"{meta['chart_id']}   {meta['part']}   {meta['name']}", "Regression on shots since sharpening")
        f.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(f, "d1_sample_regression", f"Regression chart, {meta['chart_id']}")


def p_chart(d, meta, p_bar, ucl):
    """d: sample_time, attribute_count, pieces, in order; p_bar and ucl: the centre line and upper limit from the baseline fail rate."""
    x = np.arange(1, len(d) + 1); n = len(d); p = 100 * d["attribute_count"].fillna(0).values / d["pieces"].values
    with plt.rc_context(DARK):
        f, a = plt.subplots(figsize=(9.2, 3.0)); _style((a,))
        a.hlines([100 * ucl], 0.5, n + 0.2, color=LIMIT, lw=1.0, ls="--"); a.hlines([100 * p_bar], 0.5, n + 0.2, color=LIMIT, lw=0.9)
        _limit(a, n + 0.4, 100 * ucl, "UCL", "{:.1f}%"); _limit(a, n + 0.4, 100 * p_bar, "CL", "{:.2f}%")
        a.text(1, 100 * ucl + 1.2, "limits from the baseline fail rate", color=MUTED, fontsize=7.5, va="bottom", ha="left")
        a.plot(x, S.sig(p), color=LINE, lw=1.0); a.scatter(x, S.sig(p), s=14, color=LINE, lw=0, zorder=4)
        hit = p > 100 * ucl; a.scatter(x[hit], p[hit], s=90, facecolors="none", edgecolors=ALARM, linewidths=1.8, zorder=6)
        a.set_ylim(-1, max(25, float(p.max()) * 1.15)); a.set_ylabel("Fraction failed, %")
        _times(a, d["sample_time"], every=6); a.set_xlim(0.3, n + 4.5)
        _header(f, f"{meta['chart_id']}   {meta['part']}   {meta['name']}", f"p chart   {int(d['pieces'].iloc[0])} pieces a check")
        f.tight_layout(rect=(0, 0, 1, 0.9))
    return _save(f, "d1_sample_p_chart", f"p chart, {meta['chart_id']}")


def per_stroke(st, base, lam, L, meta):
    """st: stroke_no, total_kn and share_ch1 to share_ch4 for the strokes shown; base: the run's baseline mean, sd, lag-1 autocorrelation and the
    channel-share levels and sds from its first 500 production strokes."""
    x = st["stroke_no"].values; n = len(st)
    with plt.rc_context(DARK):
        f, (a, b) = plt.subplots(2, 1, figsize=(9.2, 4.6), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]}); _style((a, b))
        a.plot(x, S.sig(st["ewma"]), color=LINE, lw=1.1); a.hlines([base["mean"]], x[0], x[-1], color=MUTED, lw=1.0)
        for sign, lab in ((1, "UCL"), (-1, "LCL")):
            y = base["mean"] + sign * L * base["sz"]; a.hlines([y], x[0], x[-1], color=WARN, lw=1.0, ls="--"); _limit(a, x[-1] + n * 0.005, y, lab, "{:.1f}", WARN)
        _limit(a, x[-1] + n * 0.005, base["mean"], "CL", "{:.1f}", MUTED)
        a.set_ylim(base["mean"] - 1.5 * L * base["sz"], base["mean"] + 1.5 * L * base["sz"]); a.set_ylabel("EWMA of total, kN")
        for c, colour in zip(("ch1", "ch2", "ch3", "ch4"), SHADES):
            lv, sd = base[f"level_{c}"], base[f"sd_{c}"]
            b.plot(x, S.sig((st[f"share_{c}"] - lv) / sd), color=colour, lw=0.6, label=f"Channel {c[-1]}")
        for sign, lab in ((1, "UCL"), (-1, "LCL")):
            b.hlines([sign * L], x[0], x[-1], color=WARN, lw=1.0, ls="--"); _limit(b, x[-1] + n * 0.005, sign * L, lab, "{:+.1f}", WARN)
        b.hlines([0], x[0], x[-1], color=MUTED, lw=0.8); b.set_ylabel("Channel share,\nsigmas from level"); b.set_ylim(-1.5 * L, 1.5 * L)
        b.legend(loc="lower left", ncol=4, frameon=False, fontsize=7.5); b.set_xlabel("Production stroke on the run"); b.xaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
        b.set_xlim(x[0], x[-1] + n * 0.1)
        _header(f, f"{meta['run']}   {meta['press']}   {meta['part']}", f"Per-stroke tonnage   EWMA lambda {lam:.2f}, L {L:.1f}; channel shares at L {L:.1f}")
        f.tight_layout(rect=(0, 0, 1, 0.94), h_pad=0.4)
    return _save(f, "d1_sample_per_stroke", f"Per-stroke tonnage charts, run {meta['run']}")
