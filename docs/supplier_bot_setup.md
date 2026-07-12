# External supplier bot setup

The **API Bot Management** dashboard connects VenteBot to the Canboso Telegram
buyer API. Supplier credentials remain server-side and are never returned to the
browser.

## Railway variables

```env
CANBOSO_API_KEY=replace_with_a_new_telegram_buyer_key
CANBOSO_API_BASE_URL=https://canboso.com
CANBOSO_API_AUTH_HEADER=X-API-Key
```

After deployment:

1. Open **API Bot Management**.
2. Click **Sync catalog**.
3. Set the global margin to a fixed USD amount or percentage.
4. Enable only the products that should appear in the Telegram bot.
5. Optionally override the global margin for an individual product.

## Pricing

- Fixed margin: `customer price = supplier price + margin`.
- Percentage margin: `customer price = supplier price * (1 + margin / 100)`.
- Existing customer orders keep the amount recorded when the order was created.
- A catalog sync updates supplier prices, remote stock, and enabled local product
  prices.

## Wallet-based availability

- The dashboard reads the supplier wallet through
  `GET /api/telegram-buyer/balance`.
- Customer-facing availability is
  `min(remote stock, floor(supplier wallet balance / supplier unit price))`.
- The supplier unit price is used for this calculation, before the resale margin.
- A supplier product with zero affordable units is hidden from the Telegram
  catalog, even when the supplier still reports remote stock.
- Availability is checked again immediately before a customer wallet debit.
- The balance cache is cleared after every successful supplier purchase.
- If the supplier balance endpoint is unavailable, supplier products fail closed
  with zero customer-facing availability until the balance can be verified.

## Delivery safety

Each local order has at most one supplier purchase record. Completed purchases
are replayed from the local receipt without calling the supplier again. If a POST
times out after being sent, the result is marked `unknown` and is not retried
automatically because the supplier may already have debited the buyer wallet.

An explicit supplier rejection is marked `failed`. A paid customer order remains
`PAID_PENDING_DELIVERY` instead of being lost or incorrectly completed.

## Supplier contract

- `GET /api/telegram-buyer/products` lists available products.
- `POST /api/telegram-buyer/purchase` purchases a product using the supplier-side
  buyer wallet.
- Authentication is accepted through the configured header; the documented
  `key` query/body field is also sent for compatibility.
- Purchase body: `key`, `product_id`, and `quantity`.

The response adapter accepts common catalog envelopes such as `products`, `data`,
or a direct list, and delivery fields such as `items`, `accounts`, `credentials`,
or `account_data`, including Canboso's `deliveredAccounts`. Verify the live response contract with a low-value test order
before enabling customer traffic.
