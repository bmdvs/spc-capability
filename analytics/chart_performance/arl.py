"""Run lengths and false-alarm rates of the charts as designed, by the Markov chain method.

Every chart point is standardised on the chart's true sigma of the plotted statistic. Limits estimated from a
baseline enter as a centre offset and a sigma ratio: the centre line lies `centre` true sigmas from the process mean
and the limits are `width` times the true three-sigma distance. The rate expected on a chart with estimated limits
is the per-point signal rate averaged over the distribution of the baseline estimates (normal for the centre,
scaled chi for the sigma), by quadrature.

Conventions, as the SPC software applies the rules:
- rule 1, one point beyond three sigma; rule 2, two of three beyond two sigma on one side, the newest among them;
  rule 3, four of five beyond one sigma on one side, the newest among them; rule 4, eight in a row on one side;
- the range chart (subgroups of five) and the moving-range chart signal on rule 1 only;
- a signal rate counts every point that carries a signal, as the alarm log does.
"""
from functools import lru_cache
from itertools import product

import numpy as np
from scipy import integrate, sparse, stats
from scipy.sparse.linalg import spsolve

from analytics.stats import arl_shewhart

N = 5
D2 = {5: 2.326, 2: 1.128}
D4 = {5: 2.114, 2: 3.267}
RANGE_DF = {5: 3.8}                          # degrees of freedom of the scaled-chi approximation to one range (Patnaik)
EDGES = np.array([-3, -2, -1, 0, 1, 2, 3], dtype=float)


# ── the range of a normal subgroup ─────────────────────────────────────────────

@lru_cache(maxsize=None)
def range_sf(w, n=N):
    """P(range of n standard normal readings > w)."""
    f = lambda x: n * stats.norm.pdf(x) * (stats.norm.cdf(x + w) - stats.norm.cdf(x)) ** (n - 1)
    return 1.0 - float(integrate.quad(f, -9, 9, limit=200)[0])


def range_rate(width=1.0, n=N):
    """Per-subgroup rule 1 rate of the range chart whose upper limit is `width` times D4 times the true mean range."""
    return range_sf(round(float(width * D4[n] * D2[n]), 10), n)


# ── means charts with Western Electric rules ───────────────────────────────────

def zone_probs(shift=0.0, centre=0.0, width=1.0):
    """Probabilities of the eight zones (beyond -3, the six zones, beyond +3) for a point of mean `shift`."""
    cdf = stats.norm.cdf(centre + width * EDGES - shift)
    return np.diff(np.concatenate([[0.0], cdf, [1.0]]))


_CODES = np.array([-4, -3, -2, -1, 1, 2, 3, 4])
_IDX = np.array(list(product(range(8), repeat=5)))                       # every history of the five newest points
_Z = _CODES[_IDX]


@lru_cache(maxsize=None)
def _rule_masks(rules):
    cur = _Z[:, -1]; s = np.where(cur > 0, 1, -1)[:, None]
    a = np.zeros(len(_Z), dtype=bool)
    if 1 in rules:
        a |= np.abs(cur) == 4
    if 2 in rules:
        a |= (np.abs(cur) >= 3) & ((s * _Z[:, -3:] >= 3).sum(1) >= 2)
    if 3 in rules:
        a |= (np.abs(cur) >= 2) & ((s * _Z >= 2).sum(1) >= 4)
    run5 = (s * _Z > 0).all(1) & (4 in rules)
    return a, run5, s[:, 0]


def flag_rate_rules(p, rules=(1, 2, 3, 4)):
    """Stationary per-point probability that a point carries a signal under `rules`, independent points with zone
    probabilities p (zones coded -4..-1, 1..4). Rule 4 needs the eight newest points on one side; the five newest
    are enumerated and the three before them enter through the side probabilities."""
    p = np.asarray(p, dtype=float)
    a, run5, s = _rule_masks(tuple(rules))
    pr = p[_IDX].prod(1)
    q = np.where(s > 0, p[4:].sum(), p[:4].sum())
    return float((pr * a).sum() + (pr * (~a) * run5 * q ** 3).sum())


def arl_rules(shift=0.0, rules=(1, 2, 3, 4), centre=0.0, width=1.0, range_p=0.0):
    """ARL from the start of a means chart under `rules`, with an independent range chart signalling at rate range_p."""
    if range_p <= 0:
        return arl_shewhart(shift, 1.0, rules=rules, limit_width=width, centre=centre)
    # the range chart signals independently each subgroup: scale the means chain's continuation by (1 - range_p)
    edges = centre + width * EDGES
    cdf = stats.norm.cdf(edges, loc=shift, scale=1.0)
    p = np.diff(np.concatenate([[0.0], cdf, [1.0]])) * (1 - range_p)
    return _arl_chain(p, rules)


