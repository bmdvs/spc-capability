"""Figures for the SPC monthly summary. Each function takes the summary tables and writes one figure under docs/figures."""
import numpy as np
import pandas as pd

from analytics.style import style as S

MONTHS = "JFMAMJJASOND"
REDESIGN = ((1 + 2 / 28, "Pilot presses,\n3 February"), (8 + 1 / 30, "Other presses,\n2 September"))          # position on the month axis, January at 0


def _months(t):
    return pd.date_range(t["periods"]["twelve_months"][0], periods=12, freq="MS")


def series(t):
    """The monthly values of the headline measures over the twelve months, one column per measure; a month with no value is NaN."""
    idx = _months(t); a = t["alarms_by_month"].set_index("month_start").reindex(idx); p = t["planned_checks_by_month"].set_index("month_start").reindex(idx)
    e = t["entries_by_month"].pivot_table(index="month_start", columns="entry_method", values=["subgroups", "late"], aggfunc="sum").reindex(idx)
    s = t["sharpenings_by_month"].set_index("month_start").reindex(idx); b = t["burr_by_month"].set_index("month_start").reindex(idx)
    lim = t["limits_recalculated_by_month"].set_index("month_start")["charts"].reindex(idx); st = t["stops_by_month"].set_index("month_start")["stops"].reindex(idx)
    d = pd.DataFrame(index=idx)
    d["alarm_signals_per_100_subgroups"] = a["alarm_signals"] / a["variable_subgroups"] * 100
    d["adjustment_share"] = a["with_an_adjustment_recorded"] / a["alarm_signals"] * 100
    d["acknowledgement_or_adjustment_share"] = a["with_an_acknowledgement_or_adjustment"] / a["alarm_signals"] * 100
    d["planned_checks_recorded_share"] = p["recorded"] / p["planned_checks"] * 100
    for m, name in (("gauge-connected", "late_entries_gauge_connected_share"), ("keyed", "late_entries_keyed_share")):
        d[name] = e[("late", m)] / e[("subgroups", m)] * 100
    d["charts_recalculated"] = lim
    d["sharpenings_at_or_before_the_due_count_share"] = s["at_or_before_the_due_count"] / s["sharpenings_on_a_die_with_a_burr_line"] * 100
    d["intervals_with_burr_over_the_limit_share"] = b["over_the_limit"] / b["intervals"] * 100
    d["per_stroke_stops"] = st
    return d


PANELS = [("alarm_signals_per_100_subgroups", "Alarm signals per\n100 subgroups", "{:.1f}"), ("adjustment_share", "Alarms with an\nadjustment, %", "{:.0f}"), ("acknowledgement_or_adjustment_share", "Alarms with an acknow-\nledgement or adjustment, %", "{:.0f}"),
          ("planned_checks_recorded_share", "Planned checks\nrecorded, %", "{:.1f}"), ("late_entries_gauge_connected_share", "Late entries,\ngauge-connected, %", "{:.1f}"), ("late_entries_keyed_share", "Late entries,\nkeyed, %", "{:.1f}"),
          ("charts_recalculated", "Charts\nrecalculated", "{:.0f}"), ("sharpenings_at_or_before_the_due_count_share", "Sharpenings at or before\nthe due count, %", "{:.0f}"), ("intervals_with_burr_over_the_limit_share", "Intervals with burr\nover the limit, %", "{:.0f}"),
          ("per_stroke_stops", "Per-stroke\nstops", "{:.0f}")]


def small_multiples(t):
    """One panel per headline measure: the monthly value over the twelve months, with the redesign dates marked."""
    d = series(t)
    f, axes = S.fig(h=5.4, ncols=5, nrows=2)
    for ax, (col, title, fmt) in zip(axes.ravel(), PANELS):
        v = S.sig(d[col].values.astype(float)); x = np.arange(12); ok = ~np.isnan(v)
        ax.plot(x[ok], v[ok], color=S.BRAND_BLUE, lw=1.6); ax.scatter(x[ok], v[ok], s=10, color=S.BRAND_BLUE, zorder=3)
        ax.scatter([11], [v[11]], s=30, color=S.AMBER, zorder=4); ax.text(11, v[11], " " + fmt.format(v[11]), fontsize=8, va="center", ha="left", color=S.TEXT)
        for pos, _ in REDESIGN:
            ax.axvline(pos - 0.5, color=S.GREY, lw=1.0, ls="--")
        top = np.nanmax(v); ax.set_ylim(0, top * 1.18 if top > 0 else 1); ax.set_xlim(-0.6, 13.4)
        ax.set_xticks(range(12)); ax.set_xticklabels(list(MONTHS), fontsize=7); ax.tick_params(axis="y", labelsize=7.5); ax.set_title(title, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "monthly_headline_measures", "Monthly values of the headline measures on all presses, January to December 2025, with the dates the redesign took effect")


