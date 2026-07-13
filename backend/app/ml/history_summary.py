"""Trend-focused historical summary for a symbol (data_loader.load_symbol output)."""
import pandas as pd


def _contiguous_ranges(df: pd.DataFrame, mask: pd.Series) -> list:
    """Collapse a boolean mask into a list of {start, end} contiguous date ranges."""
    ranges = []
    start = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            ranges.append((start, i - 1))
            start = None
    if start is not None:
        ranges.append((start, len(mask) - 1))

    return [
        {"start": df["date"].iloc[s].strftime("%Y-%m-%d"), "end": df["date"].iloc[e].strftime("%Y-%m-%d")}
        for s, e in ranges
    ]


def summarize_history(df: pd.DataFrame) -> dict:
    high_idx = df["close"].idxmax()
    low_idx = df["close"].idxmin()

    top_gains = df.nlargest(3, "log_return")
    top_losses = df.nsmallest(3, "log_return")

    threshold = df["volatility_20"].quantile(0.8)
    high_vol_mask = df["volatility_20"] > threshold

    return {
        "period_start": df["date"].iloc[0].strftime("%Y-%m-%d"),
        "period_end": df["date"].iloc[-1].strftime("%Y-%m-%d"),
        "overall_return_pct": float((df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100),
        "highest_close": {
            "price": float(df["close"].loc[high_idx]),
            "date": df["date"].loc[high_idx].strftime("%Y-%m-%d"),
        },
        "lowest_close": {
            "price": float(df["close"].loc[low_idx]),
            "date": df["date"].loc[low_idx].strftime("%Y-%m-%d"),
        },
        "top_gains": [
            {"date": row["date"].strftime("%Y-%m-%d"), "return_pct": float(row["log_return"] * 100)}
            for _, row in top_gains.iterrows()
        ],
        "top_losses": [
            {"date": row["date"].strftime("%Y-%m-%d"), "return_pct": float(row["log_return"] * 100)}
            for _, row in top_losses.iterrows()
        ],
        "high_volatility_periods": _contiguous_ranges(df, high_vol_mask),
        "high_volatility_threshold": float(threshold),
    }
