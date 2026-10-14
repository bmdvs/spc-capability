"""Figures for the per-stroke monitoring analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np

from analytics.data import query
from analytics.style import style as S

LAMBDA, L = 0.02, 5.5          # the EWMA on the per-stroke total as designed
SEED = 20250108
FINDINGS = [("punch worn and replaced", "Punch worn and replaced", S.BRAND_BLUE), ("punch chipped and replaced", "Punch chipped and replaced", S.AMBER),
            ("slug pulling cleared", "Slug pulling cleared", S.ACCENT), ("nothing found", "Nothing found", S.GREY)]


def the_worn_punch_stop(t):
    """The EWMA stop with a worn punch found whose rise at the stop is nearest the median of such stops."""
    r = t["rise_rows"]; r = r[(r["finding"] == "punch worn and replaced") & (r["chart"] == "EWMA on the total") & r["rise_over_the_last_6000"].notna()].copy()
    r["d"] = (r["rise_against_the_first_500"] - r["rise_against_the_first_500"].median()).abs()
    return r.sort_values(["d", "fault_event_id"]).iloc[0]


def one_worn_punch_stop(t):
    """The per-stroke total over the 6,500 strokes before one stop, with the EWMA and its limits from the run's first 500 strokes."""
    k = the_worn_punch_stop(t)
    d = query("select strokes_before_the_stop, total_kn from marts.mart_per_stroke_stop_strokes where fault_event_id = ? order by stroke_no", [k.fault_event_id])
    b = query("select baseline_total_kn_mean as m, baseline_total_kn_sd as sd, baseline_lag_1_autocorrelation as phi from marts.mart_per_stroke_run_tonnage where run_id = ?", [k.run_id]).iloc[0]
    x = -d["strokes_before_the_stop"].values; y = d["total_kn"].values.astype(float)
    z = np.empty(len(y)); z[0] = y[:200].mean()
    for i in range(1, len(y)):
        z[i] = LAMBDA * y[i] + (1 - LAMBDA) * z[i - 1]
    a = b.phi * (1 - LAMBDA); sz = b.sd * np.sqrt(LAMBDA / (2 - LAMBDA) * (1 + a) / (1 - a))
    f, ax = S.fig(h=4.1)
    ax.scatter(x[::3], S.sig(y[::3]), s=2, color=S.LIGHT_BLUE, alpha=0.5, lw=0, label="Total per stroke (every third stroke)")
    ax.plot(x[250:], S.sig(z[250:]), color=S.BRAND_BLUE, lw=1.6, label="EWMA")
    ax.axhline(float(S.sig(b.m)), color=S.DARK_GREY, lw=1.0, label="Level of the first 500 strokes of the run")
    ax.axhline(float(S.sig(b.m + L * sz)), color=S.AMBER, lw=1.2, ls="--", label="EWMA limits"); ax.axhline(float(S.sig(b.m - L * sz)), color=S.AMBER, lw=1.2, ls="--")
    ax.axvline(0, color=S.RED, lw=1.2); ax.text(-60, float(S.sig(b.m - 3.2 * b.sd)), f"Stop: total {k.rise_against_the_first_500 * 100:.1f}% above\nthe level of the first 500", ha="right", va="center", fontsize=8.5, color=S.RED)
    ax.set_ylim(float(S.sig(b.m - 4 * b.sd)), float(S.sig(b.m + 4.5 * b.sd))); ax.set_xlim(-6500, 120)
    ax.set_xlabel("Strokes before the stop"); ax.set_ylabel("Total peak force, kN")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False, fontsize=8.5, markerscale=5)
    f.tight_layout()
    return S.save(f, "per_stroke_one_worn_punch_stop", f"Per-stroke total over the 6,500 strokes before stop {k.fault_event_id} on {k.press_id}, run {k.run_id}, with the EWMA and its limits"), k, float(z[-1] / b.m - 1), float(L * sz / b.m)


def the_punch_break(t):
    """The first punch break on a press with four channels."""
    b = t["punch_breaks"]; b = b[b["press_id"].isin(["PR-06", "PR-09"])]
    return b.sort_values("fault_event_id").iloc[0]


def one_punch_break(t):
    """The channel shares over the last 300 strokes before one punch break."""
    k = the_punch_break(t)
    d = query("select strokes_before_the_stop, share_ch1, share_ch2, share_ch3, share_ch4 from marts.mart_per_stroke_stop_strokes where fault_event_id = ? and strokes_before_the_stop <= 300 order by stroke_no", [k.fault_event_id])
    x = -d["strokes_before_the_stop"].values
    f, ax = S.fig(h=4.0)
    for c in ("ch1", "ch2", "ch3", "ch4"):
        hit = c == k.channel; v = S.sig(d[f"share_{c}"].values * 100)
        ax.plot(x, v, color=S.AMBER if hit else S.GREY, lw=1.5 if hit else 0.9, label=f"Channel {c[-1]}" + (" (stepped)" if hit else ""))
        if hit:
            ax.scatter([0], [v[-1]], s=42, color=S.RED, zorder=4); ax.text(-6, float(v[-1]), f"Stop: peak down {k.fall_in_the_channel_peak * 100:.0f}%", ha="right", va="center", fontsize=8.5, color=S.RED)
    ax.set_xlabel("Strokes before the stop"); ax.set_ylabel("Channel share of the total, %"); ax.set_xlim(-300, 8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=4, frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "per_stroke_one_punch_break", f"Channel shares of the total over the 300 strokes before stop {k.fault_event_id} on {k.press_id}, die {k.die_id}"), k


