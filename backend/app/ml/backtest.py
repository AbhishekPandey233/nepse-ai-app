"""Long/flat backtest of the model's directional signal vs buy-and-hold, net of a transaction cost.

Profitability net of costs is the standard market-efficiency reading of "impact": a directional
edge that survives realistic costs implies exploitable inefficiency, while no edge net of costs is
consistent with weak-form efficiency. Runs on train_xgboost's test-period output, so it scores the
exact same held-out days as every other metric in the app.
"""
import numpy as np


def run_backtest(df, predictions: dict, transaction_cost_pct: float = 0.5) -> dict:
    """Go long when the predicted next-day return > 0, otherwise sit in cash (flat, no shorting).

    Charges transaction_cost_pct (% of position value) on every position change (flat->long or
    long->flat, counting the initial entry from flat). Returns both cumulative-return series for
    charting, the final totals, trade count, and a plain verdict.

    `df` is accepted for interface parity with the other ml entry points; every series below is
    derived from the predictions payload, which already carries the test-period returns and dates.
    """
    predicted = np.asarray(predictions["predictions"], dtype=float)
    actual_log = np.asarray(predictions["actual"], dtype=float)
    dates = list(predictions["dates"])

    if predicted.size == 0:
        return {
            "dates": [], "strategy_cumulative": [], "buy_hold_cumulative": [],
            "strategy_total_return": 0.0, "buy_hold_total_return": 0.0, "n_trades": 0,
            "transaction_cost_pct": transaction_cost_pct, "verdict": "No test-period data to backtest.",
        }

    market_ret = np.exp(actual_log) - 1.0          # realized simple daily return of the stock
    position = (predicted > 0).astype(int)          # 1 = long that day, 0 = flat (cash)

    prev = np.concatenate([[0], position[:-1]])     # assume flat before the first test day
    changed = position != prev
    tc = transaction_cost_pct / 100.0

    strategy_ret = position * market_ret - changed * tc

    strat_equity = np.cumprod(1.0 + strategy_ret)
    bh_equity = np.cumprod(1.0 + market_ret)

    strategy_total = float(strat_equity[-1] - 1.0)
    buy_hold_total = float(bh_equity[-1] - 1.0)
    n_trades = int(changed.sum())

    outperformed = strategy_total > buy_hold_total
    verb = "outperformed" if outperformed else "did not outperform"
    verdict = (
        f"AI-signal strategy {verb} buy-and-hold net of {transaction_cost_pct}% per-trade costs "
        f"({strategy_total * 100:.2f}% vs {buy_hold_total * 100:.2f}% over the test period, {n_trades} trades)."
    )

    return {
        "dates": dates,
        "strategy_cumulative": (strat_equity - 1.0).tolist(),
        "buy_hold_cumulative": (bh_equity - 1.0).tolist(),
        "strategy_total_return": strategy_total,
        "buy_hold_total_return": buy_hold_total,
        "n_trades": n_trades,
        "transaction_cost_pct": transaction_cost_pct,
        "outperformed": outperformed,
        "verdict": verdict,
    }
