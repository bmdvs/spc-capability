"""Figures for the die wear analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np
from scipy import stats as st

from analytics.die_wear.die_wear import BASELINE_YEAR
from analytics.data import query
from analytics.style import style as S

SEED = 20250106


def hole_diameter_on_one_die(t, die="D-0417-B", year=BASELINE_YEAR):
    """Hole diameter against shots since sharpening on one die, interval by interval, with the common slope."""
    row = t["hole_diameter_by_die"].set_index("die_id").loc[die]; keep = t["hole_diameter_intervals"]; keep = set(keep[keep["die_id"] == die]["sharpening_interval_no"])
    d = query("""select sharpening_interval_no, shots_since_sharpening / 1000 as shots, reading_mean, usl, lsl from marts.mart_wear_points
                 where die_id = ? and characteristic_id = ? and sample_year = ? and not after_redesign order by sharpening_interval_no, sample_time, subgroup_id""", [die, row.characteristic_id, year])
    d = d[d["sharpening_interval_no"].isin(keep)]; b = row.slope_mm_per_100k_shots / 100
    f, ax = S.fig(h=4.0)
    ax.axhspan(float(d["lsl"].iloc[0]), float(d["usl"].iloc[0]), color=S.LIGHT_BLUE, alpha=0.18, lw=0, label="Tolerance")
    shades = [S.BRAND_BLUE, S.ACCENT, S.AMBER, S.GREY, S.GREEN, S.DARK_GREY, S.LIGHT_BLUE]
    for n, (no, g) in enumerate(d.groupby("sharpening_interval_no", sort=True)):
        x, y = S.sig(g["shots"].values), S.sig(g["reading_mean"].values); c = shades[n % len(shades)]
        ax.scatter(x, y, s=9, color=c, alpha=0.45, lw=0, label=f"Interval {n + 1} ({len(g)} subgroups)")
        xx = np.array([x.min(), x.max()]); ax.plot(xx, y.mean() + b * (xx - x.mean()), color=c, lw=1.8)
    ax.set_xlabel("Shots since sharpening, thousands"); ax.set_ylabel("Hole diameter, subgroup mean, mm")
    ax.text(0.015, 0.97, f"{row.slope_mm_per_100k_shots:.4f} mm per 100,000 shots ({row.slope_low:.4f} to {row.slope_high:.4f}); {row.growth_as_share_of_tolerance * 100:.0f}% of tolerance over the stated interval", transform=ax.transAxes, ha="left", va="top", fontsize=9, color=S.TEXT, fontweight="bold")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3, frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "die_wear_hole_diameter_one_die", f"Hole diameter {row.characteristic_id} against shots since sharpening on die {die} by sharpening interval, {year}, with the common slope and the tolerance")


def the_burr_die(t):
    """The die with the most burr gauge subgroups among those whose stated interval is past the count at 80% of the
    burr limit and whose median interval as run is past the stated interval."""
    f = t["burr_by_die"]; f = f[f["interval_longer_than_80pct_count"] & (f["logged_interval_median"] > f["sharpening_interval_shots"])]
    return f.sort_values(["subgroups", "die_id"], ascending=[False, True]).iloc[0]


def burr_on_one_die(t, through_year=BASELINE_YEAR):
    """Burr as a share of its limit against shots since sharpening on one die, with the fitted line and its band."""
    k = the_burr_die(t)
    d = query("""select shots_since_sharpening / 1000 as shots, share_of_limit from marts.mart_wear_points
                 where characteristic_type = 'burr height' and die_id = ? and not after_redesign and sample_year <= ? order by sample_time, subgroup_id""", [k.die_id, through_year])
    x, y = d["shots"].values, d["share_of_limit"].values * 100; lr = st.linregress(x, y); n = len(x)
    stated, logged, s80 = k.sharpening_interval_shots / 1000, k.logged_interval_median / 1000, k.shots_at_80pct_of_limit / 1000
    xx = np.linspace(0, max(x.max(), logged, stated) * 1.04, 80); se = np.sqrt(((y - lr.intercept - lr.slope * x) ** 2).sum() / (n - 2)) * np.sqrt(1 / n + (xx - x.mean()) ** 2 / ((x - x.mean()) ** 2).sum())
    fit = lr.intercept + lr.slope * xx; tq = st.t.ppf(0.975, n - 2)
    f, ax = S.fig(h=4.2)
    ax.scatter(S.sig(x), S.sig(y), s=12, color=S.ACCENT, alpha=0.5, lw=0, label=f"Burr gauge subgroup ({n})")
    ax.fill_between(S.sig(xx), S.sig(fit - tq * se), S.sig(fit + tq * se), color=S.BRAND_BLUE, alpha=0.2, lw=0); ax.plot(S.sig(xx), S.sig(fit), color=S.BRAND_BLUE, lw=1.8, label="Fitted line, 95% band")
    for yv, lab in ((80, "80% of the limit"), (100, "Limit")):
        ax.axhline(yv, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(xx.max() * 0.005, yv + 1.5, lab, fontsize=8.5, color=S.DARK_GREY, va="bottom")
    top = 118
    for xv, lab, c, yt in ((s80, f"80% reached,\n{s80 * 1000:,.0f} shots", S.BRAND_BLUE, 10), (stated, f"Stated interval,\n{stated * 1000:,.0f}", S.AMBER, 24), (logged, f"Interval as run (median),\n{logged * 1000:,.0f}", S.RED, 38)):
        ax.axvline(float(S.sig(xv)), color=c, lw=1.3); ax.text(float(S.sig(xv)) + xx.max() * 0.008, yt, lab, fontsize=8.5, color=c, va="center")
    ax.set_ylim(0, top); ax.set_xlim(0, float(xx.max())); ax.set_xlabel("Shots since sharpening, thousands"); ax.set_ylabel("Burr height as a share of its limit, %")
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "die_wear_burr_one_die", f"Burr height as a share of its limit against shots since sharpening on die {k.die_id}, with the shot count at 80% of the limit, the stated sharpening interval and the interval as run"), k


def count_against_interval(t):
    """By die: the shot count at 80% of the burr limit against the stated interval and against the interval as run."""
    d = t["burr_by_die"]
    f, axes = S.fig(h=4.3, ncols=2, sharey=True, grid="both")
    for ax, col, title in zip(axes, ("sharpening_interval_shots", "logged_interval_median"), ("Stated sharpening interval", "Interval as run (logged median)")):
        g = d[d[col].notna()]; x, y = S.sig(g[col].values / 1000), S.sig(g["shots_at_80pct_of_limit"].values / 1000); below = x > y
        ax.plot([100, 650], [100, 650], color=S.DARK_GREY, ls="--", lw=1.0)
        ax.scatter(x[~below], y[~below], s=18, color=S.LIGHT_BLUE, lw=0); ax.scatter(x[below], y[below], s=18, color=S.BRAND_BLUE, lw=0)
        ax.set_title(f"{title}\n{int(below.sum())} of {len(g)} dies below the line", fontsize=10.5); ax.set_xlabel("Interval, thousand shots"); ax.set_xlim(100, 520); ax.set_ylim(100, 650)
    axes[0].set_ylabel("Shots at 80% of the burr limit, thousands")
    f.tight_layout()
    return S.save(f, "die_wear_count_against_interval", "Shot count at which burr reaches 80% of its limit against the stated sharpening interval and against the interval as run, by die")


def nonconformances_by_position(t, year=BASELINE_YEAR):
    """Burr nonconformances by the die's position in its sharpening interval at the end of the run, over all runs."""
    n = t["burr_nonconformance_rows"]; n = n[n["share_of_the_interval"].notna()]
    runs = query("""select (r.shots_since_sharpening_at_start + r.strokes) / d.sharpening_interval_shots as position
                    from intermediate.int_run_shots r join staging.stg_erp__dies d using (die_id)
                    where year(r.actual_start) = ? and r.shots_since_sharpening_at_start is not null order by r.run_id""", [year])["position"].values
    rows = [("hole burr and size", "press check", '"hole burr and size",' + chr(10) + "press check", S.GREY), ("burr", "customer", "Burr, customer", S.AMBER),
            ("burr", "dock audit", "Burr, dock audit", S.ACCENT), ("burr", "press check", "Burr, press check", S.BRAND_BLUE)]
    f, axes = S.fig(h=4.6, nrows=2, sharex=True, grid="x", gridspec_kw={"height_ratios": [2.3, 1]})
    ax = axes[0]; labels = []
    for y, (code, where, label, color) in enumerate(rows):
        g = n[(n["defect_code"] == code) & (n["detected_at"] == where)].sort_values("ncr_id"); v = S.sig(g["share_of_the_interval"].values)
        jit = np.random.default_rng([SEED, 40, y]).uniform(-0.22, 0.22, len(v))
        ax.scatter(v, y + jit, s=26, color=color, alpha=0.8, lw=0); labels.append(f"{label} ({len(v)})")
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(labels, fontsize=9); ax.set_ylim(-0.6, len(rows) - 0.4)
    edges = np.linspace(0, 1.8, 37); h, _ = np.histogram(np.clip(runs, 0, 1.8), edges)
    axes[1].bar(edges[:-1], h, width=0.05, align="edge", color=S.LIGHT_BLUE); axes[1].set_ylabel(f"All runs ({len(runs):,})", fontsize=9)
    for a in axes:
        a.axvline(1.0, color=S.DARK_GREY, ls="--", lw=1.0)
    axes[1].set_xlabel("Shots since sharpening at the end of the run, as a multiple of the die's stated sharpening interval"); axes[1].set_xlim(0, 1.8)
    burr = n[n["defect_code"] == "burr"]; past = int((burr["share_of_the_interval"] > 1).sum())
    ax.text(0.015, 0.97, f"{past} of {len(burr)} burr nonconformances past the stated interval; {(runs > 1).mean() * 100:.0f}% of runs", transform=ax.transAxes, ha="left", va="top", fontsize=9.5, color=S.TEXT, fontweight="bold")
    f.tight_layout()
    return S.save(f, "die_wear_nonconformances_by_position", f"Burr nonconformances opened in {year} by the die's position in its stated sharpening interval at the end of the run, over all runs of the year with shots since sharpening known")


def build(t):
    burr, k = burr_on_one_die(t)
    return {"hole": hole_diameter_on_one_die(t), "burr": burr, "burr_die": k.die_id, "count": count_against_interval(t), "position": nonconformances_by_position(t)}


if __name__ == "__main__":
    from analytics.die_wear.die_wear import compute
    print(build(compute()))
