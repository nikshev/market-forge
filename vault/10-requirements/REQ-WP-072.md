---
id: REQ-WP-072
title: Security holds by enforcement, not by absence
type: work-package
prd_ref: "§34"
prd_lines: "4821-4836"
phase: null
status: draft
depends_on: [REQ-WP-064, REQ-WP-065]
tags: []
---

## Requirement

PRD §34 is the only section of the PRD with **no requirement note at all**. It
opens by saying what the MVP is — *"MVP is read-only market analytics"* — and
lists eight requirements:

> - no exchange trading keys required for public market data;
> - Telegram bot token only via secret/env manager;
> - RPC API keys via secrets;
> - no secrets committed;
> - redact secrets from logs;
> - API write/admin routes authenticated;
> - CORS restricted in production;
> - rate limiting for public web API.

### Seven of the eight already hold. Five hold by accident.

Measured against this checkout, not assumed:

| §34 requirement | today | why |
|---|---|---|
| no exchange trading keys | holds | no connector reads a key; every venue is used through its public endpoints |
| Telegram token via secret manager | holds | [[ADR-018]] — the alerting package reads no environment at all; the transport and its credentials are the caller's |
| RPC API keys via secrets | holds | the capture tools use public endpoints and carry no keys |
| no secrets committed | holds | `.env` is ignored at `.gitignore:10`; only `.env.example` is committed, with empty values |
| redact secrets from logs | holds | **there are no logs.** `import logging` and `logger.` appear **zero** times in `src/` |
| API write/admin routes authenticated | holds | **there are no write routes.** Zero `post`/`put`/`patch`/`delete` handlers; every route is a `GET`, plus one websocket |
| CORS restricted in production | holds | no CORS middleware is installed, so no `Access-Control-Allow-Origin` is ever sent and a browser refuses every cross-origin read |
| rate limiting for public web API | **does not hold** | nothing limits anything |

The last five of those hold **because the thing that could go wrong has not been
built yet**. That is not compliance; it is the absence of an opportunity. The day
somebody adds the first `POST`, the first `logger.info(settings)`, or an
`allow_origins=["*"]` to make a local frontend work, §34 is broken and no test
notices.

### One hypothesis that did not survive measurement

`catalog_probe` returns `detail=f"the catalog did not answer: {cause}"` and
`/readyz` serves that string, so a catalog failure looked like it could echo the
Postgres password out of an unauthenticated endpoint — the catalog URI carries
it. Measured across the three commonest failures — connection refused, wrong
password against a live server, unresolvable host — the password appears in
**none** of the messages: `psycopg` names host and port, and SQLAlchemy does not
put the URL in its exception text. Recorded because a plausible leak that is not
real is worth writing down once, so it is not re-investigated.

### And the stack publishes more than it means to

`docker-compose.yml` publishes every service with a bare `"${PORT}:..."`, which
binds all interfaces. On a host that is not a laptop that offers Postgres, the
MinIO API and console, Redpanda, Prometheus and Grafana to whatever can reach the
host. Grafana in particular runs with `GF_AUTH_ANONYMOUS_ENABLED`,
`GF_AUTH_ANONYMOUS_ORG_ROLE: Admin` and the login form disabled, under a comment
whose stated premise is *"this stack holds no secrets and is not reachable from
anywhere"* — a premise that a deployment falsifies while leaving the setting.

This is §34's spirit rather than its letter: the section says the web API must be
rate limited and CORS restricted, and publishing a database to the internet is
the larger version of the same mistake.

## Acceptance

- A test fails if any route handler outside an authenticated router uses a
  method other than `GET` — so the first write route is a red suite, not a
  silent breach of §34.
- A test fails if CORS is configured with a wildcard origin, and the allowed
  origins are configuration rather than a literal.
- Rate limiting applies to the public read API, with the limit configurable
  (Principle X) and a test that proves the limit is enforced and that exceeding
  it is refused rather than served slowly.
- A test fails if `src/` gains logging that can render a settings object, a
  catalog URI or any value carrying a credential. The rule holds the day logging
  is introduced, not the day somebody remembers §34.
- Every service in `docker-compose.yml` binds its published port to a loopback
  address unless it is deliberately public, and a test reads the compose file and
  refuses a bare `"${PORT}:"` form for anything but the services named public.
- Grafana does not run as an anonymous admin in a configuration intended for a
  server, and whatever it does run as is stated where an operator will read it.
- The deployment document states what is exposed and what is not, and is checked
  against `docker-compose.yml` the way `docs/deployment.md` is already checked
  against the repository.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
