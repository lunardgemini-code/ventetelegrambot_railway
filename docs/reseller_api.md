# VenteBot Reseller API

This API lets a partner bot resell VenteBot products using the reseller account wallet balance.

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

The reseller can generate a key directly inside the Telegram bot with **API** then **Generate API key**. The full key is shown only once when it is created.

The admin can also create or revoke keys from the dashboard, in the **Resellers** tab.

If a reseller generates a new key from the bot, the previous active key is automatically disabled.

## Important Rules

- The reseller wallet must have enough balance.
- API purchases debit the reseller wallet.
- To avoid duplicate purchases if your bot retries the same request, always send `idempotency_key`.
- For `stock` products, delivered accounts are returned in `order.items`.
- For `activation` products, send `activation_identifier` when creating the order, or later with the dedicated endpoint.

## Test Your Key

```http
GET /api/reseller/me
X-Reseller-Key: YOUR_KEY
```

Response:

```json
{
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

`lang` accepts `en`, `fr`, `ar`, `zh`.

Response:

```json
{
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

## Common Error Codes

- `401`: missing, invalid, or revoked key.
- `400`: unavailable product, insufficient stock, invalid quantity, or missing activation identifier.
- `402`: insufficient wallet balance.
- `404`: order not found or outside the reseller account.
- `500`: server error.

## JavaScript Example

```js
const API_URL = "https://your-domain.com";
const KEY = "vbr_live_xxxxx_yyyyyyyy";

async function buy(productId, customerId) {
  const res = await fetch(`${API_URL}/api/reseller/orders`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Reseller-Key": KEY
    },
    body: JSON.stringify({
      product_id: productId,
      quantity: 1,
      customer_reference: String(customerId),
      idempotency_key: `${customerId}-${productId}-${Date.now()}`
    })
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "API error");
  return data.order;
}
```
