"""Charts and limits: the limits as set against limits computed from a stable baseline after each sharpening.

Reads the chart audit, the subgroup signal comparison and the two limits marts for the baseline year and returns
the tables of the analysis. Average run lengths are by the Markov chain method for the fixed limits; the rolling
limits are judged on the record, by the subgroups they signalled against the subgroups fixed limits signal.
"""
import numpy as np
import pandas as pd

from analytics.data import query
from analytics.stats import XBAR_FACTOR, RANGE_FACTOR, arl_shewhart, wilson

CLASS_SQL = """case when characteristic_type in ('formed height', 'bend angle') then 'formed'
                    when characteristic_type = 'hole diameter' then 'hole diameter'
                    else 'other punched and dimensional' end"""
CLASS_ORDER = ["formed", "hole diameter", "other punched and dimensional"]
METHODS = ["rolling 25 at entry", "PPAP study"]
SHIFTS = (1.0, 1.5)          # sustained shifts of the mean, in within-subgroup sigma


def chart_audit():
    """Characteristics charted in the baseline year by how their limits were set."""
    return query("""
        select limits_as_set_method, press_group,
               count(*) as characteristics,
               count(*) filter (where critical) as critical_characteristics,
               sum(subgroups)::bigint as subgroups,
               sum(subgroups_with_a_reading_set_aside)::bigint as subgroups_with_a_reading_set_aside,
               sum(subgroups_with_limits_in_force)::bigint as subgroups_with_limits_in_force,
               min(limits_as_set_from) as earliest_limit_set, max(limits_as_set_from) as latest_limit_set,
               median(limits_as_set_subgroups_used) as subgroups_used_to_set,
               sum(signals_as_set_rule_1)::bigint as signals_rule_1,
               sum(signals_as_set_any_rule)::bigint as signals_any_rule,
               sum(signals_with_action_recorded)::bigint as signals_with_action_recorded
        from marts.mart_limits_chart_audit
        group by 1, 2 order by 1""")


def signal_comparison():
    """Subgroups after each baseline window: signals under the limits as set and under the limits as computed."""
    d = query(f"""
        select limits_as_set_method, {CLASS_SQL} as characteristic_class,
               count(distinct characteristic_id) as characteristics,
               count(*) as subgroups,
               count(*) filter (where signal_as_computed_rule_1) as signals_as_computed,
               count(*) filter (where signal_as_set_rule_1) as signals_as_set,
               count(*) filter (where signal_as_computed_rule_1 and signal_as_set_rule_1) as signals_by_both
        from marts.mart_limits_subgroup_flags
        group by 1, 2""")
    d["share_of_computed_also_set"] = d["signals_by_both"] / d["signals_as_computed"]
    ci = [wilson(k, n) for k, n in zip(d["signals_by_both"], d["signals_as_computed"])]
    d["share_low"], d["share_high"] = [c[0] for c in ci], [c[1] for c in ci]
    d["rate_as_set_per_100"] = d["signals_as_set"] / d["subgroups"] * 100
    d["rate_as_computed_per_100"] = d["signals_as_computed"] / d["subgroups"] * 100
    d["share_of_set_not_computed"] = 1 - d["signals_by_both"] / d["signals_as_set"]
    d["m"] = d["limits_as_set_method"].map(METHODS.index); d["c"] = d["characteristic_class"].map(CLASS_ORDER.index)
    return d.sort_values(["m", "c"]).drop(columns=["m", "c"]).reset_index(drop=True)


TEXTBOOK_RATE_PER_100 = 0.27          # one point beyond three sigma on a stable process with correct limits


