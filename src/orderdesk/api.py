from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from orderdesk import __version__, db
from orderdesk.models import Order, OrderStatus


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="orderdesk", version=__version__, lifespan=lifespan)


class OrderIn(BaseModel):
    customer_email: EmailStr
    item: str = Field(min_length=1, max_length=200)
    quantity: int = Field(default=1, ge=1, le=1000)


class OrderOut(BaseModel):
    id: int
    customer_email: str
    item: str
    quantity: int
    status: OrderStatus
    created_at: datetime
    processed_at: datetime | None
    note: str | None

    model_config = {"from_attributes": True}


@app.get("/health")
def health() -> dict[str, str]:
    try:
        db.ping()
    except Exception as exc:  # pragma: no cover - exercised only when the DB is down
        detail = f"database unavailable: {exc.__class__.__name__}"
        raise HTTPException(status_code=503, detail=detail) from exc
    return {"status": "ok", "version": __version__}


@app.post("/orders", response_model=OrderOut, status_code=201)
def create_order(payload: OrderIn, session: Session = Depends(db.get_session)) -> Order:
    order = Order(customer_email=payload.customer_email, item=payload.item, quantity=payload.quantity)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, session: Session = Depends(db.get_session)) -> Order:
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


@app.get("/orders", response_model=list[OrderOut])
def list_orders(
    status: OrderStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(db.get_session),
) -> list[Order]:
    stmt = select(Order).order_by(Order.id.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(Order.status == status)
    return list(session.scalars(stmt))
