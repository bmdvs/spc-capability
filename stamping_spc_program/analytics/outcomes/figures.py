"""Figures for the outcomes analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np
import pandas as pd

from analytics.data import query
from analytics.style import style as S

YEARS = [2024, 2025, 2026]
YEAR_COLOR = {2024: S.LIGHT_BLUE, 2025: S.GREY, 2026: S.BRAND_BLUE}
SETS = [("pilot presses", "Pilot presses,\nApril to June"), ("comparison presses", "Comparison presses,\nApril to June")]


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
    """The pilot presses on five measures, April to June of 2024, 2025 and 2026."""
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
    return S.save(f, "outcomes_pilot_five_measures", "The pilot presses on sorting events, customer PPM, scrap and rework, Ppk on critical formed characteristics and alarm signals, April to June of 2024, 2025 and 2026")


def three_press_sets(t):
    """The press sets on the same five measures, 2025 against 2026."""
    m = _measures(t)
    f, axes = S.fig(h=3.5, ncols=5, grid="x")
    for k, (ax, (key, title, fmt)) in enumerate(zip(axes, PANELS)):
        vals = []
        for i, (s, label) in enumerate(SETS):
            y = len(SETS) - 1 - i; a, b = float(S.sig(m[(s, 2025)][key][0])), float(S.sig(m[(s, 2026)][key][0])); vals += [a, b]
            ax.plot([a, b], [y, y], color=S.LIGHT_BLUE, lw=3, zorder=1)
            ax.scatter([a], [y], s=40, color=S.GREY, zorder=2, label="2025" if (k == 0 and i == 0) else None); ax.scatter([b], [y], s=40, color=S.BRAND_BLUE, zorder=2, label="2026" if (k == 0 and i == 0) else None)
            note = f"{fmt.format(a)} to {fmt.format(b)}"
            ax.text((a + b) / 2, y + 0.2, note, ha="center", va="bottom", fontsize=7.5)
        span = max(vals) - min(vals); ax.set_xlim(min(vals) - 0.35 * span, max(vals) + 0.35 * span); ax.set_ylim(-0.5, len(SETS) - 0.1)
        ax.set_yticks(range(len(SETS))); ax.set_yticklabels([lab for _, lab in SETS][::-1] if k == 0 else [], fontsize=8.5); ax.set_title(title.replace("critical formed", "formed").replace(" (median)", ""), fontsize=8.5); ax.tick_params(axis="x", labelsize=8)
    f.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.05))
    counts = "; ".join(f"{lab.split(',')[0].lower()} {m[(s_, 2025)]['ppk_n']} and {m[(s_, 2026)]['ppk_n']}" for s_, lab in SETS)
    f.text(0.01, 0.01, f"Ppk: characteristics with 60 subgroups or more in the period, 2025 and 2026: {counts}.", fontsize=8, color=S.DARK_GREY, ha="left", va="bottom")
    f.tight_layout(rect=(0, 0.12, 1, 1))
    return S.save(f, "outcomes_three_press_sets", "The pilot and comparison presses on five measures, April to June 2025 against April to June 2026")


def ppk_by_characteristic(t):
    """Ppk on the pilot presses' critical formed characteristics, 2025 against 2026."""
    c = t["capability_by_characteristic"]; c = c[(c["press_set"] == "pilot presses") & (c["class"] == "formed")]
    w = c.pivot_table(index="characteristic_id", columns="year", values="ppk").dropna(subset=[2025, 2026]).sort_index()
    x, y = S.sig(w[2025].values), S.sig(w[2026].values)
    f, ax = S.fig(h=4.6, w=5.2, grid="y"); lim = (0.5, 2.3)
    ax.plot(lim, lim, color=S.DARK_GREY, ls="--", lw=1.0)
    ax.axvline(1.33, color=S.AMBER, lw=1.0); ax.axhline(1.33, color=S.AMBER, lw=1.0); ax.text(lim[1] - 0.02, 1.35, "1.33", color=S.AMBER, fontsize=8.5, ha="right", va="bottom")
    ax.scatter(x, y, s=20, color=S.BRAND_BLUE, alpha=0.75, lw=0)
    ax.set_xlim(*lim); ax.set_ylim(*lim); ax.set_aspect("equal"); ax.set_xlabel("Ppk, April to June 2025"); ax.set_ylabel("Ppk, April to June 2026")
    f.tight_layout()
    return S.save(f, "outcomes_ppk_by_characteristic", f"Production Ppk on the {len(w)} critical formed characteristics of the pilot presses, April to June 2025 against April to June 2026"), w


