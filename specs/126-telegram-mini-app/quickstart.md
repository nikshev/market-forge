# Quickstart

## 1. The verifier and the gate (no services)
    .venv/bin/python -m pytest tests/unit/api/test_telegram_auth.py tests/unit/api/test_telegram_gate.py tests/unit/deploy/test_telegram_profile.py -q

## 2. The page (Node)
    make web-install && make web-test

## 3. Locally, in a plain browser, with a signed launch
    cd apps/web && npm run dev:init -- --token <the bot token or a dev one>   # writes .env.development.local
    CHANNELFLOW_TELEGRAM_AUTH=required TELEGRAM_BOT_TOKEN=<same> ...           # start the API
    npm run dev

## 4. In Telegram (needs the owner's bot token and tunnel)
Create the bot with @BotFather; create a Cloudflare Tunnel whose public hostname points at `http://web:8080`;
set `TELEGRAM_BOT_TOKEN`, `CHANNELFLOW_TELEGRAM_AUTH=required`, `CHANNELFLOW_TUNNEL_TOKEN` in `.env`;
`docker compose --profile telegram up -d --build`; in BotFather set the Mini App URL to the public
hostname. Open the bot on a phone: overview, a market's chart, the timeframe selector, the channel overlay.
