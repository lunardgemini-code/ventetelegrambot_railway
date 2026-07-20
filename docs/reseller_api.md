# VenteBot Reseller API

This API lets a partner bot resell VenteBot products using the reseller account wallet balance.

API version: `1.2.0`. This release is backward compatible with existing integrations. Existing catalog, quote, order, status, and wallet-history calls do not need to change.

Interactive Swagger documentation:

```text
https://YOUR-DOMAIN/api/swagger/
```

## Authentication

Every reseller request must send the API key in this HTTP header:

```http
X-Reseller-Key: vbr_live_xxxxx_yyyyyyyy
Content-Type: application/json
```

`X-Reseller-Key` is recommended. For compatibility with common reseller bot integrations, protected reseller endpoints also accept the same reseller key in `X-API-Key`.

The dashboard admin `X-API-Key` is separate and does not authenticate reseller purchases.

The reseller can generate a key directly inside the Telegram bot with **API** then **Generate API key**. The full key is shown only once when it is created.

The admin can also create or revoke keys from the dashboard, in the **Resellers** tab.

If a reseller generates a new key from the bot, the previous active key is automatically disabled.

## Important Rules

- The reseller wallet must have enough balance.
- API purchases debit the reseller wallet.
- To avoid duplicate purchases if your bot retries the same request, always send a stable `idempotency_key` and reuse it for every retry of that purchase.
- Reusing an order or deposit `idempotency_key` with a different request body returns `409 IDEMPOTENCY_CONFLICT`.
- For `stock` products, delivered accounts are returned in `order.items`.
- For `supplier_api` products, send the order only when its status is `COMPLETED`. If the response is `PAID_PENDING_DELIVERY`, poll the order endpoint until delivery finishes instead of sending an empty message.
- For `activation` products, send `activation_identifier` when creating the order, or later with the dedicated endpoint.
- If you call the API from a browser website, set `CORS_ORIGINS` on the bot backend to your website domain, for example `https://your-site.com`.
- If your hosting plan sleeps, ping `GET /health` every few minutes instead of pinging protected reseller endpoints.
- The default rate limit is `60` requests per `60` seconds per API key. You can adjust it with `RESELLER_API_RATE_LIMIT` and `RESELLER_API_RATE_WINDOW`.

Rate limit headers are returned on successful protected reseller requests:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1783333333
```

## Test Your Key

```http
GET /api/reseller/me
X-Reseller-Key: YOUR_KEY
```

Response:

```json
{
  "success": true,
  "user_telegram_id": 123456789,
  "username": "partner",
  "first_name": "Partner",
  "wallet_balance": 42.5,
  "key_name": "Partner bot",
  "key_prefix": "abc123"
}
```

## Product Catalog

```http
GET /api/reseller/products?lang=en
X-Reseller-Key: YOUR_KEY
```

`lang` accepts `en`, `fr`, `ar`, `zh`, `vi`, and `ru`. An unsupported value falls back to English.

Response:

```json
{
  "success": true,
  "products": [
    {
      "id": 10,
      "name": "Product",
      "description": "Description",
      "emoji": "box",
      "image_url": null,
      "price_usd": 5.0,
      "standard_price_usd": 6.0,
      "pricing_type": "reseller_special",
      "special_price_expires_at": null,
      "warranty_days": 7,
      "delivery_type": "stock",
      "stock": 12,
      "price_tiers": []
    }
  ]
}
```

The catalog is personalized for the authenticated reseller account. When an administrator assigns a special product price, `price_usd` is the effective fixed unit price, `pricing_type` is `reseller_special`, and `standard_price_usd` contains the price before the override. A reseller special price replaces quantity tiers. Always use the current catalog or quote response instead of copying a price from another API key.

The catalog supports conditional HTTP caching. Save the `ETag` response header, then send it on the next request:

```http
GET /api/reseller/products?lang=en
X-Reseller-Key: YOUR_KEY
If-None-Match: "CATALOG_ETAG"
```

If nothing changed, the API returns `304 Not Modified` with no response body. Continue using your cached catalog. A normal `200` response also includes:

```http
ETag: "CATALOG_ETAG"
X-Catalog-Version: 12
X-Catalog-Stale: false
```

`X-Catalog-Stale: true` means a temporary database or supplier failure occurred and the API safely returned its last known catalog snapshot. Purchases still perform their own live balance and stock checks.

### Low-cost API test product

The authenticated reseller catalog also contains **VenteBot API Test Product** with `delivery_type: "api_test"` and `api_test: true`. It is virtual and is never displayed in the regular Telegram customer catalog. It costs `$0.01`, supports quantity `1` per order, and returns synthetic delivery data. There is no hourly purchase cap: create as many distinct test orders as needed. Each order uses the real reseller wallet so the entire debit, idempotency, response parsing, and delivery flow can be tested safely.

## Quote Before Buying

```http
POST /api/reseller/quote
X-Reseller-Key: YOUR_KEY
Content-Type: application/json

