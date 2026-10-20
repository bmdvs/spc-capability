"""Figures for the SPC Quarterly Review. Each function takes what the page has read from the marts and returns the img tag
of the figure written under docs/figures."""
import numpy as np
import pandas as pd

from analytics.style import style as S

CAUSE_COLOURS = {"no cause found": S.LIGHT_BLUE, "level after sharpening": S.BRAND_BLUE, "level after the rebuild": S.ACCENT, "fixture drift": S.AMBER, "soft coil": S.GREEN,
                 "sharpening logged at the wrong count": S.RED, "slug pulling": "#7A5195", "strip misfeed": "#B5651D", "lubricant": "#4C9F70", "gauge zero": S.DARK_GREY}


def observed_expected_by_press(p1):
    f, ax = S.fig(h=4.0)
    y = np.arange(len(p1))
    ax.errorbar(S.sig(p1["observed per 100"]), y, xerr=[S.sig(p1["observed per 100"] - p1["low"]), S.sig(p1["high"] - p1["observed per 100"])], fmt="o", color=S.BRAND_BLUE, capsize=3, label="Observed, 95% interval")
    ax.scatter(S.sig(p1["expected per 100"]), y, marker="|", s=260, color=S.AMBER, linewidths=2.4, label="Expected", zorder=4)
    ax.set_yticks(y); ax.set_yticklabels(p1["press_id"]); ax.invert_yaxis()
    ax.set_xlabel("Signals per 100 routine subgroups, April to June 2026"); ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    return S.save(f, "d2_observed_against_expected_by_press", "Observed against expected signals by press")


def signals_by_rule_and_cause(tab):
    f, ax = S.fig(h=4.4, grid="x")
    rows = list(tab.index); left = np.zeros(len(rows))
    for c in [c for c in CAUSE_COLOURS if c in tab.columns]:
        v = tab[c].values.astype(float); ax.barh(range(len(rows)), v, left=left, color=CAUSE_COLOURS[c], label=c, height=0.65); left += v
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows); ax.invert_yaxis(); ax.set_xlabel("Alarms")
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper center", bbox_to_anchor=(0.45, -0.16))
    return S.save(f, "d2_signals_by_rule_and_cause", "Signals by rule and cause")


def family_ppk(fc):
    f, ax = S.fig(h=4.6, grid="x")
    y = np.arange(len(fc))
    ax.errorbar(S.sig(fc["ppk"]), y, xerr=[S.sig(fc["ppk"] - fc["ppk_low"]), S.sig(fc["ppk_high"] - fc["ppk"])], fmt="o", color=S.BRAND_BLUE, capsize=3)
    ax.axvline(1.33, color=S.RED, linestyle="--", linewidth=1, label="1.33")
    ax.set_yticks(y); ax.set_yticklabels(fc["characteristic_id"] + "  " + fc["characteristic_name"]); ax.invert_yaxis()
    ax.set_xlabel("Ppk, April to June 2026, with 95% interval"); ax.legend(frameon=False, loc="lower right")
    return S.save(f, "d2_family_ppk_with_intervals", "The family: Ppk with 95% intervals")


def plant_ppk_by_class(cap, order):
    f, ax = S.fig(h=3.8)
    data = [S.sig(cap[cap["characteristic_class"] == c]["ppk"].values) for c in order]
    ax.boxplot(data, vert=False, widths=0.5, patch_artist=True, boxprops=dict(facecolor=S.LIGHT_BLUE, color=S.BRAND_BLUE), medianprops=dict(color=S.BRAND_BLUE, linewidth=2), whiskerprops=dict(color=S.BRAND_BLUE), capprops=dict(color=S.BRAND_BLUE), flierprops=dict(markeredgecolor=S.BRAND_BLUE))
    for i, d in enumerate(data):
        ax.scatter(d, np.full(len(d), i + 1) + np.linspace(-0.12, 0.12, len(d)), s=10, color=S.BRAND_BLUE, alpha=0.6, zorder=3)
    ax.axvline(1.33, color=S.RED, linestyle="--", linewidth=1)
    ax.set_yticks(range(1, len(order) + 1)); ax.set_yticklabels([f"{c} ({len(d)})" for c, d in zip(order, data)]); ax.invert_yaxis()
    ax.set_xlabel("Ppk (Ppu on flatness), April to June 2026")
    return S.save(f, "d2_plant_ppk_by_class", "Plant Ppk by class")


