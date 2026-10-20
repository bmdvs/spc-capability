"""Statistical routines shared by the analyses."""
import numpy as np
from scipy import optimize, sparse, stats
from scipy.sparse.linalg import spsolve

XBAR_FACTOR, RANGE_FACTOR, SIGMA_FACTOR = 0.577, 2.114, 2.326          # X-bar and R constants for subgroups of five


def wilson(k, n, level=0.95):
    """Wilson score interval for a proportion."""
    if n == 0:
        return (np.nan, np.nan)
    z = stats.norm.ppf(1 - (1 - level) / 2); p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n); h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)


def _zone(z):
    """Zone of a standardised point: 1, 2, 3 for within one, two and three sigma, signed by side; 4 beyond three sigma."""
    a = abs(z)
    return int(np.sign(z) or 1) * (1 if a <= 1 else 2 if a <= 2 else 3 if a <= 3 else 4)


def _signals(hist, run, rules):
    """Whether the newest point completes a signal. hist: the last zones, newest last; run: points in a row on its side."""
    z = hist[-1]; s = 1 if z > 0 else -1
    if 1 in rules and abs(z) == 4:
        return True
    if 2 in rules and abs(z) >= 3 and sum(1 for x in hist[-3:] if x * s >= 3) >= 2:
        return True
    if 3 in rules and abs(z) >= 2 and sum(1 for x in hist[-5:] if x * s >= 2) >= 4:
        return True
    if 4 in rules and run >= 8:
        return True
    return False


def arl_shewhart(mean, sd, rules=(1,), limit_width=1.0, centre=0.0):
    """Average run length of a means chart with Western Electric rules, by the Markov chain method.

    The plotted point is normal with the given mean and sd, in units of the chart's sigma of the mean when
    limit_width is 1. limit_width scales the chart's own sigma and centre moves its centre line, for limits that
    were set on another basis. Rules: 1 one point beyond three sigma; 2 two of three beyond two sigma on a side;
    3 four of five beyond one sigma on a side; 4 eight in a row on a side. A point beyond three sigma is kept in the
    history for the other rules when rule 1 is not in use."""
    edges = centre + limit_width * np.array([-3, -2, -1, 0, 1, 2, 3], dtype=float)
    cdf = stats.norm.cdf(edges, loc=mean, scale=sd)
    p = np.diff(np.concatenate([[0.0], cdf, [1.0]]))          # beyond -3, the six zones, beyond +3
    zones = [-4, -3, -2, -1, 1, 2, 3, 4]
    keep = 4 if 3 in rules else 2 if 2 in rules else 0
    start = ((), 0, 0)
    index = {start: 0}; order = [start]; rows, cols, vals = [], [], []
    i = 0
    while i < len(order):
        hist, side, run = order[i]
        for z, pz in zip(zones, p):
            if pz <= 0:
                continue
            s = 1 if z > 0 else -1
            nrun = min(run + 1, 8) if s == side else 1
            nh = (hist + (z,))
            if _signals(nh, nrun, rules):
                continue
            nh = nh[-keep:] if keep else ()
            state = (nh, s if 4 in rules else 0, nrun if 4 in rules else 0)
            if state not in index:
                index[state] = len(order); order.append(state)
            rows.append(i); cols.append(index[state]); vals.append(pz)
        i += 1
    n = len(order)
    q = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
    return float(spsolve((sparse.identity(n, format="csc") - q.tocsc()), np.ones(n))[0])


def reml_nested(means, groups, sigma_within, n=5):
    """Variance components of a nested model, coil within characteristic and subgroup within coil, by REML.

    The within-subgroup component is the pooled within-subgroup variance (balanced, n readings a subgroup). The other
    two come from the REML likelihood of the subgroup means as a one-way random-effects layout with unequal numbers
    of subgroups a coil. Returns the three components as variances: between coils, between subgroups within a coil,
    within subgroups."""
    means = np.asarray(means, dtype=float)
    _, inv = np.unique(np.asarray(groups), return_inverse=True)
    ni = np.bincount(inv).astype(float); gm = np.bincount(inv, weights=means) / ni
    ss = float(((means - gm[inv]) ** 2).sum())
    floor = sigma_within ** 2 / n

    def neg(theta):
        tau2 = floor + np.exp(theta[0]); c2 = np.exp(theta[1])
        d = tau2 + ni * c2; w = ni / d
        mu = (w * gm).sum() / w.sum()
        return 0.5 * (((ni - 1) * np.log(tau2)).sum() + np.log(d).sum() + ss / tau2 + (w * (gm - mu) ** 2).sum() + np.log(w.sum()))

    v0 = max(means.var(ddof=1), 1e-12)
    best = None
    for a, b in ((0.3, 0.5), (0.05, 0.9), (0.6, 0.1)):
        r = optimize.minimize(neg, [np.log(max(a * v0, 1e-14)), np.log(max(b * v0, 1e-14))], method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-10, "maxiter": 4000})
        if best is None or r.fun < best.fun:
            best = r
    between_subgroups = float(np.exp(best.x[0])); between_coils = float(np.exp(best.x[1]))
    if between_coils < 1e-10 * v0:
        between_coils = 0.0
    if between_subgroups < 1e-10 * v0:
        between_subgroups = 0.0
    return between_coils, between_subgroups, float(sigma_within ** 2)


