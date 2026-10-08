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
    """Parts between routine checks by press: the range across parts at run speed, with the median at run speed and at the realised rate."""
    d = t["risk_window"].sort_values(["press_group", "press_id"], kind="stable").reset_index(drop=True)
    f, ax = S.fig(h=4.4, grid="x")
    y = np.arange(len(d))[::-1]
    lo = S.sig(d["fewest_parts_between_checks"].values); hi = S.sig(d["most_parts_between_checks"].values)
    ax.hlines(y, lo, hi, color=S.LIGHT_BLUE, lw=7, label="Lowest to highest part, at run speed", zorder=2)
    ax.scatter(S.sig(d["median_parts_between_checks"].values), y, s=46, color=S.BRAND_BLUE, zorder=3, label="Median part, at run speed")
    ax.scatter(S.sig(d["median_parts_between_checks_at_the_realised_rate"].values), y, s=46, color=S.AMBER, marker="D", zorder=3, label="Median part, at the realised stroke rate")
    ax.set_yticks(y); ax.set_yticklabels([f"{p}  ({g.replace('_', '-')}, {int(fq)} min)" for p, g, fq in zip(d["press_id"], d["press_group"], d["plan_frequency_minutes"])])
    ax.set_xlabel("Parts between routine checks"); ax.set_xlim(0, 40000)
    ax.xaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "risk_parts_between_checks", "Parts between routine checks by press, at run speed and at the realised stroke rate")


def sorted_against_exposure(through=2024):
    """One point per sorting event found at the press: parts since the check before (estimated) against quantity sorted."""
    d = query("""select sort_basis, parts_from_check_before_to_finding_at_the_realised_rate as exposure, quantity_sorted
                 from marts.mart_sorting_events where detected_at <> 'customer' and sort_year <= ? order by sorting_event_id""", [through])
    f, ax = S.fig(h=4.6, w=6.6, grid="y")
    for b in BASES[:4]:
        g = d[d["sort_basis"] == b]
        ax.scatter(S.sig(g["exposure"].values), S.sig(g["quantity_sorted"].values), s=34, color=BASIS_COLOR[b], label=f"{BASIS_LABEL[b]} ({len(g)})", zorder=3,
                   edgecolors="white", linewidths=0.6)
    ax.plot([500, 60000], [500, 60000], color=S.DARK_GREY, lw=1.0, zorder=1)
    ax.text(38000, 47000, "1:1", fontsize=9, color=S.DARK_GREY, ha="right")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(500, 60000); ax.set_ylim(500, 60000)
    for a in (ax.xaxis, ax.yaxis):
        a.set_major_formatter(lambda v, _: f"{int(v):,}")
    ax.set_xlabel("Parts since the check before (estimated), log scale"); ax.set_ylabel("Quantity sorted, log scale")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "risk_sorted_against_exposure" + ("" if through == 2024 else f"_to_{through}"), "Quantity sorted against the parts made since the check before, by the basis of the sorting")


def sorting_by_year(through=2024):
    """Sorting events and cost by year and basis."""
    d = query("""select sort_year, sort_basis, count(*) as events, sum(sorting_cost_booked_or_estimated) as cost
                 from marts.mart_sorting_events where sort_year between 2023 and ? group by 1, 2 order by 1, 2""", [through])
    f, axes = S.fig(h=4.3, ncols=2)
    years = list(range(2023, through + 1)); x = np.arange(len(years))
    for ax, col, title, fmt in zip(axes, ("events", "cost"), ("Sorting events", "Cost booked or estimated, $"), ("{:.0f}", "${:,.0f}")):
        bottom = np.zeros(len(years))
        for b in BASES:
            v = np.array([float(d[(d["sort_year"] == y) & (d["sort_basis"] == b)][col].sum()) for y in years]); v = S.sig(v)
            ax.bar(x, v, 0.6, bottom=bottom, color=BASIS_COLOR[b], label=BASIS_LABEL[b])
            bottom = bottom + v
        for xi, tot in zip(x, bottom):
            ax.text(xi, tot * 1.015, fmt.format(tot), ha="center", va="bottom", fontsize=9.5, color=S.TEXT)
        ax.set_xticks(x); ax.set_xticklabels([str(y) for y in years]); ax.set_title(title, fontsize=11.5); ax.set_ylim(0, bottom.max() * 1.14)
    axes[1].yaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
    h_, l_ = axes[0].get_legend_handles_labels()
    f.legend(h_, l_, loc="lower center", ncol=2, frameon=False, fontsize=8.5)
    f.tight_layout(rect=(0, 0.17, 1, 1))
    return S.save(f, "risk_sorting_by_year" + ("" if through == 2024 else f"_to_{through}"), "Sorting events and sorting cost by year and basis of the sorting")


def rejected_share(through=2024):
    """Rejected share of the quantity sorted, by basis: pieces pooled over the events of each basis."""
    d = query("""select sort_basis, count(*) as events, sum(quantity_sorted)::bigint as sorted, sum(quantity_rejected)::bigint as rejected
                 from marts.mart_sorting_events where sort_year between 2023 and ? group by 1""", [through]).set_index("sort_basis").reindex(BASES).dropna()
    f, ax = S.fig(h=3.9, w=7.4)
    x = np.arange(len(d)); share = S.sig((d["rejected"] / d["sorted"]).values * 100)
    ax.bar(x, share, 0.6, color=[BASIS_COLOR[b] for b in d.index])
    for xi, v, n in zip(x, share, d["events"]):
        ax.text(xi, v + 2.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(x); ax.set_xticklabels([f"{lab}\n({int(n)} events)" for lab, n in zip([SHORT[b] for b in d.index], d["events"])], fontsize=9)
    ax.set_ylabel("Rejected share of the quantity sorted, %"); ax.set_ylim(0, 100)
    f.tight_layout()
    return S.save(f, "risk_rejected_share" + ("" if through == 2024 else f"_to_{through}"), f"Rejected share of the quantity sorted by the basis of the sorting, 2023 to {through}")


def build(t):
    return {"risk": parts_between_checks(t), "exposure": sorted_against_exposure(), "years": sorting_by_year(), "rejected": rejected_share(),
            "exposure_to_2025": sorted_against_exposure(2025), "years_to_2025": sorting_by_year(2025), "rejected_to_2025": rejected_share(2025)}


if __name__ == "__main__":
    from analytics.risk_window.risk_window import compute
    print(build(compute()))
