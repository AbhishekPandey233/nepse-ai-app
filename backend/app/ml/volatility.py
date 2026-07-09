"""GARCH(1,1) volatility modeling on a daily log-return series."""
import numpy as np
import pandas as pd
from arch import arch_model


def fit_garch(returns: pd.Series, forecast_days: int = 10) -> dict:
    """Fit GARCH(1,1) and return conditional volatility + an N-day-ahead forecast.

    Returns are scaled by 100 before fitting (arch's optimizer struggles to converge
    on raw fractional daily returns close to zero), then rescaled back down.
    """
    returns = returns.dropna()
    scaled_returns = returns * 100

    model = arch_model(scaled_returns, vol="Garch", p=1, q=1)
    fit = model.fit(disp="off")

    conditional_volatility = fit.conditional_volatility / 100

    forecast_result = fit.forecast(horizon=forecast_days, reindex=False)
    forecast_variance = forecast_result.variance.values[-1]
    forecast_volatility = np.sqrt(forecast_variance) / 100

    if isinstance(returns.index, pd.DatetimeIndex):
        dates = [d.strftime("%Y-%m-%d") for d in returns.index]
    else:
        dates = list(returns.index)

    return {
        "dates": dates,
        "conditional_volatility": conditional_volatility.tolist(),
        "forecast": forecast_volatility.tolist(),
        "model_summary": str(fit.summary()),
    }
