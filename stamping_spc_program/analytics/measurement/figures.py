"""Figures for the measurement systems analysis. Each function takes the analysis tables and writes one figure under docs/figures.
With after=False a figure holds the record of the assessment; with after=True it also holds what followed (the studies after
rebuild, the burr check after the new limit samples, the gauge-connected readings)."""
import numpy as np

from analytics.style import style as S

STUDY_COLOR = {"PPAP": S.LIGHT_BLUE, "redesign": S.BRAND_BLUE, "rebuilt": S.ACCENT}
STUDY_LABEL = {"PPAP": "PPAP study", "redesign": "Assessment study, January 2025", "rebuilt": "After rebuild"}


def grr_by_study(t, after=False):
    """%GRR of tolerance by fixture and study, with ndc at each column."""
    d = t["gauge_rr"]; studies = ("PPAP", "redesign", "rebuilt") if after else ("PPAP", "redesign"); d = d[d["study"].isin(studies)]
    f, ax = S.fig(h=4.0)
    step = len(studies) + 1; pos = {}
    for i, fx in enumerate(("F-20417", "F-31102")):
        for j, st in enumerate(studies):
            pos[(fx, st)] = i * step + j
    pos[("F-10823", "redesign")] = 2 * step; centres = [(len(studies) - 1) / 2, step + (len(studies) - 1) / 2, 2 * step]
    seen = set()
    for r in d.itertuples():
        x = pos[(r.fixture, r.study)]; v = float(S.sig(r.pct_tolerance))
        ax.bar(x, v, 0.8, color=STUDY_COLOR[r.study], label=STUDY_LABEL[r.study] if r.study not in seen else None); seen.add(r.study)
        ax.text(x, (v if v > 10.5 else 10.0) + 0.7, f"{v:.1f}%\nndc {r.ndc}", ha="center", va="bottom", fontsize=8.5, color=S.TEXT)
    right = 2 * step + 0.9
    for y, lab in ((10, "10%"), (30, "30%")):
        ax.axhline(y, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(right - 0.15, y + 0.5, lab, ha="right", va="bottom", fontsize=8.5, color=S.DARK_GREY)
    ax.set_xticks(centres); ax.set_xticklabels(["F-20417\nformed height", "F-31102\nhole-to-edge", "F-10823\nformed height"])
    ax.set_ylabel("%GRR of tolerance (6 sigma)"); ax.set_ylim(0, 42); ax.set_xlim(-0.8, right)
    handles, labels = ax.get_legend_handles_labels(); order = [labels.index(STUDY_LABEL[k]) for k in studies]
    ax.legend([handles[i] for i in order], [labels[i] for i in order], loc="upper right", frameon=False, fontsize=9, bbox_to_anchor=(1.0, 0.93))
    f.tight_layout()
    return S.save(f, "measurement_grr_by_study" + ("_after_rebuild" if after else ""), "Gauge R&R as a share of tolerance by check fixture and study, with the number of distinct categories")


def gauge_variance_split(t, after=False):
    """Repeatability against reproducibility in the gauge variance on the two reworked fixtures."""
    d = t["gauge_rr"].set_index(["fixture", "study"])
    rows = [("F-31102, after rebuild", ("F-31102", "rebuilt"), 0.55), ("F-31102, assessment study", ("F-31102", "redesign"), 1.0), ("F-20417, after rebuild", ("F-20417", "rebuilt"), 0.55), ("F-20417, assessment study", ("F-20417", "redesign"), 1.0)]
    if not after:
        rows = [r for r in rows if r[1][1] == "redesign"]
    f, ax = S.fig(h=2.9 if after else 2.1, grid="x")
    for y, (label, key, alpha) in enumerate(rows):
        rp = float(S.sig(d.loc[key, "reproducibility_share_of_grr"] * 100)); rt = 100 - rp; top = y == len(rows) - 1
        ax.barh(y, rt, color=S.LIGHT_BLUE, alpha=alpha, height=0.6, label="Repeatability" if top else None)
        ax.barh(y, rp, left=rt, color=S.BRAND_BLUE, alpha=alpha, height=0.6, label="Reproducibility (between operators)" if top else None)
        ax.text(rt / 2, y, f"{rt:.0f}%", ha="center", va="center", fontsize=9.5, color=S.TEXT)
        ax.text(rt + rp / 2, y, f"{rp:.0f}%", ha="center", va="center", fontsize=9.5, color="white")
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows]); ax.set_xlim(0, 100); ax.set_xlabel("Share of the gauge variance, %")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.3 if after else -0.45), ncol=2, frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "measurement_gauge_variance_split" + ("_after_rebuild" if after else ""), "Repeatability and reproducibility as shares of the gauge variance on the two reworked fixtures")


