"""Figures for the recording analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np

from analytics.style import style as S


def _minute_panel(t, method, name, alt):
    d = t["minute_of_the_hour"]
    g = d[d["entry_method"] == method].set_index("minute_of_the_hour")["subgroups"].reindex(range(60)).fillna(0); v = S.sig(g.values / g.values.sum() * 100)
    f, ax = S.fig(h=3.5, w=6.4)
    ax.bar(range(60), v, 0.85, color=[S.BRAND_BLUE if (m <= 5 or m >= 55) else S.LIGHT_BLUE for m in range(60)])
    ax.axhline(100 / 60, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(44, 100 / 60 + 0.25, "Uniform timing", fontsize=8.5, color=S.DARK_GREY, va="bottom")
    ax.set_xlabel("Minute of the hour"); ax.set_xticks(range(0, 60, 10)); ax.set_xlim(-1, 60); ax.set_ylabel("Share of routine subgroups, %")
    f.tight_layout()
    return S.save(f, name, alt)


def minute_of_the_hour(t):
    """Keyed routine subgroups by the minute of the hour of entry."""
    return _minute_panel(t, "keyed", "recording_minute_of_the_hour", "Keyed routine subgroups by the minute of the hour of entry, against uniform timing")


def minute_of_the_hour_paper(t):
    """Paper routine subgroups by the minute of the hour noted on the chart form."""
    return _minute_panel(t, "paper transcription", "recording_minute_of_the_hour_paper", "Routine subgroups on paper charts by the minute of the hour noted on the form, against uniform timing")


def planned_checks_by_hour(t):
    """Planned checks recorded by hour of the day, by press group."""
    d = t["planned_checks_by_hour"]
    f, ax = S.fig(h=3.9)
    for group, label, color, dx in (("high_speed", "High-speed presses (paper)", S.AMBER, -0.07), ("medium", "Medium presses (software)", S.BRAND_BLUE, 0.07)):
        g = d[d["press_group"] == group].sort_values("hour_of_day"); x = g["hour_of_day"].values + dx
        v, lo, hi = (S.sig(g[c].values * 100) for c in ("recorded_share", "recorded_share_low", "recorded_share_high"))
        ax.errorbar(x, v, yerr=[v - lo, hi - v], color=color, lw=1.5, marker="o", ms=4.5, capsize=3, label=label)
    ax.axvline(14.5, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(14.6, 61.5, "Shift change, 14:30", fontsize=8.5, color=S.DARK_GREY, va="bottom")
    ax.set_xticks(range(6, 23)); ax.set_xticklabels([f"{h:02d}:00" for h in range(6, 23)], fontsize=8, rotation=45, ha="right")
    ax.set_ylim(60, 100); ax.set_ylabel("Planned checks recorded, %"); ax.set_xlabel("Planned time")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "recording_planned_checks_by_hour", "Planned checks recorded by hour of the day and press group, with 95% intervals and the shift change marked")


def minutes_to_entry(t, after=False):
    """Minutes from the parts to the entry on a log axis: keyed entry in the baseline year, and with after=True the
    gauge-connected and keyed subgroups on the pilot presses beside it."""
    d = t["minutes_to_entry"]
    lines = [("keyed, software presses, 2024", "Keyed, software presses, 2024", S.BRAND_BLUE, 1.8)]
    if after:
        lines += [("gauge-connected, pilot presses, March to December 2025", "Gauge-connected, pilot presses, March to December 2025", S.AMBER, 1.8),
                  ("keyed attribute checks, pilot presses, March to December 2025", "Keyed attribute checks, pilot presses, March to December 2025", S.LIGHT_BLUE, 1.3)]
    f, ax = S.fig(h=3.8 if after else 3.2)
    for record, label, color, lw in lines:
        g = d[d["record"] == record].set_index("band")["subgroups"]; bands = np.arange(int(g.index.min()), int(g.index.max()) + 1); g = g.reindex(bands).fillna(0)
        x = 10 ** ((bands + 0.5) / 8); v = S.sig(g.values / g.values.sum() * 100)
        ax.plot(S.sig(x), v, color=color, lw=lw, label=label)
    ax.axvline(20, color=S.DARK_GREY, ls="--", lw=1.0); ax.text(21.5, ax.get_ylim()[1] * 0.93, "20 minutes", fontsize=8.5, color=S.DARK_GREY, va="top")
    ax.set_xscale("log"); ax.set_xticks([0.1, 1, 10, 100, 1000]); ax.set_xticklabels(["0.1", "1", "10", "100", "1,000"])
    ax.set_xlabel("Minutes from the parts to the entry, log scale"); ax.set_ylabel("Share of routine subgroups, %")
    if after:
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1, frameon=False, fontsize=8.5)
    f.tight_layout()
    return S.save(f, "recording_minutes_to_entry" + ("_after_gauge_connection" if after else ""), "Minutes from the parts to the entry on keyed routine subgroups" + (", with gauge-connected and keyed subgroups on the pilot presses from March to December 2025" if after else " of 2024"))


def pilot_planned_checks(t):
    """Planned checks recorded by pilot press and shift, March to December 2024 against 2025."""
    d = t["pilot_planned_checks"]
    rows = [(p_, s_) for p_ in ("PR-09", "PR-06", "PR-03") for s_ in ("nights", "days")]
    f, ax = S.fig(h=3.4, grid="x")
    for y, (press, shift) in enumerate(rows):
        g = d[(d["press_id"] == press) & (d["shift"] == shift)].set_index("period")["recorded_share"] * 100
        a, b = float(S.sig(g["March to December 2024"])), float(S.sig(g["March to December 2025"]))
        ax.plot([a, b], [y, y], color=S.LIGHT_BLUE, lw=3, zorder=1)
        ax.scatter([a], [y], s=48, color=S.GREY, zorder=2, label="March to December 2024" if y == 0 else None); ax.scatter([b], [y], s=48, color=S.BRAND_BLUE, zorder=2, label="March to December 2025" if y == 0 else None)
        ax.text(a - 0.6, y, f"{a:.1f}%", ha="right", va="center", fontsize=8.5); ax.text(b + 0.6, y, f"{b:.1f}%", ha="left", va="center", fontsize=8.5)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([f"{p_}, {s_}" for p_, s_ in rows]); ax.set_xlim(74, 103); ax.set_xlabel("Planned checks recorded, %")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False, fontsize=9)
    f.tight_layout()
    return S.save(f, "recording_pilot_planned_checks", "Planned checks recorded by pilot press and shift, March to December 2024 against March to December 2025")


def build(t):
    return {"minute": minute_of_the_hour(t), "minute_paper": minute_of_the_hour_paper(t), "by_hour": planned_checks_by_hour(t), "entry": minutes_to_entry(t), "entry_after": minutes_to_entry(t, True), "pilot": pilot_planned_checks(t)}


if __name__ == "__main__":
    from analytics.recording.recording import compute
    print(build(compute()))
