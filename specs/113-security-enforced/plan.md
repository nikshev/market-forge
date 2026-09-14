# Implementation Plan: Security holds by enforcement, not by absence

**Branch**: `wp-072-security` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/113-security-enforced/spec.md`

## Summary

PRD §34's eight requirements mostly hold, and five of them hold because nothing
has yet had the chance to break them. This turns each absence into a test that
fails when the absence ends, builds the one thing genuinely missing — rate
limiting — and stops the stack publishing a database to whatever can reach the
host.

Planning found one hazard that is **not** hypothetical, and it reshapes the
approach: `Settings` is a frozen dataclass, so its default `repr` prints the
Postgres password and the S3 secret access key in full. §34's "redact secrets
from logs" is therefore not a future problem waiting for logging — the type is
already built to leak, and logging would merely be the delivery. So the fix is a
type that cannot render a credential, not a lint that looks for `logger.`.

## What planning measured

**The credential leak, measured:**

    >>> repr(settings)
    Settings(catalog_uri='postgresql+psycopg://cf:sup3rs3cret@db:5432/cf',
             warehouse='s3://bucket/warehouse',
             storage={'s3.endpoint': '…', 's3.access-key-id': 'keyid',
                      's3.secret-access-key': 'AKIA-SECRET-VALUE'})

    password visible in repr:  True
    s3 secret visible in repr: True

**The route table, measured** — 17 routes, every one `GET` (the four docs routes
also answer `HEAD`, which Starlette adds), plus one websocket. Zero non-`GET`
handlers, confirming §34's sixth bullet holds today.

**And the trap underneath it.** FastAPI 0.141.1 does not flatten included
routers: `app.routes` holds four `Route`s, three `_IncludedRouter`s and one
`APIWebSocketRoute`. A naive walk sees **5 of the 17** routes and none of the
twelve that matter — and finds no non-`GET` method, so it passes. A gate written
the obvious way would be green and worthless. The traversal must descend through
`original_router.routes`, and the test must assert the route count so a
traversal that silently stops failing to find things fails instead.

## Technical Context

**Language/Version**: Python 3.12, FastAPI 0.141.1, Starlette

**Primary Dependencies**: none new. A rate limiter is ~40 lines; a dependency for
it would be a supply-chain cost for arithmetic, and [[ADR-002]] already dropped
Redis as unnecessary.

**Storage**: N/A

**Testing**: pytest, `@pytest.mark.trace("REQ-WP-072")`, mutation sweep

**Target Platform**: `src/channelflow/`, `docker-compose.yml`, `docs/`

**Project Type**: single project

**Performance Goals**: a refusal costs no more than a served request — the limiter
is O(1) per request and holds no lock across I/O.

**Constraints**: `mypy --strict`; the unit suite needs no services and no
network; `# @trace: REQ-WP-072` on every source file touched.

**Scale/Scope**: one API process. The limiter's scope is documented, not assumed.

## Constitution Check

| Principle | How this plan satisfies it |
|---|---|
| VI. Every feature documented | The limiter's scope, key and exemptions are in the deployment document, not only in code. |
| VII. Live and replay are the same code | The limiter takes a clock. Tests drive it deterministically through the same code path a deployment uses; no test-only branch. |
| X. Thresholds are configuration | The limit, the window, the allowed origins and the bind address are all configuration. Nothing numeric is compiled in. |
| XII. Correctness precedes performance | A fixed window, not a sliding log. Simpler to prove; its edge behaviour is documented rather than optimised away. |
| XIV. Everything is traceable | Trace markers on every file; markers on every test. |

No violations. Complexity Tracking omitted.

## Project Structure

### Documentation (this feature)

```text
specs/113-security-enforced/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── limits-and-exposure.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/channelflow/
├── settings.py               # MODIFY: Settings that cannot render a credential
└── api/
    ├── app.py                # MODIFY: install CORS and the limiter
    ├── security.py           # CREATE: origins, the limiter, the route gate's rule
    └── main.py               # MODIFY: read the new settings

docker-compose.yml            # MODIFY: bind through CHANNELFLOW_BIND_ADDRESS
.env.example                  # MODIFY: the new names, empty or safe defaults
docs/deployment.md            # MODIFY: exposure table; fix three stale claims

tests/
├── unit/api/test_security.py # CREATE
├── unit/test_settings.py     # MODIFY: the credential-rendering tests
├── unit/deploy/test_exposure.py  # CREATE: reads docker-compose.yml
└── mutations/security.toml   # CREATE
```

**Structure Decision**: one new module, `api/security.py`, holding the three
things that are one subject — what origins are allowed, what the rate limit is,
and what a route is permitted to be. Spreading them across `app.py` would make
the §34 surface something a reader has to assemble.

## The three stale claims to correct

`docs/deployment.md` is checked against the repository by
`tests/unit/docs/test_deployment_doc.py`, but that test checks *names*, not
prose. Three claims are now false:

- line 13: "Five containers, started together:" — followed by a table of nine.
- line 28: the API and web app "are not containerised here, and that is a gap".
- line 162: "Nothing is containerised beyond the stateful services."

All four application services have `build:` stanzas. The exposure table this
plan adds is checked mechanically; these three are corrected by hand, and the
lesson is recorded rather than assumed away: a document checked for names can
still be confidently wrong about everything else.
