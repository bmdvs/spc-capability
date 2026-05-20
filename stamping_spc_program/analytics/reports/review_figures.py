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
    f, ax = S.fig(h=max(5.4, 0.19 * len(d)), grid="x")
    for i, r in d.iterrows():
        ax.plot([r.previous_pct_grr, r.pct_grr_of_tolerance], [i, i], color=S.GREY, linewidth=1, zorder=1)
    ax.scatter(S.sig(d["previous_pct_grr"]), y, s=18, color=S.LIGHT_BLUE, label="Previous study", zorder=2)
    ax.scatter(S.sig(d["pct_grr_of_tolerance"]), y, s=22, color=S.BRAND_BLUE, label="Study in the quarter", zorder=3)
    ax.axvline(10, color=S.AMBER, linestyle="--", linewidth=1, label="10%"); ax.axvline(30, color=S.RED, linestyle="--", linewidth=1, label="30%")
    ax.set_yticks(y); ax.set_yticklabels(d["label"], fontsize=8); ax.set_ylim(len(d) - 0.5, -0.5); ax.set_xlabel("%GRR of tolerance"); ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.03), fontsize=9)
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


def sharpening_share(shr):
    f, ax = S.fig(h=3.8)
    bins = np.arange(0.5, 1.15, 0.025)
    for g, colour in (("high_speed", S.BRAND_BLUE), ("medium", S.AMBER)):
        ax.hist(S.sig(shr[shr["press_group"] == g]["share_of_due_count"]), bins=bins, color=colour, alpha=0.7, label=g.replace("_", "-") + " presses")
    ax.axvline(1.0, color=S.RED, linestyle="--", linewidth=1, label="Due count")
    ax.set_xlabel("Shots at sharpening as a share of the due count"); ax.set_ylabel("Sharpenings"); ax.legend(frameon=False)
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
