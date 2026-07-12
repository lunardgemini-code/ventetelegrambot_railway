# VenteBot Reseller API

This API lets a partner bot resell VenteBot products using the reseller account wallet balance.

API version: `1.0.1`. This documentation update is backward compatible with existing integrations.

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
- For `stock` products, delivered accounts are returned in `order.items`.
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
      "warranty_days": 7,
      "delivery_type": "stock",
      "stock": 12,
      "price_tiers": [
        { "min_qty": 5, "max_qty": 10, "price_usd": 4.5 }
      ]
    }
  ]
}
```

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

## Common Error Codes

- `401`: missing, invalid, or revoked key.
- `400`: unavailable product, insufficient stock, invalid quantity, or an order in the wrong state.
- `402`: insufficient wallet balance.
- `404`: order not found or outside the reseller account.
- `409`: the order state changed while an activation identifier was being submitted; reload the order before deciding whether to retry.
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
