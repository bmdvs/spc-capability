"""Figures for the recording analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np

from analytics.style import style as S


def minute_of_the_hour(t):
    """Routine subgroups by the minute of the hour, two panels on one scale: keyed entries by the time of entry, and
    paper charts by the time noted on the form, with the share within five minutes of the hour."""
    d = t["minute_of_the_hour"]; oh = t["on_the_hour"].set_index("entry_method")
    f, axes = S.fig(h=3.7, ncols=2, sharey=True)
    for ax, (method, title) in zip(axes, (("keyed", "Keyed entries, by the time of entry"), ("paper transcription", "Paper charts, by the time noted on the form"))):
        g = d[d["entry_method"] == method].set_index("minute_of_the_hour")["subgroups"].reindex(range(60)).fillna(0); v = S.sig(g.values / g.values.sum() * 100)
        ax.axvspan(-0.5, 5.5, color=S.LIGHT_BLUE, alpha=0.3, lw=0); ax.axvspan(54.5, 59.5, color=S.LIGHT_BLUE, alpha=0.3, lw=0)
        ax.bar(range(60), v, 0.85, color=[S.BRAND_BLUE if (m <= 5 or m >= 55) else S.ACCENT for m in range(60)])
        ax.axhline(100 / 60, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(30, 100 / 60 + 0.25, "Uniform timing", fontsize=8.5, color=S.DARK_GREY, va="bottom", ha="center")
        ax.text(0.5, 0.93, f"{oh.loc[method, 'stamped_share'] * 100:.1f}% within five minutes of the hour", transform=ax.transAxes, ha="center", va="top", fontsize=9.5, color=S.BRAND_BLUE, fontweight="bold")
        ax.set_xlabel("Minute of the hour"); ax.set_xticks(range(0, 60, 10)); ax.set_xlim(-1, 60); ax.set_title(title, fontsize=10.5)
    axes[0].set_ylabel("Share of routine subgroups, %")
    f.tight_layout()
    return S.save(f, "recording_minute_of_the_hour", "Routine subgroups by the minute of the hour, keyed entries and paper charts, against uniform timing")


def planned_checks_by_hour(t):
    """Planned checks recorded by hour of the day, by press group."""
    d = t["planned_checks_by_hour"]
    f, ax = S.fig(h=3.9)
    for group, label, color, dx in (("high_speed", "High-speed presses (paper)", S.AMBER, -0.07), ("medium", "Medium presses (software)", S.BRAND_BLUE, 0.07)):
        g = d[d["press_group"] == group].sort_values("hour_of_day"); x = g["hour_of_day"].values + dx
        v, lo, hi = (S.sig(g[c].values * 100) for c in ("recorded_share", "recorded_share_low", "recorded_share_high"))
        ax.errorbar(x, v, yerr=[v - lo, hi - v], color=color, lw=1.5, marker="o", ms=4.5, capsize=3, label=label)
    ax.axvline(14.5, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(14.6, 61.5, "Shift change, 14:30", fontsize=8.5, color=S.DARK_GREY, va="bottom")
    al = d[d["press_group"] == "all presses"].sort_values("hour_of_day"); six = al[al["hour_of_day"] == 6].iloc[0]
    ax.annotate(f"06:00, all presses: {six.recorded_share * 100:.0f}%", (6, float(S.sig(six.recorded_share * 100))), textcoords="offset points", xytext=(14, -4), fontsize=9, color=S.TEXT, fontweight="bold")
    pc = t["planned_checks"].set_index(["press_group", "shift"])
    ax.text(18.6, 70.5, f"Nights: high-speed {pc.loc[('high_speed', 'nights'), 'recorded_share'] * 100:.1f}%,\nmedium {pc.loc[('medium', 'nights'), 'recorded_share'] * 100:.1f}%", fontsize=9, color=S.TEXT, ha="center", va="center")
    ax.set_xticks(range(6, 23)); ax.set_xticklabels([f"{h:02d}:00" for h in range(6, 23)], fontsize=8, rotation=45, ha="right")
    ax.set_ylim(60, 100); ax.set_ylabel("Planned checks recorded, %"); ax.set_xlabel("Planned time")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "recording_planned_checks_by_hour", "Planned checks recorded by hour of the day and press group, with 95% intervals and the shift change marked")


def minutes_to_entry(t, after=False):
    """Minutes from the parts to the entry on a log axis: keyed entry in the baseline year, and with after=True the
    gauge-connected and keyed subgroups on the pilot presses beside it."""
    d = t["minutes_to_entry"]
    lines = [("keyed, software presses, 2025", "Keyed, software presses, 2025", S.BRAND_BLUE, 1.8)]
    if after:
        lines += [("gauge-connected, pilot presses, April to June 2026", "Gauge-connected, pilot presses, April to June 2026", S.AMBER, 1.8),
                  ("keyed attribute checks, pilot presses, April to June 2026", "Keyed attribute checks, pilot presses, April to June 2026", S.LIGHT_BLUE, 1.3)]
    f, ax = S.fig(h=3.8 if after else 3.2)
    for record, label, color, lw in lines:
        g = d[d["record"] == record].set_index("band")["subgroups"]; bands = np.arange(int(g.index.min()), int(g.index.max()) + 1); g = g.reindex(bands).fillna(0)
        x = 10 ** ((bands + 0.5) / 8); v = S.sig(g.values / g.values.sum() * 100)
        ax.plot(S.sig(x), v, color=color, lw=lw, label=label)
    ax.axvline(20, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(21.5, ax.get_ylim()[1] * 0.93, "20 minutes", fontsize=8.5, color=S.DARK_GREY, va="top")
    if not after:
        e = t["entry_after_the_parts"].iloc[0]
        ax.text(0.985, 0.72, f"{e.share * 100:.1f}% more than 20 minutes after the parts\nMedian {e.minutes_to_entry_median:.1f} minutes", transform=ax.transAxes, ha="right", va="top", fontsize=9.5, color=S.TEXT, fontweight="bold")
    ax.set_xscale("log"); ax.set_xticks([0.1, 1, 10, 100, 1000]); ax.set_xticklabels(["0.1", "1", "10", "100", "1,000"])
    ax.set_xlabel("Minutes from the parts to the entry, log scale"); ax.set_ylabel("Share of routine subgroups, %")
    if after:
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1, frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "recording_minutes_to_entry" + ("_after_gauge_connection" if after else ""), "Minutes from the parts to the entry on keyed routine subgroups" + (", with gauge-connected and keyed subgroups on the pilot presses from April to June 2026" if after else " of 2025"))


def pilot_planned_checks(t):
    """Planned checks recorded by pilot press and shift, April to June 2025 against 2026."""
    d = t["pilot_planned_checks"]
    rows = [(p_, s_) for p_ in ("PR-09", "PR-06", "PR-03") for s_ in ("nights", "days")]
    f, ax = S.fig(h=3.4, grid="x")
    for y, (press, shift) in enumerate(rows):
        g = d[(d["press_id"] == press) & (d["shift"] == shift)].set_index("period")["recorded_share"] * 100
        a, b = float(S.sig(g["April to June 2025"])), float(S.sig(g["April to June 2026"]))
        ax.plot([a, b], [y, y], color=S.LIGHT_BLUE, lw=3, zorder=1)
        ax.scatter([a], [y], s=48, color=S.GREY, zorder=2, label="April to June 2025" if y == 0 else None); ax.scatter([b], [y], s=48, color=S.BRAND_BLUE, zorder=2, label="April to June 2026" if y == 0 else None)
        ax.text(a - 0.6, y, f"{a:.1f}%", ha="right", va="center", fontsize=8.5); ax.text(b + 0.6, y, f"{b:.1f}%", ha="left", va="center", fontsize=8.5)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([f"{p_}, {s_}" for p_, s_ in rows]); ax.set_xlim(74, 103); ax.set_xlabel("Planned checks recorded, %")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "recording_pilot_planned_checks", "Planned checks recorded by pilot press and shift, April to June 2025 against April to June 2026")


def build(t):
    return {"minute": minute_of_the_hour(t), "by_hour": planned_checks_by_hour(t), "entry": minutes_to_entry(t), "entry_after": minutes_to_entry(t, True), "pilot": pilot_planned_checks(t)}


if __name__ == "__main__":
    from analytics.recording.recording import compute
    print(build(compute()))
