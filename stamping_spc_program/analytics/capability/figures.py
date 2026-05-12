"""Figures for the subgrouping and capability analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np

from analytics.data import query
from analytics.style import style as S

FORMED_COLOR, PUNCHED_COLOR = S.BRAND_BLUE, S.AMBER
PUNCHED_LIGHT = "#EBC48E"          # the light version of the punched colour: as filed


def filed_against_production(t):
    """Filed Ppk against production Ppk, one point per study, with the production interval and each class's medians."""
    d = t["by_study"]
    f, ax = S.fig(h=4.9, w=6.8)
    for cls, color in (("formed", FORMED_COLOR), ("punched", PUNCHED_COLOR)):
        g = d[d["characteristic_class"] == cls]
        x = S.sig(g["filed_ppk"].values); y = S.sig(g["ppk"].values); lo = S.sig(g["ppk_low"].values); hi = S.sig(g["ppk_high"].values)
        ax.vlines(x, lo, hi, color=color, alpha=0.22, lw=1.0, zorder=2)
        ax.scatter(x, y, s=16, color=color, label=f"{cls.capitalize()} ({len(g)} studies)", zorder=3)
        mx, my = float(g["filed_ppk"].median()), float(g["ppk"].median())
        ax.scatter([float(S.sig(mx))], [float(S.sig(my))], s=150, facecolors="white", edgecolors=color, linewidths=2.4, zorder=5)
        ax.annotate(f"{cls.capitalize()}: {mx:.2f} filed, {my:.2f} production", (mx, my), textcoords="offset points", xytext=(-12, -18 if cls == "formed" else 14), ha="right", fontsize=9, color=color, fontweight="bold", zorder=6, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1.5})
    ax.plot([0.6, 2.4], [0.6, 2.4], color=S.DARK_GREY, lw=1.0, zorder=1)
    ax.text(2.36, 2.26, "filed = production", ha="right", va="top", fontsize=8.5, color=S.DARK_GREY, rotation=37)
    ax.axhline(1.33, color=S.DARK_GREY, ls="--", lw=1.0, zorder=1); ax.axvline(1.33, color=S.DARK_GREY, ls="--", lw=1.0, zorder=1); ax.text(0.63, 1.35, "1.33", fontsize=8.5, color=S.DARK_GREY, va="bottom")
    fo = d[d["characteristic_class"] == "formed"]
    ax.text(0.03, 0.83, f"Formed, filed at least 0.40\nabove production: {int((fo['filed_less_production_ppk'] >= 0.40).sum())} of {len(fo)}", transform=ax.transAxes, ha="left", va="top", fontsize=9.5, color=FORMED_COLOR)
    ax.set_xlim(0.6, 2.4); ax.set_ylim(0.6, 2.4); ax.set_xlabel("Ppk filed at PPAP, 300 consecutive pieces on the CMM"); ax.set_ylabel("Production Ppk on the check fixture")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "capability_filed_against_production", "Filed Ppk against production Ppk by study, with the production interval and the medians of formed and punched characteristics")


def ppk_by_punched_subclass(t):
    """Punched characteristics by sub-class: the median Ppk filed, the median production Ppk with its bootstrap interval
    and the median production Cpk, with the studies within 0.25 of the filed figure."""
    d = t["by_study"]; d = d[d["characteristic_class"] == "punched"]; order = ["hole-to-hole", "hole-to-edge", "hole diameter"]; names = ["Hole-to-hole", "Hole-to-edge", "Hole diameter"]
    f, ax = S.fig(h=4.2, w=6.8); w = 0.3
    for i, ty in enumerate(order):
        g = d[d["characteristic_type"] == ty]; v = g["ppk"].values; r = np.random.default_rng([20250102, 7, i])
        boot = [np.median(v[r.integers(0, len(v), len(v))]) for _ in range(2000)]; lo, hi = float(S.sig(np.percentile(boot, 2.5))), float(S.sig(np.percentile(boot, 97.5)))
        fl, pr, cp = (float(S.sig(g[c].median())) for c in ("filed_ppk", "ppk", "cpk")); within = int((g["filed_less_production_ppk"].abs() <= 0.25).sum())
        ax.bar(i - w / 2, fl, w, color=PUNCHED_LIGHT, label="Ppk filed at PPAP, median" if i == 0 else None); ax.bar(i + w / 2, pr, w, color=PUNCHED_COLOR, label="Production Ppk, median, with its 95% interval" if i == 0 else None)
        ax.errorbar(i + w / 2, pr, yerr=[[pr - lo], [hi - pr]], color=S.TEXT, lw=1.2, capsize=4)
        ax.scatter([i + w / 2], [cp], marker="D", s=62, facecolors="white", edgecolors=S.TEXT, linewidths=1.6, zorder=5, label="Production Cpk, median" if i == 0 else None)
        ax.text(i - w / 2, fl + 0.03, f"{fl:.2f}", ha="center", va="bottom", fontsize=9); ax.text(i + w / 2, pr - 0.2, f"{pr:.2f}", ha="center", va="top", fontsize=9, color="white", fontweight="bold")
        ax.text(i + w / 2 + 0.1, cp, f"Cpk {cp:.2f}", ha="left", va="center", fontsize=9)
        ax.text(i, 2.5, f"Within 0.25:\n{within} of {len(g)}", ha="center", va="center", fontsize=9.5, fontweight="bold", color=S.TEXT)
    ax.axhline(1.33, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(-0.48, 1.35, "1.33", fontsize=8.5, color=S.DARK_GREY, va="bottom")
    ax.set_xticks(range(3)); ax.set_xticklabels(names); ax.set_ylim(0, 2.75); ax.set_xlim(-0.5, 2.75); ax.set_ylabel("Capability index, median over studies")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.3), ncol=3, frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "capability_ppk_by_punched_subclass", "Median Ppk filed, production Ppk and production Cpk on hole-to-hole, hole-to-edge and hole diameter characteristics, with the studies within 0.25 of the filed figure")