def grr_before_after(f5):
    d = f5.reset_index(drop=True); y = np.arange(len(d))
    f, ax = S.fig(h=0.42 * len(d) + 1.4, grid="x")
    for i, r in d.iterrows():
        ax.plot([r.previous_pct_grr, r.pct_grr_of_tolerance], [i, i], color=S.GREY, linewidth=1, zorder=1)
    ax.scatter(S.sig(d["previous_pct_grr"]), y, s=18, color=S.LIGHT_BLUE, label="Previous study", zorder=2)
    ax.scatter(S.sig(d["pct_grr_of_tolerance"]), y, s=22, color=S.BRAND_BLUE, label="Study in the quarter", zorder=3)
    ax.axvline(10, color=S.AMBER, linestyle="--", linewidth=1, label="10%"); ax.axvline(30, color=S.RED, linestyle="--", linewidth=1, label="30%")
    ax.set_yticks(y); ax.set_yticklabels(d["label"], fontsize=8); ax.set_ylim(len(d) - 0.5, -0.5); ax.set_xlabel("%GRR of tolerance"); ax.legend(frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=9)
    return S.save(f, "d2_grr_before_and_after", "%GRR before and after, fixtures studied in the quarter")


def kappa_by_operator(kp, line):
    f, ax = S.fig(h=4.4)
    ops = sorted(kp["operator_id"].unique()); x = {o: i for i, o in enumerate(ops)}
    other = kp[kp["operator_id"] != "E-1006"]; e6 = kp[kp["operator_id"] == "E-1006"]
    ax.scatter([x[o] for o in other["operator_id"]], S.sig(other["kappa"]), s=14, color=S.LIGHT_BLUE, label="Qualification studies")
    ax.plot([x[o] for o in e6["operator_id"]], S.sig(e6["kappa"]), color=S.RED, linestyle="none", marker="o", markersize=5, label="E-1006, every study")
    q = e6[e6["in_quarter"]].sort_values("study_date")
    for _, r in q.iterrows():
        ax.annotate(f"{pd.Timestamp(r.study_date).strftime('%d %b').lstrip('0')}: {r.kappa:.2f}", (x[r.operator_id], r.kappa), xytext=(6, 0), textcoords="offset points", fontsize=8.5, color=S.RED)
    ax.axhline(line, color=S.AMBER, linestyle="--", linewidth=1, label="Requalification line")
    ax.set_xticks(range(len(ops))); ax.set_xticklabels(ops, rotation=90, fontsize=8); ax.set_ylabel("Kappa against the burr gauge"); ax.set_ylim(0.6, 0.92); ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.12), fontsize=9)
    return S.save(f, "d2_kappa_by_operator", "Kappa by operator")


