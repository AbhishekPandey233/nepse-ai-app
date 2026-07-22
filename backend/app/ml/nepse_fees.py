

SEBON_FEE_RATE = 0.00015
DP_CHARGE = 25.0
MIN_COMMISSION = 10.0


_COMMISSION_SLABS = [
    (50_000, 0.0036),
    (500_000, 0.0033),
    (2_000_000, 0.0031),
    (10_000_000, 0.0027),
    (float("inf"), 0.0024),
]

CGT_SHORT_TERM = 0.075
CGT_LONG_TERM = 0.05


def broker_commission(amount: float) -> float:
    for upper, rate in _COMMISSION_SLABS:
        if amount <= upper:
            return round(max(amount * rate, MIN_COMMISSION), 2)
    return round(max(amount * _COMMISSION_SLABS[-1][1], MIN_COMMISSION), 2)


def sebon_fee(amount: float) -> float:
    return round(amount * SEBON_FEE_RATE, 2)


def cgt_rate(holding_days: int | None) -> float:
    """Long-term rate only when the holding period is known to be >= 365 days; otherwise the
    (higher) short-term rate is assumed."""
    return CGT_LONG_TERM if holding_days is not None and holding_days >= 365 else CGT_SHORT_TERM


def buy_costs(amount: float) -> dict:
    commission = broker_commission(amount)
    sebon = sebon_fee(amount)
    return {
        "commission": commission,
        "sebon_fee": sebon,
        "dp_charge": DP_CHARGE,
        "total": round(commission + sebon + DP_CHARGE, 2),
    }


def sell_costs(amount: float, capital_gain: float, holding_days: int | None) -> dict:
    commission = broker_commission(amount)
    sebon = sebon_fee(amount)
    rate = cgt_rate(holding_days)
    cgt = round(rate * capital_gain, 2) if capital_gain > 0 else 0.0
    return {
        "commission": commission,
        "sebon_fee": sebon,
        "dp_charge": DP_CHARGE,
        "cgt_rate": rate,
        "capital_gains_tax": cgt,
        "total": round(commission + sebon + DP_CHARGE + cgt, 2),
    }
