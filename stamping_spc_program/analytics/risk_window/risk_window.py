"""Risk window and sorting: the parts that pass between routine checks, and each sorting event traced to its die event
and the check that preceded it, with the quantity sorted against the parts at risk and the hours and cost as booked
and as estimated."""
import pandas as pd

from analytics.data import query
from analytics.stats import wilson

BASELINE_YEAR = 2024


def risk_window():
    """Parts between routine checks by press, by the plan and as recorded, in the baseline year."""
    return query("""
        select press_group, press_id, count(*) as parts, sum(runs)::bigint as runs,
               median(strokes_per_minute) as strokes_per_minute, median(plan_frequency_minutes) as plan_frequency_minutes,
               min(parts_between_checks_by_plan) as fewest_parts_between_checks, median(parts_between_checks_by_plan) as median_parts_between_checks,
               max(parts_between_checks_by_plan) as most_parts_between_checks,
               median(minutes_between_routine_checks_recorded) as minutes_between_routine_checks_recorded,
               median(parts_between_checks_recorded) as parts_between_checks_recorded,
               median(realised_share_of_run_speed) as realised_share_of_run_speed,
               median(parts_between_checks_at_the_realised_rate) as median_parts_between_checks_at_the_realised_rate,
               min(parts_between_checks_at_the_realised_rate) as fewest_parts_between_checks_at_the_realised_rate,
               max(parts_between_checks_at_the_realised_rate) as most_parts_between_checks_at_the_realised_rate
        from marts.mart_risk_window group by 1, 2 order by 2""")


def sorting_events(year=BASELINE_YEAR):
    """Every sorting event of the year with its trace."""
    return query("""
        select sorting_event_id, press_id, run_id, sort_started, sorted_at, detected_at, defect_code, traced_to, die_event_type, die_event_date,
               die_protection_faults_in_the_window, fault_inputs, check_before, found_at, minutes_from_check_before_to_finding,
               sort_basis, found_at_a_check, parts_from_check_before_to_finding, parts_from_check_before_to_finding_at_the_realised_rate,
               quantity_affected, quantity_sorted, quantity_rejected, sorted_over_parts_at_risk,
               booked_to_the_sorting_labor_code, sorting_hours_booked, sorting_hours_estimated_from_run_hours, sorting_hours_booked_or_estimated,
               sorting_cost_booked, sorting_cost_booked_or_estimated
        from marts.mart_sorting_events where sort_year = ? order by sort_started""", [year])


def sorting_summary():
    """Sorting events by year: how many trace to a die event between two checks, quantity, hours and cost."""
    d = query("select * from marts.mart_sorting_events order by sort_started")
    rows = []
    for year, g in d.groupby("sort_year", sort=True):
        k = int((g["traced_to"] == "die event between two checks").sum()); lo, hi = wilson(k, len(g))
        press = g[g["detected_at"] != "customer"]
        booked = int(g["booked_to_the_sorting_labor_code"].sum())
        rows.append({"year": int(year), "sorting_events": len(g), "traced_to_a_die_event_between_two_checks": k, "share_traced": k / len(g), "share_low": lo, "share_high": hi,
                     "followed_a_customer_complaint": int((g["traced_to"] == "customer complaint").sum()),
                     "quantity_sorted": int(g["quantity_sorted"].sum()), "quantity_sorted_median": float(g["quantity_sorted"].median()),
                     "quantity_sorted_min": int(g["quantity_sorted"].min()), "quantity_sorted_max": int(g["quantity_sorted"].max()),
                     "quantity_rejected": int(g["quantity_rejected"].sum()),
                     "parts_at_risk_median": float(press["parts_from_check_before_to_finding"].median()), "sorted_over_parts_at_risk_median": float(press["sorted_over_parts_at_risk"].median()),
                     "minutes_from_check_before_median": float(press["minutes_from_check_before_to_finding"].median()),
                     "events_booked_to_the_sorting_labor_code": booked, "share_booked": booked / len(g),
                     "hours_booked": float(g["sorting_hours_booked"].sum()), "hours_estimated_from_run_hours": float(g["sorting_hours_estimated_from_run_hours"].sum()),
                     "hours_booked_or_estimated": float(g["sorting_hours_booked_or_estimated"].sum()),
                     "cost_booked": float(g["sorting_cost_booked"].sum()), "cost_booked_or_estimated": float(g["sorting_cost_booked_or_estimated"].sum()),
                     "share_of_hours_booked": float(g["sorting_hours_booked"].sum() / g["sorting_hours_booked_or_estimated"].sum())})
    return pd.DataFrame(rows)


