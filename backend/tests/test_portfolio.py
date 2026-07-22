"""assert-based self-check for routers/portfolio.py P&L math — run with: python tests/test_portfolio.py"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bson import ObjectId

from app.ml.nepse_fees import buy_costs, sell_costs
from app.routers.portfolio import _enrich


def test_enrich_applies_nepse_charges_and_cgt():
    doc = {"_id": ObjectId(), "symbol": "NABIL", "quantity": 10, "buy_price": 500.0, "buy_date": "2025-01-01"}
    out = _enrich(doc, close=600.0, today=date(2025, 4, 11))

    buy_amount, sell_amount = 5000.0, 6000.0
    b = buy_costs(buy_amount)
    s = sell_costs(sell_amount, capital_gain=1000.0, holding_days=100)

    assert out["total_buy_cost"] == round(buy_amount + b["total"], 2)
    assert out["sell_costs"]["capital_gains_tax"] == round(0.075 * 1000.0, 2)
    assert out["net_sell_value"] == round(sell_amount - s["total"], 2)
    assert out["net_pnl"] == round(out["net_sell_value"] - out["total_buy_cost"], 2)
    assert 0 < out["net_pnl"] < 1000
    assert out["gross_pnl"] == 1000.0
    print("test_enrich_applies_nepse_charges_and_cgt passed:", {"net_pnl": out["net_pnl"], "charges": out["total_charges"]})


def test_enrich_long_term_lower_tax():
    doc = {"_id": ObjectId(), "symbol": "NABIL", "quantity": 10, "buy_price": 500.0, "buy_date": "2024-01-01"}
    out = _enrich(doc, close=600.0, today=date(2025, 4, 11))
    assert out["sell_costs"]["cgt_rate"] == 0.05
    assert out["sell_costs"]["capital_gains_tax"] == round(0.05 * 1000.0, 2)
    print("test_enrich_long_term_lower_tax passed")


def test_enrich_no_tax_on_loss():
    doc = {"_id": ObjectId(), "symbol": "ADBL", "quantity": 5, "buy_price": 400.0, "buy_date": "2025-01-01"}
    out = _enrich(doc, close=360.0, today=date(2025, 6, 1))
    assert out["sell_costs"]["capital_gains_tax"] == 0.0
    assert out["net_pnl"] < 0
    print("test_enrich_no_tax_on_loss passed")


def test_enrich_handles_unknown_close():
    doc = {"_id": ObjectId(), "symbol": "GHOST", "quantity": 5, "buy_price": 400.0}
    out = _enrich(doc, close=None)
    assert out["net_pnl"] is None and out["market_value"] is None and out["sell_costs"] is None
    assert out["total_buy_cost"] > 2000.0
    print("test_enrich_handles_unknown_close passed")


if __name__ == "__main__":
    test_enrich_applies_nepse_charges_and_cgt()
    test_enrich_long_term_lower_tax()
    test_enrich_no_tax_on_loss()
    test_enrich_handles_unknown_close()