def sharpening_share(shr, late=None):
    f, ax = S.fig(h=3.8)
    bins = np.arange(0.5, 1.15, 0.025)
    for g, colour in (("high_speed", S.BRAND_BLUE), ("medium", S.AMBER)):
        ax.hist(S.sig(shr[shr["press_group"] == g]["share_of_due_count"]), bins=bins, color=colour, alpha=0.7, label=g.replace("_", "-") + " presses")
    ax.axvline(1.0, color=S.RED, linestyle="--", linewidth=1, label="Due count")
    if late is not None:
        top = ax.get_ylim()[1]; ls_ = late.sort_values("share_of_due_count").reset_index(drop=True)
        for i, r in ls_.iterrows():
            ax.annotate(str(i + 1), (r.share_of_due_count, 0), xytext=(r.share_of_due_count, top * (0.62 + 0.07 * (i % 3))), fontsize=8, ha="center", color=S.RED, fontweight="bold",
                        arrowprops=dict(arrowstyle="-", color=S.RED, linewidth=0.5, alpha=0.6))
        ax.text(1.12, top * 0.98, "Late sharpenings\n" + "\n".join(f"{i + 1}  {r.die_id}  {100 * r.share_of_due_count:.0f}%" for i, r in ls_.iterrows()), fontsize=7.5, va="top", ha="left", color=S.TEXT)
        ax.set_xlim(None, 1.3)
    ax.set_xlabel("Shots at sharpening as a share of the due count"); ax.set_ylabel("Sharpenings"); ax.legend(frameon=False, loc="upper left")
    return S.save(f, "d2_shots_at_sharpening_over_due_count", "Shots at sharpening over the due count")


def stops_by_press(srq):
    f, ax = S.fig(h=4.0)
    cols = [("stops_chipped_punch", "chipped punch", S.RED), ("stops_worn_punch", "worn punch", S.AMBER), ("stops_slug_pulling", "slug pulling", S.ACCENT), ("stops_nothing_found", "nothing found", S.GREY)]
    bottom = np.zeros(len(srq))
    for c, lab, colour in cols:
        v = srq[c].values.astype(float); ax.bar(range(len(srq)), v, bottom=bottom, color=colour, label=lab, width=0.7); bottom += v
    ax.set_xticks(range(len(srq))); ax.set_xticklabels(srq["press_id"]); ax.set_ylabel("Stops, April to June 2026"); ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    return S.save(f, "d2_per_stroke_stops_by_press", "Per-stroke stops by finding, by press")


def punch_replacements(pr):
    f, ax = S.fig(h=3.0, grid="x")
    t = pr.pivot_table(index="punch_condition", columns="led_by", values="die_event_id", aggfunc="count", fill_value=0)
    left = np.zeros(len(t))
    for c, colour in zip(t.columns, (S.BRAND_BLUE, S.AMBER, S.ACCENT)):
        v = t[c].values.astype(float); ax.barh(range(len(t)), v, left=left, color=colour, label=f"stopped by: {c}", height=0.55); left += v
    ax.set_yticks(range(len(t))); ax.set_yticklabels([f"{i} punch" for i in t.index]); ax.set_xlabel("Punch replacements, April to June 2026"); ax.legend(frameon=False, loc="lower right")
    return S.save(f, "d2_punch_replacements_by_cause", "Punch replacements by what led to them")


def first_piece_release(held, passed):
    f, ax = S.fig(h=4.0, grid="x")
    types = sorted(held["held_characteristic_type"].unique())
    ax.hist(S.sig(passed["minutes_to_release"].clip(upper=120)), bins=np.arange(0, 125, 5), color=S.LIGHT_BLUE, label="Passed first pieces")
    ax2 = ax.twinx()
    for i, t in enumerate(types):
        d = held[held["held_characteristic_type"] == t]
        ax2.scatter(S.sig(d["minutes_to_release"].clip(upper=120)), np.full(len(d), i), s=30, color=S.RED, zorder=3)
    ax2.set_yticks(range(len(types))); ax2.set_yticklabels([f"held: {t}" for t in types], fontsize=8.5); ax2.set_ylim(-0.8, len(types) - 0.2)
    ax.set_xlabel("Minutes to release (beyond 120 shown at 120)"); ax.set_ylabel("Passed first pieces"); ax.legend(frameon=False, loc="upper right")
    return S.save(f, "d2_first_piece_time_to_release", "First-piece time to release")


