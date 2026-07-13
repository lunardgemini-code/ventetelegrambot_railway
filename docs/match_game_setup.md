# Match Arena setup

Match Arena is an optional football prediction game that uses virtual Batman Coins only. Batman Coins have no cash value, cannot be purchased, and cannot be withdrawn.

## 1. Configure the sports provider

1. Create an API token on `football-data.org`.
2. In Railway, open the bot service, then **Variables**.
3. Add `FOOTBALL_DATA_API_KEY` with the provider token.
4. Keep `FOOTBALL_DATA_BASE_URL=https://api.football-data.org/v4`.
5. Redeploy the service.

The token remains server-side. It is never returned by the dashboard API or shown to Telegram users.

## 2. Select matches

Open **Jeu & Matchs** in the dashboard:

1. Choose a date range of up to 31 days.
2. Filter by competition, provider status, team, or stage.
3. Click **Configurer** on a scheduled match.
4. Select the market, lock time, minimum and maximum stake, and game fee.
5. Publish immediately or save a draft and publish later.

Only published matches appear in Telegram. Predictions close automatically at `kickoff - lock time`.

## 3. Markets and settlement

- **Team to qualify**: two choices; extra time and penalties are included.
- **Result after 90 minutes**: home, draw, or away; extra time and penalties are excluded.

The sports API synchronizes only selected matches. When the provider reports a final score, the dashboard proposes a result in **Résultats à confirmer**. An administrator must confirm it before coins are distributed.

Payouts use a pari-mutuel pool: the distributable pool is shared proportionally among winners after the configured game fee. If nobody selected the winning outcome, all active stakes are refunded. Settlement and cancellation are idempotent.

## 4. Lightweight defaults

- Daily claim: `GAME_DAILY_CLAIM=300`
- Minimum stake: `GAME_DEFAULT_MIN_STAKE=25`
- Maximum stake: `GAME_DEFAULT_MAX_STAKE=500`
- Pool fee: `GAME_DEFAULT_FEE_BPS=500` (5%)
- Background cycle: `GAME_SYNC_WORKER_SECONDS=120`

The dashboard catalog is cached for five minutes, the Telegram match list for twenty seconds, and synchronization becomes more frequent only near kickoff.