def _arl_chain(p, rules):
    from analytics.stats import _signals
    zones = [-4, -3, -2, -1, 1, 2, 3, 4]
    keep = 4 if 3 in rules else 2 if 2 in rules else 0
    start = ((), 0, 0); index = {start: 0}; order = [start]; rows, cols, vals = [], [], []
    i = 0
    while i < len(order):
        hist, side, run = order[i]
        for z, pz in zip(zones, p):
            if pz <= 0:
                continue
            s = 1 if z > 0 else -1
            nrun = min(run + 1, 8) if s == side else 1
            nh = hist + (z,)
            if _signals(nh, nrun, rules):
                continue
            nh = nh[-keep:] if keep else ()
            st = (nh, s if 4 in rules else 0, nrun if 4 in rules else 0)
            if st not in index:
                index[st] = len(order); order.append(st)
            rows.append(i); cols.append(index[st]); vals.append(pz)
        i += 1
    n = len(order)
    qm = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
    return float(spsolve(sparse.identity(n, format="csc") - qm.tocsc(), np.ones(n))[0])


# ── three-way charts: individuals on subgroup means, moving range, range ──────

def _grid(lo, hi, m):
    w = (hi - lo) / m
    return lo + w * (np.arange(m) + 0.5), w


def three_way_flag_rate(shift=0.0, centre=0.0, s_ratio=1.0, mr_ratio=1.0, r_ratio=1.0, phi=0.0):
    """Per-point signal rate of a three-way chart: rule 1 on the individuals (limits at three times the estimated
    sigma of the means), rule 1 on the moving range (D4 times the estimated mean moving range) and on the range.
    Points are AR(1) with lag-1 autocorrelation phi in stationary state."""
    ucl, lcl = centre + 3 * s_ratio, centre - 3 * s_ratio
    u = D4[2] * D2[2] * mr_ratio
    x, w = _grid(-8, 8, 1601)
    f_prev = stats.norm.pdf(x) * w
    s_e = np.sqrt(1 - phi ** 2)
    # P(no individuals signal and no moving-range signal) = sum over previous x of P(x_t within limits and |x_t - x_prev| <= u)
    lo = np.maximum(lcl, x - u); hi = np.minimum(ucl, x + u)
    m_t = shift + phi * (x - shift) if phi else shift + 0 * x
    ok = np.where(hi > lo, stats.norm.cdf((hi - m_t) / s_e) - stats.norm.cdf((lo - m_t) / s_e), 0.0)
    p_ind_mr = 1.0 - float((f_prev * ok).sum())
    p_r = range_rate(r_ratio)
    return 1.0 - (1.0 - p_ind_mr) * (1.0 - p_r)


def three_way_arl(shift=0.0, centre=0.0, s_ratio=1.0, mr_ratio=1.0, r_ratio=1.0, phi=0.0, with_moving_range=True, with_range=True, m=241):
    """ARL from the start of a three-way chart, the previous mean carried as a discretised state (Brook and Evans)."""
    ucl, lcl = centre + 3 * s_ratio, centre - 3 * s_ratio
    u = D4[2] * D2[2] * mr_ratio if with_moving_range else np.inf
    x, w = _grid(lcl, ucl, m)
    s_e = np.sqrt(1 - phi ** 2)
    mu = shift + phi * (x[:, None] - shift)
    lo = x[None, :] - w / 2; hi = x[None, :] + w / 2
    P = stats.norm.cdf((hi - mu) / s_e) - stats.norm.cdf((lo - mu) / s_e)
    P = P * (np.abs(x[None, :] - x[:, None]) <= u)
    if with_range:
        P = P * (1 - range_rate(r_ratio))
    arl = np.linalg.solve(np.eye(m) - P, np.ones(m))
    # the first point: from the process's stationary distribution, no moving range
    p0 = stats.norm.cdf((hi[0] - shift)) - stats.norm.cdf((lo[0] - shift))
    if with_range:
        p0 = p0 * (1 - range_rate(r_ratio))
    return float(1 + p0 @ arl)


# ── autocorrelated means: rule 1 and rules 1 to 4 ─────────────────────────────

