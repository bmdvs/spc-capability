"""Figures for the outcomes analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np
import pandas as pd

from analytics.data import query
from analytics.style import style as S

YEARS = [2023, 2024, 2025]
YEAR_COLOR = {2023: S.LIGHT_BLUE, 2024: S.GREY, 2025: S.BRAND_BLUE}
SETS = [("pilot presses", "Pilot presses,\nMarch to December"), ("comparison presses", "Comparison presses,\nFebruary to August"), ("rollout presses", "Rollout presses,\nSeptember to December")]


def _measures(t):
    """The five measures by press set and year: value, interval where one is reported, and the format."""
    so, pp, sc, ca, si = t["sorting"], t["ppm"], t["scrap_and_rework"], t["capability"], t["signals"]
    ca = ca[ca["characteristics_class"] == "formed"]; si = si[si["presses"] == "all presses of the set"]
    out = {}
    for s, _ in SETS:
        for y in YEARS:
            a = so[(so["press_set"] == s) & (so["year"] == y)].iloc[0]; b = pp[(pp["press_set"] == s) & (pp["year"] == y)].iloc[0]; c = sc[(sc["press_set"] == s) & (sc["year"] == y)].iloc[0]
            d = ca[(ca["press_set"] == s) & (ca["year"] == y)].iloc[0]; e = si[(si["press_set"] == s) & (si["period_year"] == y)].iloc[0]
            out[(s, y)] = {"sorting": (float(a.sorting_events), None, None), "ppm": (float(b.ppm), float(b.low), float(b.high)), "scrap": (float(c.scrap_and_rework_share_of_revenue) * 100, None, None),
                           "ppk": (float(d.ppk_median), float(d.ppk_low), float(d.ppk_high)), "signals": (float(e.alarm_signals_per_100_subgroups), None, None), "ppk_n": int(d.characteristics)}
    return out


PANELS = [("sorting", "Sorting events", "{:.0f}"), ("ppm", "Customer PPM", "{:.0f}"), ("scrap", "Scrap and rework,\n% of revenue", "{:.2f}"), ("ppk", "Ppk, critical formed\ncharacteristics (median)", "{:.2f}"),
          ("signals", "Alarm signals per\n100 subgroups", "{:.1f}")]


def pilot_five_measures(t):
    """The pilot presses on five measures, March to December of 2023, 2024 and 2025."""
    m = _measures(t)
    f, axes = S.fig(h=3.7, ncols=5)
    for ax, (key, title, fmt) in zip(axes, PANELS):
        top = 0
        for x, y in enumerate(YEARS):
            v, lo, hi = m[("pilot presses", y)][key]; v = float(S.sig(v))
            ax.bar(x, v, 0.68, color=YEAR_COLOR[y])
            if lo is not None:
                ax.errorbar(x, v, yerr=[[v - float(S.sig(lo))], [float(S.sig(hi)) - v]], color=S.TEXT, lw=1.1, capsize=3)
            edge = float(S.sig(hi)) if hi is not None else v; top = max(top, edge)
            ax.text(x, edge, fmt.format(v), ha="center", va="bottom", fontsize=8.5)
        ax.set_xticks(range(3)); ax.set_xticklabels([str(y) for y in YEARS], fontsize=8.5); ax.set_title(title, fontsize=9.5); ax.set_ylim(0, top * 1.16); ax.tick_params(axis="y", labelsize=8)
    f.tight_layout()
    return S.save(f, "outcomes_pilot_five_measures", "The pilot presses on sorting events, customer PPM, scrap and rework, Ppk on critical formed characteristics and alarm signals, March to December of 2023, 2024 and 2025")


def three_press_sets(t):
    """The three press sets on the same five measures, 2024 against 2025."""
    m = _measures(t)
    f, axes = S.fig(h=3.5, ncols=5, grid="x")
    for k, (ax, (key, title, fmt)) in enumerate(zip(axes, PANELS)):
        vals = []
        for i, (s, label) in enumerate(SETS):
            y = 2 - i; a, b = float(S.sig(m[(s, 2024)][key][0])), float(S.sig(m[(s, 2025)][key][0])); vals += [a, b]
            ax.plot([a, b], [y, y], color=S.LIGHT_BLUE, lw=3, zorder=1)
            ax.scatter([a], [y], s=40, color=S.GREY, zorder=2, label="2024" if (k == 0 and i == 0) else None); ax.scatter([b], [y], s=40, color=S.BRAND_BLUE, zorder=2, label="2025" if (k == 0 and i == 0) else None)
            note = f"{fmt.format(a)} to {fmt.format(b)}"
            ax.text((a + b) / 2, y + 0.2, note, ha="center", va="bottom", fontsize=7.5)
        span = max(vals) - min(vals); ax.set_xlim(min(vals) - 0.35 * span, max(vals) + 0.35 * span); ax.set_ylim(-0.5, 2.9)
        ax.set_yticks(range(3)); ax.set_yticklabels([lab for _, lab in SETS][::-1] if k == 0 else [], fontsize=8.5); ax.set_title(title.replace("critical formed", "formed").replace(" (median)", ""), fontsize=8.5); ax.tick_params(axis="x", labelsize=8)
    f.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.05))
    counts = "; ".join(f"{lab.split(',')[0].lower()} {m[(s_, 2024)]['ppk_n']} and {m[(s_, 2025)]['ppk_n']}" for s_, lab in SETS)
    f.text(0.01, 0.01, f"Ppk: characteristics with 60 subgroups or more in the period, 2024 and 2025: {counts}.", fontsize=8, color=S.DARK_GREY, ha="left", va="bottom")
    f.tight_layout(rect=(0, 0.12, 1, 1))
    return S.save(f, "outcomes_three_press_sets", "The pilot, comparison and rollout presses on five measures, 2024 against 2025, each on its own months")


def ppk_by_characteristic(t):
    """Ppk on the pilot presses' critical formed characteristics, 2024 against 2025."""
    c = t["capability_by_characteristic"]; c = c[(c["press_set"] == "pilot presses") & (c["class"] == "formed")]
    w = c.pivot_table(index="characteristic_id", columns="year", values="ppk").dropna(subset=[2024, 2025]).sort_index()
    x, y = S.sig(w[2024].values), S.sig(w[2025].values)
    f, ax = S.fig(h=4.6, w=5.2, grid="y"); lim = (0.5, 2.3)
    ax.plot(lim, lim, color=S.DARK_GREY, ls="--", lw=1.0)
    ax.axvline(1.33, color=S.AMBER, lw=1.0); ax.axhline(1.33, color=S.AMBER, lw=1.0); ax.text(lim[1] - 0.02, 1.35, "1.33", color=S.AMBER, fontsize=8.5, ha="right", va="bottom")
    ax.scatter(x, y, s=20, color=S.BRAND_BLUE, alpha=0.75, lw=0)
    ax.set_xlim(*lim); ax.set_ylim(*lim); ax.set_aspect("equal"); ax.set_xlabel("Ppk, March to December 2024"); ax.set_ylabel("Ppk, March to December 2025")
    f.tight_layout()
    return S.save(f, "outcomes_ppk_by_characteristic", f"Production Ppk on the {len(w)} critical formed characteristics of the pilot presses, March to December 2024 against March to December 2025"), w


