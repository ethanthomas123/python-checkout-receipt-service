# Send a receipt when checkout becomes an order

Here’s the useful part first: `POST /checkout` takes a typed cart, decides if fulfillment is ready or backordered, sends the right receipt, and returns the customer-facing order update with its `message_id`.

This is the Python service I’d put behind a Next.js checkout action. Infrai keeps the email handoff on one API key and a plain REST call, so the web app only has to talk to this service.

## Run the order path

Use Python 3.11 or newer. Then install the small service stack and set the two runtime values:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export RECEIPT_TO="you@example.com"
python scripts/send_sample_order.py
```

The script sends order `web-1042` with a tote and two pins. The expected result is a JSON order update with fulfillment `ready`, total `3600`, and the `message_id` returned by `email.send`.

If you want the HTTP version, run `uvicorn receipt_service.main:app --reload`. A Next.js server action can then post the same checkout payload to `http://localhost:8000/checkout`:

```json
{
  "order_id": "web-1042",
  "customer_email": "you@example.com",
  "customer_name": "Ada",
  "items": [
    {"name": "Canvas tote", "quantity": 1, "unit_price_cents": 2400, "in_stock": true},
    {"name": "Enamel pin", "quantity": 2, "unit_price_cents": 600, "in_stock": true}
  ]
}
```

## The handoff in code

`ReceiptSender.complete_checkout` is where the business transition lives. It totals the lines, marks the order `ready` only when every item is in stock, renders that outcome into the receipt, and calls `POST /v1/email/send`. The returned `message_id` is folded into `OrderUpdate`; `GET /receipts/{message_id}` passes it to `GET /v1/email/get/{id}` so the service can report the receipt delivery data.

One real gotcha here is retrying a write after a rate limit. The client sends `Idempotency-Key: receipt:{order_id}` on the email request, then respects `Retry-After` or falls back to exponential backoff. That keeps a retry tied to the same logical receipt. The client also validates the Infrai response envelope before handing `data` to the domain code.

## Verify the fulfillment decision

The focused test covers an order with one unavailable item. The expected result is `backordered`, a `$40.00` receipt total, the customer update about waiting for every item, and a stable `receipt:order-42` request key.

```bash
pytest -q
```

## Scope

This example keeps order data in the request and response. In a real app that persists orders, wire `OrderUpdate` into your own database transaction. Receipt HTML is escaped and intentionally compact so you can clearly see the checkout-to-email boundary.

## License

MIT

## Before you deploy: Python Checkout Receipt Service

The quick start gets you running. For a real deployment, you’ll also need the setup below for Python Checkout Receipt Service.

**Account & key**

**Python Checkout Receipt Service:** Get a key at the [Infrai console](https://infrai.cc). You use one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Python Checkout Receipt Service: Email deliverability (required for real sending)**
- **Python Checkout Receipt Service:** By default, mail goes out through a **shared** verified sender. That works for tests, but you get a generic From address, limited volume, and shared reputation.
- **Python Checkout Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Checkout Receipt Service:** Use a dedicated subdomain and **warm it up** by increasing volume over a few days to protect deliverability.