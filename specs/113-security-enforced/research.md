# Phase 0 — Research

Everything below was measured against this checkout during planning.

## Does anything already leak a credential?

**Decision**: yes, and it is the centre of this work. `Settings` gets a `repr`
and a `str` that mask credentials, and the tests pin what is masked *and* what
is still shown.

**Rationale**: measured. `Settings` is `@dataclass(frozen=True)`, so its
generated `repr` renders every field:

    password visible in repr:  True
    s3 secret visible in repr: True

The Postgres password lives inside `catalog_uri`; the S3 secret is
`storage['s3.secret-access-key']`. Any f-string, any exception that interpolates
the object, any traceback rendering local variables spills both. §34's "redact
secrets from logs" is usually read as a logging rule; here the leak is in the
type, and logging would only be the delivery mechanism.

**Alternatives considered**: a lint that forbids `logger.*(settings)`. Rejected —
it catches one spelling of the mistake and misses `f"{settings}"`, `print`,
`assert x, settings` and every traceback.

**What must still be visible.** A mask that hides everything makes the object
useless for diagnosis, and somebody will then log the fields individually. So the
host, port and database of the catalog URI stay; only the password becomes
`***`. `s3.access-key-id` is an identifier, not a secret, and stays;
`s3.secret-access-key` goes entirely.

## What did *not* leak

`/readyz` serves `catalog_probe`'s `detail` string, built as `f"the catalog did
not answer: {cause}"`, and the URI carries the password — so an unauthenticated
endpoint looked like it could echo it. Measured across connection refused, wrong
password against a live server, and unresolvable host: the password appears in
**none** of the three messages. `psycopg` names host and port; SQLAlchemy keeps
the URL out of its exception text.

Recorded because a plausible leak that turns out not to be real is worth writing
down once, so nobody re-investigates it — and because it is the reason the fix
above is on `Settings` rather than on the probe.

## How do you enumerate every route, actually?

**Decision**: descend through `original_router.routes`, and assert the total.

**Rationale**: measured on FastAPI 0.141.1. `app.routes` is **not** flat:

    top-level: ['Route', 'Route', 'Route', 'Route',
                '_IncludedRouter', '_IncludedRouter', '_IncludedRouter',
                'APIWebSocketRoute']

A naive iteration sees five things: four documentation routes and the websocket.
The twelve routes that matter are inside the `_IncludedRouter` objects, which
expose neither `.path` nor `.routes` — the way in is `.original_router`. And
because a naive walk finds no non-`GET` method, it **passes**. A gate written the
obvious way would be green and prove nothing.

So the test asserts the count as well as the property. Seventeen routes today:
twelve `APIRoute`, four documentation `Route`s (which answer `GET` and the `HEAD`
Starlette adds), one `APIWebSocketRoute`.

**Alternatives considered**: reading the OpenAPI schema. Rejected — it omits the
websocket entirely and would silently drop exactly the route that is hardest to
classify.

## In-process rate limiting, or a shared one?

**Decision**: in-process fixed window, no new dependency, clock injected.

**Rationale**: one API process runs. A shared counter needs a store; [[ADR-002]]
dropped Redis as unnecessary and nothing has needed it since, so adding it here
would be building for a deployment that does not exist. A fixed window is O(1),
holds no lock across I/O, and its edge behaviour — up to twice the limit across a
window boundary — is simple enough to state plainly, which a sliding log is not.

The clock is an argument, because Principle VII forbids a test-only branch: the
tests drive the same code a deployment runs, just with a clock they control.

**Alternatives considered**: `slowapi` or `limits`. Rejected — a dependency for
arithmetic. Rate limiting in nginx: rejected, it protects only what arrives
through nginx and the API is reachable directly.

**The cost, written down**: with N API processes the effective limit is N times
the configured one. Documented rather than discovered.

## What is exempt?

**Decision**: `/metrics` and `/readyz`.

**Rationale**: throttling a readiness probe makes an orchestrator declare the
service unhealthy — the limiter causing the outage it exists to prevent. A
Prometheus scrape interval is already a rate limit.

## CORS

**Decision**: origins from configuration; empty means no middleware installed at
all; a wildcard is refused at startup.

**Rationale**: today no CORS middleware exists, so no `Access-Control-Allow-Origin`
is ever sent and a browser refuses every cross-origin read. That is the correct
end state for this deployment — the web app is served same-origin behind nginx,
which proxies `/api`. The requirement is not to add permissiveness but to make
the current restriction deliberate and to make the permissive mistake impossible
to ship. Refusing at startup rather than warning follows `settings_from_env`,
which already raises rather than defaulting.

## Binding

**Decision**: one variable, `CHANNELFLOW_BIND_ADDRESS`, defaulting to
`127.0.0.1`, used by every published port.

**Rationale**: nine services publish with a bare `"${PORT}:…"`, which binds all
interfaces. One named place to change beats nine lines an operator edits by hand
(Principle X), and a default of loopback means the safe case needs no decision.

**A trap worth naming.** On Linux, Docker inserts its rules into the `DOCKER`
chain of the `nat` table, traversed before the `INPUT` chain that `ufw` manages
by default — so a published port can be reachable while `ufw` reports the port
denied. Binding to loopback removes the question rather than answering it.