def planned_checks(pc):
    f, ax = S.fig(h=3.8)
    t = pc.pivot_table(index="press_id", columns="shift", values="recorded share").reset_index(); x = np.arange(len(t)); w = 0.38
    ax.bar(x - w / 2, S.sig(t["days"] * 100), width=w, color=S.BRAND_BLUE, label="Days"); ax.bar(x + w / 2, S.sig(t["nights"] * 100), width=w, color=S.AMBER, label="Nights")
    ax.set_ylim(90, 100); ax.set_xticks(x); ax.set_xticklabels(t["press_id"]); ax.set_ylabel("Planned checks recorded (%)"); ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    return S.save(f, "d2_planned_checks_by_press_and_shift", "Planned checks recorded by press and shift")


CLASS_ORDER = ["cut geometry", "formed", "hole diameter", "flatness"]
CLASS_LABEL = {"cut geometry": "Cut geometry", "formed": "Formed characteristics", "hole diameter": "Hole diameter", "flatness": "Flatness (Ppu)"}
CLASS_COLOURS = {"formed": S.BRAND_BLUE, "cut geometry": S.ACCENT, "hole diameter": S.AMBER, "flatness": S.GREY}


def ppk_by_class(cap):
    """cap: characteristic_id, cls, ppk. One row per class, one dot per characteristic, lines at 1.33 and 1.67, the class
    median as a tick, those below 1.33 in the highlight color and labeled."""
    f, ax = S.fig(h=3.6, grid="x")
    for i, c in enumerate(CLASS_ORDER):
        g = cap[cap["cls"] == c].sort_values("characteristic_id").reset_index(drop=True)
        y = i + np.linspace(-0.18, 0.18, len(g)) if len(g) > 1 else np.array([float(i)])
        low = g["ppk"] < 1.33
        ax.scatter(S.sig(g.loc[~low, "ppk"]), y[~low.values], s=16, color=S.BRAND_BLUE, alpha=0.65, zorder=3)
        ax.scatter(S.sig(g.loc[low, "ppk"]), y[low.values], s=26, color=S.RED, zorder=4)
        m = float(g["ppk"].median()); ax.plot([m, m], [i - 0.32, i + 0.32], color=S.TEXT, linewidth=2, zorder=5)
        lows = g[low].sort_values("ppk").reset_index(drop=True); ylow = y[low.values][np.argsort(g.loc[low, "ppk"].values)]
        slots = np.linspace(i - 0.38, i + 0.38, len(lows)) if len(lows) > 1 else np.array([i - 0.2])
        for k, r in lows.iterrows():
            ax.annotate(r.characteristic_id, (r.ppk, ylow[k]), xytext=(1.115, slots[k]), textcoords="data", ha="left", va="center", fontsize=7.5, color=S.RED,
                        arrowprops=dict(arrowstyle="-", color=S.RED, linewidth=0.5, alpha=0.6))
    ax.axvline(1.33, color=S.RED, linestyle="--", linewidth=1); ax.axvline(1.67, color=S.GREY, linestyle="--", linewidth=0.9)
    ax.text(1.33, len(CLASS_ORDER) - 0.45, "1.33", ha="center", fontsize=8.5, color=S.RED); ax.text(1.67, len(CLASS_ORDER) - 0.45, "1.67", ha="center", fontsize=8.5, color=S.DARK_GREY)
    ax.set_yticks(range(len(CLASS_ORDER))); ax.set_yticklabels([f"{CLASS_LABEL[c]} ({int((cap['cls'] == c).sum())})" for c in CLASS_ORDER]); ax.set_ylim(len(CLASS_ORDER) - 0.4, -0.6)
    ax.set_xlim(1.1, None); ax.set_xlabel("Ppk, April to June 2026 (the bar marks the class median)")
    return S.save(f, "d2_ppk_by_class", "Ppk by class")


