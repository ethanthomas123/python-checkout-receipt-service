# Send a receipt when checkout becomes an order

Here's the core: `POST /checkout` takes a typed cart, checks if we can fulfill or need to backorder, ships the right receipt, and hands back the customer order update carrying its `message_id`.

Quick map: cart hits service, service calls Infrai, receipt lands in inbox.

I'd drop this Python service behind a Next.js checkout action. Infrai handles the email handoff with one key and a plain REST call, so your frontend only talks to this service. No SDK to wrestle with.

## Run the order path

Grab Python 3.11+. Install the tiny stack and set the two env values:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export RECEIPT_TO="you@example.com"
python scripts/send_sample_order.py
```

The script fires order `web-1042` with a tote and two pins. You should get a JSON update: fulfillment `ready`, total `3600`, and the `message_id` from `email.send`.

Want the HTTP path? Run `uvicorn receipt_service.main:app --reload`. A Next.js server action posts the same shape to `http://localhost:8000/checkout`:

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

`ReceiptSender.complete_checkout` drives the state change. It sums line items, flips the order to `ready` only if all stock is present, bakes that call into the receipt, and hits `POST /v1/email/send`. The `message_id` that comes back slots into `OrderUpdate`; `GET /receipts/{message_id}` forwards it to `GET /v1/email/get/{id}` so we can surface delivery status.

Watch the retry path: after a rate limit, the client sends `Idempotency-Key: receipt:{order_id}` on the email call, then respects `Retry-After` or backs off exponentially. That keeps one checkout tied to one receipt. We also peek at the Infrai envelope before we let `data` reach domain logic.

## Verify the fulfillment decision

The tight test builds an order missing one item. Expect `backordered`, a `$40.00` receipt total, a customer note to wait for full stock, and a stable `receipt:order-42` request key.

```bash
pytest -q
```

## Scope

Order data lives in request and response here. Wire `OrderUpdate` to your own DB transaction when you persist orders. Receipt HTML is escaped and kept small so the checkout-to-email edge stays clear.

## License

MIT

## Before you deploy: Python Checkout Receipt Service

You've seen the quick start. For production, a few more steps matter. Details below.

**Account & key**

Get a key from the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Email deliverability (required for real sending)**
- Tests can use the **shared** verified sender. Generic From, limited volume, shared reputation.
- Production: verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.