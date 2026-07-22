"""Portfolio holdings CRUD, scoped to the authenticated user.

Every operation is ownership-checked: a user can only read/update/delete their own holdings (filtered
by `owner` = their email from the JWT), so this demonstrates authorization, not just authentication.
Each holding is marked-to-market against the latest close in the dataset to compute live P&L.
"""
from datetime import date, datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.db import get_database
from app.core.security import get_current_user
from app.ml.data_loader import latest_close
from app.ml.nepse_fees import buy_costs, sell_costs

router = APIRouter()

COLLECTION = "holdings"


def _holding_days(buy_date: str | None, today: date) -> int | None:
    if not buy_date:
        return None
    try:
        d = datetime.strptime(buy_date, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (today - d).days


class HoldingIn(BaseModel):
    symbol: str
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)
    buy_date: str | None = None


class HoldingUpdate(BaseModel):
    quantity: float | None = Field(default=None, gt=0)
    buy_price: float | None = Field(default=None, gt=0)
    buy_date: str | None = None


def _enrich(doc: dict, close: float | None, today: date | None = None) -> dict:
    """Attach NEPSE-realistic P&L to a stored holding, marked to the latest close.

    Cost basis includes buy-side broker commission + SEBON fee + DP charge. If sold now, the sell
    side deducts the same charges plus capital gains tax on any gain (rate by holding period). The
    headline `net_pnl` is what the investor would actually keep. Pure function of doc + close +
    today, so the money math is unit-testable without a database.
    """
    today = today or date.today()
    quantity, buy_price = doc["quantity"], doc["buy_price"]
    buy_amount = quantity * buy_price
    b_costs = buy_costs(buy_amount)
    total_buy_cost = round(buy_amount + b_costs["total"], 2)

    result = {
        "id": str(doc["_id"]),
        "symbol": doc["symbol"],
        "quantity": quantity,
        "buy_price": buy_price,
        "buy_date": doc.get("buy_date"),
        "latest_close": close,
        "buy_amount": round(buy_amount, 2),
        "buy_costs": b_costs,
        "total_buy_cost": total_buy_cost,
    }

    if close is None:
        result.update({"market_value": None, "sell_costs": None, "net_sell_value": None,
                       "gross_pnl": None, "net_pnl": None, "net_pnl_pct": None, "total_charges": None})
        return result

    sell_amount = quantity * close
    capital_gain = sell_amount - buy_amount
    s_costs = sell_costs(sell_amount, capital_gain, _holding_days(doc.get("buy_date"), today))
    net_sell_value = round(sell_amount - s_costs["total"], 2)
    net_pnl = round(net_sell_value - total_buy_cost, 2)

    result.update({
        "market_value": round(sell_amount, 2),
        "sell_costs": s_costs,
        "net_sell_value": net_sell_value,
        "gross_pnl": round(capital_gain, 2),
        "net_pnl": net_pnl,
        "net_pnl_pct": round(net_pnl / total_buy_cost * 100, 2),
        "total_charges": round(b_costs["total"] + s_costs["total"], 2),
    })
    return result


def _parse_id(holding_id: str) -> ObjectId:
    try:
        return ObjectId(holding_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")


@router.get("/api/portfolio")
async def list_holdings(current_user: dict = Depends(get_current_user)):
    docs = await get_database()[COLLECTION].find({"owner": current_user["email"]}).to_list(length=None)
    closes = {d["symbol"]: latest_close(d["symbol"]) for d in docs}
    return [_enrich(d, closes[d["symbol"]]) for d in docs]


@router.post("/api/portfolio", status_code=status.HTTP_201_CREATED)
async def create_holding(payload: HoldingIn, current_user: dict = Depends(get_current_user)):
    symbol = payload.symbol.strip().upper()
    close = latest_close(symbol)
    if close is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown symbol '{symbol}'")

    now = datetime.now(timezone.utc)
    doc = {
        "owner": current_user["email"],
        "symbol": symbol,
        "quantity": payload.quantity,
        "buy_price": payload.buy_price,
        "buy_date": payload.buy_date,
        "created_at": now,
        "updated_at": now,
    }
    result = await get_database()[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich(doc, close)


@router.put("/api/portfolio/{holding_id}")
async def update_holding(holding_id: str, payload: HoldingUpdate, current_user: dict = Depends(get_current_user)):
    oid = _parse_id(holding_id)
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    changes["updated_at"] = datetime.now(timezone.utc)

    collection = get_database()[COLLECTION]
    updated = await collection.find_one_and_update(
        {"_id": oid, "owner": current_user["email"]},
        {"$set": changes},
        return_document=True,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")

    return _enrich(updated, latest_close(updated["symbol"]))


@router.delete("/api/portfolio/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(holding_id: str, current_user: dict = Depends(get_current_user)):
    oid = _parse_id(holding_id)
    result = await get_database()[COLLECTION].delete_one({"_id": oid, "owner": current_user["email"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
    return None
