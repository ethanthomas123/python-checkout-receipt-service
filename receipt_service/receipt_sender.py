from html import escape
from typing import Protocol

from .models import CheckoutRequest, FulfillmentState, OrderUpdate, ReceiptStatus


class EmailGateway(Protocol):
    def email_send(
        self, payload: dict[str, object], idempotency_key: str
    ) -> dict[str, object]:
        raise AssertionError("Protocol declaration")

    def email_get(self, message_id: str) -> dict[str, object]:
        raise AssertionError("Protocol declaration")


class ReceiptSender:
    def __init__(self, email: EmailGateway) -> None:
        self.email = email

    def complete_checkout(self, checkout: CheckoutRequest) -> OrderUpdate:
        fulfillment = (
            FulfillmentState.READY
            if all(item.in_stock for item in checkout.items)
            else FulfillmentState.BACKORDERED
        )
        total_cents = sum(item.quantity * item.unit_price_cents for item in checkout.items)
        customer_message = (
            "Your order is ready for fulfillment."
            if fulfillment is FulfillmentState.READY
            else "We received your order and will update you when every item is ready."
        )
        result = self.email.email_send(
            {
                "to": str(checkout.customer_email),
                "subject": f"Receipt for order {checkout.order_id}",
                "html": self._receipt_html(checkout, total_cents, customer_message),
            },
            idempotency_key=f"receipt:{checkout.order_id}",
        )
        message_id = result.get("message_id")
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("email.send response did not include message_id")
        return OrderUpdate(
            order_id=checkout.order_id,
            fulfillment=fulfillment,
            message_id=message_id,
            total_cents=total_cents,
            customer_message=customer_message,
        )

    def receipt_status(self, message_id: str) -> ReceiptStatus:
        return ReceiptStatus(message_id=message_id, delivery=self.email.email_get(message_id))

    @staticmethod
    def _receipt_html(checkout: CheckoutRequest, total_cents: int, message: str) -> str:
        rows = "".join(
            f"<li>{escape(item.name)} x {item.quantity}: "
            f"${item.quantity * item.unit_price_cents / 100:.2f}</li>"
            for item in checkout.items
        )
        return (
            f"<h1>Thanks, {escape(checkout.customer_name)}</h1>"
            f"<p>Order {escape(checkout.order_id)}</p><ul>{rows}</ul>"
            f"<p><strong>Total: ${total_cents / 100:.2f}</strong></p>"
            f"<p>{escape(message)}</p>"
        )