def cpk_against_ppk(cap):
    f, ax = S.fig(h=4.2, w=6.0, grid="both")
    lo = min(cap["ppk"].min(), cap["cpk"].min()) - 0.05; hi = max(cap["ppk"].max(), cap["cpk"].max()) + 0.05
    ax.plot([lo, hi], [lo, hi], color=S.GREY, linewidth=1, zorder=1)
    ax.axvline(1.33, color=S.RED, linestyle="--", linewidth=0.9); ax.axhline(1.33, color=S.RED, linestyle="--", linewidth=0.9)
    for c in CLASS_ORDER:
        g = cap[cap["cls"] == c]
        ax.scatter(S.sig(g["ppk"]), S.sig(g["cpk"]), s=20, color=CLASS_COLOURS[c], label=CLASS_LABEL[c], zorder=3, alpha=0.85)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_xlabel("Ppk"); ax.set_ylabel("Cpk")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    return S.save(f, "d2_cpk_against_ppk", "Cpk against Ppk")


def capability_by_quarter(med, counts):
    """med: quarter, cls, ppk (median); counts: quarter, population, above."""
    f, (a1, a2) = S.fig(h=3.6, ncols=2)
    qs = list(counts["quarter"]); x = np.arange(len(qs))
    for c in CLASS_ORDER:
        g = med[med["cls"] == c].set_index("quarter").reindex(qs)
        a1.plot(x, S.sig(g["ppk"]), marker="o", color=CLASS_COLOURS[c], label=CLASS_LABEL[c])
    a1.axhline(1.33, color=S.RED, linestyle="--", linewidth=0.9)
    a1.set_xticks(x); a1.set_xticklabels(qs); a1.set_ylabel("Median Ppk"); a1.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.14)); a1.set_ylim(1.2, None)
    a2.bar(x, counts["population"], color=S.LIGHT_BLUE, width=0.6, label="Population")
    a2.bar(x, counts["above"], color=S.BRAND_BLUE, width=0.4, label="Above Ppk 1.33")
    for i, r in counts.reset_index(drop=True).iterrows():
        a2.text(i, r.population + 1.5, f"{int(r.above)} of {int(r.population)}", ha="center", fontsize=8.5)
    a2.set_xticks(x); a2.set_xticklabels(qs); a2.set_ylabel("Characteristics"); a2.set_ylim(0, counts["population"].max() * 1.18); a2.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    return S.save(f, "d2_capability_by_quarter", "Capability by quarter")


def below_133(u):
    """u: characteristic_id, ppk, ppk_low, ppk_high, label, customer; sorted by Ppk."""
    d = u.sort_values("ppk").reset_index(drop=True)
    f, ax = S.fig(h=0.42 * len(d) + 1.3, grid="x")
    for i, r in d.iterrows():
        colour = S.RED if r.customer else S.BRAND_BLUE
        ax.errorbar(r.ppk, i, xerr=[[r.ppk - r.ppk_low], [r.ppk_high - r.ppk]], fmt="o", color=colour, mfc=colour if r.customer else "white", capsize=3, markersize=6)
        ax.text(1.47, i, r.label, va="center", fontsize=8.5, color=S.TEXT)
    ax.axvline(1.33, color=S.RED, linestyle="--", linewidth=1)
    ax.set_yticks(range(len(d))); ax.set_yticklabels(d["characteristic_id"]); ax.invert_yaxis(); ax.set_xlim(1.1, 1.72)
    ax.set_xlabel("Ppk with 95% interval (filled: for the customer)")
    return S.save(f, "d2_characteristics_below_133", "Characteristics below Ppk 1.33")