def cpk_interval(cpk, readings, level=0.95):
    """Interval for Cpk by the AIAG approximation (Bissell)."""
    z = stats.norm.ppf(1 - (1 - level) / 2)
    h = z * np.sqrt(1 / (9 * readings) + cpk ** 2 / (2 * (readings - 1)))
    return cpk - h, cpk + h


def anderson_darling_normal(x):
    """Anderson-Darling statistic for normality with the adjustment for estimated mean and sigma, and its p-value."""
    x = np.sort(np.asarray(x, dtype=float)); n = len(x)
    z = np.clip(stats.norm.cdf((x - x.mean()) / x.std(ddof=1)), 1e-12, 1 - 1e-12)
    i = np.arange(1, n + 1)
    a2 = -n - ((2 * i - 1) * (np.log(z) + np.log(1 - z[::-1]))).sum() / n
    a = a2 * (1 + 0.75 / n + 2.25 / n ** 2)
    if a >= 0.6:
        pv = np.exp(1.2937 - 5.709 * a + 0.0186 * a * a)
    elif a >= 0.34:
        pv = np.exp(0.9177 - 4.279 * a - 1.38 * a * a)
    elif a >= 0.2:
        pv = 1 - np.exp(-8.318 + 42.796 * a - 59.938 * a * a)
    else:
        pv = 1 - np.exp(-13.436 + 101.14 * a - 223.73 * a * a)
    return float(a), float(min(max(pv, 0.0), 1.0))


def grr_anova(df, tolerance):
    """Crossed gauge R&R by the ANOVA method (AIAG MSA 4th edition). df has columns operator, part, trial, value.
    The operator by part interaction is pooled into repeatability when its p-value exceeds 0.25. Returns the ANOVA
    table rows and the variance components with %tolerance at 6 sigma, %study variation and ndc."""
    o, p_, n = df["operator"].nunique(), df["part"].nunique(), df["trial"].nunique()
    g = df["value"].mean()
    ss_o = p_ * n * ((df.groupby("operator")["value"].mean() - g) ** 2).sum()
    ss_p = o * n * ((df.groupby("part")["value"].mean() - g) ** 2).sum()
    cell = df.groupby(["operator", "part"])["value"].transform("mean")
    ss_e = ((df["value"] - cell) ** 2).sum(); ss_t = ((df["value"] - g) ** 2).sum(); ss_op = ss_t - ss_o - ss_p - ss_e
    df_o, df_p, df_op, df_e = o - 1, p_ - 1, (o - 1) * (p_ - 1), o * p_ * (n - 1)
    ms_o, ms_p, ms_op, ms_e = ss_o / df_o, ss_p / df_p, ss_op / df_op, ss_e / df_e
    p_int = float(stats.f.sf(ms_op / ms_e, df_op, df_e))
    pooled = p_int > 0.25
    if pooled:
        ms_r = (ss_e + ss_op) / (df_e + df_op)
        rep = ms_r; inter = 0.0; oper = max((ms_o - ms_r) / (p_ * n), 0.0); part = max((ms_p - ms_r) / (o * n), 0.0)
    else:
        rep = ms_e; inter = max((ms_op - ms_e) / n, 0.0); oper = max((ms_o - ms_op) / (p_ * n), 0.0); part = max((ms_p - ms_op) / (o * n), 0.0)
    repro = oper + inter; grr = rep + repro; total = grr + part
    anova = [("Part", df_p, ss_p, ms_p, ms_p / (ms_e if pooled else ms_op)), ("Operator", df_o, ss_o, ms_o, ms_o / (ms_e if pooled else ms_op)),
             ("Part * Operator", df_op, ss_op, ms_op, ms_op / ms_e), ("Repeatability", df_e, ss_e, ms_e, np.nan), ("Total", o * p_ * n - 1, ss_t, np.nan, np.nan)]
    return {"anova": anova, "interaction_p": p_int, "interaction_pooled": pooled, "repeatability_var": rep, "operator_var": oper, "interaction_var": inter,
            "reproducibility_var": repro, "grr_var": grr, "part_var": part, "total_var": total,
            "pct_tolerance": 6 * np.sqrt(grr) / tolerance * 100, "pct_study_variation": np.sqrt(grr / total) * 100 if total > 0 else np.nan,
            "ndc": int(np.floor(1.41 * np.sqrt(part / grr))) if grr > 0 else None}


def fleiss_kappa(calls):
    """Fleiss' kappa for a table of two-category calls: rows are parts, columns are ratings (0 or 1)."""
    calls = np.asarray(calls); n = calls.shape[1]
    k1 = calls.sum(axis=1); k0 = n - k1
    p_i = (k1 * (k1 - 1) + k0 * (k0 - 1)) / (n * (n - 1))
    pj = np.array([k0.sum(), k1.sum()]) / calls.size
    pe = float((pj ** 2).sum())
    return float((p_i.mean() - pe) / (1 - pe))
