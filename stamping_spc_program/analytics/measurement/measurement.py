"""Measurement systems: gauge R&R on the three check fixtures from the study worksheets, the measurement share of the
production variance, attribute agreement on the burr check, and the readings by entry method (last digit, mis-keyed
readings, readings at the limit), with the gauge calibration status of the subgroups."""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from analytics.data import ROOT, query
from analytics.stats import fleiss_kappa, grr_anova, wilson

SEED = 20250104
R5 = ["r1", "r2", "r3", "r4", "r5"]
STUDIES = ROOT / "data" / "raw" / "studies"
BASELINE_YEAR = 2025


READINGS_CTE = f"""
        with raw as (
            select h.characteristic_id, h.entry_method, h.usl, h.lsl, h.nominal, h.tolerance_width, unnest([h.r1, h.r2, h.r3, h.r4, h.r5]) as reading
            from intermediate.int_characteristic_history h
            where h.r1 is not null and h.data_type = 'variable' and h.characteristic_type not in ('burr height', 'flatness')
              and ((h.entry_method <> 'gauge-connected' and year(h.sample_time) = {BASELINE_YEAR}) or (h.entry_method = 'gauge-connected' and h.is_pilot_press and h.sample_time >= date '2026-04-01'))),
        -- the step a characteristic is read to, from its own readings: the coarsest of the steps below that 99% of them sit on
        step as (
            select characteristic_id,
                   case when avg((abs(reading / 1.0 - round(reading / 1.0)) < 1e-6)::int) >= 0.99 then 1.0
                        when avg((abs(reading / 0.5 - round(reading / 0.5)) < 1e-6)::int) >= 0.99 then 0.5
                        when avg((abs(reading / 0.1 - round(reading / 0.1)) < 1e-6)::int) >= 0.99 then 0.1
                        when avg((abs(reading / 0.05 - round(reading / 0.05)) < 1e-6)::int) >= 0.99 then 0.05
                        when avg((abs(reading / 0.01 - round(reading / 0.01)) < 1e-6)::int) >= 0.99 then 0.01
                        when avg((abs(reading / 0.005 - round(reading / 0.005)) < 1e-6)::int) >= 0.99 then 0.005
                        else 0.001 end as resolution
            from raw group by 1),
        h as (select raw.*, step.resolution from raw join step using (characteristic_id)),
"""


def _sheet(name):
    return pd.read_csv(STUDIES / name, comment="#")


def gauge_rr():
    """Each fixture study worksheet by the ANOVA method, with the figure the shop recorded beside it."""
    rec = query("""select s.study_id, s.gauge_id, s.characteristic_id, s."date" as study_date, s.trigger, s.pct_grr_of_tolerance, s.ndc, s.worksheet_file, c.usl - c.lsl as tolerance
                   from staging.stg_calibration__gauge_studies s join staging.stg_spc__characteristics c using (characteristic_id)
                   where s.worksheet_file is not null order by s.gauge_id, s."date" """)
    rows, anovas = [], {}
    for r in rec.itertuples():
        if not (STUDIES / r.worksheet_file).exists():
            continue
        a = grr_anova(_sheet(r.worksheet_file), float(r.tolerance))
        stage = "rebuilt" if "rebuilt" in r.worksheet_file else "redesign" if "redesign" in r.worksheet_file else "PPAP"
        anovas[(r.gauge_id, stage)] = a
        rows.append({"fixture": r.gauge_id, "study": stage, "study_date": r.study_date, "characteristic_id": r.characteristic_id, "tolerance_mm": float(r.tolerance),
                     "recorded_pct_tolerance": float(r.pct_grr_of_tolerance), "recorded_ndc": int(r.ndc),
                     "pct_tolerance": a["pct_tolerance"], "pct_study_variation": a["pct_study_variation"], "ndc": a["ndc"],
                     "repeatability_sd_mm": np.sqrt(a["repeatability_var"]), "reproducibility_sd_mm": np.sqrt(a["reproducibility_var"]), "part_sd_mm": np.sqrt(a["part_var"]),
                     "reproducibility_share_of_grr": a["reproducibility_var"] / a["grr_var"], "interaction_p": a["interaction_p"], "interaction_pooled": a["interaction_pooled"]})
    return pd.DataFrame(rows), anovas


REWORKED_FROM = {"F-20417": "2025-03-01", "F-31102": "2025-06-01"}          # the first full month after each fixture's indicators were replaced and nests reworked


