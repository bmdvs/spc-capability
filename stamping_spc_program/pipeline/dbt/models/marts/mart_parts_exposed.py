"""Parts exposed per punch failure, on the per-stroke charts and under an hourly check. Grain: one row per per-stroke
stop with a punch found chipped whose strokes the historian keeps. A worn punch has no single onset and is left out.

On the per-stroke charts: the strokes from the estimated onset of the failure to the stop. The onset is the single
change in the series watched by the chart that stopped the press. On the EWMA of the total it is the single step that best
splits the strokes before the stop (least squares). On a channel share it is the earliest stroke from which every stroke to
the stop lies two sigmas or more from the share's level over the first 200 strokes of the window, on the side of the stop
stroke (the least-squares step where the stop stroke itself is within two sigmas); the channel with the larger departure
is taken. The shift of the total and the largest shift of a channel's
share at the onset are given beside it. Under an hourly check: the parts made at the run's stroke
rate in up to an hour, and half that on average, computed from the run speed and the press's realised share of it.
"""
import numpy as np
import pandas as pd


def best_step(y):
    """Index of the least-squares single step in y, and the step size in units of the series' sigma before it."""
    n = len(y)
    if n < 20:
        return None, 0.0
    c = np.cumsum(y); csq = np.cumsum(y * y); tot = c[-1]; best, k_best = np.inf, None
    for k in range(10, n):
        mean_before = c[k - 1] / k; mean_after = (tot - c[k - 1]) / (n - k)
        sse = (csq[k - 1] - k * mean_before * mean_before) + (csq[-1] - csq[k - 1] - (n - k) * mean_after * mean_after)
        if sse < best:
            best, k_best = sse, k
    sd = float(np.std(y[:k_best], ddof=1)) or 1.0
    return k_best, abs(float(y[k_best:].mean() - y[:k_best].mean())) / sd


def sustained_departure(y, ref=200, k=2.0):
    """Index of the earliest stroke from which every stroke to the stop lies at least k sigmas from the level of the
    first `ref` strokes, on the side of the stop stroke; None when the stop stroke itself is within k sigmas."""
    m0, s0 = float(np.mean(y[:ref])), float(np.std(y[:ref], ddof=1)) or 1.0
    d = (y - m0) / s0; side = 1.0 if d[-1] > 0 else -1.0
    if side * d[-1] < k:
        return None, 0.0
    i = len(y) - 1
    while i > ref and side * d[i - 1] >= k:
        i -= 1
    return i, abs(float(np.mean(d[i:])))


def model(dbt, session):
    dbt.config(materialized="table")
    stops = dbt.ref("mart_per_stroke_stops").df()
    batch = stops["export_batch_id"].iloc[0]
    stops = stops[stops["strokes_kept"] & stops["finding_class"].eq("chipped punch")]
    st = dbt.ref("mart_per_stroke_stop_strokes").df()
    rate = dbt.ref("int_press_stroke_rate").df().set_index("press_id")["realised_share_of_run_speed"]
    rows = []
    for s in stops.sort_values("fault_event_id").itertuples():
        g = st[st["fault_event_id"] == s.fault_event_id].sort_values("stroke_no")
        if len(g) < 20:
            continue
        cand = []
        series = {"EWMA on the total": ("total_kn",), "channel share": ("share_ch1", "share_ch2", "share_ch3", "share_ch4")}.get(s.chart, ("total_kn", "share_ch1", "share_ch2", "share_ch3", "share_ch4"))
        for col in series:
            if g[col].isna().all():
                continue
            y = g[col].values.astype(float)
            k, size = sustained_departure(y) if s.chart == "channel share" else best_step(y)
            if k is None:
                k, size = best_step(y)
            if k is not None:
                cand.append((size, k, col))
        size, k, col = max(cand)
        exposed = int(len(g) - 1 - k)
        tot = g["total_kn"].values.astype(float)
        share_pts = max(abs(float(g[c][k:].mean() - g[c][:k].mean())) * 100 for c in ("share_ch1", "share_ch2", "share_ch3", "share_ch4"))
        spm = float(s.run_speed_spm) * float(rate.get(s.press_id, 1.0))
        rows.append({"fault_event_id": s.fault_event_id, "press_id": s.press_id, "press_group": s.press_group, "run_id": s.run_id, "die_id": s.die_id,
                     "stopped_at": s.stopped_at, "chart": s.chart, "finding_class": s.finding_class, "in_quarter": bool(s.in_quarter),
                     "onset_series": col, "onset_step_sigma": size, "total_shift_at_onset": float(tot[k:].mean() / tot[:k].mean() - 1),
                     "largest_channel_share_shift_points": share_pts, "strokes_exposed_per_stroke_charts": exposed,
                     "parts_exposed_per_stroke_charts": exposed * int(s.parts_per_stroke),
                     "strokes_per_minute_realised": spm, "parts_per_stroke": int(s.parts_per_stroke),
                     "parts_exposed_hourly_check_up_to": spm * 60 * int(s.parts_per_stroke), "parts_exposed_hourly_check_average": spm * 30 * int(s.parts_per_stroke)})
    out = pd.DataFrame(rows)
    out["export_batch_id"] = batch
    return out