{
  "product_id": 10,
  "quantity": 2
}
```

Response:

```json
{
  "success": true,
  "quote": {
    "product_id": 10,
    "quantity": 2,
    "unit_price": 5.0,
    "standard_unit_price": 6.0,
    "pricing_type": "reseller_special",
    "total": 10.0,
    "delivery_type": "stock",
    "stock": 12
  },
  "wallet_balance": 42.5
}
```

## Buy a Stock Product

```http
POST /api/reseller/orders
X-Reseller-Key: YOUR_KEY
Content-Type: application/json

{
  "product_id": 10,
  "quantity": 1,
  "customer_reference": "telegram-client-555",
  "idempotency_key": "telegram-client-555-product-10-2026-07-06"
}
```

Response:

```json
{
  "success": true,
  "status": "ok",
  "idempotent": false,
  "balance_after": 37.5,
  "unit_price": 5.0,
  "standard_unit_price": 6.0,
  "pricing_type": "reseller_special",
  "total": 5.0,
  "order": {
    "id": 123,
    "status": "COMPLETED",
    "product_id": 10,
    "product_name": "Product",
    "quantity": 1,
    "amount_usd": 5.0,
    "delivery_type": "stock",
    "customer_reference": "telegram-client-555",
    "items": [
      { "id": 987, "account_data": "email@example.com:password" }
    ]
  }
}
```

Your bot can then send `account_data` to its customer.

If the same `idempotency_key` is submitted again, the API returns the existing order with `idempotent: true` and does not debit the wallet or deliver stock again. On this replay response, `balance_after`, `unit_price`, and `total` can be `null`; use `order.amount_usd` for the original order total.

## Buy a Supplier API Product

Supplier-backed products use `delivery_type: "supplier_api"`. The same purchase endpoint and idempotency rules apply. Most successful purchases return `COMPLETED` immediately with credentials in `order.items`.

If the supplier needs more time, the response is:

```json
{
  "success": true,
  "status": "ok",
  "order": {
    "id": 125,
    "status": "PAID_PENDING_DELIVERY",
    "delivery_type": "supplier_api",
    "items": []
  }
}
```

Do not send an empty message to the customer. Poll `GET /api/reseller/orders/125` using a short backoff. Deliver `order.items` only after the status becomes `COMPLETED`. Reuse the original `idempotency_key` if the create-order request itself must be retried.

## Buy an Activation Product

```http
POST /api/reseller/orders
X-Reseller-Key: YOUR_KEY
Content-Type: application/json

{
  "product_id": 20,
  "quantity": 1,
  "activation_identifier": "@client_telegram",
  "customer_reference": "telegram-client-555",
  "idempotency_key": "telegram-client-555-product-20-2026-07-06"
}
```

Response:

```json
{
  "success": true,
  "status": "ok",
  "order": {
    "id": 124,
    "status": "AWAITING_ACTIVATION",
    "delivery_type": "activation",
    "activation_identifier": "@client_telegram",
    "items": []
  }
}
```

The admin will see this activation in the dashboard and in `/admin`.

## Submit the Activation Identifier Later

If the order was created without `activation_identifier`:

```http
POST /api/reseller/orders/124/activation-identifier
X-Reseller-Key: YOUR_KEY
Content-Type: application/json

{
  "activation_identifier": "@client_telegram"
}
```

## Read an Order

```http
GET /api/reseller/orders/123
X-Reseller-Key: YOUR_KEY
```

## Wallet History

```http
GET /api/reseller/wallet/transactions?limit=50&offset=0
X-Reseller-Key: YOUR_KEY
```

`limit` accepts values from `1` to `100`. The default is `50`.

## Just-in-time BEP20 Wallet Funding

The reseller can fund its VenteBot wallet automatically before creating an order. The current implementation supports `USDT` on `BEP20`. Direct crypto payment attached to each reseller order is not exposed; deposit only the missing wallet amount, wait for `CREDITED`, then create the normal idempotent order.

Recommended flow:

1. Receive and confirm your own customer's payment.
2. Call `GET /api/reseller/me` and calculate the missing VenteBot wallet amount.
3. Read the current network minimum from `GET /api/reseller/wallet/deposit-methods`.
4. Create one deposit with a persistent `idempotency_key`.
5. Send exactly the returned `pay_amount` to the returned `address` before `expires_at`.
6. Poll the deposit every 10 to 15 seconds, or receive signed webhooks.
7. Create the reseller order only after the deposit status becomes `CREDITED`.

### Supported deposit methods

```http
GET /api/reseller/wallet/deposit-methods
X-Reseller-Key: YOUR_KEY
```

The provider minimum can change, so read `minimum_deposit_usd` immediately before creating a deposit. A null minimum with an `error` means the provider minimum is temporarily unavailable.

### Create a deposit

```http
POST /api/reseller/wallet/deposits
X-Reseller-Key: YOUR_KEY
Content-Type: application/json