def complaints_by_month(t):
    """Complaints received by month on the pilot presses' parts, 2024 to 2026."""
    d = t["pilot_complaints_by_month"]
    months = pd.date_range("2024-01-01", "2026-06-01", freq="MS"); v = d.set_index("month_start")["complaints"].reindex(months).fillna(0).values
    f, ax = S.fig(h=3.4)
    ax.bar(range(len(months)), v, 0.8, color=[YEAR_COLOR[m.year] for m in months])
    for xpos, label in ((25 + 1 / 28, "Redesign,\n2 February 2026"), (27.0, "Per-stroke monitoring,\n1 April 2026")):
        ax.axvline(xpos - 0.5, color=S.RED, lw=1.1); ax.text(xpos - 0.3, v.max() + (0.6 if xpos < 26 else -0.4), label, fontsize=8, color=S.RED, va="top")
    ax.set_xticks(range(0, len(months), 3)); ax.set_xticklabels([months[i].strftime("%b %Y") for i in range(0, len(months), 3)], fontsize=8, rotation=45, ha="right")
    ax.set_ylabel("Complaints received"); ax.set_ylim(0, v.max() + 0.8); ax.yaxis.get_major_locator().set_params(integer=True)
    f.tight_layout()
    return S.save(f, "outcomes_complaints_by_month", "Complaints received by month on the pilot presses' parts, 2024 to 2026, with the dates of the redesign and of per-stroke monitoring"), int(v.sum())


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
    ax.set_xlabel("Booked, April to June, $ (log scale)"); ax.xaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "outcomes_cost_lines", "Quality cost lines as booked by category on the pilot presses, April to June of 2024, 2025 and 2026")


def press_sets_five_measures(t):
    """The press sets on the five measures, April to June of 2024, 2025 and 2026."""
    m = _measures(t)
    order = ["scrap", "ppk", "signals", "ppm", "sorting"]; panels = sorted(PANELS, key=lambda p: order.index(p[0])); tops = {}
    f, axes = S.fig(h=2.4 * len(SETS), ncols=5, nrows=len(SETS), sharey="col")
    for i, (s, label) in enumerate(SETS):
        for j, (key, title, fmt) in enumerate(panels):
            ax = axes[i, j]; top = tops.get(key, 0)
            for x, y in enumerate(YEARS):
                v, lo, hi = m[(s, y)][key]; v = float(S.sig(v))
                ax.bar(x, v, 0.68, color=YEAR_COLOR[y])
                if lo is not None:
                    ax.errorbar(x, v, yerr=[[v - float(S.sig(lo))], [float(S.sig(hi)) - v]], color=S.TEXT, lw=1.1, capsize=3)
                edge = float(S.sig(hi)) if hi is not None else v; top = max(top, edge)
                ax.text(x, edge, fmt.format(v), ha="center", va="bottom", fontsize=8.5)
            tops[key] = top; ax.set_xticks(range(3)); ax.set_xticklabels([str(y) for y in YEARS], fontsize=8.5); ax.set_ylim(0, max(top, 1) * 1.16); ax.tick_params(axis="y", labelsize=8, labelleft=True)
            if key == "sorting":
                ax.yaxis.get_major_locator().set_params(integer=True)
            if i == 0:
                ax.set_title(title, fontsize=9.5)
            if j == 0:
                ax.set_ylabel(label, fontsize=9.5, fontweight="bold", color=S.BRAND_BLUE)
    counts = "; ".join(f"{lab.split(',')[0].lower()} " + ", ".join(str(m[(s_, y)]["ppk_n"]) for y in YEARS) for s_, lab in SETS)
    f.text(0.01, 0.005, f"Ppk: characteristics with 60 subgroups or more in both 2025 and 2026, and in 2024 those of them with 60 there; counts for 2024, 2025 and 2026: {counts}.", fontsize=8, color=S.DARK_GREY, ha="left", va="bottom")
    f.tight_layout(rect=(0, 0.03, 1, 1))
    return S.save(f, "outcomes_press_sets_five_measures", "The pilot and comparison presses on sorting events, customer PPM, scrap and rework, Ppk on critical formed characteristics and alarm signals, April to June of 2024, 2025 and 2026")