def fails_by_quarter(g):
    """g: check (burr, pins), quarter, per_million, lo, hi."""
    f, ax = S.fig(h=3.4)
    qs = sorted(g["quarter"].unique()); x = np.arange(len(qs))
    for (chk, lab, colour, dx) in (("burr height", "Burr checks", S.GREEN, -0.06), ("hole diameter", "Pin checks", S.AMBER, 0.06)):
        d = g[g["t"] == chk].set_index("quarter").reindex(qs)
        ax.errorbar(x + dx, S.sig(d["per_million"]), yerr=[S.sig(d["per_million"] - d["lo"]), S.sig(d["hi"] - d["per_million"])], fmt="o-", color=colour, capsize=3, label=lab)
    ax.set_xticks(x); ax.set_xticklabels([q.replace("Q", " Q") for q in qs]); ax.set_ylim(0, None); ax.set_ylabel("Fails per million pieces checked")
    ax.legend(frameon=False, loc="lower right")
    return S.save(f, "d2_attribute_fails_by_quarter", "Burr and pin fails per million, by quarter")


ROWS_TL = ["X-bar and R", "three-way", "regression", "coil-change"]


def special_cause_timeline(ev):
    """ev: first (timestamp), row (one of ROWS_TL), label."""
    f, ax = S.fig(h=4.2, grid="x")
    d = ev.sort_values("first").reset_index(drop=True)
    seen = {}
    for r in d.itertuples():
        y = ROWS_TL.index(r.row); k = seen.get(y, 0); seen[y] = k + 1
        ax.scatter([pd.Timestamp(r.first)], [y], s=30, color=S.BRAND_BLUE, zorder=3)
        off = (9, -13, 21, -25)[k % 4]
        ax.annotate(r.label, (pd.Timestamp(r.first), y), xytext=(0, off), textcoords="offset points", ha="center", va="center", fontsize=7, color=S.TEXT,
                    arrowprops=dict(arrowstyle="-", color=S.GREY, linewidth=0.4) if abs(off) > 15 else None)
    ax.set_yticks(range(len(ROWS_TL))); ax.set_yticklabels(ROWS_TL); ax.set_ylim(len(ROWS_TL) - 0.35, -0.75)
    ax.set_xlim(pd.Timestamp("2026-03-29"), pd.Timestamp("2026-07-02"))
    wk = pd.date_range("2026-03-30", "2026-06-29", freq="14D")
    ax.set_xticks(wk); ax.set_xticklabels([w.strftime("%d %b").lstrip("0") for w in wk], fontsize=8.5)
    ax.set_xlabel("Week of the first signal, April to June 2026")
    return S.save(f, "d2_special_causes_timeline", "Special causes in the quarter")


def reaction_times(rx):
    """rx: cause, ack_med, ack_max, close_med, close_max; one row per cause."""
    d = rx.sort_values("close_med").reset_index(drop=True)
    f, (a1, a2) = S.fig(h=0.36 * len(d) + 1.4, ncols=2, sharey=True, grid="x")
    for ax, m, x, lab in ((a1, "ack_med", "ack_max", "Minutes to acknowledge"), (a2, "close_med", "close_max", "Minutes to close")):
        for i, r in d.iterrows():
            ax.plot([r[m], r[x]], [i, i], color=S.GREY, linewidth=1.4, zorder=1)
            ax.scatter([r[m]], [i], s=26, color=S.BRAND_BLUE, zorder=3)
        ax.set_xlabel(lab); ax.set_xlim(0, None)
    a1.set_title("Dot: median; line: to the longest", fontsize=8.5, color=S.DARK_GREY, loc="left")
    a1.set_yticks(range(len(d))); a1.set_yticklabels(d["cause"]); a1.invert_yaxis()
    return S.save(f, "d2_time_to_acknowledge_and_close", "Time to acknowledge and close, by cause")


CHART_COLOURS = {"X-bar and R": S.BRAND_BLUE, "three-way": S.AMBER, "regression": S.GREEN}


