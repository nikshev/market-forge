# Contract: what the API refuses, and what the host publishes

## Configuration

| variable | default | meaning |
|---|---|---|
| `CHANNELFLOW_CORS_ORIGINS` | empty | comma-separated origins; empty installs no CORS middleware; `*` is refused at startup |
| `CHANNELFLOW_RATE_LIMIT` | empty | requests per window; empty means no limiting, chosen explicitly |
| `CHANNELFLOW_RATE_WINDOW_SECONDS` | `60` | the window |
| `CHANNELFLOW_BIND_ADDRESS` | `127.0.0.1` | the address every compose service publishes on |
| `GRAFANA_ADMIN_PASSWORD` | empty | Grafana's credential; anonymous access is off unless `GRAFANA_ANONYMOUS` is set |

Empty means absent, as everywhere else in `settings.py`: a variable a shell gives
for one nobody set.

## The limiter

```python
@dataclass(frozen=True)
class RateLimit:
    requests: int
    window_seconds: float

class FixedWindowLimiter:
    def __init__(self, limit: RateLimit, *, clock: Callable[[], float]) -> None: ...
    def allow(self, key: str) -> Decision: ...   # never raises, never blocks
```

`Decision` carries `allowed: bool` and `retry_after_seconds: float`.

- Keyed on the client address as the application sees it. Behind a proxy that is
  the proxy's address — stated, not silently trusted from a header.
- `/metrics` and `/readyz` are exempt.
- A refusal is answered `429` with `Retry-After`. Immediately: not queued, not
  delayed.
- The clock is an argument (Principle VII). There is no test-only branch.

**Edge behaviour, stated rather than hidden**: a fixed window admits up to twice
the limit across a boundary — the last requests of one window and the first of
the next. A sliding log would not, at the cost of per-key storage proportional to
the limit. Correctness before performance, and the simpler thing whose failure
mode is written down.

## The route gate

```python
def offending_routes(app: FastAPI, *, authenticated: frozenset[str]) -> list[tuple[str, list[str]]]: ...
```

Walks `app.routes`, descending into `original_router.routes` for every included
router. Returns routes whose methods exceed `{GET, HEAD}` and are not in
`authenticated`.

The test that uses it **must also assert the number of routes walked**. A
traversal that silently stops descending finds nothing and reports success; the
count is what separates "no offending routes" from "no routes".

## The exposure check

Reads `docker-compose.yml` and, for every service publishing a port, requires the
host side to be `${CHANNELFLOW_BIND_ADDRESS}:<port>`. A bare `"${PORT}:…"` fails.
A service meant to be public is named in one list in the test, with the reason.
