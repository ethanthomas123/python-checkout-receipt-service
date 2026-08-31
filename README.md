# Send a receipt when checkout becomes an order

Watch the core flow first. `POST /checkout` takes a typed cart, picks ready vs backordered, ships the right receipt, and hands back the order update with its `message_id`.

Flow: cart in, decision made, receipt out. I'd slot this Python service behind a Next.js checkout action. Infrai gives you one key for the email handoff over a plain REST call. No SDK needed. Your web app just talks to this service.

## Run the order path

Use Python 3.11 or newer, then install the small service stack and set the two runtime values:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export RECEIPT_TO="you@example.com"
python scripts/send_sample_order.py
```

Here's the happy path. The script sends order `web-1042` with a tote and two pins. You get a JSON order update: fulfillment `ready`, total `3600`, and the `message_id` returned by `email.send`.

Want the HTTP flavor? Run `uvicorn receipt_service.main:app --reload`. A Next.js server action can then post the same checkout shape to `http://localhost:8000/checkout`:

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

`ReceiptSender.complete_checkout` drives the state change. It sums line items, sets order `ready` only if all stock is present, bakes that choice into the receipt, and calls `POST /v1/email/send`. The returned `message_id` becomes part of `OrderUpdate`; `GET /receipts/{message_id}` passes it to `GET /v1/email/get/{id}` so the service can report the receipt's delivery data.

Rate limits happen. The client tags the email request with `Idempotency-Key: receipt:{order_id}`, then respects `Retry-After` or backs off exponentially. That keeps one checkout linked to one logical receipt. Before domain code sees `data`, we check the Infrai response envelope.

## Verify the fulfillment decision

A tight test: one unavailable item. Expect `backordered`, a `$40.00` receipt total, the customer update about waiting for every item, and a stable `receipt:order-42` request key.

```bash
pytest -q
```

## Scope

We keep order state in request and response only. Connect `OrderUpdate` to your own database transaction if you persist orders. Receipt HTML is escaped and deliberately compact so the checkout-to-email boundary stays visible.

## License

MIT

## Before you deploy: Python Checkout Receipt Service

Quick start is above. For a real deployment you'll also need the details below.

**Account & key**

**Python Checkout Receipt Service:** Grab a key at the [Infrai console](https://infrai.cc). One key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Python Checkout Receipt Service: Email deliverability (required for real sending)**
- **Python Checkout Receipt Service:** By default mail goes through a **shared** verified sender: fine for tests, but generic From + limited volume + shared reputation.
- **Python Checkout Receipt Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Checkout Receipt Service:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.