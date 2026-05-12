"""Recording: when routine checks are stamped, the planned checks recorded by shift, short runs with no routine check,
and entry after the parts were made; the baseline year, and the pilot presses before and after gauge connection."""
import pandas as pd

from analytics.data import query
from analytics.stats import wilson

BASELINE_YEAR = 2025
PILOT_BEFORE = "sample_time >= date '2025-04-01' and sample_time < date '2025-07-01'"
PILOT_AFTER = "sample_time >= date '2026-04-01' and sample_time < date '2026-07-01'"


def _with_intervals(d, pairs):
    for k, n, name in pairs:
        d[name] = d[k] / d[n]; ci = [wilson(a, b) if b else (float("nan"), float("nan")) for a, b in zip(d[k], d[n])]
        d[name + "_low"], d[name + "_high"] = [c[0] for c in ci], [c[1] for c in ci]
    return d


def on_the_hour(year=BASELINE_YEAR):
    """Routine subgroups stamped within five minutes of the hour, by entry method, with the time of the parts beside
    the stamped time on keyed entry. Uniform timing gives 11 minutes in 60, 18.3%."""
    d = query("""
        select coalesce(entry_method, 'all routine subgroups') as entry_method, count(*) as subgroups,
               count(*) filter (where minute(stamped_time) <= 5 or minute(stamped_time) >= 55) as stamped_within_five_minutes_of_the_hour,
               count(*) filter (where minute(sample_time) <= 5 or minute(sample_time) >= 55) as parts_time_within_five_minutes_of_the_hour
        from marts.mart_recording_routine_subgroups where sample_year = ? and not after_redesign
        group by grouping sets ((entry_method), ()) order by 1""", [year])
    return _with_intervals(d, (("stamped_within_five_minutes_of_the_hour", "subgroups", "stamped_share"), ("parts_time_within_five_minutes_of_the_hour", "subgroups", "parts_time_share")))


def minute_of_the_hour(year=BASELINE_YEAR):
    """Routine subgroups by the minute of the hour stamped, by entry method (for the figure)."""
    return query("""select entry_method, minute(stamped_time) as minute_of_the_hour, count(*) as subgroups
                    from marts.mart_recording_routine_subgroups where sample_year = ? and not after_redesign group by 1, 2 order by 1, 2""", [year])


def planned_checks(year=BASELINE_YEAR):
    """Planned checks recorded by shift, with press group beside."""
    d = query("""
        select coalesce(g.press_group, 'all presses') as press_group, c.shift, count(*) as planned_checks, count(*) filter (where c.recorded) as recorded
        from marts.mart_recording_planned_checks c join intermediate.int_press_redesign g using (press_id)
        where c.planned_year = ? and not c.after_redesign
        group by grouping sets ((g.press_group, c.shift), (c.shift)) order by 1, 2""", [year])
    return _with_intervals(d, (("recorded", "planned_checks", "recorded_share"),))


def planned_checks_by_hour(year=BASELINE_YEAR):
    """Planned checks recorded by hour of the day, all presses and by press group."""
    d = query("""select coalesce(g.press_group, 'all presses') as press_group, hour(c.planned_time) as hour_of_day, any_value(c.shift) as shift, count(*) as planned_checks, count(*) filter (where c.recorded) as recorded
                 from marts.mart_recording_planned_checks c join intermediate.int_press_redesign g using (press_id)
                 where c.planned_year = ? and not c.after_redesign
                 group by grouping sets ((g.press_group, hour(c.planned_time)), (hour(c.planned_time))) order by 1, 2""", [year])
    return _with_intervals(d, (("recorded", "planned_checks", "recorded_share"),))


def minutes_to_entry():
    """Minutes from the parts to the entry in bands, for the three records compared: keyed in the baseline year on the
    software presses, and gauge-connected and keyed subgroups on the pilot presses after gauge connection."""
    return query(f"""
        with s as (
            select 'keyed, software presses, {BASELINE_YEAR}' as record, minutes_to_entry from marts.mart_recording_routine_subgroups where sample_year = {BASELINE_YEAR} and not after_redesign and entry_method = 'keyed'
            union all
            select 'gauge-connected, pilot presses, April to June 2026', minutes_to_entry from marts.mart_recording_routine_subgroups where is_pilot_press and after_redesign and entry_method = 'gauge-connected' and {PILOT_AFTER}
            union all
            select 'keyed attribute checks, pilot presses, April to June 2026', minutes_to_entry from marts.mart_recording_routine_subgroups where is_pilot_press and after_redesign and entry_method = 'keyed' and {PILOT_AFTER})
        select record, floor(log10(greatest(minutes_to_entry, 0.1)) * 8) as band, count(*) as subgroups
        from s group by 1, 2 order by 1, 2""")


def time_of_the_parts_before_and_after():
    """Time of the parts within five minutes of the hour on the medium pilot presses: keyed, April to June 2025,
    against gauge-connected, April to June 2026."""
    d = query(f"""
        select case when after_redesign then 'April to June 2026, gauge-connected' else 'April to June 2025, keyed' end as record, count(*) as subgroups,
               count(*) filter (where minute(sample_time) <= 5 or minute(sample_time) >= 55) as parts_time_within_five_minutes_of_the_hour
        from marts.mart_recording_routine_subgroups
        where is_pilot_press and press_group = 'medium' and ((not after_redesign and entry_method = 'keyed' and {PILOT_BEFORE}) or (after_redesign and entry_method = 'gauge-connected' and {PILOT_AFTER}))
        group by 1 order by 1""")
    return _with_intervals(d, (("parts_time_within_five_minutes_of_the_hour", "subgroups", "share"),))