def variance_components(t):
    """Median share of overall variance by component, formed and punched."""
    d = t["capability_summary"].set_index("characteristic_class")
    f, ax = S.fig(h=2.6, grid="x")
    parts = (("share_between_coils", "Between coils", S.BRAND_BLUE), ("share_between_subgroups_within_coil", "Between subgroups within a coil", S.ACCENT), ("share_within_subgroup", "Within subgroups", S.LIGHT_BLUE))
    for yi, cls in enumerate(("punched", "formed")):
        v = np.array([float(d.loc[cls, c]) for c, _, _ in parts]); v = S.sig(v / v.sum() * 100); left = 0.0
        for (c, label, color), w in zip(parts, v):
            ax.barh(yi, w, left=left, color=color, height=0.55, label=label if yi == 0 else None)
            if w >= 4:
                ax.text(left + w / 2, yi, f"{w:.0f}%", ha="center", va="center", fontsize=10, color="white" if color != S.LIGHT_BLUE else S.TEXT)
            else:
                ax.text(left + w / 2, yi + 0.3, f"{w:.0f}%", ha="center", va="bottom", fontsize=9, color=color)
            left += w
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Punched", "Formed"]); ax.set_xlim(0, 100); ax.set_xlabel("Share of overall variance, median across studies, %")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.38), ncol=3, frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "capability_variance_components", "Share of overall variance between coils, between subgroups within a coil and within subgroups, formed and punched")


