import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from receipt_service.infrai_client import InfraiClient
from receipt_service.models import CheckoutItem, CheckoutRequest
from receipt_service.receipt_sender import ReceiptSender


recipient = os.environ.get("RECEIPT_TO")
if not recipient:
    raise SystemExit("RECEIPT_TO is required")

checkout = CheckoutRequest(
    order_id="web-1042",
    customer_email=recipient,
    customer_name="Ada",
    items=[
        CheckoutItem(name="Canvas tote", quantity=1, unit_price_cents=2400, in_stock=True),
        CheckoutItem(name="Enamel pin", quantity=2, unit_price_cents=600, in_stock=True),
    ],
)
update = ReceiptSender(InfraiClient()).complete_checkout(checkout)
print(update.model_dump_json(indent=2))