def short_runs(year=BASELINE_YEAR):
    """Runs under two hours from production start to end, and those with no routine check."""
    d = query("""
        with r as (select r.run_id, date_diff('minute', r.production_start, r.actual_end) as minutes,
                          (select count(*) from intermediate.int_run_checks c where c.run_id = r.run_id and c.routine_check) as routine_checks
                   from intermediate.int_run_shots r where year(r.production_start) = ? and r.actual_end is not null)
        select case when minutes < 120 then 'under two hours' else 'two hours and over' end as run_length, count(*) as runs,
               count(*) filter (where routine_checks = 0) as with_no_routine_check
        from r group by 1 order by 1 desc""", [year])
    return _with_intervals(d, (("with_no_routine_check", "runs", "share_with_no_routine_check"),))


def entry_after_the_parts():
    """Subgroups entered more than 20 minutes after the parts were made: software presses in the baseline year, and the
    pilot presses before and after gauge connection."""
    d = query(f"""
        select * from (
            select 1 as o, 'software presses, {BASELINE_YEAR}, keyed' as record, count(*) as subgroups, count(*) filter (where minutes_to_entry > 20) as entered_more_than_20_minutes_after, median(minutes_to_entry) as minutes_to_entry_median
            from marts.mart_recording_routine_subgroups where sample_year = {BASELINE_YEAR} and not after_redesign and entry_method = 'keyed'
            union all
            select 2, 'pilot presses, April to June 2025, keyed', count(*), count(*) filter (where minutes_to_entry > 20), median(minutes_to_entry)
            from marts.mart_recording_routine_subgroups where is_pilot_press and not after_redesign and entry_method = 'keyed' and {PILOT_BEFORE}
            union all
            select 3, 'pilot presses, April to June 2026, gauge-connected', count(*), count(*) filter (where minutes_to_entry > 20), median(minutes_to_entry)
            from marts.mart_recording_routine_subgroups where is_pilot_press and after_redesign and entry_method = 'gauge-connected' and {PILOT_AFTER}
            union all
            select 4, 'pilot presses, April to June 2026, keyed (attribute checks)', count(*), count(*) filter (where minutes_to_entry > 20), median(minutes_to_entry)
            from marts.mart_recording_routine_subgroups where is_pilot_press and after_redesign and entry_method = 'keyed' and {PILOT_AFTER}
        ) order by o""").drop(columns=["o"])
    return _with_intervals(d, (("entered_more_than_20_minutes_after", "subgroups", "share"),))


def pilot_before_and_after():
    """The pilot presses, April to June 2025 against April to June 2026: planned checks recorded by shift and
    routine subgroups stamped within five minutes of the hour or the half hour."""
    c = query("""
        select c.press_id, case when c.after_redesign then 'April to June 2026' else 'April to June 2025' end as period, c.shift,
               count(*) as planned_checks, count(*) filter (where c.recorded) as recorded
        from marts.mart_recording_planned_checks c
        where c.is_pilot_press and ((not c.after_redesign and c.planned_time >= date '2025-04-01' and c.planned_time < date '2025-07-01')
                                 or (c.after_redesign and c.planned_time >= date '2026-04-01' and c.planned_time < date '2026-07-01'))
        group by 1, 2, 3 order by 1, 2, 3""")
    c = _with_intervals(c, (("recorded", "planned_checks", "recorded_share"),))
    s = query(f"""
        select press_id, case when after_redesign then 'April to June 2026' else 'April to June 2025' end as period, entry_method, count(*) as subgroups,
               count(*) filter (where minute(stamped_time) <= 5 or minute(stamped_time) >= 55) as within_five_minutes_of_the_hour,
               count(*) filter (where minute(stamped_time) between 25 and 35) as within_five_minutes_of_the_half_hour
        from marts.mart_recording_routine_subgroups
        where is_pilot_press and ((not after_redesign and {PILOT_BEFORE}) or (after_redesign and {PILOT_AFTER}))
        group by 1, 2, 3 order by 1, 2, 3""")
    s = _with_intervals(s, (("within_five_minutes_of_the_hour", "subgroups", "hour_share"), ("within_five_minutes_of_the_half_hour", "subgroups", "half_hour_share")))
    return c, s


def compute():
    checks, stamps = pilot_before_and_after()
    return {"on_the_hour": on_the_hour(), "planned_checks": planned_checks(), "planned_checks_by_hour": planned_checks_by_hour(), "short_runs": short_runs(),
            "entry_after_the_parts": entry_after_the_parts(), "pilot_planned_checks": checks, "pilot_stamps": stamps, "time_of_the_parts": time_of_the_parts_before_and_after(), "minutes_to_entry": minutes_to_entry(), "minute_of_the_hour": minute_of_the_hour()}


if __name__ == "__main__":
    pd.set_option("display.width", 320); pd.set_option("display.max_columns", 60); pd.set_option("display.max_colwidth", 70)
    for name, table in compute().items():
        print(f"\n== {name}\n{table.head(40).round(4).to_string(index=False)}")
