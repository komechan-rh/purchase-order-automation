from pydantic import BaseModel, Field


class GeminiReplyPurchaseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    count: int = Field(ge=1, le=99)
    product_url: str = Field(min_length=1, max_length=2000)
    message: str = Field(default="", max_length=500)


class PurchaseAcceptedResponse(BaseModel):
    item_name: str
    quantity: int
    note: str
    source: str
    status: str
    product_url: str