{
  "amount_usd": 5.0,
  "network": "BEP20",
  "idempotency_key": "fund-checkout-555-001",
  "reference": "checkout-555"
}
```

Example response:

```json
{
  "success": true,
  "idempotent": false,
  "deposit": {
    "deposit_id": "dep_a1b2c3d4e5f6",
    "status": "WAITING",
    "wallet_credit_amount": 5.0,
    "pay_amount": 5.012345,
    "pay_currency": "USDTBSC",
    "network": "BEP20",
    "address": "0x...",
    "memo": null,
    "fees": {
      "ventebot_fee_usd": 0.0,
      "provider_quote_included": true
    },
    "expires_at": "2026-07-19T18:10:00Z"
  }
}
```

The wallet receives `wallet_credit_amount`. The blockchain transfer must use the exact provider `pay_amount`; never add or subtract a local fee buffer. Retrying the exact request with the same key returns the existing deposit and never creates a second provider invoice.

### Read a deposit

```http
GET /api/reseller/wallet/deposits/dep_a1b2c3d4e5f6?refresh=true
X-Reseller-Key: YOUR_KEY
```

Statuses are `CREATING`, `CREATION_UNKNOWN`, `WAITING`, `CONFIRMING`, `UNDERPAID`, `CREDITED`, `EXPIRED`, `FAILED`, `REFUNDED`, or `REVIEW_REQUIRED`. `stale: true` means VenteBot returned its last stored state because the payment provider could not be refreshed; retry later without creating another deposit.

## IP Allowlisting and Signed Webhooks

Read or update security settings with:

```http
GET /api/reseller/security
X-Reseller-Key: YOUR_KEY
```

```http
PUT /api/reseller/security
X-Reseller-Key: YOUR_KEY
Content-Type: application/json

{
  "ip_allowlist": ["203.0.113.10/32"],
  "webhook_url": "https://store.example.com/webhooks/ventebot",
  "webhook_enabled": true,
  "rotate_webhook_secret": false
}
```

Use IP restrictions only when the calling bot has a stable outbound IP. An empty list allows every IP. Webhook URLs must use HTTPS, port 443, and resolve only to public IP addresses.

The signing secret is returned only when webhooks are enabled for the first time or when `rotate_webhook_secret` is true. Store it immediately. Deposit events are retried by a durable background queue and include:

```http
X-Vente-Event-Id: evt_...
X-Vente-Event: deposit.credited
X-Vente-Timestamp: 1784484000
X-Vente-Signature: v1=...
```

Verify `HMAC-SHA256(secret, timestamp + "." + raw_request_body)`, reject timestamps older than five minutes, compare signatures in constant time, and deduplicate by `X-Vente-Event-Id`.

```js
import crypto from "node:crypto";

function validVenteSignature(rawBody, timestamp, received, secret) {
  const expected = "v1=" + crypto
    .createHmac("sha256", secret)
    .update(`${timestamp}.${rawBody}`)
    .digest("hex");
  return expected.length === received.length &&
    crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(received));
}
```

## Common Error Codes

- `401`: missing, invalid, or revoked key.
- `400`: unavailable product, insufficient stock, invalid quantity, or an order in the wrong state.
- `402`: insufficient wallet balance.
- `403`: the caller IP is outside the configured allowlist.
- `404`: order not found or outside the reseller account.
- `409`: an idempotency key was reused with a different request, or an order state changed during an update.
- `422`: invalid request format, for example missing `product_id`, non-numeric `quantity`, or an activation identifier that is too short.
- `429`: rate limit exceeded.
- `500`: unexpected server error. Keep the same `idempotency_key` if you retry a purchase whose result is unknown.
- `503`: authentication database temporarily unavailable. Wait for the `Retry-After` delay and retry with the same `idempotency_key`.

Errors return a stable JSON format:

```json
{
  "success": false,
  "code": "INSUFFICIENT_BALANCE",
  "message": "Insufficient wallet balance"
}
```

Validation errors include a `details` array:

```json
{
  "success": false,
  "code": "VALIDATION_ERROR",
  "message": "Invalid request format.",
  "details": []
}
```

## JavaScript Example

```js
const API_URL = "https://your-domain.com";
const KEY = "vbr_live_xxxxx_yyyyyyyy";

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function buy(productId, customerId, idempotencyKey) {
  const body = JSON.stringify({
    product_id: productId,
    quantity: 1,
    customer_reference: String(customerId),
    idempotency_key: idempotencyKey
  });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    const res = await fetch(`${API_URL}/api/reseller/orders`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Reseller-Key": KEY
      },
      body
    });

    const data = await res.json();
    if (res.ok && data.success !== false) return data.order;

    if (res.status === 503 && attempt < 2) {
      const retryAfter = Number(res.headers.get("Retry-After") || 3);
      await sleep(retryAfter * 1000);
      continue;
    }

    throw new Error(`${data.code || "API_ERROR"}: ${data.message || "API error"}`);
  }
}

// Generate and persist this value when the customer starts the purchase.
// Reuse the exact same value until that purchase succeeds or is reconciled.
const order = await buy(10, 555, "customer-555-checkout-20260711-001");
```
