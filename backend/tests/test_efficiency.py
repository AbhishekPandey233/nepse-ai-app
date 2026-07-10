"""assert-based self-check for ml/efficiency.py — run with: python tests/test_efficiency.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.data_loader import load_symbol
from app.ml.efficiency import run_efficiency_tests


def test_variance_ratio_near_one_for_iid_returns():
    rng = np.random.default_rng(42)
    returns = pd.Series(rng.normal(loc=0.0, scale=0.01, size=2000))

    result = run_efficiency_tests(returns)

    vr = result["variance_ratio"]["variance_ratio"]
    assert abs(vr - 1) < 0.15, f"VR for iid returns should be close to 1, got {vr}"
    assert result["variance_ratio"]["p_value"] > 0.05, "should not reject random walk null for iid returns"
    assert "weak-form Efficient Market Hypothesis" in result["verdict"]

    print("test_variance_ratio_near_one_for_iid_returns passed")


def test_variance_ratio_does_not_reject_price_random_walk():
    """Build an actual random-walk PRICE series (cumulative sum of iid steps, not just iid
    returns directly) and derive log returns from it, to sanity-check the variance ratio
    formula end-to-end the way real price data would be built."""
    rng = np.random.default_rng(123)
    steps = rng.normal(loc=0.0, scale=1.0, size=5000)
    price = 100 * np.exp(np.cumsum(steps) * 0.01)  # geometric random walk in price level
    log_returns = pd.Series(np.diff(np.log(price)))

    result = run_efficiency_tests(log_returns)

    vr = result["variance_ratio"]["variance_ratio"]
    assert abs(vr - 1) < 0.15, f"VR for a price random walk should be close to 1, got {vr}"
    assert result["variance_ratio"]["p_value"] > 0.05, "should not reject random-walk null for a real random walk"

    print("test_variance_ratio_does_not_reject_price_random_walk passed:", vr)


def test_detects_autocorrelation_in_trending_series():
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 0.001, size=1000)
    ar1 = np.zeros(1000)
    for t in range(1, 1000):
        ar1[t] = 0.8 * ar1[t - 1] + noise[t]  # strong positive autocorrelation (AR(1), phi=0.8)
    momentum_returns = pd.Series(ar1)

    result = run_efficiency_tests(momentum_returns)

    assert result["ljung_box"]["p_value"] < 0.05, "strongly autocorrelated series should reject Ljung-Box null"
    assert "AGAINST weak-form efficiency" in result["verdict"]

    print("test_detects_autocorrelation_in_trending_series passed")


def test_real_symbol():
    df = load_symbol("nabil")
    result = run_efficiency_tests(df["log_return"])

    for key in ("adf", "ljung_box", "variance_ratio", "verdict"):
        assert key in result

    assert 0 <= result["adf"]["p_value"] <= 1
    assert 0 <= result["ljung_box"]["p_value"] <= 1
    assert 0 <= result["variance_ratio"]["p_value"] <= 1
    assert isinstance(result["verdict"], str) and len(result["verdict"]) > 0

    print("test_real_symbol passed:", result["verdict"])


if __name__ == "__main__":
    test_variance_ratio_near_one_for_iid_returns()
    test_variance_ratio_does_not_reject_price_random_walk()
    test_detects_autocorrelation_in_trending_series()
    test_real_symbol()