def paper_signals():
    """The paper presses by characteristic class: signals per 100 subgroups under the printed limits, signals per 100
    that limits computed from the stable baseline give on the same subgroups, the reference rate, and the share of
    printed-limit signals with an action recorded."""
    d = query(f"""
        select {CLASS_SQL} as characteristic_class,
               count(distinct characteristic_id) as characteristics,
               count(*) as subgroups,
               count(*) filter (where signal_as_set_rule_1) as signals_as_printed,
               count(*) filter (where signal_as_computed_rule_1) as signals_as_computed,
               count(*) filter (where signal_as_set_rule_1 and action_recorded) as signals_with_action_recorded
        from marts.mart_limits_subgroup_flags where limits_as_set_method = 'PPAP study'
        group by 1""")
    tot = d.drop(columns="characteristic_class").sum(); tot["characteristic_class"] = "all"
    d = pd.concat([d, pd.DataFrame([tot])], ignore_index=True)
    d["printed_per_100"] = d["signals_as_printed"] / d["subgroups"] * 100
    d["computed_per_100"] = d["signals_as_computed"] / d["subgroups"] * 100
    d["reference_per_100"] = TEXTBOOK_RATE_PER_100
    d["action_share"] = d["signals_with_action_recorded"] / d["signals_as_printed"]
    ci = [wilson(k, n) for k, n in zip(d["signals_with_action_recorded"], d["signals_as_printed"])]
    d["action_share_low"], d["action_share_high"] = [c[0] for c in ci], [c[1] for c in ci]
    d["c"] = d["characteristic_class"].map(lambda x: CLASS_ORDER.index(x) if x in CLASS_ORDER else 9)
    return d.sort_values("c").drop(columns="c").reset_index(drop=True)


def paper_actions():
    """The paper presses by characteristic class, on every subgroup of the baseline year with printed limits in
    force: rule-1 signals and the share with an action recorded."""
    d = query(f"""
        select {CLASS_SQL} as characteristic_class, count(*) as characteristics,
               sum(subgroups_with_limits_in_force)::bigint as subgroups, sum(signals_as_set_rule_1)::bigint as signals,
               sum(signals_with_action_recorded)::bigint as signals_with_action_recorded
        from marts.mart_limits_chart_audit where limits_as_set_method = 'PPAP study' group by 1""")
    d["action_share"] = d["signals_with_action_recorded"] / d["signals"]
    ci = [wilson(k, n) for k, n in zip(d["signals_with_action_recorded"], d["signals"])]
    d["action_share_low"], d["action_share_high"] = [c[0] for c in ci], [c[1] for c in ci]
    d["c"] = d["characteristic_class"].map(CLASS_ORDER.index)
    return d.sort_values("c").drop(columns="c").reset_index(drop=True)


def paper_signals_all_subgroups():
    """Every subgroup on the paper presses in the baseline year with printed limits in force, whether or not a
    baseline could be computed for its interval: the signal rate and the action recorded."""
    d = query("""
        select count(*) as characteristics, sum(subgroups_with_limits_in_force)::bigint as subgroups,
               sum(signals_as_set_rule_1)::bigint as signals, sum(signals_with_action_recorded)::bigint as signals_with_action_recorded
        from marts.mart_limits_chart_audit where limits_as_set_method = 'PPAP study'""").iloc[0]
    lo, hi = wilson(d["signals"], d["subgroups"]); alo, ahi = wilson(d["signals_with_action_recorded"], d["signals"])
    return pd.DataFrame([{"characteristics": int(d["characteristics"]), "subgroups": int(d["subgroups"]), "signals_rule_1": int(d["signals"]),
                          "signal_rate": d["signals"] / d["subgroups"], "signal_rate_low": lo, "signal_rate_high": hi,
                          "signals_with_action_recorded": int(d["signals_with_action_recorded"]), "action_share": d["signals_with_action_recorded"] / d["signals"],
                          "action_share_low": alo, "action_share_high": ahi}])


def software_acknowledgements():
    """The software presses: alarms by rule and the acknowledgement text entered."""
    return query("""
        with a as (
            select h.alarm_rule_1, h.alarm_rule_2, lower(trim(h.acknowledgement_text)) as txt, h.adjustment_recorded
            from intermediate.int_characteristic_history h
            where year(h.sample_time) = 2025 and h.entry_method = 'keyed' and h.alarm_raised and h.data_type = 'variable'
              and h.characteristic_type <> 'burr height' and h.subgroup_mean is not null)
        select count(*) as alarms,
               count(*) filter (where alarm_rule_1) as rule_1, count(*) filter (where alarm_rule_2 and not alarm_rule_1) as rule_2_only,
               count(*) filter (where txt is not null) as acknowledged_with_text,
               count(*) filter (where txt in ('ok', 'checked', 'adj', 'ack', 'k', 'chk', 'okay', 'ok.', 'checked ok')) as text_of_one_word,
               count(*) filter (where adjustment_recorded) as adjustment_recorded
        from a""")