def complaints_by_month(t):
    """Complaints received by month on the pilot presses' parts, 2023 to 2025."""
    d = t["pilot_complaints_by_month"]
    months = pd.date_range("2023-01-01", "2025-12-01", freq="MS"); v = d.set_index("month_start")["complaints"].reindex(months).fillna(0).values
    f, ax = S.fig(h=3.4)
    ax.bar(range(36), v, 0.8, color=[YEAR_COLOR[m.year] for m in months])
    for xpos, label in ((24 + 2 / 28, "Redesign,\n3 February 2025"), (28 + 4 / 31, "Per-stroke monitoring,\n5 May 2025")):
        ax.axvline(xpos - 0.5, color=S.RED, lw=1.1); ax.text(xpos - 0.3, v.max() + (0.6 if xpos < 26 else -0.4), label, fontsize=8, color=S.RED, va="top")
    ax.set_xticks(range(0, 36, 3)); ax.set_xticklabels([months[i].strftime("%b %Y") for i in range(0, 36, 3)], fontsize=8, rotation=45, ha="right")
    ax.set_ylabel("Complaints received"); ax.set_ylim(0, v.max() + 0.8); ax.yaxis.get_major_locator().set_params(integer=True)
    f.tight_layout()
    return S.save(f, "outcomes_complaints_by_month", "Complaints received by month on the pilot presses' parts, 2023 to 2025, with the dates of the redesign and of per-stroke monitoring"), int(v.sum())


def cost_lines(t):
    """Quality cost lines as booked by category on the pilot presses, three years."""
    d = t["cost_lines"]; d = d[(d["press_set"] == "pilot presses") & ~d["category"].str.startswith("sorting, booked or estimated")].set_index("category")
    order = ["customer charge-back", "premium freight", "third-party sorting", "sorting labor", "rework labor", "scrap"]
    f, ax = S.fig(h=4.2, grid="x")
    for i, cat in enumerate(order):
        for j, y in enumerate(YEARS):
            v = float(S.sig(d.loc[cat, y])); ypos = i + (1 - j) * 0.27
            ax.barh(ypos, max(v, 1), 0.25, color=YEAR_COLOR[y], label=str(y) if i == 0 else None)
            ax.text(max(v, 100) * 1.12, ypos, f"${v:,.0f}", va="center", fontsize=8)
    ax.set_xscale("log"); ax.set_xlim(100, 2_000_000); ax.set_yticks(range(len(order))); ax.set_yticklabels([c[0].upper() + c[1:] for c in order])
    ax.set_xlabel("Booked, March to December, $ (log scale)"); ax.xaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "outcomes_cost_lines", "Quality cost lines as booked by category on the pilot presses, March to December of 2023, 2024 and 2025")


def build(t):
    ppk, w = ppk_by_characteristic(t); comp, n = complaints_by_month(t)
    return {"pilot": pilot_five_measures(t), "sets": three_press_sets(t), "ppk": ppk, "ppk_table": w, "complaints": comp, "complaints_n": n, "costs": cost_lines(t)}


if __name__ == "__main__":
    from analytics.outcomes.outcomes import compute
    b = build(compute()); w = b.pop("ppk_table")
    print(b); print(len(w), int((w[2025] > w[2024]).sum()), int((w[2024] < 1.33).sum()), int((w[2025] < 1.33).sum()), int(((w[2024] < 1.33) & (w[2025] >= 1.33)).sum()))