def _grouped_by_set(ax, values, fmt, intervals=None, notes=None):
    """One group of three year columns per press set; values, intervals and notes are keyed by (press set, year)."""
    top = 0
    for i, (s, _) in enumerate(SETS):
        for j, y in enumerate(YEARS):
            x = i + (j - 1) * 0.27; v = float(S.sig(values[(s, y)]))
            ax.bar(x, v, 0.25, color=YEAR_COLOR[y], label=str(y) if i == 0 else None); edge = v
            if intervals is not None:
                lo, hi = (float(S.sig(q)) for q in intervals[(s, y)]); ax.errorbar(x, v, yerr=[[v - lo], [hi - v]], color=S.TEXT, lw=1.1, capsize=3); edge = hi
            ax.text(x, edge, fmt.format(v) + (f"\n{notes[(s, y)]}" if notes else ""), ha="center", va="bottom", fontsize=8)
            top = max(top, edge)
    ax.set_xticks(range(len(SETS))); ax.set_xticklabels([lab for _, lab in SETS], fontsize=9)
    return top


def burr_over_the_limit(t):
    """Share of sharpening intervals with burr over the limit before the sharpening, by press set and year."""
    b = t["burr"].set_index(["press_set", "period_year"])
    val = {k: b.loc[k, "share_over_the_limit"] * 100 for k in b.index}; ci = {k: (b.loc[k, "low"] * 100, b.loc[k, "high"] * 100) for k in b.index}
    note = {k: f"{int(b.loc[k, 'intervals_with_burr_over_the_limit'])} of {int(b.loc[k, 'intervals_with_burr_gauge_subgroups'])}" for k in b.index}
    f, ax = S.fig(h=4.0)
    top = _grouped_by_set(ax, val, "{:.0f}%", ci, note)
    ax.set_ylim(0, top * 1.22); ax.set_ylabel("Sharpening intervals with burr\nover the limit before the sharpening, %"); ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.legend(loc="upper right", frameon=False, fontsize=9, ncol=3)
    f.tight_layout()
    return S.save(f, "outcomes_burr_over_the_limit", "Share of sharpening intervals with burr over the limit before the sharpening, with 95% intervals, by press set and year")


def alarm_rate_and_response(t):
    """Alarm signals per 100 subgroups and the share with an adjustment recorded, by press set and year."""
    g = t["signals"]; g = g[g["presses"] == "all presses of the set"].set_index(["press_set", "period_year"])
    f, axes = S.fig(h=4.0, ncols=2)
    top = _grouped_by_set(axes[0], {k: g.loc[k, "alarm_signals_per_100_subgroups"] for k in g.index}, "{:.1f}")
    axes[0].set_ylim(0, top * 1.14); axes[0].set_title("Alarm signals\nper 100 subgroups", fontsize=11)
    _grouped_by_set(axes[1], {k: g.loc[k, "adjustment_share"] * 100 for k in g.index}, "{:.0f}%")
    axes[1].set_ylim(0, 100); axes[1].set_title("Alarm signals with\nan adjustment recorded", fontsize=11); axes[1].yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    for ax in axes:
        ax.set_xticklabels([lab.replace(" to ", " to\n") for _, lab in SETS], fontsize=8.5)
    f.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=3, frameon=False, fontsize=9)
    f.tight_layout(rect=(0, 0.07, 1, 1), w_pad=2.5)
    return S.save(f, "outcomes_alarm_rate_and_response", "Alarm signals per 100 subgroups and the share with an adjustment recorded, by press set and year")


