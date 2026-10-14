"""Figures for the risk window and sorting analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np

from analytics.data import query
from analytics.style import style as S

BASES = ["sorted from a logged die-protection fault", "sorted back to the check before, in-house", "sorted back to the check before, sorting service",
         "fault logged at the check before; basis not distinguishable", "sorted at the customer"]
BASIS_LABEL = {BASES[0]: "From a logged die-protection fault", BASES[1]: "Back to the check before, in-house", BASES[2]: "Back to the check before, sorting service",
               BASES[3]: "Fault logged at the check before: basis not distinguishable", BASES[4]: "At the customer"}
SHORT = {BASES[0]: "From a logged\nfault", BASES[1]: "Back to the check,\nin-house", BASES[2]: "Back to the check,\nsorting service", BASES[3]: "Basis not\ndistinguishable", BASES[4]: "At the\ncustomer"}
BASIS_COLOR = {BASES[0]: S.BRAND_BLUE, BASES[1]: S.ACCENT, BASES[2]: S.AMBER, BASES[3]: S.GREY, BASES[4]: S.LIGHT_BLUE}


def parts_between_checks(t):
    """Parts between routine checks by press: the range across parts at run speed, with the median at run speed and at
    the realised rate, the bars coloured by press type."""
    d = t["risk_window"].sort_values(["press_group", "press_id"], kind="stable").reset_index(drop=True)
    f, ax = S.fig(h=4.8, grid="x")
    y = np.arange(len(d))[::-1]; hs = (d["press_group"] == "high_speed").values
    lo = S.sig(d["fewest_parts_between_checks"].values); hi = S.sig(d["most_parts_between_checks"].values); real = S.sig(d["median_parts_between_checks_at_the_realised_rate"].values)
    for mask, color, label in ((hs, S.ACCENT, "High-speed presses: lowest to highest part, at run speed"), (~hs, S.LIGHT_BLUE, "Medium presses: lowest to highest part, at run speed")):
        ax.hlines(y[mask], lo[mask], hi[mask], color=color, lw=8, label=label, zorder=2)
    ax.scatter(S.sig(d["median_parts_between_checks"].values), y, s=46, color=S.BRAND_BLUE, zorder=3, label="Median part, at run speed")
    ax.scatter(real, y, s=46, color=S.AMBER, marker="D", zorder=4, label="Median part, at the realised stroke rate")
    for yi, v in zip(y, real):
        ax.text(v, yi + 0.33, f"{v:,.0f}", ha="center", va="bottom", fontsize=8, color=S.AMBER, fontweight="bold")
    ax.text(float(hi.max()), y[int(np.argmax(hi))] + 0.33, f"{hi.max():,.0f}", ha="center", va="bottom", fontsize=8, color=S.DARK_GREY)
    ax.set_yticks(y); ax.set_yticklabels([f"{p} \u00b7 {int(fq)} min" for p, fq in zip(d["press_id"], d["plan_frequency_minutes"])])
    ax.set_xlabel("Parts between routine checks"); ax.set_xlim(0, 41000); ax.set_ylim(-0.7, len(d) - 0.2)
    ax.xaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.36), ncol=2, frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "risk_parts_between_checks", "Parts between routine checks by press, at run speed and at the realised stroke rate, with the check frequency of each press")


def sorted_against_exposure(through=2025):
    """One point per sorting event found at the press: parts since the check before (estimated) against quantity sorted,
    coloured by the basis of the sorting, filled for the last year shown and open for the years before."""
    d = query("""select sort_basis, sort_year, parts_from_check_before_to_finding_at_the_realised_rate as exposure, quantity_sorted
                 from marts.mart_sorting_events where detected_at <> 'customer' and sort_year <= ? order by sorting_event_id""", [through])
    groups = [("Bounded by a die-protection fault", [BASES[0]], S.BRAND_BLUE), ("Sorted back to the check before", [BASES[1], BASES[2]], S.AMBER), ("Fault logged at the check before: basis not distinguishable", [BASES[3]], S.GREY)]
    f, ax = S.fig(h=5.4, w=6.8, grid="y")
    for k, (label, bases, color) in enumerate(groups):
        g = d[d["sort_basis"].isin(bases)]
        for last, kw in ((True, {"color": color}), (False, {"facecolors": "white", "edgecolors": color, "linewidths": 1.6})):
            q = g[(g["sort_year"] == through) == last]
            ax.scatter(S.sig(q["exposure"].values), S.sig(q["quantity_sorted"].values), s=36, zorder=3, label=f"{label}, {through if last else 'earlier'} ({len(q)})", **kw)
        if k < 2 and len(g):
            q = g if k == 0 else g[g["sort_basis"] == BASES[1]]
            ax.text(0.985, 0.13 - 0.06 * k, f"{label}{'' if k == 0 else ', in-house'}: median {float(q['quantity_sorted'].median()):,.0f} parts sorted", transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=color, fontweight="bold")
    ax.plot([500, 60000], [500, 60000], color=S.DARK_GREY, lw=1.0, zorder=1)
    ax.text(38000, 47000, "1:1", fontsize=9, color=S.DARK_GREY, ha="right")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(500, 60000); ax.set_ylim(500, 60000)
    for a in (ax.xaxis, ax.yaxis):
        a.set_major_formatter(lambda v, _: f"{int(v):,}")
    ax.set_xlabel("Parts made since the check before (estimated), log scale"); ax.set_ylabel("Quantity sorted, log scale")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False, fontsize=8)
    f.tight_layout()
    return S.save(f, "risk_sorted_against_exposure" + ("" if through == 2025 else f"_to_{through}"), "Quantity sorted against the parts made since the check before, by the basis of the sorting and the year")


def sorting_by_year(through=2025):
    """Sorting events and cost by year and basis."""
    d = query("""select sort_year, sort_basis, count(*) as events, sum(sorting_cost_booked_or_estimated) as cost
                 from marts.mart_sorting_events where sort_year between 2024 and ? group by 1, 2 order by 1, 2""", [through])
    f, axes = S.fig(h=4.3, ncols=2)
    years = list(range(2024, through + 1)); x = np.arange(len(years))
    for ax, col, title, fmt in zip(axes, ("events", "cost"), ("Sorting events", "Cost booked or estimated, $"), ("{:.0f}", "${:,.0f}")):
        bottom = np.zeros(len(years))
        for b in BASES:
            v = np.array([float(d[(d["sort_year"] == y) & (d["sort_basis"] == b)][col].sum()) for y in years]); v = S.sig(v)
            ax.bar(x, v, 0.6, bottom=bottom, color=BASIS_COLOR[b], label=BASIS_LABEL[b])
            if col == "cost" and b in BASES[1:3]:
                for xi, vi, bi in zip(x, v, bottom):
                    if vi > 0:
                        ax.text(xi, bi + vi / 2, f"${vi:,.0f}", ha="center", va="center", fontsize=8.5, color="white" if b == BASES[1] else S.TEXT)
            bottom = bottom + v
        for xi, tot in zip(x, bottom):
            ax.text(xi, tot * 1.015, fmt.format(tot), ha="center", va="bottom", fontsize=9.5, color=S.TEXT)
        ax.set_xticks(x); ax.set_xticklabels([str(y) for y in years]); ax.set_title(title, fontsize=11.5); ax.set_ylim(0, bottom.max() * 1.14)
    axes[1].yaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    h_, l_ = axes[0].get_legend_handles_labels()
    f.legend(h_, l_, loc="lower center", ncol=2, frameon=False, fontsize=8.5)
    f.tight_layout(rect=(0, 0.17, 1, 1))
    return S.save(f, "risk_sorting_by_year" + ("" if through == 2025 else f"_to_{through}"), "Sorting events and sorting cost by year and basis of the sorting")


def rejected_share(through=2025):
    """Rejected share of the quantity sorted, by basis: pieces pooled over the events of each basis."""
    d = query("""select sort_basis, count(*) as events, sum(quantity_sorted)::bigint as sorted, sum(quantity_rejected)::bigint as rejected
                 from marts.mart_sorting_events where sort_year between 2024 and ? group by 1""", [through]).set_index("sort_basis").reindex(BASES).dropna()
    f, ax = S.fig(h=3.9, w=7.4)
    x = np.arange(len(d)); share = S.sig((d["rejected"] / d["sorted"]).values * 100)
    ax.bar(x, share, 0.6, color=[BASIS_COLOR[b] for b in d.index])
    for xi, v, n in zip(x, share, d["events"]):
        ax.text(xi, v + 2.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels([f"{lab}\n({int(n)} events)" for lab, n in zip([SHORT[b] for b in d.index], d["events"])], fontsize=9)
    ax.set_ylabel("Rejected share of the quantity sorted, %"); ax.set_ylim(0, 100)
    f.tight_layout()
    return S.save(f, "risk_rejected_share" + ("" if through == 2025 else f"_to_{through}"), f"Rejected share of the quantity sorted by the basis of the sorting, 2024 to {through}")


def build(t):
    return {"risk": parts_between_checks(t), "exposure": sorted_against_exposure(), "years": sorting_by_year(), "rejected": rejected_share(),
            "exposure_to_2026": sorted_against_exposure(2026), "years_to_2026": sorting_by_year(2026), "rejected_to_2026": rejected_share(2026)}


if __name__ == "__main__":
    from analytics.risk_window.risk_window import compute
    print(build(compute()))
