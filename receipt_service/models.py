from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class FulfillmentState(str, Enum):
    READY = "ready"
    BACKORDERED = "backordered"


class CheckoutItem(BaseModel):
    name: str
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)
    in_stock: bool


class CheckoutRequest(BaseModel):
    order_id: str = Field(min_length=1)
    customer_email: EmailStr
    customer_name: str = Field(min_length=1)
    items: list[CheckoutItem] = Field(min_length=1)


class OrderUpdate(BaseModel):
    order_id: str
    fulfillment: FulfillmentState
    message_id: str
    total_cents: int
    customer_message: str


class ReceiptStatus(BaseModel):
    message_id: str
    delivery: dict[str, object]
