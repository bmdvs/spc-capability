"""Figures for the subgrouping and capability analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np

from analytics.data import query
from analytics.style import style as S

FORMED_COLOR, PUNCHED_COLOR = S.BRAND_BLUE, S.AMBER


def filed_against_production(t):
    """Filed Ppk against production Ppk, one point per study, with the production interval."""
    d = t["by_study"]
    f, ax = S.fig(h=4.6, w=6.6)
    for cls, color in (("formed", FORMED_COLOR), ("punched", PUNCHED_COLOR)):
        g = d[d["characteristic_class"] == cls]
        x = S.sig(g["filed_ppk"].values); y = S.sig(g["ppk"].values); lo = S.sig(g["ppk_low"].values); hi = S.sig(g["ppk_high"].values)
        ax.vlines(x, lo, hi, color=color, alpha=0.22, lw=1.0, zorder=2)
        ax.scatter(x, y, s=16, color=color, label=f"{cls.capitalize()} ({len(g)} studies)", zorder=3)
    ax.plot([0.6, 2.4], [0.6, 2.4], color=S.DARK_GREY, lw=1.0, zorder=1)
    ax.text(2.36, 2.26, "filed = production", ha="right", va="top", fontsize=8.5, color=S.DARK_GREY, rotation=37)
    ax.axhline(1.33, color=S.DARK_GREY, ls="--", lw=1.0, zorder=1); ax.text(0.63, 1.35, "1.33", fontsize=8.5, color=S.DARK_GREY, va="bottom")
    ax.set_xlim(0.6, 2.4); ax.set_ylim(0.6, 2.4); ax.set_xlabel("Filed Ppk, 300 consecutive pieces on the CMM"); ax.set_ylabel("Production Ppk on the check fixture")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "capability_filed_against_production", "Filed Ppk against production Ppk by study, with the production interval")


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
    f.tight_layout()
    return S.save(f, "capability_coil_fit", "Formed height by coil against certificate thickness for one study window, and the residual standard deviation across windows")


def fixture_against_cmm(t, after=False):
    """Fixture less CMM on matched first-piece parts with the mean and its interval: the record before the redesign,
    and with after=True the groups after it beside."""
    d = t["fixture_against_cmm_parts"]; rows = t["fixture_against_cmm"].set_index("group")
    groups = ["all fixtures, before the redesign", "other fixtures, after the redesign", "rebuilt fixtures, after the rebuild"][:3 if after else 1]
    f, ax = S.fig(h=3.9, w=None if after else 5.0)
    for i, name in enumerate(groups):
        v = np.sort(d[d["group"] == name]["fixture_less_cmm"].values)
        jitter = np.random.default_rng([20250102, 4, i]).uniform(-0.26, 0.26, len(v))          # a seeded spread: the differences are quantised, since the fixture reads to 0.01 mm
        ax.scatter(i + jitter, S.sig(v), s=12, color=S.ACCENT if len(v) > 1 else S.AMBER, alpha=0.75, zorder=2)
        if len(v) > 1:
            m, lo, hi = rows.loc[name, "mean_difference_mm"], rows.loc[name, "low"], rows.loc[name, "high"]
            ax.errorbar(i + 0.36, m, yerr=[[m - lo], [hi - m]], fmt="o", color=S.BRAND_BLUE, capsize=4, ms=6, zorder=4)
            ax.text(i + 0.41, m, f" {m:.3f}", va="center", fontsize=9, color=S.BRAND_BLUE)
        else:
            ax.annotate("one matched first piece", (i, float(v[0])), textcoords="offset points", xytext=(10, 10), fontsize=9, color=S.DARK_GREY)
    ax.axhline(0, color=S.DARK_GREY, lw=1.0, zorder=1)
    first = rows.loc[groups[0]]
    labels = [f"All fixtures,\nbefore the redesign\n({int(first.matched_first_pieces)})"] if after else [f"{int(first.matched_first_pieces)} matched first pieces\non {int(first.fixtures)} fixtures"]
    if after:
        labels += [f"Other fixtures,\nafter the redesign\n({int(rows.loc[groups[1], 'matched_first_pieces'])})", "Rebuilt fixtures,\nafter the rebuild\n(1)"]
    ax.set_xticks(range(len(groups))); ax.set_xticklabels(labels)
    ax.set_ylabel("Check fixture less CMM, mm"); ax.set_xlim(-0.5, len(groups) - 0.3)
    f.tight_layout()
    return S.save(f, "capability_fixture_against_cmm" + ("_after_the_redesign" if after else ""), "Check fixture reading less CMM reading on matched first-piece parts")


def bounded_indices(t):
    """Burr height and flatness: the upper capability index by the percentile method, the normal fit and Box-Cox."""
    d = t["bounded_summary"].set_index("characteristic_type")
    f, ax = S.fig(h=3.6, w=6.4)
    cols = (("ppu_percentile_median", "Percentile method, readings as recorded", S.BRAND_BLUE), ("ppu_normal_median", "Normal fit", S.ACCENT), ("ppu_box_cox_median", "Box-Cox", S.LIGHT_BLUE))
    x = np.arange(2); w = 0.26
    for i, (c, label, color) in enumerate(cols):
        v = S.sig(d.loc[["burr height", "flatness"], c].values)
        b = ax.bar(x + (i - 1) * w, v, w, color=color, label=label)
        for bi, vi in zip(b, v):
            ax.text(bi.get_x() + bi.get_width() / 2, vi + 0.03, f"{vi:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"Burr height\n({int(d.loc['burr height', 'characteristics'])} characteristics)", f"Flatness\n({int(d.loc['flatness', 'characteristics'])} characteristics)"])
    ax.set_ylabel("Upper capability index, median"); ax.set_ylim(0, 2.2); ax.legend(loc="upper left", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "capability_bounded_indices", "Upper capability index on burr height and flatness by three methods")


def build(t):
    return {"capability": filed_against_production(t), "components": variance_components(t), "coil": coil_fit(t), "cmm": fixture_against_cmm(t), "cmm_after": fixture_against_cmm(t, True), "bounded": bounded_indices(t)}


if __name__ == "__main__":
    from analytics.capability.capability import compute
    print(build(compute()))