def stops_by_chart(t):
    """Stops by chart and finding."""
    d = t["stops_by_chart"].set_index("chart")
    f, ax = S.fig(h=2.9, grid="x")
    for y, chart in enumerate(("channel share", "EWMA on the total")):
        left = 0
        for key, label, color in FINDINGS:
            n = int(d.loc[chart, key]) if key in d.columns else 0
            ax.barh(y, n, left=left, color=color, height=0.6, label=label if y == 0 else None)
            if n:
                ax.text(left + n / 2, y, str(n), ha="center", va="center", fontsize=9.5, color="white" if color in (S.BRAND_BLUE, S.ACCENT) else S.TEXT)
            left += n
        ax.text(left + 0.8, y, f"{left} stops", va="center", fontsize=9.5)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["Channel share", "EWMA on the total"]); ax.set_xlabel("Stops, 1 April to 30 June 2026"); ax.set_xlim(0, 72)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=4, frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "per_stroke_stops_by_chart", "Stops by the per-stroke charts on the pilot presses by chart and the toolmaker's finding")


def punch_replacements(t):
    """Punch replacements by what led to them, by year."""
    d = t["punch_replacements"]
    kinds = [("after a stop by the per-stroke charts", "After a stop by the per-stroke charts", S.BRAND_BLUE), ("at a sharpening", "At a sharpening", S.LIGHT_BLUE),
             ("punch chipped", "Punch chipped, as logged", S.AMBER), ("after nonconforming parts", "After nonconforming parts", S.RED)]
    years = [2024, 2025, 2026]; f, ax = S.fig(h=4.0, w=6.4); bottom = np.zeros(3)
    for key, label, color in kinds:
        v = np.array([float(d[(d["event_year"] == y) & (d["led_by"] == key)]["punch_replacements"].sum()) for y in years])
        ax.bar(range(3), v, 0.6, bottom=bottom, color=color, label=label)
        for x, (n, b0) in enumerate(zip(v, bottom)):
            if n:
                ax.text(x, b0 + n / 2, f"{n:.0f}", ha="center", va="center", fontsize=9.5, color="white" if color in (S.BRAND_BLUE, S.RED) else S.TEXT)
        bottom += v
    for x, n in enumerate(bottom):
        ax.text(x, n + 1, f"{n:.0f}", ha="center", va="bottom", fontsize=9.5)
    ax.set_xticks(range(3)); ax.set_xticklabels([str(y) for y in years]); ax.set_ylabel("Punch replacements, 1 April to 30 June"); ax.set_ylim(0, 80)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "per_stroke_punch_replacements", "Punch replacements on the dies run on the pilot presses by what led to them, 1 April to 30 June of 2024, 2025 and 2026")


def fall_at_the_breaks(t):
    """Fall in the affected channel's peak at the punch breaks."""
    b = t["punch_breaks"].sort_values("fault_event_id"); v = S.sig(b["fall_in_the_channel_peak"].values * 100)
    f, ax = S.fig(h=2.1, grid="x")
    ax.scatter(v, np.random.default_rng([SEED, 5]).uniform(-0.18, 0.18, len(v)), s=42, color=S.BRAND_BLUE, alpha=0.85, lw=0)
    ax.axvline(float(np.median(v)), color=S.AMBER, lw=1.4, ls="--"); ax.text(float(np.median(v)) + 0.3, 0.36, f"median {np.median(v):.1f}%", fontsize=8.5, color=S.AMBER)
    ax.set_yticks([]); ax.set_ylim(-0.5, 0.5); ax.set_xlim(0, 25); ax.set_xlabel("Fall in the affected channel's peak at the stop, %")
    f.tight_layout()
    return S.save(f, "per_stroke_fall_at_the_breaks", "Fall in the affected channel's peak at the 13 punch breaks stopped by the channel share chart")


def autocorrelation_by_run(t):
    """Lag-1 autocorrelation of the per-stroke total by run, by press."""
    d = query("select press_id, lag_1_autocorrelation from marts.mart_per_stroke_run_tonnage order by press_id, run_id")
    f, ax = S.fig(h=2.9, grid="x")
    ax.axvspan(0.50, 0.70, color=S.LIGHT_BLUE, alpha=0.2, lw=0, label="Autocorrelation range covered by the chart design, 0.50 to 0.70")
    for y, press in enumerate(("PR-09", "PR-06", "PR-03")):
        v = S.sig(d[d["press_id"] == press]["lag_1_autocorrelation"].values)
        ax.scatter(v, y + np.random.default_rng([SEED, 6, y]).uniform(-0.22, 0.22, len(v)), s=14, color=S.BRAND_BLUE, alpha=0.6, lw=0)
        ax.plot([np.median(v)] * 2, [y - 0.32, y + 0.32], color=S.AMBER, lw=1.8)
    ax.set_yticks(range(3)); ax.set_yticklabels(["PR-09", "PR-06", "PR-03"]); ax.set_xlim(0.45, 0.75); ax.set_xlabel("Lag-1 autocorrelation of the per-stroke total, by run (median marked)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.3), frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "per_stroke_autocorrelation_by_run", "Lag-1 autocorrelation of the per-stroke total by run on the three pilot presses")


def build(t):
    worn, k, ewma_at_stop, limit = one_worn_punch_stop(t); brk, kb = one_punch_break(t)
    return {"worn": worn, "worn_stop": dict(k), "ewma_at_the_stop_over_baseline": ewma_at_stop, "limit_over_baseline": limit, "break": brk, "break_stop": dict(kb), "stops": stops_by_chart(t),
            "replacements": punch_replacements(t), "falls": fall_at_the_breaks(t), "autocorrelation": autocorrelation_by_run(t)}


if __name__ == "__main__":
    from analytics.per_stroke.per_stroke import compute
    for k_, v_ in build(compute()).items():
        print(k_, v_)
