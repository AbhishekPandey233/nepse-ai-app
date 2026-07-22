"""assert-based self-check for ml/nepse_fees.py — run with: python tests/test_nepse_fees.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.nepse_fees import broker_commission, buy_costs, cgt_rate, sell_costs


def test_broker_commission_slabs_and_floor():
    assert broker_commission(40_000) == round(40_000 * 0.0036, 2)
    assert broker_commission(300_000) == round(300_000 * 0.0033, 2)
    assert broker_commission(1_000_000) == round(1_000_000 * 0.0031, 2)
    assert broker_commission(100) == 10.0
    print("test_broker_commission_slabs_and_floor passed")


def test_cgt_rate_by_holding_period():
    assert cgt_rate(400) == 0.05
    assert cgt_rate(100) == 0.075
    assert cgt_rate(None) == 0.075
    print("test_cgt_rate_by_holding_period passed")


def test_sell_costs_taxes_gain_only():
    on_gain = sell_costs(100_000, capital_gain=20_000, holding_days=100)
    assert on_gain["capital_gains_tax"] == round(0.075 * 20_000, 2)

    on_loss = sell_costs(100_000, capital_gain=-5_000, holding_days=100)
    assert on_loss["capital_gains_tax"] == 0.0

    long_term = sell_costs(100_000, capital_gain=20_000, holding_days=400)
    assert long_term["capital_gains_tax"] == round(0.05 * 20_000, 2)
    print("test_sell_costs_taxes_gain_only passed")


def test_buy_costs_components():
    c = buy_costs(100_000)
    assert c["commission"] == round(100_000 * 0.0033, 2)
    assert c["sebon_fee"] == round(100_000 * 0.00015, 2)
    assert c["dp_charge"] == 25.0
    assert c["total"] == round(c["commission"] + c["sebon_fee"] + 25.0, 2)
    print("test_buy_costs_components passed")


if __name__ == "__main__":
    test_broker_commission_slabs_and_floor()
    test_cgt_rate_by_holding_period()
    test_sell_costs_taxes_gain_only()
    test_buy_costs_components()