def arl_ar1_rules(phi, rules=(1,), shift=0.0, per_zone=6):
    """In-control ARL of a means chart under `rules` when consecutive means are AR(1) with lag-1 autocorrelation phi,
    by a chain on the zone history joined with the previous mean discretised within each zone."""
    from analytics.stats import _signals
    edges = np.concatenate([[-3.0], np.linspace(-3, 3, 6 * per_zone + 1)[1:-1], [3.0]])
    bins = np.linspace(-3, 3, 6 * per_zone + 1); mids = (bins[:-1] + bins[1:]) / 2
    zone_of_bin = np.array([int(np.sign(v)) * (int(np.floor(abs(v))) + 1) for v in mids])
    s_e = np.sqrt(1 - phi ** 2)
    keep = 4 if 3 in rules else 2 if 2 in rules else 0

    def step_probs(prev):
        mu = shift + (phi * (prev - shift) if prev is not None else 0.0); sd = s_e if prev is not None else 1.0
        cdf = stats.norm.cdf((bins - mu) / sd)
        return float(cdf[0]), np.diff(cdf), float(1 - cdf[-1])

    start = (None, (), 0, 0); index = {start: 0}; order = [start]; rows, cols, vals = [], [], []
    i = 0
    while i < len(order):
        b, hist, side, run = order[i]
        below, inside, above = step_probs(None if b is None else mids[b])
        outcomes = [(None, -4, below), (None, 4, above)] + [(k, int(zone_of_bin[k]), float(inside[k])) for k in range(len(mids))]
        for nb, z, pz in outcomes:
            if pz <= 1e-15:
                continue
            s = 1 if z > 0 else -1
            nrun = min(run + 1, 8) if s == side else 1
            nh = hist + (z,)
            if _signals(nh, nrun, rules) or nb is None:
                continue
            nh = nh[-keep:] if keep else ()
            st = (nb, nh, s if 4 in rules else 0, nrun if 4 in rules else 0)
            if st not in index:
                index[st] = len(order); order.append(st)
            rows.append(i); cols.append(index[st]); vals.append(pz)
        i += 1
    n = len(order)
    qm = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
    return float(spsolve(sparse.identity(n, format="csc") - qm.tocsc(), np.ones(n))[0])


# ── estimated limits ───────────────────────────────────────────────────────────

def _normal_nodes(k=9):
    x, w = np.polynomial.hermite_e.hermegauss(k)
    return x, w / w.sum()


def _chi_ratio_nodes(df, k=9):
    """Nodes and weights for sqrt(chi2(df) / df), by Gauss-Legendre on its probability scale."""
    u, w = np.polynomial.legendre.leggauss(k)
    pr = (u + 1) / 2
    return np.sqrt(stats.chi2.ppf(pr, df) / df), w / w.sum()


def expected_rate_xbar_r(baseline, rules=(1, 2, 3, 4), with_range=True, k=9):
    """Expected signals per point of an X-bar and R chart whose limits come from `baseline` subgroups of five:
    centre offset normal with variance 1/baseline (in sigmas of the mean), sigma ratio from the average range."""
    cx, cw = _normal_nodes(k); rx, rw = _chi_ratio_nodes(RANGE_DF[N] * baseline, k)
    tot = 0.0
    for c, wc in zip(cx / np.sqrt(baseline), cw):
        for r, wr in zip(rx, rw):
            pm = flag_rate_rules(zone_probs(0.0, c, r), rules)
            pr = range_rate(r) if with_range else 0.0
            tot += wc * wr * (1 - (1 - pm) * (1 - pr))
    return tot


def expected_rate_tool_wear(baseline, rules=(1, 2, 3, 4), with_range=True, k=9):
    """As X-bar and R, about a regression line from `baseline` subgroups: the line's error at a point is taken at twice
    the variance of a mean of `baseline` (the average leverage over an interval), the residual sigma on baseline - 2
    degrees of freedom, the range limit on the average range of the same subgroups."""
    cx, cw = _normal_nodes(k); sx, sw = _chi_ratio_nodes(max(baseline - 2, 1), k); rx, rw = _chi_ratio_nodes(RANGE_DF[N] * baseline, k)
    tot = 0.0
    for c, wc in zip(cx * np.sqrt(2.0 / baseline), cw):
        for s, ws in zip(sx, sw):
            pm = flag_rate_rules(zone_probs(0.0, c, s), rules)
            for r, wr in zip(rx, rw):
                pr = range_rate(r) if with_range else 0.0
                tot += wc * ws * wr * (1 - (1 - pm) * (1 - pr))
    return tot


