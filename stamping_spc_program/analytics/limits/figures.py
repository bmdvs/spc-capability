"""Figures for the charts and limits analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np

from analytics.style import style as S

CLASSES = ["formed", "hole diameter", "other punched and dimensional"]
LABELS = ["Formed", "Hole\ndiameter", "Other punched\nand dimensional"]
SET_COLOR, COMPUTED_COLOR, REF_COLOR = S.BRAND_BLUE, S.LIGHT_BLUE, S.GREY


def _labels(ax, bars, values, fmt="{:.1f}", dy=0.0):
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + dy, fmt.format(v), ha="center", va="bottom", fontsize=9, color=S.TEXT)


def signals_as_set_and_as_computed(t):
    """Signals per 100 subgroups under the limits as set and under limits computed from the stable baseline, by class."""
    d = t["signal_comparison"]
    f, axes = S.fig(h=3.9, ncols=2, sharey=True)
    for ax, method, title in zip(axes, ("rolling 25 at entry", "PPAP study"), ("Software presses: rolling limits", "Paper presses: printed PPAP limits")):
        g = d[d["limits_as_set_method"] == method].set_index("characteristic_class").loc[CLASSES]
        x = np.arange(len(CLASSES)); w = 0.38
        a = S.sig(g["rate_as_set_per_100"].values); c = S.sig(g["rate_as_computed_per_100"].values)
        b1 = ax.bar(x - w / 2, a, w, color=SET_COLOR, label="Limits as set"); b2 = ax.bar(x + w / 2, c, w, color=COMPUTED_COLOR, label="Limits computed from the stable baseline")
        _labels(ax, b1, a, dy=0.6); _labels(ax, b2, c, dy=0.6)
        ax.set_xticks(x); ax.set_xticklabels(LABELS); ax.set_title(title, fontsize=11.5)
    axes[0].set_ylabel("Rule-1 signals per 100 subgroups"); axes[0].set_ylim(0, 85)
    h_, l_ = axes[0].get_legend_handles_labels()
    f.legend(h_, l_, loc="lower center", ncol=2, frameon=False)
    f.tight_layout(rect=(0, 0.08, 1, 1))
    return S.save(f, "limits_signals_as_set_and_computed", "Signals per 100 subgroups under the limits as set and as computed, by characteristic class")


def paper_press_signal_rates(t):
    """Paper presses by class: signals under the printed limits and under computed limits on the same subgroups, with
    the rate of a stable process on correct limits as a reference line; beside it the share of printed-limit signals
    with an action recorded, on every subgroup with printed limits in force."""
    d = t["paper_signals"].set_index("characteristic_class").loc[CLASSES]
    f, axes = S.fig(h=4.3, ncols=2, gridspec_kw={"width_ratios": [2.2, 1]})
    ax = axes[0]; x = np.arange(len(CLASSES)); w = 0.38
    for i, (col, label, color) in enumerate((("printed_per_100", "Printed limits", SET_COLOR), ("computed_per_100", "Computed limits, same subgroups", COMPUTED_COLOR))):
        v = S.sig(d[col].values)
        b = ax.bar(x + (i - 0.5) * w, v, w, color=color, label=label)
        _labels(ax, b, v, dy=0.6)
    ref = float(d["reference_per_100"].iloc[0])
    ax.axhline(ref, color=S.DARK_GREY, ls="--", lw=1.1)
    ax.text(len(CLASSES) + 0.2, ref + 1.0, f"stable process on\ncorrect limits, {ref:.2f}", ha="right", va="bottom", fontsize=8.5, color=S.DARK_GREY)
    ax.set_xticks(x); ax.set_xticklabels(LABELS); ax.set_ylabel("Rule-1 signals per 100 subgroups"); ax.set_ylim(0, 85); ax.set_xlim(-0.6, len(CLASSES) + 0.25)
    ax.set_title("Rule-1 signals", fontsize=11.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, fontsize=9)
    ax = axes[1]
    a = t["paper_actions"].set_index("characteristic_class").loc[CLASSES]
    share = S.sig(a["action_share"].values * 100); lo = S.sig(a["action_share_low"].values * 100); hi = S.sig(a["action_share_high"].values * 100)
    b = ax.bar(x, share, 0.55, color=S.ACCENT, yerr=[share - lo, hi - share], error_kw={"ecolor": S.DARK_GREY, "capsize": 3, "lw": 1})
    for bi, v, h_ in zip(b, share, hi):
        ax.text(bi.get_x() + bi.get_width() / 2, h_ + 1.2, f"{v:.0f}%", ha="center", va="bottom", fontsize=9, color=S.TEXT)
    ax.set_xticks(x); ax.set_xticklabels(["Formed", "Hole\ndiameter", "Other"]); ax.set_ylim(0, 50); ax.set_ylabel("Signals with an action recorded, %")
    ax.set_title("Action recorded", fontsize=11.5)
    f.tight_layout()
    return S.save(f, "limits_paper_press_signal_rates", "Paper presses: signals per 100 subgroups under printed and computed limits, and the share with an action recorded")


def printed_limit_age(t):
    """The dies on the paper presses: months since the printed limits were set against sharpenings since."""
    d = t["paper_limit_age_by_die"].sort_values("die_id").reset_index(drop=True)
    f, ax = S.fig(h=4.0)
    jitter = ((np.arange(len(d)) * 7) % 11 - 5) / 5.0 * 0.15          # a fixed spread within 0.15 so dies with the same count do not overprint
    ok = d["set_at_most_recent_rebuild"].fillna(False).astype(bool).values
    x = S.sig(d["months_in_force"].values); y = np.maximum(d["sharpenings_since_set"].values + jitter, 0.0)
    ax.scatter(x[ok], y[ok], s=34, color=SET_COLOR, label="Set at the die's most recent rebuild", zorder=3)
    ax.scatter(x[~ok], y[~ok], s=46, facecolors="white", edgecolors=S.AMBER, linewidths=1.8, label="Set before the die log in the record begins: not confirmed", zorder=3)
    for xi, yi, name in zip(x[~ok], y[~ok], d["die_id"].values[~ok]):
        ax.annotate(name, (xi, yi), textcoords="offset points", xytext=(-6, 8), ha="right", fontsize=8.5, color=S.DARK_GREY)
    ax.set_xlabel("Months the printed limits had been in force at 31 December 2025"); ax.set_ylabel("Sharpenings since the limits were set")
    ax.set_xlim(0, 40); ax.set_ylim(-0.4, 10)
    ax.text(0.985, 0.04, f"Set at the last rebuild on {int(ok.sum())} of {len(d)} dies", transform=ax.transAxes, ha="right", va="bottom", fontsize=9.5, color=SET_COLOR)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "limits_printed_limit_age", "Dies on the paper presses: months since the printed limits were set against sharpenings since")


def run_lengths(t):
    """Paper presses: average run length in control and after shifts of 1 and 1.5 sigma, a pair of columns per class in
    each group, the printed limits dark and the computed rule-1 limits light."""
    d = t["run_lengths"]; d = d[(d["limits_as_set_method"] == "PPAP study") & d["in_report"]]
    cols = ["arl_in_control", "arl_shift_1_sigma", "arl_shift_1_5_sigma"]; groups = ["Process in control", "1-sigma shift", "1.5-sigma shift"]; short = ["Formed", "Hole\ndiameter", "Other\npunched and\ndimensional"]
    f, ax = S.fig(h=4.4); w = 0.13; ticks, names = [], []
    for j, cls in enumerate(CLASSES):
        g = d[d["characteristic_class"] == cls]
        comp = S.sig(g[g["limits"].str.startswith("computed")][cols].values[0]); prin = S.sig(g[g["limits"].str.startswith("as set")][cols].values[0])
        for i in range(3):
            c = i + (j - 1) * 0.31
            ax.bar(c - w / 2, prin[i], w, color=SET_COLOR, label="Printed PPAP limits" if (i == 0 and j == 0) else None); ax.bar(c + w / 2, comp[i], w, color=COMPUTED_COLOR, label="Limits computed from the stable baseline" if (i == 0 and j == 0) else None)
            for xx, v in ((c - w / 2, prin[i]), (c + w / 2, comp[i])):
                ax.text(xx, v * 1.1, f"{v:.1f}", ha="center", va="bottom", fontsize=7.5, color=S.TEXT)
            ticks.append(c); names.append(short[j])
    ax.set_yscale("log"); ax.set_ylim(0.8, 400); ax.set_xticks(ticks); ax.set_xticklabels(names, fontsize=7.5); ax.set_ylabel("Subgroups to a signal (log scale)")
    for i, name in enumerate(groups):
        ax.text(i, 300, name, ha="center", va="top", fontsize=10, color=S.TEXT, fontweight="bold")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.36), ncol=2, frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "limits_run_lengths", "Paper presses: average run length under printed and computed limits on rule 1, in control and after shifts of 1 and 1.5 sigma, by characteristic class")


def signals_and_actions(t):
    """Signals per 100 subgroups under the limits as set and as computed by class, software presses and paper presses
    side by side, with the share of paper-press signals carrying a recorded action."""
    d = t["signal_comparison"]
    f, axes = S.fig(h=4.3, ncols=3, gridspec_kw={"width_ratios": [1, 1, 1.25]})
    x = np.arange(len(CLASSES)); w = 0.38
    for ax, method, title in zip(axes[:2], ("rolling 25 at entry", "PPAP study"), ("Software presses:\nrolling limits", "Paper presses:\nprinted PPAP limits")):
        g = d[d["limits_as_set_method"] == method].set_index("characteristic_class").loc[CLASSES]
        a = S.sig(g["rate_as_set_per_100"].values); c = S.sig(g["rate_as_computed_per_100"].values)
        b1 = ax.bar(x - w / 2, a, w, color=SET_COLOR, label="Limits as set"); b2 = ax.bar(x + w / 2, c, w, color=COMPUTED_COLOR, label="Limits computed from the stable baseline")
        _labels(ax, b1, a, dy=0.6); _labels(ax, b2, c, dy=0.6)
        ax.set_xticks(x); ax.set_xticklabels(["Formed", "Hole\ndiameter", "\n\nOther punched\nand dimensional"], fontsize=8); ax.set_title(title, fontsize=10.5); ax.set_ylim(0, 85)
    axes[0].set_ylabel("Rule-1 signals per 100 subgroups"); axes[1].tick_params(axis="y", labelleft=False)
    r = d[(d["limits_as_set_method"] == "rolling 25 at entry") & d["characteristic_class"].isin(CLASSES[:2])]
    axes[0].text(0.04, 0.97, f"Formed and hole diameter: {r['signals_by_both'].sum() / r['signals_as_computed'].sum() * 100:.1f}%\nof baseline signals also flagged", transform=axes[0].transAxes, ha="left", va="top", fontsize=8.5, color=SET_COLOR, fontweight="bold")
    ax = axes[2]; a = t["paper_actions"].set_index("characteristic_class").loc[CLASSES]; al = t["paper_signals_all_subgroups"].iloc[0]
    share = S.sig(np.append(a["action_share"].values, al["action_share"]) * 100); lo = S.sig(np.append(a["action_share_low"].values, al["action_share_low"]) * 100); hi = S.sig(np.append(a["action_share_high"].values, al["action_share_high"]) * 100)
    xs = np.arange(4); b = ax.bar(xs, share, 0.55, color=[S.ACCENT] * 3 + [S.DARK_GREY], yerr=[share - lo, hi - share], error_kw={"ecolor": S.TEXT, "capsize": 3, "lw": 1})
    for bi, v, h_ in zip(b, share, hi):
        ax.text(bi.get_x() + bi.get_width() / 2, h_ + 1.0, f"{v:.0f}%", ha="center", va="bottom", fontsize=9, color=S.TEXT)
    ax.set_xticks(xs); ax.set_xticklabels(["Formed", "Hole\ndiameter", "\n\nOther punched\nand dimensional", "All"], fontsize=8); ax.set_ylim(0, 50); ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_title("Paper presses: signals\nwith an action recorded", fontsize=10.5)
    h_, l_ = axes[0].get_legend_handles_labels()
    f.legend(h_, l_, loc="lower center", ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(0.36, 0.0))
    f.tight_layout(rect=(0, 0.06, 1, 1))
    return S.save(f, "limits_signals_and_actions", "Signals per 100 subgroups under the limits as set and as computed by characteristic class on the software and paper presses, and the share of paper-press signals with an action recorded")


def build(t):
    return {"age": printed_limit_age(t), "run_lengths": run_lengths(t)}


if __name__ == "__main__":
    from analytics.limits.limits import compute
    print(build(compute()))
