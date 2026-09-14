---
traces: [REQ-WP-072]
status: draft
---

# Feature Specification: Security holds by enforcement, not by absence

**Feature Branch**: `wp-072-security`

**Created**: 2026-09-14

**Status**: Draft

**Input**: REQ-WP-072 — PRD §34, the only section of the PRD with no requirement
note extracted from it.

## Context

Measured against this checkout, seven of §34's eight requirements already hold.
Five of them hold because the thing that could go wrong has not been built yet:

| §34 | holds because |
|---|---|
| redact secrets from logs | there are no logs — `import logging` and `logger.` appear **zero** times in `src/` |
| write/admin routes authenticated | there are no write routes — zero `post`/`put`/`patch`/`delete` handlers |
| CORS restricted in production | no CORS middleware is installed, so no `Access-Control-Allow-Origin` is ever sent |
| no secrets committed | `.env` is ignored at `.gitignore:10` — and nothing tests that |
| rate limiting | **it does not hold.** Nothing limits anything |

That is not compliance; it is the absence of an opportunity. The first `POST`,
the first `logger.info(settings)`, or an `allow_origins=["*"]` added to make a
local frontend work breaks §34, and no test notices.

Separately, `docker-compose.yml` publishes every service with a bare
`"${PORT}:…"`, which binds all interfaces, and Grafana runs as an anonymous
admin with the login form disabled — under a comment whose stated premise is
"not reachable from anywhere", which a deployment falsifies while leaving the
setting.

**One hypothesis did not survive measurement**, recorded so it is not chased
again: `/readyz` serves `catalog_probe`'s detail string and the catalog URI
carries the Postgres password, so it looked like an unauthenticated endpoint
could echo it. Across connection refused, wrong password against a live server
and unresolvable host, the password appears in none of the messages.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The first write route is a red suite (Priority: P1)

**Acceptance**: a handler registered with any method other than `GET` outside an
authenticated router fails the suite, naming the route. Adding one deliberately,
behind authentication, passes.

### User Story 2 - A wildcard origin cannot be shipped (Priority: P1)

**Acceptance**: configuring CORS with `*` fails the suite. Allowed origins are
read from configuration, and an empty configuration means no cross-origin
allowance at all — the state the system is in today.

### User Story 3 - The public read API is rate limited (Priority: P1)

**Acceptance**: within one window a client may make the configured number of
requests; the next is **refused** with a status that says so and a header saying
when to retry. It is not queued, not delayed, not served slowly.

### User Story 4 - Logging cannot render a credential (Priority: P2)

**Acceptance**: the rule exists before logging does. A settings object, a catalog
URI, or any credential-bearing value rendered into a log record fails the suite —
on the day logging is introduced, not on the day somebody remembers §34.

### User Story 5 - The stack publishes only what it means to (Priority: P1)

**Acceptance**: every service binds its published port to a loopback address by
default. A service meant to be reachable from elsewhere says so in one named
place, and a test reading the compose file refuses any other bare form.

### User Story 6 - Grafana is not an anonymous admin (Priority: P2)

**Acceptance**: anonymous access is off by default and the credential comes from
configuration. Starting without it fails loudly rather than falling back.

### User Story 7 - The deployment document says what is exposed (Priority: P2)

**Acceptance**: the exposure table in the document is checked against
`docker-compose.yml`, the way the rest of that document is already checked
against the repository.

### Edge Cases

- A rate limit that counts per process protects one process. With several, the
  effective limit multiplies — stated, not silently wrong.
- The websocket route is not a `GET` handler in the same sense and must be
  named explicitly rather than slipping through the method check.
- `/metrics` and `/readyz` are operational, not part of §28's read API; whether
  they are rate limited is a decision that must be made rather than defaulted.
- A rate limiter keyed on client address sees the proxy's address when behind
  one. What it keys on has to be stated.
- A test that greps for `logging` catches the import, not the leak. It must fail
  on the value reaching a record, not on the module being imported.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A test enumerates every route the application registers and fails
  on any non-`GET` method not covered by authentication.
- **FR-002**: Allowed CORS origins come from configuration; a wildcard is
  refused at startup, not merely discouraged.
- **FR-003**: An empty origin configuration results in no CORS headers at all.
- **FR-004**: The public read API refuses requests beyond a configured rate,
  with the limit and window both configuration (Principle X).
- **FR-005**: A refused request is answered immediately with a status meaning
  "too many requests" and a retry-after indication.
- **FR-006**: What the limiter keys on, and its scope (per process or shared),
  is stated in the deployment document.
- **FR-007**: A test fails if a credential-bearing value can reach a log record.
- **FR-008**: Every compose service binds its published port to a configurable
  address defaulting to loopback.
- **FR-009**: A test reads `docker-compose.yml` and fails on a published port
  that is not bound through that setting.
- **FR-010**: Grafana's anonymous access is off unless explicitly enabled, and
  its credential comes from configuration.
- **FR-011**: The deployment document carries an exposure table, checked against
  the compose file.
- **FR-012**: A test fails if `.env` stops being ignored.

### Key Entities

- **Exposure**: a service, the address its port binds to, and whether that is
  deliberate.
- **Rate limit**: a count, a window, and what the count is keyed on.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Adding a `POST` handler without authentication turns the suite
  red, demonstrated by a test that does exactly that.
- **SC-002**: Setting a wildcard origin turns the suite red.
- **SC-003**: A client exceeding the configured limit receives a refusal, and
  the refusal arrives in the same order of magnitude of time as a served
  request — it is a refusal, not a delay.
- **SC-004**: With the default configuration, no compose service listens on a
  non-loopback address, verified by reading the file.
- **SC-005**: Every one of §34's eight bullets has at least one test that fails
  when it is violated — the section stops holding by accident.
- **SC-006**: The suite still runs with no services and no network for the
  checks that do not need them.

## Assumptions

- **The rate limiter counts in-process.** This deployment runs one API process;
  a shared counter would mean a new dependency ([[ADR-002]] dropped Redis as
  unnecessary), and adding one before there are two processes would be building
  for a deployment that does not exist. The limit's scope is documented rather
  than silently assumed, so the day a second process appears the cost is
  visible.
- **Rate limiting lives in the API, not the proxy.** A limit in nginx protects
  only requests that arrive through nginx, and the API is reachable directly.
- **`/metrics` and `/readyz` are exempt.** An orchestrator polling readiness
  must not be throttled into reporting the service unhealthy, and a scrape
  interval is already a rate limit.
- **The limiter keys on the client address as the application sees it.** Behind
  a proxy that is the proxy; making it trust a forwarded header is a decision
  with its own risks and is out of scope here.
- **No authentication scheme is introduced.** There are no write routes to
  protect; FR-001 is a gate that makes adding one a deliberate act, not an
  authentication system built in advance of a user for it.
- **Grafana's default becomes "off unless configured".** A developer who wants
  the old convenience enables it in `.env`.