def expected_rate_three_way(baseline, k=7):
    """Expected signals per point of a three-way chart: individuals limits from the standard deviation of `baseline`
    means, moving-range limit from their mean moving range (scaled chi on 0.62 of baseline - 1 degrees of freedom),
    range limit from the average range."""
    cx, cw = _normal_nodes(k); sx, sw = _chi_ratio_nodes(baseline - 1, k)
    mx, mw = _chi_ratio_nodes(0.62 * (baseline - 1), k); rx, rw = _chi_ratio_nodes(RANGE_DF[N] * baseline, k)
    tot = 0.0
    for c, wc in zip(cx / np.sqrt(baseline), cw):
        for s, ws in zip(sx, sw):
            for mr, wm in zip(mx, mw):
                for r, wr in zip(rx, rw):
                    tot += wc * ws * wm * wr * three_way_flag_rate(0.0, c, s, mr, r)
    return tot


def expected_arl_xbar(baseline, shift, rules, k=9):
    """ARL averaged over the baseline estimates of an X-bar chart (means only), at a shift in sigmas of the mean."""
    cx, cw = _normal_nodes(k); rx, rw = _chi_ratio_nodes(RANGE_DF[N] * baseline, k)
    return float(sum(wc * wr * arl_rules(shift, rules, c, r) for c, wc in zip(cx / np.sqrt(baseline), cw) for r, wr in zip(rx, rw)))


def expected_arl_three_way(baseline, shift, k=7):
    """ARL averaged over the baseline estimates of a three-way chart's individuals, moving-range and range charts."""
    cx, cw = _normal_nodes(k); sx, sw = _chi_ratio_nodes(baseline - 1, k)
    return float(sum(wc * ws * three_way_arl(shift, c, s) for c, wc in zip(cx / np.sqrt(baseline), cw) for s, ws in zip(sx, sw)))


# ── per-stroke EWMA on the total ───────────────────────────────────────────────

def ewma_sd_factor(lam, phi):
    """Stationary sigma of an EWMA of AR(1) data with unit variance."""
    a = phi * (1 - lam)
    return np.sqrt(lam / (2 - lam) * (1 + a) / (1 - a))


def ewma_arl(lam, L, shift_sd, phi, m=301):
    """ARL of a two-sided EWMA with limits at L EWMA sigmas on AR(1) data, input shift in sigmas of the data: the chain
    is run on an independent input whose EWMA has the AR(1)-adjusted variance (Brook and Evans, m states)."""
    s_e = ewma_sd_factor(lam, phi)
    s_in = s_e / np.sqrt(lam / (2 - lam))
    h = L * s_e; w = 2 * h / m; c = -h + w * (np.arange(m) + 0.5)
    lo = (c[None, :] - w / 2 - (1 - lam) * c[:, None]) / lam; hi = lo + w / lam
    P = stats.norm.cdf((hi - shift_sd) / s_in) - stats.norm.cdf((lo - shift_sd) / s_in)
    x = np.linalg.solve(np.eye(m) - P, np.ones(m))
    return float(x[m // 2])


def ewma_limit_for(lam, arl0, phi, lo=2.0, hi=8.0):
    """The limit L at which the EWMA's in-control ARL equals arl0, by bisection."""
    for _ in range(60):
        mid = (lo + hi) / 2
        if ewma_arl(lam, mid, 0.0, phi) < arl0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ── three-way design alternatives under the residual coil effect ──────────────

def coil_block_rate(rho, rules=(1,), width=1.0, k=21):
    """Per-point signal rate of a means chart on points that share a coil offset: the offset is normal with share rho
    of the variance of the plotted means, the points within a coil independent about it, the rule history taken
    within the coil. width scales the three-sigma limits on the total sigma of the means."""
    b, w = _normal_nodes(k); s = np.sqrt(1 - rho)
    return float(sum(wi * flag_rate_rules(zone_probs(bi * np.sqrt(rho) / s, 0.0, width / s), rules) for bi, wi in zip(b, w)))


def moving_range_sigma_ratio(rho, points_per_coil):
    """Sigma of the means estimated from the average moving range, as a share of their total sigma, when a share rho of
    their variance is between coils and points_per_coil points are charted on each coil."""
    cross = 1.0 / points_per_coil
    return float((1 - cross) * np.sqrt(1 - rho) + cross * 1.0)
