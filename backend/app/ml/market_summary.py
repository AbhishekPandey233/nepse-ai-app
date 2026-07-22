"""Market-wide aggregation of the per-symbol efficiency + volatility results.

Runs the EXISTING run_efficiency_tests and fit_garch across many symbols and rolls the outputs up
into one summary, so market-level claims ("X% of NEPSE symbols show evidence against weak-form
efficiency") rest on the whole market rather than a single-symbol anecdote. Expensive (GARCH over
hundreds of symbols) -- meant to be run offline by scripts/build_market_summary.py, not per request.
"""
import logging

import numpy as np
import pandas as pd

from app.ml.data_loader import load_symbol
from app.ml.efficiency import _variance_ratio_test, run_efficiency_tests
from app.ml.volatility import fit_garch

logger = logging.getLogger("nepse-ai")


def _summary_stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "mean": None, "median": None, "std": None, "min": None, "max": None}
    arr = np.asarray(values, dtype=float)
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": float(arr.std(ddof=0)),
        "min": float(arr.min()),
        "max": float(arr.max()),
    }


def _analyze_symbol(symbol: str) -> dict:
    """Per-symbol slice of what the market summary aggregates. Reuses the existing modules verbatim."""
    df = load_symbol(symbol)
    returns = df["log_return"]

    eff = run_efficiency_tests(returns)
    against_efficiency = eff["ljung_box"]["p_value"] < 0.05 or eff["variance_ratio"]["p_value"] < 0.05

    garch = fit_garch(returns)
    persistence = garch["params"]["alpha[1]"] + garch["params"]["beta[1]"]

    return {
        "symbol": symbol.upper(),
        "against_efficiency": bool(against_efficiency),
        "adf_stat": float(eff["adf"]["statistic"]),
        "variance_ratio": float(eff["variance_ratio"]["variance_ratio"]),
        "garch_persistence": float(persistence),
    }


def build_market_summary(symbols: list[str]) -> dict:
    """Analyze every symbol, skipping (and logging) any that error out, then aggregate.

    Aggregates: % of symbols with evidence against weak-form efficiency, and mean/median/std of the
    ADF statistic, variance ratio, and GARCH persistence (alpha+beta) across all processed symbols.
    """
    per_symbol = []
    skipped = []

    for symbol in symbols:
        try:
            per_symbol.append(_analyze_symbol(symbol))
        except Exception as exc:
            logger.warning("market_summary: skipped %s (%s)", symbol, exc)
            skipped.append({"symbol": symbol.upper(), "reason": str(exc)})

    n = len(per_symbol)
    against_count = sum(1 for r in per_symbol if r["against_efficiency"])

    return {
        "n_symbols_processed": n,
        "n_symbols_skipped": len(skipped),
        "skipped": skipped,
        "pct_against_efficiency": round(against_count / n * 100, 2) if n else 0.0,
        "n_against_efficiency": against_count,
        "adf_stat": _summary_stats([r["adf_stat"] for r in per_symbol]),
        "variance_ratio": _summary_stats([r["variance_ratio"] for r in per_symbol]),
        "garch_persistence": _summary_stats([r["garch_persistence"] for r in per_symbol]),
        "per_symbol": per_symbol,
    }




def _pearson(x: list, y: list) -> float | None:
    """Pearson r over the pairs where both are finite; None if too few points or a series is flat."""
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    mask = np.isfinite(xa) & np.isfinite(ya)
    if mask.sum() < 3:
        return None
    xv, yv = xa[mask], ya[mask]
    if xv.std() == 0 or yv.std() == 0:
        return None
    return float(np.corrcoef(xv, yv)[0, 1])


def rolling_efficiency_vs_accuracy(df: pd.DataFrame, window: int = 60) -> dict:
    """Over rolling `window`-day windows of the test period, compute the model's directional
    accuracy, a rolling inefficiency measure (|variance ratio - 1|), and rolling realized
    volatility, then correlate each against accuracy.

    Realized volatility is used as the volatility proxy rather than refitting GARCH per window
    (far too slow to do hundreds of times). Answers RQ1/RQ2: do less-efficient / differently-
    volatile regimes coincide with the model predicting better or worse?
    """
    from app.ml.prediction import _test_split, train_xgboost

    pred_out = train_xgboost(df)
    predicted = np.asarray(pred_out["predictions"], dtype=float)
    actual = np.asarray(pred_out["actual"], dtype=float)
    test_dates = pred_out["dates"]
    n_test = len(actual)

    returns_arr, split_idx, _, _ = _test_split(df)

    empty = {
        "window": window,
        "n_windows": 0,
        "correlations": {"inefficiency_vs_accuracy": None, "volatility_vs_accuracy": None},
        "series": {"dates": [], "directional_accuracy": [], "variance_ratio": [], "inefficiency": [], "volatility": []},
    }
    if n_test < window:
        empty["message"] = f"Test period ({n_test} days) is shorter than the {window}-day window."
        return empty

    correct = np.sign(predicted) == np.sign(actual)
    valid = actual != 0

    dates_out, acc_out, vr_out, ineff_out, vol_out = [], [], [], [], []
    for j in range(window - 1, n_test):
        sl = slice(j - window + 1, j + 1)
        v = valid[sl]
        acc_out.append(float(correct[sl][v].mean() * 100) if v.any() else None)

        r0, r1 = split_idx + (j - window + 1), split_idx + j
        win_returns = returns_arr[r0: r1 + 1]

        vr = _variance_ratio_test(pd.Series(win_returns), k=2)["variance_ratio"]
        vr = vr if np.isfinite(vr) else None
        vr_out.append(vr)
        ineff_out.append(abs(vr - 1.0) if vr is not None else None)
        vol_out.append(float(np.std(win_returns, ddof=1)))

        dates_out.append(test_dates[j])

    return {
        "window": window,
        "n_windows": len(dates_out),
        "correlations": {
            "inefficiency_vs_accuracy": _pearson(ineff_out, acc_out),
            "volatility_vs_accuracy": _pearson(vol_out, acc_out),
        },
        "series": {
            "dates": dates_out,
            "directional_accuracy": acc_out,
            "variance_ratio": vr_out,
            "inefficiency": ineff_out,
            "volatility": vol_out,
        },
    }