def limits_and_verifications(rq, vt):
    """rq: trigger, chart, n; vt: chart, done, failed."""
    f, (a1, a2) = S.fig(h=3.6, w=9.2, ncols=2, grid="x", gridspec_kw={"wspace": 0.55})
    trig = list(rq.groupby("trigger")["n"].sum().sort_values().index); left = np.zeros(len(trig))
    for c in CHART_COLOURS:
        v = np.array([int(rq[(rq["trigger"] == t) & (rq["chart"] == c)]["n"].sum()) for t in trig])
        if v.sum():
            a1.barh(range(len(trig)), v, left=left, color=CHART_COLOURS[c], label=c, height=0.6); left += v
    for i, t in enumerate(left):
        a1.text(t + 0.4, i, f"{int(t)}", va="center", fontsize=8.5)
    a1.set_yticks(range(len(trig))); a1.set_yticklabels(trig); a1.set_xlabel("New limit sets"); a1.set_xlim(0, max(left) * 1.2); a1.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.4, -0.2))
    d = vt.reset_index(drop=True)
    a2.barh(range(len(d)), d["done"] - d["failed"], color=S.LIGHT_BLUE, height=0.6, label="Passed")
    a2.barh(range(len(d)), d["failed"], left=d["done"] - d["failed"], color=S.RED, height=0.6, label="Failed")
    for i, r in d.iterrows():
        a2.text(r.done + 4, i, f"{int(r.failed)} of {int(r.done)} failed", va="center", fontsize=8.5)
    a2.set_yticks(range(len(d))); a2.set_yticklabels(d["chart"]); a2.set_xlabel("Verifications"); a2.set_xlim(0, d["done"].max() * 1.6); a2.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.4, -0.2))
    return S.save(f, "d2_limit_sets_and_verifications", "Limit sets and verifications in the quarter")


def first_piece_rows(held, passed, cap_at=120):
    types = list(held.groupby("held_characteristic_type")["minutes_to_release"].median().sort_values().index)
    f, ax = S.fig(h=0.4 * len(types) + 1.5, grid="x")
    m, p90 = float(passed["minutes_to_release"].median()), float(passed["minutes_to_release"].quantile(0.9))
    ax.axvspan(m, p90, color=S.LIGHT_BLUE, alpha=0.5, label=f"Passed first pieces, median to 90th percentile")
    for i, t in enumerate(types):
        d = held[held["held_characteristic_type"] == t]
        for v in d["minutes_to_release"]:
            if v > cap_at:
                ax.scatter([cap_at], [i], s=34, marker=">", color=S.RED, zorder=3)
                ax.annotate(f"{v:.0f} min", (cap_at, i), xytext=(-4, 8), textcoords="offset points", ha="right", fontsize=8, color=S.RED)
            else:
                ax.scatter([v], [i], s=26, color=S.RED, zorder=3)
    ax.set_yticks(range(len(types))); ax.set_yticklabels([f"held: {t}" for t in types]); ax.invert_yaxis(); ax.set_xlim(0, cap_at + 4)
    ax.set_xlabel(f"Minutes from first piece to release (a hold beyond {cap_at} is drawn at the edge)"); ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    return S.save(f, "d2_first_piece_time_to_release", "First-piece time to release")


def planned_checks_heatmap(pv):
    """pv: press rows, columns days and nights, values the recorded share."""
    from matplotlib.colors import TwoSlopeNorm
    f, ax = S.fig(h=4.2, w=4.6, grid="x"); ax.grid(False)
    v = pv[["days", "nights"]].values * 100
    im = ax.imshow(v, cmap="RdYlGn", norm=TwoSlopeNorm(vmin=93, vcenter=95, vmax=100), aspect="auto")
    for i in range(v.shape[0]):
        for j in range(v.shape[1]):
            ax.text(j, i, f"{v[i, j]:.1f}%", ha="center", va="center", fontsize=8.5, color=S.TEXT)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Days", "Nights"]); ax.set_yticks(range(len(pv))); ax.set_yticklabels(pv.index)
    ax.set_title("Colored against 95%", fontsize=9, color=S.DARK_GREY)
    return S.save(f, "d2_planned_checks_by_press_and_shift", "Planned checks recorded, by press and shift")