def paper_limit_age():
    """The printed limits on the paper presses at the assessment: when set, on what, and the die work since."""
    d = query("""
        select s.die_id,
               count(*) as characteristics,
               min(s.effective_from) as limits_set_from, max(s.effective_from) as limits_set_to,
               bool_and(s.rebuild_on_or_before_set is not null) as every_set_follows_a_rebuild,
               max(t.last_rebuild) as last_rebuild_before_assessment,
               bool_and(s.rebuild_on_or_before_set = t.last_rebuild) as set_at_most_recent_rebuild,
               median(s.months_in_force_at_assessment) as months_in_force,
               max(s.sharpenings_while_in_force_to_assessment) as sharpenings_since_set
        from marts.mart_limits_as_set s
        left join (select die_id, max(event_date) as last_rebuild from intermediate.int_die_event_timeline
                   where event_type = 'rebuild' and event_date <= date '2025-12-31' group by 1) t on t.die_id = s.die_id
        where s.method = 'PPAP study' and s.in_force_at_assessment and s.press_group = 'high_speed'
        group by 1 order by 1""")
    between = query("""
        with rb as (select die_id, event_date, lead(event_date) over (partition by die_id order by event_date) as next_rebuild
                    from intermediate.int_die_event_timeline where event_type = 'rebuild'),
             hs as (select distinct die_id from marts.mart_limits_as_set where press_group = 'high_speed' and method = 'PPAP study')
        select rb.die_id, rb.event_date as rebuild, rb.next_rebuild, date_diff('day', rb.event_date, rb.next_rebuild) / 30.4 as months_between,
               (select count(*) from intermediate.int_die_event_timeline e where e.die_id = rb.die_id and e.event_type = 'sharpening'
                    and e.event_date > rb.event_date and e.event_date <= rb.next_rebuild) as sharpenings_between
        from rb join hs using (die_id) where rb.next_rebuild is not null order by 1, 2""")
    summary = pd.DataFrame([{
        "dies": len(d), "characteristics": int(d["characteristics"].sum()),
        "dies_with_every_limit_set_at_the_most_recent_rebuild": int(d["set_at_most_recent_rebuild"].fillna(False).sum()),
        "months_in_force_median": float(d["months_in_force"].median()), "months_in_force_min": float(d["months_in_force"].min()), "months_in_force_max": float(d["months_in_force"].max()),
        "sharpenings_since_set_median": float(d["sharpenings_since_set"].median()), "sharpenings_since_set_min": int(d["sharpenings_since_set"].min()), "sharpenings_since_set_max": int(d["sharpenings_since_set"].max()),
        "pairs_of_rebuilds": len(between), "months_between_rebuilds_median": float(between["months_between"].median()),
        "sharpenings_between_rebuilds_min": int(between["sharpenings_between"].min()), "sharpenings_between_rebuilds_max": int(between["sharpenings_between"].max())}])
    return d, summary


def baseline_coverage():
    """Sharpening intervals of the baseline year by the basis of their computed limits."""
    return query("""
        select baseline_basis, count(*) as intervals, count(distinct characteristic_id) as characteristics, sum(usable_subgroups)::bigint as usable_subgroups
        from marts.mart_limits_as_computed group by 1 order by 2 desc""")


