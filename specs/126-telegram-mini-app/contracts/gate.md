# Contract: the API gate

1. **Scope**: every HTTP route under `/api/v1/`, and the websocket `/ws/market`.
2. **Mode off**: nothing changes.
3. **Mode required**: a request without `Authorization: tma <initData>` that verifies gets `401` with a
   body carrying no market data and a `reason` from the closed set; a verifying request gets the response
   it would get today, byte for byte. The websocket is refused with close code 1008.
4. **Start**: mode `required` with no `TELEGRAM_BOT_TOKEN` stops the service, naming the variable.
5. **Never**: the token, the header, or the user's identity in a log record, an error message or a body.
6. **Not gated and not reachable through the public address**: `/readyz`, `/metrics`.