def hole_diameter_on_the_tool_wear_chart(die="D-0417-B", characteristic="C-20417-01"):
    """One hole diameter on its tool-wear chart: subgroup means against shots since sharpening with the centre line and
    limits in force at each entry, on the die's sharpening interval that began in April to June 2026, ended or still running at 30 June."""
    d = query("""select h.sharpening_interval_no, h.shots_since_sharpening / 1000 as shots, h.subgroup_mean, h.centre_line, h.ucl_mean, h.lcl_mean, h.usl, h.lsl, h.alarm_raised
                 from intermediate.int_characteristic_history h join intermediate.int_sharpening_intervals i using (die_id, sharpening_interval_no)
                 where h.die_id = ? and h.characteristic_id = ? and h.after_redesign and h.limits_in_force and h.subgroup_mean is not null
                   and i.interval_start >= date '2026-04-01' and (i.interval_end is null or i.interval_end < date '2026-07-01')
                 order by h.sharpening_interval_no, h.shots_since_sharpening, h.subgroup_id""", [die, characteristic])
    no = d.groupby("sharpening_interval_no").size().sort_values(ascending=False, kind="stable").index[0]; d = d[d["sharpening_interval_no"] == no]
    x = S.sig(d["shots"].values); a = d["alarm_raised"].values.astype(bool)
    f, ax = S.fig(h=4.2)
    usl, lsl = float(d["usl"].iloc[0]), float(d["lsl"].iloc[0])
    for v, lab in ((usl, "USL"), (lsl, "LSL")):
        ax.axhline(v, color=S.GREY, lw=1.4); ax.text(float(x.max()) * 1.015, v, f"{lab} {v:.4f}", color=S.DARK_GREY, fontsize=8.5, ha="right", va="bottom")
    ax.plot(x, S.sig(d["centre_line"].values), color=S.BRAND_BLUE, lw=1.6, label="Tool-wear centre line")
    ax.plot(x, S.sig(d["ucl_mean"].values), color=S.RED, lw=1.0, ls="--", label="Limits"); ax.plot(x, S.sig(d["lcl_mean"].values), color=S.RED, lw=1.0, ls="--")
    ax.scatter(x[~a], S.sig(d["subgroup_mean"].values[~a]), s=10, color=S.ACCENT, alpha=0.6, lw=0, label=f"Subgroup mean ({len(d)})")
    ax.scatter(x[a], S.sig(d["subgroup_mean"].values[a]), s=34, facecolors="none", edgecolors=S.RED, linewidths=1.5, label=f"Alarm signal ({int(a.sum())})")
    pad = (usl - lsl) * 0.09; ax.set_ylim(lsl - pad, usl + pad); ax.set_xlim(0, float(x.max()) * 1.02)
    ax.set_xlabel("Shots since sharpening, thousands"); ax.set_ylabel("Hole diameter, subgroup mean, mm")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=4, frameon=False, fontsize=8.5)
    f.tight_layout()
    begun = pd.Timestamp(query("select interval_start from intermediate.int_sharpening_intervals where die_id = ? and sharpening_interval_no = ?", [die, float(no)])["interval_start"].iloc[0])
    info = {"die_id": die, "characteristic_id": characteristic, "interval_begun": f"{begun.day} {begun.strftime('%B %Y')}", "subgroups": len(d), "alarm_signals": int(a.sum()), "shots_at_the_last_subgroup": float(d["shots"].max()) * 1000, "centre_line_at_the_first": float(d["centre_line"].iloc[0]),
            "centre_line_at_the_last": float(d["centre_line"].iloc[-1]), "limit_half_width": float((d["ucl_mean"] - d["centre_line"]).median())}
    return S.save(f, "outcomes_hole_diameter_tool_wear_chart", f"Hole diameter {characteristic} on die {die} against shots since sharpening over one sharpening interval of 2026, with the tool-wear centre line and limits"), info


def build(t):
    ppk, w = ppk_by_characteristic(t); comp, n = complaints_by_month(t)
    return {"pilot": pilot_five_measures(t), "sets": three_press_sets(t), "ppk": ppk, "ppk_table": w, "complaints": comp, "complaints_n": n, "costs": cost_lines(t)}


if __name__ == "__main__":
    from analytics.outcomes.outcomes import compute
    b = build(compute()); w = b.pop("ppk_table")
    print(b); print(len(w), int((w[2026] > w[2025]).sum()), int((w[2025] < 1.33).sum()), int((w[2026] < 1.33).sum()), int(((w[2025] < 1.33) & (w[2026] >= 1.33)).sum()))
