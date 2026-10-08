"""Figures for the adjustment analysis. Each function takes the analysis tables and writes one figure under docs/figures."""
import numpy as np

from analytics.adjustment.adjustment import BASELINE_YEAR, GROUPS
from analytics.data import query
from analytics.style import style as S


def the_run_with_most_adjustments(single_coil, year=BASELINE_YEAR, min_subgroups=30):
    """The run, on a formed characteristic on a software press, with the most recorded adjustments among runs of at
    least min_subgroups routine subgroups (and, where single_coil, runs that consumed one coil); ties go to the lower
    characteristic id and run id."""
    return query(f"""
        select p.characteristic_id, p.run_id, any_value(p.press_id) as press_id, any_value(p.characteristic_type) as characteristic_type,
               count(*) as subgroups, count(*) filter (where p.adjustment_recorded) as adjustments_recorded
        from marts.mart_adjustment_points p join intermediate.int_run_shots r using (run_id)
        where p.sample_year = ? and not p.after_redesign and p.entry_method = 'keyed' and p.characteristic_type in ('formed height', 'bend angle')
          {"and r.coils_on_run = 1" if single_coil else ""}
        group by 1, 2 having count(*) >= ? order by adjustments_recorded desc, p.characteristic_id, p.run_id limit 1""", [year, min_subgroups]).iloc[0]


def _run_panel(ax, k, title):
    d = query("""select subgroup_mean, centre_line, ucl_mean, lcl_mean, adjustment_recorded
                 from marts.mart_adjustment_points where characteristic_id = ? and run_id = ? order by sample_time, subgroup_id""", [k.characteristic_id, k.run_id])
    x = np.arange(1, len(d) + 1); m = S.sig(d["subgroup_mean"].values); cl, ucl, lcl = (S.sig(d[c].values) for c in ("centre_line", "ucl_mean", "lcl_mean"))
    span = float(m.max() - m.min()); lo, hi = float(m.min()) - 0.45 * span, float(m.max()) + 0.45 * span
    off = (ucl > hi + span) | (lcl < lo - span)          # limits far outside the means are not drawn
    cl, ucl, lcl = (np.where(off, np.nan, v) for v in (cl, ucl, lcl))
    ax.step(x, ucl, where="mid", color=S.DARK_GREY, lw=1.0, label="Limits in force (3 sigma)"); ax.step(x, lcl, where="mid", color=S.DARK_GREY, lw=1.0)
    ax.step(x, cl + (ucl - cl) * 2 / 3, where="mid", color=S.GREY, lw=0.9, ls="--", label="2 sigma"); ax.step(x, cl - (ucl - cl) * 2 / 3, where="mid", color=S.GREY, lw=0.9, ls="--")
    ax.step(x, cl, where="mid", color=S.LIGHT_BLUE, lw=1.0, label="Centre line")
    ax.plot(x, m, color=S.BRAND_BLUE, lw=1.2, marker="o", ms=3.5, label="Subgroup mean")
    a = d["adjustment_recorded"].values.astype(bool)
    ax.scatter(x[a], m[a], s=80, facecolors="none", edgecolors=S.AMBER, linewidths=1.7, zorder=4, label="Adjustment recorded")
    if off.any():
        ax.text(float(x[off].mean()), hi - 0.04 * span, "Limits beyond the scale", ha="center", va="top", fontsize=8.5, color=S.DARK_GREY)
    ax.set_ylim(lo, hi)
    ax.set_title(title, fontsize=10.5); ax.set_xlabel("Routine subgroup on the run")
    ax.set_ylabel("Subgroup mean, mm" if k.characteristic_type == "formed height" else "Subgroup mean, degrees")


def one_run(t):
    """Subgroup means on two runs with the limits in force and the recorded adjustments marked: the run with the most
    recorded adjustments among single-coil runs, and the run with the most among all runs."""
    a, b = the_run_with_most_adjustments(True), the_run_with_most_adjustments(False)
    f, axes = S.fig(h=4.2, ncols=2)
    _run_panel(axes[0], a, f"{a.characteristic_id}, run {a.run_id}, {a.press_id}: one coil"); _run_panel(axes[1], b, f"{b.characteristic_id}, run {b.run_id}, {b.press_id}")
    h_, l_ = axes[0].get_legend_handles_labels()
    f.legend(h_, l_, loc="lower center", ncol=5, frameon=False, fontsize=8.5)
    f.tight_layout(rect=(0, 0.07, 1, 1))
    return S.save(f, "adjustment_one_run", f"Subgroup means of {a.characteristic_id} on run {a.run_id} and of {b.characteristic_id} on run {b.run_id}, with the limits in force and the recorded adjustments marked"), (a, b)


def what_the_single_coil_run_shows():
    """On the single-coil run: the plotted subgroups at which a recorded adjustment beyond two sigma is followed by a
    mean on the other side of the centre line by more than one sigma, and the last plotted subgroup before the limits
    in force widen to more than three times their width."""
    k = the_run_with_most_adjustments(True)
    d = query("""select position_in_sigma, next_position_in_sigma, adjustment_recorded, ucl_mean - lcl_mean as width
                 from marts.mart_adjustment_points where characteristic_id = ? and run_id = ? order by sample_time, subgroup_id""", [k.characteristic_id, k.run_id])
    z, nz = d["position_in_sigma"].values, d["next_position_in_sigma"].values
    hit = d["adjustment_recorded"].values.astype(bool) & (np.abs(z) > 2) & (np.sign(nz) == -np.sign(z)) & (np.abs(nz) > 1)
    wide = np.where(d["width"].values > 3 * d["width"].values[0])[0]
    return [int(i) + 1 for i in np.where(hit)[0]], (int(wide[0]) if len(wide) else None)


