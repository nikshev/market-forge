---
id: OUT-2026-09-14-plan-security-enforced
step: plan
records: [REQ-WP-072]
commit: null
---

## What was done

Planned [[REQ-WP-072]] into `specs/113-security-enforced/` — plan, research, data
model, one contract and a quickstart. Planning changed the shape of the work
twice, both times because a measurement contradicted the plan I was about to
write.

## What was decided

**The credential leak is in the type, not in the logging.** Measured: `Settings`
is a frozen dataclass, so its generated `repr` renders the Postgres password
inside `catalog_uri` **and** `storage['s3.secret-access-key']` in full. The spec
had framed §34's "redact secrets from logs" as a gate on future logging. It is
not a future problem — the object is already built to leak, and logging would
only be the delivery. So the fix is a `repr` and `str` that mask, and the
rejected alternative is a lint forbidding `logger.*(settings)`: it catches one
spelling and misses `f"{settings}"`, `print`, `assert x, settings`, and every
traceback that renders locals.

**What stays visible is part of the contract.** The catalog URI keeps scheme,
user, host, port and database; only the password becomes `***`.
`s3.access-key-id` is an identifier and is shown. A mask that hid everything
would make the object useless for diagnosis, and somebody would then log the
fields one at a time — the same leak, reached by a longer road.

**The obvious route gate would have passed and proved nothing.** Measured on
FastAPI 0.141.1: `app.routes` is not flat. It holds four `Route`s, three
`_IncludedRouter`s and one `APIWebSocketRoute`, and the `_IncludedRouter` objects
expose neither `.path` nor `.routes` — the way in is `.original_router`. A naive
walk sees **5 of 17** routes, misses every route under `/api/v1`, finds no
non-`GET` method and reports success. So the test asserts the **count** as well
as the property. That is what separates "no offending routes" from "no routes".

**The limiter counts in-process, takes a clock, and states its cost.** No new
dependency — `slowapi` or `limits` would be a supply-chain cost for arithmetic,
and [[ADR-002]] already dropped Redis. A fixed window rather than a sliding log:
Principle XII, and its edge behaviour — up to twice the limit across a boundary —
is simple enough to write down, which is better than an optimisation whose
failure mode is not. The clock is an argument because Principle VII forbids a
test-only branch.

**`/metrics` and `/readyz` are exempt**, because throttling a readiness probe
makes an orchestrator declare the service unhealthy — the limiter causing the
outage it exists to prevent.

**CORS is made deliberate, not permissive.** No middleware exists today, so
nothing is allowed cross-origin, and that is already the right end state: the web
app is same-origin behind nginx. The work is to make the restriction chosen and
the permissive mistake unshippable — a wildcard raises at startup, following
`settings_from_env`, which already raises rather than defaulting.

**One variable binds every port.** `CHANNELFLOW_BIND_ADDRESS`, defaulting to
`127.0.0.1`. Nine services currently publish with a bare `"${PORT}:…"`. One named
place beats nine lines edited by hand, and a loopback default means the safe case
needs no decision.

## What is still open

**A trap named rather than solved.** On Linux, Docker inserts rules into the
`DOCKER` chain of the `nat` table, traversed before the `INPUT` chain `ufw`
manages — so a published port can be reachable while `ufw` reports it denied.
Binding to loopback removes the question instead of answering it, which is why
the plan does that rather than documenting a firewall recipe.

**Three stale claims in `docs/deployment.md`**, to be corrected by hand: line 13
says "Five containers" above a table of nine; lines 28 and 162 say the API and
web app are not containerised, when all four application services have `build:`
stanzas. `tests/unit/docs/test_deployment_doc.py` checks that document's *names*
against the repository and passed throughout — a document checked for names can
still be confidently wrong about everything else. The exposure table this plan
adds is checked mechanically; the prose is not, and that limit is now written
down.

**What the limiter keys on behind a proxy** stays the address the application
sees. Trusting a forwarded header is a separate decision with its own risks.
