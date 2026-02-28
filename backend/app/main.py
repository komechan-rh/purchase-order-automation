from datetime import datetime

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import PurchaseOrder
from .schemas import LineIntentRequest, LineIntentResponse, PurchaseCreate, PurchaseResponse
from .services.catalog import fetch_catalog_items, find_catalog_item
from .services.gemini import parse_purchase_intent_with_gemini
from .services.purchase_runner import run_purchase_automation
from .settings import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)


def _require_api_key(x_api_key: str | None) -> None:
    if settings.backend_api_key and x_api_key != settings.backend_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/purchases", response_model=PurchaseResponse)
def create_purchase(
    payload: PurchaseCreate,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> PurchaseOrder:
    _require_api_key(x_api_key)

    order = PurchaseOrder(
        item_name=payload.item_name,
        quantity=payload.quantity,
        note=payload.note,
        source=payload.source,
        status="PENDING",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    background_tasks.add_task(_run_and_update_status, order.id, None)
    return order


@app.get("/api/purchases", response_model=list[PurchaseResponse])
def list_purchases(
    limit: int = 50,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> list[PurchaseOrder]:
    _require_api_key(x_api_key)
    safe_limit = min(max(limit, 1), 200)
    return db.query(PurchaseOrder).order_by(desc(PurchaseOrder.created_at)).limit(safe_limit).all()


@app.post("/api/line/intents", response_model=LineIntentResponse)
async def create_purchase_from_line_intent(
    payload: LineIntentRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> LineIntentResponse:
    _require_api_key(x_api_key)

    catalog_items = await fetch_catalog_items()
    parsed = await parse_purchase_intent_with_gemini(
        payload.text,
        [item.item_name for item in catalog_items],
    )
    catalog_item = find_catalog_item(catalog_items, parsed.item_name)
    if catalog_item is None:
        raise HTTPException(status_code=422, detail="Item not found in spreadsheet catalog")

    note = parsed.note
    if payload.user_id:
        note = f"{note}\nline_user_id={payload.user_id}" if note else f"line_user_id={payload.user_id}"

    order = PurchaseOrder(
        item_name=catalog_item.item_name,
        quantity=parsed.quantity,
        note=note,
        source="line",
        status="PENDING",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    background_tasks.add_task(_run_and_update_status, order.id, catalog_item.product_url)

    return LineIntentResponse(
        order_id=order.id,
        item_name=catalog_item.item_name,
        quantity=parsed.quantity,
        product_url=catalog_item.product_url,
        status=order.status,
    )


async def _run_and_update_status(order_id: int, product_url: str | None) -> None:
    db = SessionLocal()
    try:
        order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if order is None:
            return
        try:
            await run_purchase_automation(order.item_name, order.quantity, order.note, product_url)
            order.status = "ORDERED"
        except Exception as exc:  # noqa: BLE001
            order.status = f"FAILED: {type(exc).__name__}"
        order.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