def return_by_group(t):
    """The next subgroup's position as a share of the point's position, four groups of points on keyed entry."""
    d = t["return_toward_centre"]; d = d[d["entry_method"] == "keyed"].set_index("points_group")
    rows = [(GROUPS[0], "Beyond two sigma,\nadjustment recorded", S.AMBER), (GROUPS[1], "Beyond two sigma,\nnone recorded", S.BRAND_BLUE),
            (GROUPS[2], "Beyond two sigma,\ncharacteristics not\nadjusted at the press", S.GREY), (GROUPS[3], "Between one\nand two sigma", S.LIGHT_BLUE)]
    f, ax = S.fig(h=4.0)
    for x, (g, label, color) in enumerate(rows):
        v, lo, hi = (float(S.sig(d.loc[g, c])) for c in ("next_as_share_of_position", "low", "high"))
        ax.bar(x, v, 0.6, color=color); ax.errorbar(x, v, yerr=[[v - lo], [hi - v]], color=S.TEXT, lw=1.2, capsize=4)
        ax.text(x, hi + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=9.5, color=S.TEXT)
    ax.set_xticks(range(4)); ax.set_xticklabels([f"{r[1]}\n({int(d.loc[r[0], 'points']):,} points)" for r in rows], fontsize=8.5)
    ax.set_ylabel("Next subgroup's position as a share\nof the point's position"); ax.set_ylim(0, 0.7)
    f.tight_layout()
    return S.save(f, "adjustment_return_by_group", "Position of the next subgroup as a share of the position of the point, by group of points, keyed entry, with 95% intervals")


def autocorrelation(t, after=False):
    """Lag-1 autocorrelation of subgroup means within a run and coil, with intervals: the baseline year, and with
    after=True the pilot presses under the reaction plan beside it."""
    d = t["autocorrelation"]
    if not after:
        d = d[d["period"].str.startswith("2024")]
    f, ax = S.fig(h=3.0 if after else 2.0, grid="x")
    labels = []
    for y, r in enumerate(d.iloc[::-1].itertuples()):
        v, lo, hi = (float(S.sig(q)) for q in (r.lag_1_autocorrelation, r.low, r.high)); color = S.BRAND_BLUE if r.characteristics == "adjusted at the press" else S.GREY
        ax.errorbar(v, y, xerr=[[v - lo], [hi - v]], color=color, lw=1.6, capsize=4, marker="o", ms=7)
        ax.text(hi + 0.014, y, f"{v:.2f}", va="center", fontsize=9.5, color=S.TEXT)
        labels.append(f"{r.period[0].upper() + r.period[1:]}:\n{r.characteristics}" if after else r.characteristics[0].upper() + r.characteristics[1:])
    ax.axvline(0, color=S.DARK_GREY, lw=1.0, ls="--")
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=8.5 if after else 9.5); ax.set_xlim(-0.2, 0.12); ax.set_ylim(-0.6, len(labels) - 0.4)
    ax.set_xlabel("Lag-1 autocorrelation of subgroup means within a run and coil")
    f.tight_layout()
    return S.save(f, "adjustment_autocorrelation" + ("_under_the_reaction_plan" if after else ""), "Lag-1 autocorrelation of subgroup means within a run and coil by whether the characteristic is adjusted at the press, with 95% intervals")


def added_variance(t):
    """Added variance by characteristic, sorted, with the median marked."""
    v = S.sig(np.sort(t["variance_by_characteristic"]["added_variance"].values) * 100); med = float(S.sig(np.median(v)))
    f, ax = S.fig(h=3.8)
    ax.bar(np.arange(1, len(v) + 1), v, 1.0, color=[S.BRAND_BLUE if q > 0 else S.GREY for q in v])
    ax.axhline(0, color=S.DARK_GREY, lw=1.0); ax.axhline(med, color=S.AMBER, lw=1.4, ls="--"); ax.text(2, med + 6, f"median {med:.0f}%", fontsize=9, color=S.AMBER, va="bottom")
    ax.set_xlabel(f"Characteristics adjusted at the press, sorted ({len(v)})"); ax.set_ylabel("Added variance, %")
    ax.set_xlim(0, len(v) + 1)
    f.tight_layout()
    return S.save(f, "adjustment_added_variance", "Added variance by characteristic against the same characteristic's runs with no recorded adjustment and no point beyond two sigma")


def build(t):
    run, k = one_run(t)
    overshoot, widen = what_the_single_coil_run_shows()
    return {"run": run, "runs_shown": [dict(q) for q in k], "overshoot_at": overshoot, "limits_widen_after": widen, "return": return_by_group(t), "autocorrelation": autocorrelation(t), "autocorrelation_after": autocorrelation(t, True), "variance": added_variance(t)}


if __name__ == "__main__":
    from analytics.adjustment.adjustment import compute
    print(build(compute()))
