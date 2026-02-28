from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PurchaseCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=255)
    quantity: int = Field(ge=1, le=99)
    note: str = Field(default="", max_length=500)
    source: Literal["manual", "line", "gas"] = "manual"


class PurchaseResponse(BaseModel):
    id: int
    item_name: str
    quantity: int
    note: str
    source: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LineIntentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    user_id: str = Field(default="", max_length=128)
    reply_token: str = Field(default="", max_length=255)


class LineIntentResponse(BaseModel):
    order_id: int
    item_name: str
    quantity: int
    product_url: str
    status: str