def _paired(ax, labels, before, now, fmt, names):
    x = np.arange(len(labels)); a, b = S.sig(before), S.sig(now)
    ax.bar(x - 0.2, a, 0.38, color=S.GREY, label=names[0]); ax.bar(x + 0.2, b, 0.38, color=S.BRAND_BLUE, label=names[1])
    for dx, v in ((-0.2, a), (0.2, b)):
        for xi, vi in zip(x, v):
            ax.text(xi + dx, vi, fmt.format(vi), ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8.5)


def alarms_by_press(t):
    """Alarm signals per 100 subgroups by press, the month against the twelve months before the last twelve."""
    a = t["alarms"]; a = a[a["press_id"] != "all presses"]; now = a[a["period"] == "month"].set_index("press_id"); before = a[a["period"] == "twelve_months_before"].set_index("press_id").reindex(now.index)
    f, ax = S.fig(h=3.7)
    _paired(ax, list(now.index), before["alarm_signals_per_100_subgroups"].values, now["alarm_signals_per_100_subgroups"].values, "{:.1f}", ("2024", "December 2025"))
    ax.set_ylabel("Alarm signals per 100 subgroups"); ax.set_ylim(0, float(before["alarm_signals_per_100_subgroups"].max()) * 1.12); ax.legend(loc="upper right", frameon=False, fontsize=9, ncol=2)
    f.tight_layout()
    return S.save(f, "monthly_alarms_by_press", "Alarm signals per 100 subgroups by press, December 2025 against 2024")


def planned_checks_by_press(t):
    """Planned checks recorded by press and shift, the month against the twelve months before the last twelve."""
    p = t["planned_checks"]; p = p[p["press_id"] != "all presses"]
    f, axes = S.fig(h=5.4, nrows=2, sharex=True)
    for ax, shift in zip(axes, ("days", "nights")):
        g = p[p["shift"] == shift]; now = g[g["period"] == "month"].set_index("press_id"); before = g[g["period"] == "twelve_months_before"].set_index("press_id").reindex(now.index)
        _paired(ax, list(now.index), before["recorded_share"].values * 100, now["recorded_share"].values * 100, "{:.0f}", ("2024", "December 2025"))
        ax.set_ylim(60, 106); ax.set_ylabel(f"{shift.capitalize()}: planned checks\nrecorded, %"); ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    axes[0].legend(loc="lower right", frameon=False, fontsize=9, ncol=2)
    f.tight_layout()
    return S.save(f, "monthly_planned_checks_by_press", "Planned checks recorded by press and shift, December 2025 against 2024")


def sharpenings_by_month(t):
    """Sharpenings on dies with a burr line by month: at or before the due count, and after it."""
    s = t["sharpenings_by_month"].set_index("month_start").reindex(_months(t)); on = S.sig(s["at_or_before_the_due_count"].values.astype(float)); late = S.sig((s["sharpenings_on_a_die_with_a_burr_line"] - s["at_or_before_the_due_count"]).values.astype(float)); x = np.arange(12)
    f, ax = S.fig(h=3.7)
    ax.bar(x, on, 0.7, color=S.BRAND_BLUE, label="At or before the due count"); ax.bar(x, late, 0.7, bottom=on, color=S.AMBER, label="After the due count")
    for xi, a, b in zip(x, on, late):
        ax.text(xi, a + b, f"{a:.0f} of {a + b:.0f}", ha="center", va="bottom", fontsize=8)
    for pos, lab in REDESIGN:
        ax.axvline(pos - 0.5, color=S.GREY, lw=1.0, ls="--"); ax.text(pos - 0.42, float((on + late).max()) * 1.24, lab, fontsize=8, color=S.DARK_GREY, va="top")
    ax.set_xticks(x); ax.set_xticklabels([m.strftime("%b") for m in _months(t)]); ax.set_ylabel("Sharpenings"); ax.set_ylim(0, float((on + late).max()) * 1.26)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "monthly_sharpenings_against_the_due_count", "Sharpenings at or before the due count and after it, by month, 2025")


def build(t):
    return {"headline": small_multiples(t), "alarms": alarms_by_press(t), "checks": planned_checks_by_press(t), "sharpenings": sharpenings_by_month(t)}