def measurement_share(studies, anovas):
    """The redesign study's gauge variance against the variance of the production readings on the study characteristic:
    on the months of the baseline year after the fixture's rework, the state the study measured, with the whole year beside it."""
    rows = []
    for r in studies[studies["study"] == "redesign"].itertuples():
        v = query("""select sample_time, r1, r2, r3, r4, r5 from intermediate.int_characteristic_history
                     where characteristic_id = ? and year(sample_time) = ? and implausible_readings = 0 and r1 is not null and not after_redesign
                     order by sample_time, subgroup_id""", [r.characteristic_id, BASELINE_YEAR])
        g = anovas[(r.fixture, "redesign")]["grr_var"]
        year = v[R5].values.astype(float).ravel()
        start = REWORKED_FROM.get(r.fixture)
        after = v[v["sample_time"] >= start][R5].values.astype(float).ravel() if start else year
        rows.append({"fixture": r.fixture, "characteristic_id": r.characteristic_id, "period": f"from {start[:7]}" if start else "all of the year",
                     "readings": len(after), "production_sd_mm": float(after.std(ddof=1)), "gauge_sd_mm": float(np.sqrt(g)), "measurement_share_of_variance": g / float(after.var(ddof=1)),
                     "readings_whole_year": len(year), "measurement_share_whole_year": g / float(year.var(ddof=1))})
    return pd.DataFrame(rows)


def reading_steps():
    """Characteristics by the step their readings sit on."""
    return query(READINGS_CTE + """
        s as (select distinct characteristic_id, resolution from h)
        select resolution as reading_step, count(*) as characteristics from s group by 1 order by 1 desc""")


def last_digits():
    """The share of readings ending in each digit, by entry method."""
    return query(READINGS_CTE + """
        k as (select entry_method, cast(round(reading / resolution) as bigint) % 10 as last_digit from h)
        select entry_method, last_digit, count(*) as readings, count(*) * 1.0 / sum(count(*)) over (partition by entry_method) as share from k group by 1, 2 order by 1, 2""")


def attribute_agreement():
    """The burr check against the limit samples at the redesign and after the new limit samples."""
    rows, by_op = [], []
    for stage, name in (("at the redesign", "attribute_burr_redesign.csv"), ("after new limit samples", "attribute_burr_after.csv")):
        d = _sheet(name); d["call"] = (d["call"] == "accept").astype(int); d["reference"] = (d["reference"] == "accept").astype(int)
        w = d.pivot_table(index=["operator", "part"], columns="trial", values="call")
        within_k = int((w.nunique(axis=1) == 1).sum()); within_n = len(w)
        allc = d.pivot_table(index="part", columns=["operator", "trial"], values="call")
        all_k = int((allc.nunique(axis=1) == 1).sum()); parts = len(allc)
        ref = d.groupby("part")["reference"].first()
        ok = d["call"] == d["part"].map(ref)
        ops = sorted(d["operator"].unique()); pair = []
        for i, a in enumerate(ops):
            for b in ops[i + 1:]:
                for ta in allc[a].columns:
                    for tb in allc[b].columns:
                        pair.append(float((allc[a][ta] == allc[b][tb]).mean()))
        kappa = fleiss_kappa(allc.values)
        r = np.random.default_rng([SEED, len(rows)])
        boot = [fleiss_kappa(allc.values[r.integers(0, parts, parts)]) for _ in range(2000)]
        rows.append({"study": stage, "operators": len(ops), "parts": parts, "trials": int(d["trial"].nunique()), "calls": len(d),
                     "within_operator": within_k / within_n, "within_low": wilson(within_k, within_n)[0], "within_high": wilson(within_k, within_n)[1],
                     "all_operators_agree": all_k / parts, "all_low": wilson(all_k, parts)[0], "all_high": wilson(all_k, parts)[1],
                     "pairs_of_operators_agree": float(np.mean(pair)),
                     "against_reference": float(ok.mean()), "reference_low": wilson(int(ok.sum()), len(ok))[0], "reference_high": wilson(int(ok.sum()), len(ok))[1],
                     "fleiss_kappa": kappa, "kappa_low": float(np.percentile(boot, 2.5)), "kappa_high": float(np.percentile(boot, 97.5)),
                     "reference_reject_rate": float(1 - ref.mean())})
        for op, g in d.groupby("operator"):
            by_op.append({"study": stage, "operator": op, "reject_rate": float(1 - g["call"].mean()), "reference_reject_rate": float(1 - ref.mean()),
                          "against_reference": float((g["call"] == g["part"].map(ref)).mean())})
    return pd.DataFrame(rows), pd.DataFrame(by_op)