def sorting_by_basis(years=(2023, 2024)):
    """Sorting events found at the press, by the basis of the sort: from a logged die-protection fault, or back to the
    check before (in-house, or by the sorting service)."""
    return query("""
        select sort_basis, count(*) as events,
               median(quantity_sorted) as quantity_sorted_median, max(quantity_sorted) as quantity_sorted_max,
               sum(quantity_sorted)::bigint as quantity_sorted, sum(quantity_rejected)::bigint as quantity_rejected,
               sum(quantity_rejected) * 1.0 / sum(quantity_sorted) as rejected_share,
               median(minutes_from_check_before_to_finding) as minutes_from_check_before_median,
               median(parts_from_check_before_to_finding) as parts_since_check_before_at_run_speed_median,
               median(parts_from_check_before_to_finding_at_the_realised_rate) as parts_since_check_before_at_realised_rate_median,
               median(quantity_affected / nullif(parts_from_check_before_to_finding_at_the_realised_rate, 0)) as nonconformance_quantity_over_parts_since_check_before,
               sum(sorting_hours_booked_or_estimated) as hours_booked_or_estimated, sum(sorting_cost_booked_or_estimated) as cost_booked_or_estimated
        from marts.mart_sorting_events
        where detected_at <> 'customer' and sort_year in (select unnest(?))
        group by 1 order by 1""", [list(years)])


def stroke_rates():
    """The realised share of run speed by press."""
    return query("select press_id, runs, realised_share_of_run_speed, realised_share_of_run_speed_pooled from intermediate.int_press_stroke_rate order by 1")


def findings_and_checks(years=(2023, 2024)):
    """Findings at the press: made at a check or between checks, and the interval from the check before, by the plan's frequency."""
    return query("""
        with e as (
            select m.*, (select min(c.frequency_minutes) from staging.stg_spc__characteristics c where c.part_id = m.part_id and c.data_type = 'variable') as plan_frequency_minutes
            from marts.mart_sorting_events m where m.detected_at <> 'customer' and m.sort_year in (select unnest(?)))
        select found_at_a_check, plan_frequency_minutes, count(*) as events,
               median(minutes_from_check_before_to_finding) as minutes_median, min(minutes_from_check_before_to_finding) as minutes_min, max(minutes_from_check_before_to_finding) as minutes_max,
               count(*) filter (where found_at_a_check and minutes_from_check_before_to_finding > 1.5 * plan_frequency_minutes) as intervals_over_one_and_a_half_times_the_plan
        from e group by 1, 2 order by 1, 2""", [list(years)])


def trace_interval():
    """Days from a finding at a press check to the die-log entry it is traced to."""
    return query("""select count(*) as events, median(days_from_finding_to_die_log) as median_days, max(days_from_finding_to_die_log) as longest_days
                    from marts.mart_sorting_events where traced_to = 'die event between two checks'""")


def accounting_sorting(year=BASELINE_YEAR):
    """The sorting lines accounting booked in the year, beside the events."""
    return query("""select category, count(*) as lines, sum(amount) as amount, sum(hours) as hours
                    from staging.stg_accounting__quality_cost_lines
                    where period like ? and category in ('sorting labor', 'third-party sorting') group by 1 order by 1""", [f"{year}%"])


def compute():
    return {"risk_window": risk_window(), "sorting_events": sorting_events(), "sorting_summary": sorting_summary(), "sorting_by_basis": sorting_by_basis(), "findings_and_checks": findings_and_checks(),
            "trace_interval": trace_interval(), "stroke_rates": stroke_rates(), "accounting_sorting": accounting_sorting()}


if __name__ == "__main__":
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60)
    for name, table in compute().items():
        print(f"\n== {name}\n{table.to_string(index=False)}")
