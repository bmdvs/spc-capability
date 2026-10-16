"""Expected rule 1 signals on the chart of coil-change means, by Monte Carlo on the record's lot structure.

Each formed characteristic plots one point per coil: the first coil-change subgroup measured on it (10 pieces, before
centring). From 6 coils the chart carries limits from all coils on record, widened to a prediction interval for one
new coil (t on n - 1 degrees of freedom at the three-sigma probability, times the square root of 1 + 1/n, over 3); from
20 coils it takes three-sigma limits from the previous 20.

A coil-change mean is a lot effect, a coil effect within the lot and the measurement of a 10-piece mean:
- the lot share of the coil variance is estimated from the coils' certificate readings: for each formed characteristic,
  the coil means predicted from certificate thickness and hardness are split by coil lot (one-way random effects, method
  of moments), and the median share across characteristics is taken;
- the share of a coil-change mean's variance that is measurement is the within-subgroup variance of a 10-piece mean
  over the variance of the means, from the characteristic's incoming coil share (the plant median where it has none).
Each point is replicated on the lots its coils actually came from, so coils sharing a lot share an effect. The rate at
a point is the share of replicates beyond the limits; the expectation by count averages the points with that many coils
on record.
"""
import numpy as np
import pandas as pd
from scipy import stats

from analytics.data import query

SEED = 20260630
REPLICATES = 4000
MIN_COILS, WINDOW = 6, 20
ALPHA = 0.0027


def limit_factor(n):
    """Multiplier on the sample standard deviation of n coil means giving the limit distance for one new coil."""
    if n >= WINDOW:
        return 3.0
    return float(stats.t.ppf(1 - ALPHA / 2, n - 1) * np.sqrt(1 + 1 / n))


def one_way_share(values, groups):
    """Between-group share of variance by one-way random effects, method of moments (unbalanced)."""
    df = pd.DataFrame({"v": values, "g": groups})
    k = df["g"].nunique(); n = len(df)
    if k < 2 or n <= k:
        return np.nan
    ni = df.groupby("g").size().values
    gm = df.groupby("g")["v"].mean(); grand = df["v"].mean()
    ssb = float((df.groupby("g").size() * (gm - grand) ** 2).sum()); ssw = float(((df["v"] - df["g"].map(gm)) ** 2).sum())
    msb, msw = ssb / (k - 1), ssw / (n - k)
    n0 = (n - (ni ** 2).sum() / n) / (k - 1)
    sb = max((msb - msw) / n0, 0.0)
    return sb / (sb + msw) if sb + msw > 0 else np.nan


def lot_share():
    """Median lot share of the certificate-predicted coil effect across formed characteristics, and the count."""
    fit = query("select characteristic_id, per_mm_thickness, per_hrb from marts.mart_coil_fit order by characteristic_id")
    pts = query("""select characteristic_id, coil_id, coil_lot, certificate_thickness_mm, certificate_hardness_hrb
                   from marts.mart_coil_change_points where charted_point and certificate_thickness_mm is not null order by characteristic_id, sample_time""")
    shares = []
    for _, f in fit.iterrows():
        g = pts[pts["characteristic_id"] == f.characteristic_id]
        pred = f.per_mm_thickness * g["certificate_thickness_mm"] + f.per_hrb * g["certificate_hardness_hrb"]
        s = one_way_share(pred.values, g["coil_lot"].values)
        if s == s:
            shares.append(s)
    return float(np.median(shares)), len(shares)


def expectation():
    """Per-point expected rate, the table by coils on record, and the lot and measurement shares used."""
    lam, n_chars = lot_share()
    vc = query("select characteristic_id, incoming_coil_share from marts.mart_variance_components where incoming_coil_share is not null order by characteristic_id")
    noise_of = {}
    for _, r in vc.iterrows():
        s = float(r.incoming_coil_share); ratio = s / (1 - s) if s < 1 else np.inf
        noise_of[r.characteristic_id] = 0.1 / (ratio + 0.1)
    noise_default = float(np.median(list(noise_of.values())))
    pts = query("""select characteristic_id, subgroup_id, sample_time, coil_id, coil_lot, coils_on_record, alarm_rule_1_coil_change
                   from marts.mart_coil_change_points where charted_point order by characteristic_id, sample_time, subgroup_id""")
    rng = np.random.default_rng(SEED)
    rows = []
    for cid, g in pts.groupby("characteristic_id", sort=True):
        g = g.reset_index(drop=True)
        nu = noise_of.get(cid, noise_default)
        lots = g["coil_lot"].fillna(g["coil_id"]).values
        for i in range(MIN_COILS, len(g)):
            w = min(i, WINDOW); idx = np.arange(i - w, i + 1)
            lab = pd.factorize(lots[idx])[0]
            n_lots = lab.max() + 1
            L = rng.standard_normal((REPLICATES, n_lots))[:, lab]
            E = rng.standard_normal((REPLICATES, len(idx)))
            M = rng.standard_normal((REPLICATES, len(idx)))
            x = np.sqrt(1 - nu) * (np.sqrt(lam) * L + np.sqrt(1 - lam) * E) + np.sqrt(nu) * M
            hist, new = x[:, :-1], x[:, -1]
            c, s = hist.mean(1), hist.std(1, ddof=1)
            rate = float((np.abs(new - c) > limit_factor(w) * s).mean())
            rows.append({"characteristic_id": cid, "subgroup_id": g.at[i, "subgroup_id"], "coils_on_record": int(g.at[i, "coils_on_record"]),
                         "expected_rate": rate, "observed_signal": bool(g.at[i, "alarm_rule_1_coil_change"])})
    p = pd.DataFrame(rows)
    p["count"] = p["coils_on_record"].clip(upper=WINDOW)
    table = p.groupby("count").agg(points=("subgroup_id", "count"), expected_per_100=("expected_rate", lambda s: 100 * s.mean()),
                                   observed_signals=("observed_signal", "sum")).reset_index()
    table["observed_per_100"] = 100 * table["observed_signals"] / table["points"]
    return {"points": p, "table": table, "lot_share": lam, "lot_share_characteristics": n_chars, "measurement_share_median": noise_default}
