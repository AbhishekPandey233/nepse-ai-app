"""Weak-form market efficiency tests on a daily log-return series."""
import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller


def _variance_ratio_test(returns: pd.Series, k: int = 2) -> dict:
    """Lo-MacKinlay (1988) overlapping variance ratio test, homoskedastic-null version.
    VR(k) = Var(k-period return) / (k * Var(1-period return)); VR ~= 1 under the random-walk null.
    # ponytail: homoskedastic variant (simpler formula), not the heteroskedasticity-robust
    # Lo-MacKinlay statistic — upgrade if GARCH effects in volatility.py make that assumption matter.
    """
    r = returns.to_numpy()
    nq = len(r)
    mu = r.mean()

    var_1 = np.sum((r - mu) ** 2) / (nq - 1)

    m = k * (nq - k + 1) * (1 - k / nq)
    overlapping_sums = np.convolve(r, np.ones(k), mode="valid")
    var_k = np.sum((overlapping_sums - k * mu) ** 2) / m

    vr = var_k / var_1
    theta = (2 * (2 * k - 1) * (k - 1)) / (3 * k * nq)
    z_stat = (vr - 1) / np.sqrt(theta)
    p_value = 2 * (1 - norm.cdf(abs(z_stat)))

    return {"k": k, "variance_ratio": float(vr), "z_statistic": float(z_stat), "p_value": float(p_value)}


def run_efficiency_tests(returns: pd.Series, lb_lags: int = 10, vr_k: int = 2) -> dict:
    """Run ADF, Ljung-Box, and variance ratio tests on a daily log-return series."""
    returns = returns.dropna()

    adf_stat, adf_pvalue, adf_used_lag, adf_nobs, adf_crit, _ = adfuller(returns, autolag="AIC")

    lb = acorr_ljungbox(returns, lags=[lb_lags], return_df=True)
    lb_stat = float(lb["lb_stat"].iloc[0])
    lb_pvalue = float(lb["lb_pvalue"].iloc[0])

    vr = _variance_ratio_test(returns, k=vr_k)

    reasons = []
    if lb_pvalue < 0.05:
        reasons.append(f"significant return autocorrelation (Ljung-Box p={lb_pvalue:.4f} at lag {lb_lags})")
    if vr["p_value"] < 0.05:
        reasons.append(
            f"variance ratio of {vr['variance_ratio']:.3f} differs significantly from 1 (p={vr['p_value']:.4f})"
        )

    if reasons:
        verdict = "Evidence AGAINST weak-form efficiency: " + "; ".join(reasons) + "."
    else:
        verdict = (
            "No significant autocorrelation or variance-ratio deviation detected — "
            "returns behave consistently with the weak-form Efficient Market Hypothesis (random walk)."
        )

    return {
        "adf": {
            "statistic": float(adf_stat),
            "p_value": float(adf_pvalue),
            "used_lag": int(adf_used_lag),
            "n_obs": int(adf_nobs),
            "critical_values": {level: float(v) for level, v in adf_crit.items()},
        },
        "ljung_box": {
            "lags": lb_lags,
            "statistic": lb_stat,
            "p_value": lb_pvalue,
        },
        "variance_ratio": vr,
        "verdict": verdict,
    }