def coil_fit(t):
    """One study window's coil means against certificate thickness with the fit, and the residual standard deviation across windows."""
    r = t["coil_regression"].sort_values("certificate_r_squared", kind="stable").reset_index(drop=True)
    pick = r.iloc[len(r) // 2]          # the window with the median R-squared
    g = query("select coil_mean, certificate_thickness_deviation, certificate_hardness_hrb from marts.mart_capability_coil_means where study_id = ? order by coil_id", [pick["study_id"]])
    f, axes = S.fig(h=4.0, ncols=2, gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axes[0]
    x = g["certificate_thickness_deviation"].values * 100
    y = g["coil_mean"].values - pick["certificate_mm_per_hrb"] * (g["certificate_hardness_hrb"].values - pick["certificate_hardness_centre"])
    xs = np.linspace(x.min(), x.max(), 50); fit = pick["certificate_intercept"] + pick["certificate_mm_per_pct_thickness"] * xs; sd = pick["certificate_residual_sd_mm"]
    ax.fill_between(S.sig(xs), S.sig(fit - 2 * sd), S.sig(fit + 2 * sd), color=S.LIGHT_BLUE, alpha=0.45, lw=0, label="Fit plus or minus two residual standard deviations")
    ax.plot(S.sig(xs), S.sig(fit), color=S.BRAND_BLUE, lw=1.6, label="Fit")
    ax.scatter(S.sig(x), S.sig(y), s=22, color=S.BRAND_BLUE, zorder=3, label=f"Coil mean ({len(g)} coils)")
    ax.set_xlabel("Certificate thickness, % from nominal"); ax.set_ylabel("Formed height by coil, mm, at the mean hardness")
    ax.set_title(f"{pick['characteristic_id']}, study {pick['study_id']}", fontsize=10.5); ax.legend(loc="best", frameon=False, fontsize=8.5)
    ax = axes[1]
    share = S.sig(r["certificate_residual_sd_share_of_tolerance"].values * 100); spread = S.sig((r["sd_of_coil_means_mm"] / r["tolerance_mm"]).values * 100)
    bins = np.linspace(0, max(spread.max(), share.max()) * 1.05, 16)
    ax.hist(spread, bins=bins, color=S.LIGHT_BLUE, label="Coil means, standard deviation"); ax.hist(share, bins=bins, color=S.BRAND_BLUE, label="Residual about the fit")
    ax.set_xlabel("% of tolerance"); ax.set_ylabel(f"Study windows ({len(r)})"); ax.set_title("Across windows", fontsize=10.5); ax.legend(loc="upper right", frameon=False, fontsize=8.5)
    ax.text(0.97, 0.62, f"Medians: {float(np.median(spread)):.1f}% between\ncoil means, {float(np.median(share)):.1f}%\nabout the fit", transform=ax.transAxes, ha="right", va="top", fontsize=9, color=S.TEXT)
    f.tight_layout()
    return S.save(f, "capability_coil_fit", "Formed height by coil against certificate thickness for one study window, and the residual standard deviation across windows")


def fixture_against_cmm(t, after=False):
    """Fixture less CMM on matched first-piece parts with the mean and its interval: the record before the redesign,
    and with after=True the groups after it beside."""
    d = t["fixture_against_cmm_parts"]; rows = t["fixture_against_cmm"].set_index("group")
    groups = ["all fixtures, before the redesign", "other fixtures, after the redesign", "rebuilt fixtures, after the rebuild"][:3 if after else 1]
    f, ax = S.fig(h=3.9)
    for i, name in enumerate(groups):
        v = np.sort(d[d["group"] == name]["fixture_less_cmm"].values)
        jitter = np.random.default_rng([20250102, 4, i]).uniform(-0.26, 0.26, len(v))          # a seeded spread: the differences are quantised, since the fixture reads to 0.01 mm
        ax.scatter(i + jitter, S.sig(v), s=12, color=S.ACCENT if len(v) > 1 else S.AMBER, alpha=0.75, zorder=2)
        if len(v) > 1:
            m, lo, hi = rows.loc[name, "mean_difference_mm"], rows.loc[name, "low"], rows.loc[name, "high"]
            ax.errorbar(i + 0.36, m, yerr=[[m - lo], [hi - m]], fmt="o", color=S.BRAND_BLUE, capsize=4, ms=6, zorder=4)
            ax.text(i + 0.41, m, f" {m:.3f}" if after else f" Mean {m:+.3f} mm\n ({lo:.3f} to {hi:.3f})", va="center", fontsize=9, color=S.BRAND_BLUE)
        else:
            ax.annotate("one matched first piece", (i, float(v[0])), textcoords="offset points", xytext=(10, 10), fontsize=9, color=S.DARK_GREY)
    ax.axhline(0, color=S.DARK_GREY, lw=1.0, zorder=1)
    first = rows.loc[groups[0]]
    labels = [f"All fixtures,\nbefore the redesign\n({int(first.matched_first_pieces)})"] if after else [f"{int(first.matched_first_pieces)} matched first pieces\non {int(first.fixtures)} fixtures"]
    if after:
        labels += [f"Other fixtures,\nafter the redesign\n({int(rows.loc[groups[1], 'matched_first_pieces'])})", "Rebuilt fixtures,\nafter the rebuild\n(1)"]
    ax.set_xticks(range(len(groups))); ax.set_xticklabels(labels)
    ax.set_ylabel("Check fixture less CMM, mm"); ax.set_xlim(-0.5 - (0 if after else 0.9), len(groups) - 0.3 + (0 if after else 1.3))
    f.tight_layout()
    return S.save(f, "capability_fixture_against_cmm" + ("_after_the_redesign" if after else ""), "Check fixture reading less CMM reading on matched first-piece parts")


def bounded_indices(t):
    """Flatness and burr height: the median upper capability index by the percentile method."""
    d = t["bounded_summary"].set_index("characteristic_type")
    f, ax = S.fig(h=3.2)
    v = S.sig(d.loc[["flatness", "burr height"], "ppu_percentile_median"].values)
    b = ax.bar(range(2), v, 0.4, color=S.BRAND_BLUE)
    for bi, vi in zip(b, v):
        ax.text(bi.get_x() + bi.get_width() / 2, vi + 0.03, f"{vi:.2f}", ha="center", va="bottom", fontsize=10)
    ax.axhline(1.33, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(1.75, 1.35, "1.33", fontsize=8.5, color=S.DARK_GREY, va="bottom", ha="right")
    ax.set_xticks(range(2)); ax.set_xticklabels([f"Flatness\n({int(d.loc['flatness', 'characteristics'])} characteristics)", f"Burr height\n({int(d.loc['burr height', 'characteristics'])} characteristics)"])
    ax.set_ylabel("Ppu, median"); ax.set_ylim(0, 2.2); ax.set_xlim(-0.8, 1.8)
    f.tight_layout()
    return S.save(f, "capability_bounded_indices", "Median upper capability index on flatness and burr height by the percentile method")


def build(t):
    return {"capability": filed_against_production(t), "components": variance_components(t), "coil": coil_fit(t), "cmm": fixture_against_cmm(t), "cmm_after": fixture_against_cmm(t, True), "bounded": bounded_indices(t), "punched": ppk_by_punched_subclass(t)}


if __name__ == "__main__":
    from analytics.capability.capability import compute
    print(build(compute()))
