# Quickstart

1. `.venv/bin/python -m pytest tests/unit/pipeline/test_market_registration.py tests/unit/connectors/test_market_types.py -q`
2. `cd apps/web && npx vitest run src/__tests__/marketsFiveRows.test.tsx`
3. Live: `docker compose up -d --build --no-deps ingest-binance ingest-binance-eth ingest-binance-sol ingest-bybit ingest-okx`,
   then `curl localhost:8000/api/v1/markets` lists five entries with types binance spot, bybit and okx perp.
4. Twice more `docker compose restart ingest-bybit`; the list still has five.
