"""Kupiec, Christoffersen, conditional coverage ed Expected Shortfall."""

from __future__ import annotations

import math

import numpy as np
from scipy import stats


def _bernoulli_log_likelihood(successes: int, observations: int, probability: float) -> float:
    p = float(np.clip(probability, 1e-12, 1 - 1e-12))
    return (observations - successes) * math.log(1 - p) + successes * math.log(p)


def kupiec_test(returns, var_forecast, confidence: float = 0.95) -> dict:
    r, var = np.asarray(returns, float), np.asarray(var_forecast, float)
    valid = np.isfinite(r) & np.isfinite(var)
    violations = r[valid] < var[valid]
    n, x = int(len(violations)), int(violations.sum())
    expected = 1 - confidence
    observed = x / n if n else np.nan
    if not n:
        return {}
    lr = -2 * (_bernoulli_log_likelihood(x, n, expected) - _bernoulli_log_likelihood(x, n, observed))
    p_value = float(stats.chi2.sf(lr, 1))
    return {"number_of_observations": n, "number_of_violations": x,
            "expected_violation_rate": expected, "observed_violation_rate": observed,
            "likelihood_ratio": float(lr), "p_value": p_value,
            "result": "pass" if p_value >= 0.05 else "reject"}


def christoffersen_test(returns, var_forecast) -> dict:
    violations = (np.asarray(returns, float) < np.asarray(var_forecast, float)).astype(int)
    pairs = list(zip(violations[:-1], violations[1:]))
    n00 = sum(a == 0 and b == 0 for a, b in pairs); n01 = sum(a == 0 and b == 1 for a, b in pairs)
    n10 = sum(a == 1 and b == 0 for a, b in pairs); n11 = sum(a == 1 and b == 1 for a, b in pairs)
    total = n00 + n01 + n10 + n11
    if not total:
        return {}
    pi = (n01 + n11) / total
    pi0 = n01 / max(n00 + n01, 1); pi1 = n11 / max(n10 + n11, 1)
    ll_independent = _bernoulli_log_likelihood(n01 + n11, total, pi)
    ll_markov = _bernoulli_log_likelihood(n01, n00 + n01, pi0) + _bernoulli_log_likelihood(n11, n10 + n11, pi1)
    lr = -2 * (ll_independent - ll_markov)
    p_value = float(stats.chi2.sf(lr, 1))
    return {"n00": n00, "n01": n01, "n10": n10, "n11": n11,
            "likelihood_ratio": float(lr), "p_value": p_value,
            "result": "pass" if p_value >= 0.05 else "reject"}


def conditional_coverage_test(returns, var_forecast, confidence: float = 0.95) -> dict:
    coverage, independence = kupiec_test(returns, var_forecast, confidence), christoffersen_test(returns, var_forecast)
    if not coverage or not independence:
        return {}
    lr = coverage["likelihood_ratio"] + independence["likelihood_ratio"]
    p_value = float(stats.chi2.sf(lr, 2))
    return {"likelihood_ratio": lr, "p_value": p_value,
            "result": "pass" if p_value >= 0.05 else "reject",
            "coverage": coverage, "independence": independence}


def expected_shortfall_backtest(returns, var_forecast, es_forecast) -> dict:
    r, var, es = np.asarray(returns, float), np.asarray(var_forecast, float), np.asarray(es_forecast, float)
    mask = np.isfinite(r) & np.isfinite(var) & np.isfinite(es) & (r < var)
    if not mask.any():
        return {"violations": 0, "mean_exceedance_loss": None, "mean_predicted_es": None, "bias": None}
    observed, predicted = r[mask], es[mask]
    return {"violations": int(mask.sum()), "mean_exceedance_loss": float(observed.mean()),
            "mean_predicted_es": float(predicted.mean()), "bias": float(observed.mean() - predicted.mean()),
            "mae": float(np.mean(np.abs(observed - predicted)))}
