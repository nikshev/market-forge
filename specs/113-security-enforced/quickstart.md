# Quickstart — validating REQ-WP-072

No services, no network.

```bash
make test-fast
.venv/bin/pytest tests/unit/api/test_security.py tests/unit/deploy/test_exposure.py -v
```

## What proves the requirement

| Scenario | Expected |
|---|---|
| `repr(settings)` with a password-bearing catalog URI | password is `***`; host, port and database still readable |
| `repr(settings)` with an S3 secret | `s3.secret-access-key` is `***`; `s3.access-key-id` still shown |
| `str(settings)` | identical to `repr` — no unmasked second spelling |
| walk the app's routes | exactly 17, and none with a method outside `{GET, HEAD}` |
| register a `POST` handler, walk again | the route is reported; the suite is red |
| register a `POST` on the authenticated allow-list | permitted |
| `CHANNELFLOW_CORS_ORIGINS="*"` | startup raises `WildcardOrigin` |
| `CHANNELFLOW_CORS_ORIGINS=""` | no CORS middleware installed; no `Access-Control-Allow-Origin` on any response |
| limit 3/60s, four requests | first three served, fourth `429` with `Retry-After` |
| the same, with the clock advanced past the window | served again |
| `/readyz` and `/metrics` beyond the limit | served — they are exempt |
| `CHANNELFLOW_RATE_LIMIT=0` | `InvalidRateLimit` |
| read `docker-compose.yml` | every published port binds `${CHANNELFLOW_BIND_ADDRESS}` |
| `docs/deployment.md` exposure table | matches the compose file service for service |

## Trying the limiter by hand

```bash
CHANNELFLOW_RATE_LIMIT=3 make up
for i in 1 2 3 4; do curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/v1/markets; done
# 200 200 200 429
```
