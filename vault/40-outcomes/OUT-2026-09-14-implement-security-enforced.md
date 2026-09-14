---
id: OUT-2026-09-14-implement-security-enforced
step: implement
records: [REQ-WP-072]
commit: null
---

## What was done

Implemented [[REQ-WP-072]] — PRD §34, the only section of the PRD that had no
requirement note. Each of its eight bullets now has a test that fails when it is
violated.

- `src/channelflow/settings.py` — `mask_password`, `Settings.__repr__`/`__str__`,
  `RateLimit`, `InvalidRateLimit`, `WildcardOrigin`, `allowed_origins`,
  `rate_limit`.
- `src/channelflow/api/security.py` (new) — `all_routes`, `offending_routes`,
  `FixedWindowLimiter`, `Decision`, `RateLimitMiddleware`.
- `src/channelflow/api/app.py`, `api/main.py` — CORS and the limiter wired in.
- `docker-compose.yml` — eight port mappings rebound through
  `CHANNELFLOW_BIND_ADDRESS`; Grafana's anonymous admin made opt-in.
- `.env.example`, `docs/deployment.md` — the new names, an exposure table, and
  three stale claims corrected.
- `tests/unit/test_settings.py`, `tests/unit/api/test_security.py`,
  `tests/unit/deploy/test_exposure.py`, `tests/unit/deploy/test_section_34.py`.
- `tests/mutations/security.toml`, `tests/mutations/api_security.toml`.

### RED, before any implementation existed

    $ .venv/bin/python -m pytest tests/unit/test_settings.py -q
    E   ImportError: cannot import name 'InvalidRateLimit' from 'channelflow.settings'

    $ .venv/bin/python -m pytest tests/unit/api/test_security.py -q
    E   ModuleNotFoundError: No module named 'channelflow.api.security'

    $ .venv/bin/python -m pytest tests/unit/deploy/test_exposure.py -q
    5 failed, 2 passed

The two that passed in the third file are its vacuity guards — "the compose file
still publishes ports" — which must pass for the other five to mean anything.

GREEN: 2639 tests including integration; `ruff` clean; `mypy --strict` clean over
218 files.

### §34, bullet by bullet

| §34 requirement | what fails when it is violated |
|---|---|
| no exchange trading keys | `test_no_connector_reads_a_trading_credential` |
| Telegram token via secret manager | `test_the_alerting_package_reads_no_environment` |
| RPC API keys via secrets | `test_no_rpc_endpoint_carries_a_key_in_its_url` |
| no secrets committed | `test_the_environment_file_is_ignored_and_the_template_holds_no_live_secret` |
| redact secrets from logs | eleven tests in `tests/unit/test_settings.py` |
| write/admin routes authenticated | six tests in `tests/unit/api/test_security.py` |
| CORS restricted in production | four tests, plus `WildcardOrigin` at startup |
| rate limiting | nine tests |

## What was decided

**The mask is the type's, and what survives it is part of the contract.** The
catalog URI keeps scheme, user, host, port and database; `s3.access-key-id` is an
identifier and stays. A mask that hid everything would make the object useless to
read, and whoever needed the host would render the fields one at a time.

**The masking parses by position, never by splitting on punctuation** — and the
mutation sweep proved why in the sharpest possible way. See below.

**`create_app` takes the clock.** Principle VII: the tests drive the same code a
deployment runs, with a clock they control. There is no test-only branch.

**CORS middleware is absent rather than present-and-empty when no origin is
configured.** An empty allow-list still emits `Vary: Origin` and invites the
question; no middleware emits nothing, which is the state this application was
already in and the one §34 wants.

### The mutation sweep found three weak assertions, and one was alarming

28 mutations. First run **25 caught, 3 survived**. Every survivor was a weak
test, and all three are now killed by stronger assertions rather than by a
recorded excuse.

Two of them are the same mistake and are worth writing down in full. The
mutations moved the URI split by one position — `partition("@")` instead of
`rpartition`, and `rpartition(":")` instead of `partition`. Measured, they
produce:

    password `p@ssword`   →  postgresql+psycopg://cf:***@ssword@db:5432/cf
    password `a:b:c`      →  postgresql+psycopg://cf:a:b:***@db:5432/cf

In both, **the whole password is absent from the output while most of it is
present**. The test asserted `password not in rendered`, so both passed. A mask
that redacts a single character of a secret looked correct to the only test
watching it. The assertion is now the exact expected string, and the parametrised
case gained `::@@::`.

The third: `tracked_keys()` mutated to return a constant `1`, and the test only
ever checked one key's cost. It now checks four.

Second run: **28 caught, 0 survived.**

### Corrections made during implementation

Three, all mine:

- A test asserted the module's own source contained no `"socket"`. The word lives
  inside `"websocket"`. Rewritten to walk the imports with `ast`.
- `test_no_rpc_endpoint_carries_a_key_in_its_url` rejected any query string.
  `?symbol=BTCUSDT` is data, not a credential. It now matches parameter *names*
  that look like keys, and key-shaped path segments.
- `docs/deployment.md`'s "what is not covered" listed **load tests**, and the
  document test required that string. Checked: `channelflow.perf.load` exists,
  is tested, and closed [[REQ-PHASE-8]]'s acceptance line for §36's targets. The
  gap was stale, so the document says where load tests went and the test now
  requires `TLS` and `Backups` instead.

## What is still open

**The gate has no chokepoint for a future `PoolState`-style bridge** — the same
shape as [[REQ-WP-071]]'s open item. `offending_routes` is called by a test, not
by startup. A route registered after the app is built would not be seen until the
suite runs. That is enough: the suite is the gate, and a write route that never
runs in CI is not a route that ships.

**TLS is not terminated anywhere**, and the deployment document now says so.
This stack expects an SSH tunnel or something in front of it.

**The limiter's scope is one process**, written in the code, the contract and
the deployment document. With N processes the effective limit is N times the
configured one.

**§34's closing sentence** — "If trading is added later, separate execution
service and separate credentials entirely" — constrains work that does not exist.
Principle IX already forbids automatic execution in Phases 1-3.
