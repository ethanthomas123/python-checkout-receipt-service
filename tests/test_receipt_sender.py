from receipt_service.models import CheckoutRequest, FulfillmentState
from receipt_service.receipt_sender import ReceiptSender


class RecordingEmailGateway:
    def __init__(self) -> None:
        self.payload: dict[str, object] = {}
        self.idempotency_key = ""

    def email_send(self, payload: dict[str, object], idempotency_key: str) -> dict[str, object]:
        self.payload = payload
        self.idempotency_key = idempotency_key
        return {"message_id": "msg_42"}

    def email_get(self, message_id: str) -> dict[str, object]:
        return {"message_id": message_id, "status": "delivered"}


def test_backordered_checkout_sends_matching_customer_update() -> None:
    gateway = RecordingEmailGateway()
    checkout = CheckoutRequest.model_validate(
        {
            "order_id": "order-42",
            "customer_email": "buyer@example.com",
            "customer_name": "Lin",
            "items": [
                {
                    "name": "Travel mug",
                    "quantity": 2,
                    "unit_price_cents": 1750,
                    "in_stock": True,
                },
                {
                    "name": "Replacement lid",
                    "quantity": 1,
                    "unit_price_cents": 500,
                    "in_stock": False,
                },
            ],
        }
    )

    update = ReceiptSender(gateway).complete_checkout(checkout)

    assert update.fulfillment is FulfillmentState.BACKORDERED
    assert update.total_cents == 4000
    assert update.message_id == "msg_42"
    assert "when every item is ready" in update.customer_message
    assert gateway.payload["to"] == "buyer@example.com"
    assert "Total: $40.00" in str(gateway.payload["html"])
    assert gateway.idempotency_key == "receipt:order-42"
