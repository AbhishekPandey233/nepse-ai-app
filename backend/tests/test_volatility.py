"""assert-based self-check for ml/volatility.py — run with: python tests/test_volatility.py"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arch.univariate.base import ConvergenceWarning

from app.ml.data_loader import load_symbol
from app.ml.volatility import fit_garch


def test_fit_garch_real_symbol():
    df = load_symbol("nabil")
    returns = df.set_index("date")["log_return"]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = fit_garch(returns, forecast_days=10)

    convergence_warnings = [w for w in caught if issubclass(w.category, ConvergenceWarning)]
    assert not convergence_warnings, f"unexpected ConvergenceWarning: {convergence_warnings}"

    assert len(result["dates"]) == len(returns)
    assert len(result["conditional_volatility"]) == len(returns)
    assert len(result["forecast"]) == 10
    assert all(v >= 0 for v in result["conditional_volatility"]), "volatility must be non-negative"
    assert all(v >= 0 for v in result["forecast"]), "forecast volatility must be non-negative"
    assert result["dates"][0] == returns.index[0].strftime("%Y-%m-%d")
    assert isinstance(result["model_summary"], str) and "GARCH" in result["model_summary"]

    # regression guard for the x100 GARCH-fitting scale: historical and forecast volatility
    # must be the same order of magnitude (both in original fractional-return units) and the
    # forecast must continue smoothly from the last historical value, not jump ~100x
    last_historical = result["conditional_volatility"][-1]
    first_forecast = result["forecast"][0]
    assert last_historical < 1, "conditional_volatility looks unscaled (still x100)"
    assert 0.1 < first_forecast / last_historical < 10, (
        f"forecast ({first_forecast}) should be close in magnitude to the last historical "
        f"value ({last_historical}), not off by a factor of ~100"
    )

    params = result["params"]
    for key in ("omega", "alpha[1]", "beta[1]"):
        assert key in params, f"missing GARCH param {key}"
    assert params["alpha[1]"] >= 0 and params["beta[1]"] >= 0, "GARCH alpha/beta must be non-negative"
    assert params["alpha[1]"] + params["beta[1]"] < 1.5, "alpha+beta wildly outside a plausible range"

    print("test_fit_garch_real_symbol passed. params:", params)


if __name__ == "__main__":
    test_fit_garch_real_symbol()