def chart_geometry():
    """By limits method and characteristic class: the spread of subgroup means inside the baseline, and the limits as
    set, both in units of the computed chart's sigma of the mean (within-subgroup sigma over root five)."""
    return query(f"""
        with f as (
            select m.limits_as_set_method, {CLASS_SQL.replace('characteristic_type', 'm.characteristic_type')} as characteristic_class,
                   m.characteristic_id, m.sharpening_interval_no,
                   median((m.ucl_mean_as_set - m.lcl_mean_as_set) / nullif(m.ucl_mean_as_computed - m.lcl_mean_as_computed, 0)) as width_ratio,
                   median(((m.ucl_mean_as_set + m.lcl_mean_as_set) / 2 - (m.ucl_mean_as_computed + m.lcl_mean_as_computed) / 2)
                          / nullif((m.ucl_mean_as_computed - m.lcl_mean_as_computed) / 6, 0)) as centre_offset
            from marts.mart_limits_subgroup_flags m where m.limits_in_force group by 1, 2, 3, 4)
        select f.limits_as_set_method, f.characteristic_class, count(*) as intervals,
               median(b.sigma_of_means_in_baseline / (b.sigma_within / sqrt(5))) as spread_of_means,
               median(f.width_ratio) as width_ratio, median(abs(f.centre_offset)) as centre_offset
        from f join marts.mart_limits_as_computed b using (characteristic_id, sharpening_interval_no)
        group by 1, 2 order by 1, 2""")


def run_lengths():
    """Average run length in control and to sustained shifts of 1 and 1.5 within-subgroup sigma, by the Markov chain
    method, for limits computed from the stable baseline and for the printed PPAP limits, by characteristic class.
    The rows on rule 1 go in the report; the rows on rules 1 to 4 are working rows."""
    g = chart_geometry()
    rows = []
    for x in g.itertuples():
        k = float(x.spread_of_means)
        d = [sh * np.sqrt(5) for sh in SHIFTS]
        for label, rules in (("computed from the stable baseline, rule 1", (1,)), ("computed from the stable baseline, rules 1 to 4", (1, 2, 3, 4))):
            rows.append({"limits_as_set_method": x.limits_as_set_method, "characteristic_class": x.characteristic_class, "limits": label, "in_report": rules == (1,),
                         "spread_of_means": k, "arl_in_control": arl_shewhart(0, k, rules), "arl_shift_1_sigma": arl_shewhart(d[0], k, rules), "arl_shift_1_5_sigma": arl_shewhart(d[1], k, rules)})
        if x.limits_as_set_method == "PPAP study":
            # the printed centre sits to one side of the process, so a shift is evaluated in each direction
            w, c = float(x.width_ratio), float(x.centre_offset)
            rows.append({"limits_as_set_method": x.limits_as_set_method, "characteristic_class": x.characteristic_class, "limits": "as set: PPAP study, rule 1", "in_report": True,
                         "spread_of_means": k, "width_ratio": w, "centre_offset": c, "arl_in_control": arl_shewhart(0, k, (1,), w, c),
                         "arl_shift_1_sigma": arl_shewhart(-d[0], k, (1,), w, c), "arl_shift_1_5_sigma": arl_shewhart(-d[1], k, (1,), w, c),
                         "arl_shift_1_sigma_toward_printed_centre": arl_shewhart(d[0], k, (1,), w, c), "arl_shift_1_5_sigma_toward_printed_centre": arl_shewhart(d[1], k, (1,), w, c)})
    out = pd.DataFrame(rows)
    out["m"] = out["limits_as_set_method"].map(METHODS.index); out["c"] = out["characteristic_class"].map(CLASS_ORDER.index)
    return out.sort_values(["m", "c"], kind="stable").drop(columns=["m", "c"]).reset_index(drop=True)


def compute():
    dies, age = paper_limit_age()
    return {"chart_audit": chart_audit(), "signal_comparison": signal_comparison(), "paper_signals": paper_signals(), "paper_signals_all_subgroups": paper_signals_all_subgroups(), "paper_actions": paper_actions(), "software_acknowledgements": software_acknowledgements(),
            "paper_limit_age": age, "paper_limit_age_by_die": dies, "baseline_coverage": baseline_coverage(), "chart_geometry": chart_geometry(), "run_lengths": run_lengths()}


if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    for name, table in compute().items():
        print(f"\n== {name}\n{table.to_string(index=False)}")
