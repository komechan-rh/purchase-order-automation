from fastapi import BackgroundTasks, FastAPI, Header, HTTPException

from .schemas import GeminiReplyPurchaseRequest, PurchaseAcceptedResponse
from .services.purchase_runner import purchase_service
from .settings import settings

app = FastAPI(title=settings.app_name)


def _require_api_key(x_api_key: str | None) -> None:
    if settings.backend_api_key and x_api_key != settings.backend_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/purchases/amazon", response_model=PurchaseAcceptedResponse)
def create_amazon_purchase(
    payload: GeminiReplyPurchaseRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> PurchaseAcceptedResponse:
    _require_api_key(x_api_key)

    background_tasks.add_task(
        purchase_service.run,
        payload.name,
        payload.count,
        payload.message,
        payload.product_url,
    )

    return PurchaseAcceptedResponse(
        item_name=payload.name,
        quantity=payload.count,
        note=payload.message,
        source="gas",
        status="PENDING",
        product_url=payload.product_url,
    )
