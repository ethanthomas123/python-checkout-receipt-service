from fastapi import FastAPI

from .infrai_client import InfraiClient
from .models import CheckoutRequest, OrderUpdate, ReceiptStatus
from .receipt_sender import ReceiptSender

app = FastAPI(title="Checkout receipt service")


def sender() -> ReceiptSender:
    return ReceiptSender(InfraiClient())


@app.post("/checkout", response_model=OrderUpdate)
def complete_checkout(checkout: CheckoutRequest) -> OrderUpdate:
    return sender().complete_checkout(checkout)


@app.get("/receipts/{message_id}", response_model=ReceiptStatus)
def get_receipt(message_id: str) -> ReceiptStatus:
    return sender().receipt_status(message_id)
