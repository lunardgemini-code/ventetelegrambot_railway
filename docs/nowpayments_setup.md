# NOWPayments USDT/BEP20 Setup

The integration creates direct `USDTBSC` payments and confirms them through signed IPN callbacks. The existing manual BEP20 payment remains available as a fallback.

## NOWPayments account

1. Enable USDT on BNB Smart Chain (`USDTBSC`) in NOWPayments.
2. Configure the Primary Balance or outcome wallet that will receive the funds.
3. Generate a production API key.
4. Generate an IPN secret and store it immediately; NOWPayments displays the complete secret only when it is created.
5. Regenerate any credential that has been pasted into chat, logs, screenshots, tickets, or source code.

## Railway variables

```env
NOWPAYMENTS_ENABLED=true
NOWPAYMENTS_API_KEY=replace_with_a_new_api_key
NOWPAYMENTS_IPN_SECRET=replace_with_a_new_ipn_secret
NOWPAYMENTS_BASE_URL=https://api.nowpayments.io/v1
NOWPAYMENTS_FIXED_RATE=false
NOWPAYMENTS_FEE_PAID_BY_USER=false
NOWPAYMENTS_RECONCILE_SECONDS=60
WEBHOOK_URL=https://your-service.up.railway.app
```

The generated callback URL is:

```text
https://your-service.up.railway.app/webhooks/nowpayments
```

Set `NOWPAYMENTS_CALLBACK_URL` only when the callback must use a different public HTTPS URL.

## Payment rules

- Delivery occurs only for `finished` payments.
- Floating rate is the default so low-priced products can use the lowest available minimum.
- Set both `NOWPAYMENTS_FIXED_RATE=true` and `NOWPAYMENTS_FEE_PAID_BY_USER=true` only when a higher fixed-rate minimum is acceptable.
- `waiting`, `confirming`, `confirmed`, `sending`, and `spending` never trigger delivery.
- `partially_paid` asks the customer to send the remainder to the same address.
- `failed`, `refunded`, and `expired` do not trigger delivery.
- Currency, original USD price, requested USDT amount, and actually paid amount are validated before delivery.
- Every payment, stock reservation, finance update, and notification is idempotent.
- Missed IPNs are recovered by polling active payments with `GET /v1/payment/{payment_id}`.

## Deployment check

1. Deploy the application and confirm `/health` returns `200`.
2. Confirm the NOWPayments button appears in the Telegram checkout.
3. Create a sandbox payment before enabling production credentials.
4. Verify invalid IPN signatures return `401`.
5. Verify a finished sandbox payment is delivered once, even if the callback is sent twice.
6. Verify the order displays `NOWPayments · BEP20` in the dashboard.

Never place the real API key or IPN secret in this repository.
