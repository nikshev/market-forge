---
id: OUT-2026-09-14-spec-security-enforced
step: spec
records: [REQ-WP-072]
commit: null
---

## What was done

Specified [[REQ-WP-072]] as `specs/113-security-enforced/spec.md`, from a
measurement of all eight PRD §34 requirements against this checkout.

## What was decided

**Tests that fail when an absence ends, rather than an audit that passes today.**
Five of §34's eight requirements hold because the code that could violate them
does not exist. An audit would record eight green ticks and be worthless the
following week. So FR-001, FR-002 and FR-007 are gates on *future* code: the
first non-`GET` handler outside authentication, the first wildcard origin, the
first credential reaching a log record. Each is red the day it happens.

**No authentication scheme is built.** There is nothing to protect — zero write
routes. Building one in advance of a user for it would be designing against a
guess. FR-001 makes adding a write route a deliberate act instead.

**The rate limiter counts in-process, and says so.** A shared counter means a new
dependency; [[ADR-002]] dropped Redis as unnecessary and nothing has needed it
since. With one API process an in-process limit is exact. The assumption is
written down with its cost — the effective limit multiplies with processes — so
the day a second one appears the price is visible rather than discovered.

**It lives in the API, not in nginx.** A limit in the proxy protects only what
arrives through the proxy, and the API is reachable directly.

**`/metrics` and `/readyz` are exempt.** Throttling a readiness probe makes an
orchestrator declare the service unhealthy, which is the failure the limiter
would have caused rather than prevented. A scrape interval is already a rate
limit.

**Ports bind to loopback by default, through one configurable address.** Not a
hardcoded `127.0.0.1`: Principle X, and an operator who means to expose a service
should do it in one named place rather than by editing nine lines.

**Grafana's anonymous admin becomes opt-in.** Its current comment says the stack
"is not reachable from anywhere" — true of a laptop, false the moment it is
deployed, and the setting does not know the difference.

## What is still open

- **What the limiter keys on behind a proxy.** It keys on the address the
  application sees. Trusting a forwarded header is a separate decision with its
  own risks, and guessing at it here would be worse than naming it.
- **§34's closing sentence** — "If trading is added later, separate execution
  service and separate credentials entirely" — is a constraint on work that does
  not exist. Nothing here implements it, and Principle IX already forbids
  automatic execution in Phases 1-3.
- **Whether §34 belongs to a phase.** All eleven phases are `implemented` and
  none covers this requirement, so the phase accounting says the feature work is
  done while security work is outstanding. That is accurate — §34 is
  cross-cutting like §35 — but it is worth knowing when reading the dashboard.