def entry_methods():
    """Readings by entry method: the last digit, mis-keyed readings, and readings one step inside against one step outside a limit."""
    d = query(f"""
        with raw as (
            select h.characteristic_id, h.entry_method, h.usl, h.lsl, h.nominal, h.tolerance_width, unnest([h.r1, h.r2, h.r3, h.r4, h.r5]) as reading
            from intermediate.int_characteristic_history h
            where h.r1 is not null and h.data_type = 'variable' and h.characteristic_type not in ('burr height', 'flatness')
              and ((h.entry_method <> 'gauge-connected' and year(h.sample_time) = {BASELINE_YEAR}) or (h.entry_method = 'gauge-connected' and h.is_pilot_press and h.sample_time >= date '2026-04-01'))),
        -- the step a characteristic is read to, from its own readings: the coarsest of the steps below that 99% of them sit on
        step as (
            select characteristic_id,
                   case when avg((abs(reading / 1.0 - round(reading / 1.0)) < 1e-6)::int) >= 0.99 then 1.0
                        when avg((abs(reading / 0.5 - round(reading / 0.5)) < 1e-6)::int) >= 0.99 then 0.5
                        when avg((abs(reading / 0.1 - round(reading / 0.1)) < 1e-6)::int) >= 0.99 then 0.1
                        when avg((abs(reading / 0.05 - round(reading / 0.05)) < 1e-6)::int) >= 0.99 then 0.05
                        when avg((abs(reading / 0.01 - round(reading / 0.01)) < 1e-6)::int) >= 0.99 then 0.01
                        when avg((abs(reading / 0.005 - round(reading / 0.005)) < 1e-6)::int) >= 0.99 then 0.005
                        else 0.001 end as resolution
            from raw group by 1),
        h as (select raw.*, step.resolution from raw join step using (characteristic_id)),
        k as (
            select *, cast(round(reading / resolution) as bigint) % 10 as last_digit, resolution as step,
                   abs(reading - nominal) > 5 * tolerance_width as set_aside,
                   round((reading - usl) / resolution) as steps_above_usl, round((lsl - reading) / resolution) as steps_below_lsl
            from h)
        select entry_method, count(*) as readings,
               count(*) filter (where last_digit in (0, 5)) as ending_0_or_5,
               count(*) filter (where set_aside) as set_aside,
               count(*) filter (where (steps_above_usl between -1 and 0) or (steps_below_lsl between -1 and 0)) as at_or_one_step_inside_a_limit,
               count(*) filter (where (steps_above_usl between 1 and 2) or (steps_below_lsl between 1 and 2)) as one_or_two_steps_outside_a_limit,
               list(last_digit) as digits
        from k group by 1 order by 1""")
    rows = []
    for r in d.itertuples():
        counts = np.bincount(np.asarray(r.digits, dtype=int), minlength=10)[:10]
        chi2 = float(((counts - counts.mean()) ** 2 / counts.mean()).sum())
        rows.append({"entry_method": r.entry_method, "readings": int(r.readings), "ending_0_or_5": int(r.ending_0_or_5), "times_the_uniform_expectation": r.ending_0_or_5 / r.readings / 0.2,
                     "chi_square_last_digit": chi2, "p_last_digit": float(stats.chi2.sf(chi2, 9)),
                     "set_aside_by_the_plausibility_rule": int(r.set_aside), "set_aside_share": r.set_aside / r.readings,
                     "at_or_one_step_inside_a_limit": int(r.at_or_one_step_inside_a_limit), "one_or_two_steps_outside_a_limit": int(r.one_or_two_steps_outside_a_limit),
                     "inside_over_outside": r.at_or_one_step_inside_a_limit / max(r.one_or_two_steps_outside_a_limit, 1)})
    return pd.DataFrame(rows)


def readings_at_the_limit():
    """Readings by their distance from the nearer specification limit, in steps of the characteristic's resolution, by entry
    method. Step 0 is at the limit, negative steps are inside it and positive steps outside."""
    return query(READINGS_CTE + """
        s as (select entry_method, case when reading >= nominal then round((reading - usl) / resolution) else round((lsl - reading) / resolution) end as step from h)
        select entry_method, cast(step as integer) as steps_from_the_limit, count(*) as readings from s where step between -4 and 4 group by 1, 2 order by 1, 2""")


def gauge_status():
    """Subgroups of the baseline year by the calibration status of the gauge they carry."""
    return query(f"""
        select count(*) as subgroups,
               count(*) filter (where gauge_out_of_service) as on_a_gauge_out_of_service, avg(gauge_out_of_service::int) as share_out_of_service,
               count(*) filter (where gauge_past_due) as on_a_gauge_past_due, avg(gauge_past_due::int) as share_past_due,
               (select count(*) from staging.stg_calibration__gauges where status = 'lost') as gauges_recorded_as_lost,
               (select count(*) from staging.stg_spc__characteristics c join staging.stg_calibration__gauges g using (gauge_id) where g.status = 'lost') as characteristics_assigned_to_a_lost_gauge,
               count(*) filter (where gauge_recorded_as_lost) as subgroups_carrying_a_lost_gauge
        from intermediate.int_characteristic_history where year(sample_time) = {BASELINE_YEAR}""")


def compute():
    studies, anovas = gauge_rr()
    agreement, by_operator = attribute_agreement()
    return {"gauge_rr": studies, "anova_tables": anovas, "measurement_share": measurement_share(studies, anovas), "attribute_agreement": agreement,
            "attribute_by_operator": by_operator, "entry_methods": entry_methods(), "readings_at_the_limit": readings_at_the_limit(), "reading_steps": reading_steps(), "last_digits": last_digits(),
            "gauge_status": gauge_status()}


if __name__ == "__main__":
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 60)
    for name, table in compute().items():
        if name != "anova_tables":
            print(f"\n== {name}\n{table.round(4).to_string(index=False)}")