def burr_by_operator(t, after=False):
    """Reject rate on the burr check by operator against the burr gauge."""
    d = t["attribute_by_operator"]; a = d[d["study"] == "at the redesign"].set_index("operator"); b = d[d["study"] == "after new limit samples"].set_index("operator")
    ops = a.sort_values("reject_rate").index.tolist(); y = np.arange(len(ops))
    panels = [(a, "At the assessment"), (b, "After the new limit samples")] if after else [(a, None)]
    f, axes = S.fig(h=3.6, w=None if after else 6.2, ncols=len(panels), sharey=True, grid="x"); axes = np.atleast_1d(axes)
    for ax, (tab, title) in zip(axes, panels):
        ref = float(tab["reference_reject_rate"].iloc[0]) * 100; v = S.sig(tab.loc[ops, "reject_rate"].values * 100)
        ax.hlines(y, np.minimum(v, ref), np.maximum(v, ref), color=S.LIGHT_BLUE, lw=3, zorder=2)
        ax.scatter(v, y, s=52, color=S.BRAND_BLUE, zorder=3)
        ax.axvline(ref, color=S.AMBER, lw=1.6, zorder=1); ax.text(ref + 1.2, len(ops) - 0.45, f"burr gauge {ref:.0f}%", fontsize=8.5, color=S.AMBER, va="center")
        for yi, vi in zip(y, v):
            ax.text(vi + (2.2 if vi >= ref else -2.2), yi, f"{vi:.0f}%", ha="left" if vi >= ref else "right", va="center", fontsize=9)
        ax.set_xlim(15, 90); ax.set_xlabel("Parts rejected, %"); ax.set_ylim(-0.6, len(ops) - 0.1)
        if title:
            ax.set_title(title, fontsize=11.5)
    axes[0].set_yticks(y); axes[0].set_yticklabels(ops)
    f.tight_layout()
    return S.save(f, "measurement_burr_by_operator" + ("_after_new_limit_samples" if after else ""), "Share of parts rejected on the burr check by operator against the burr gauge")


def last_digit(t, after=False):
    """The last digit of readings by entry method."""
    d = t["last_digits"]; panels = [("keyed", "Keyed"), ("paper transcription", "Paper, transcribed")] + ([("gauge-connected", "Gauge-connected")] if after else [])
    f, axes = S.fig(h=3.3, w=None if after else 7.0, ncols=len(panels), sharey=True)
    for ax, (method, title) in zip(axes, panels):
        g = d[d["entry_method"] == method].set_index("last_digit").reindex(range(10)).fillna(0)
        v = S.sig(g["share"].values * 100)
        ax.bar(range(10), v, 0.75, color=[S.BRAND_BLUE if k in (0, 5) else S.LIGHT_BLUE for k in range(10)])
        ax.axhline(10, color=S.DARK_GREY, ls="--", lw=1.0)
        ax.set_xticks(range(10)); ax.set_title(f"{title} ({int(g['readings'].sum()):,})", fontsize=10.5); ax.set_xlabel("Last digit")
    axes[0].set_ylabel("Share of readings, %"); axes[0].set_ylim(0, 22)
    f.tight_layout()
    return S.save(f, "measurement_last_digit" + ("_with_gauge_connected" if after else ""), "Share of readings ending in each digit by entry method, against the uniform 10%")


def readings_near_the_limit(t, after=False):
    """Readings by distance from the nearer specification limit, by entry method."""
    d = t["readings_at_the_limit"]
    lines = [("keyed", "Keyed", S.BRAND_BLUE), ("paper transcription", "Paper, transcribed", S.AMBER)] + ([("gauge-connected", "Gauge-connected", S.ACCENT)] if after else [])
    f, ax = S.fig(h=3.8, w=6.6)
    for method, label, color in lines:
        g = d[d["entry_method"] == method].sort_values("steps_from_the_limit")
        ax.plot(g["steps_from_the_limit"].values, S.sig(g["readings"].values), marker="o", ms=5, lw=1.6, color=color, label=label)
    ax.axvline(0, color=S.DARK_GREY, ls="--", lw=1.0)
    ax.set_yscale("log"); ax.yaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    ax.set_xlabel("Steps of the reading resolution from the nearer limit (negative inside, positive outside)"); ax.set_ylabel("Readings, log scale")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "measurement_readings_near_the_limit" + ("_with_gauge_connected" if after else ""), "Readings by distance from the nearer specification limit, by entry method")


def build(t):
    out = {}
    for after, suffix in ((False, ""), (True, "_after")):
        out.update({"grr" + suffix: grr_by_study(t, after), "split" + suffix: gauge_variance_split(t, after), "burr" + suffix: burr_by_operator(t, after), "digit" + suffix: last_digit(t, after), "limit" + suffix: readings_near_the_limit(t, after)})
    return out


if __name__ == "__main__":
    from analytics.measurement.measurement import compute
    print(build(compute()))
