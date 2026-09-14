---
description: "Task list for REQ-WP-072 — security holds by enforcement, not by absence"
---

# Tasks: Security holds by enforcement, not by absence

**Input**: Design documents from `/specs/113-security-enforced/`

**Tests**: REQUIRED. Every test carries `@pytest.mark.trace("REQ-WP-072")`.
Write each test first and watch it fail for the stated reason.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Single project: `src/channelflow/`, `tests/` at repository root.

---

## Phase 1: Setup

- [ ] T001 Record the baseline in the implement outcome note: `repr(Settings)` renders both credentials; the app registers 17 routes, none outside `{GET, HEAD}`; a naive `app.routes` walk reaches 5 of them

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the configuration seam every story reads.

- [ ] T002 Add `RateLimit` (frozen: `requests: int`, `window_seconds: float`) and `InvalidRateLimit` to `src/channelflow/settings.py`, refusing a non-positive limit or window — "allow nothing" is not a rate limit
- [ ] T003 [P] Write the failing test in `tests/unit/test_settings.py` that `RateLimit(0, 60)` and `RateLimit(5, 0)` raise `InvalidRateLimit`, and that `RateLimit(1, 0.5)` is accepted
- [ ] T004 Add `allowed_origins: tuple[str, ...]` and `rate_limit: RateLimit | None` to `Settings`, read by `settings_from_env` from `CHANNELFLOW_CORS_ORIGINS`, `CHANNELFLOW_RATE_LIMIT` and `CHANNELFLOW_RATE_WINDOW_SECONDS`, treating blank as absent exactly as the existing code does. **`settings_from_env` is what raises `WildcardOrigin`**, beside `MissingConfiguration` — configuration is refused where configuration is read, and `api/security.py` then holds only middleware
- [ ] T005 [P] Write the failing test that an absent `CHANNELFLOW_RATE_LIMIT` gives `rate_limit is None` — unlimited is a state that must be chosen, not a parse failure

**Checkpoint**: configuration exists; nothing reads it yet.

---

## Phase 3: User Story 4 — A credential cannot be rendered (Priority: P1) 🎯 MVP

**Goal**: close the one defect that is live today rather than latent.

**Note on priority**: the spec originally marked this P2, framing it as a gate on
future logging. Planning measured that `Settings.__repr__` already renders the
Postgres password and the S3 secret in full, so it is the only story fixing a
present defect. The spec has been corrected to P1 and it goes first.

**Independent Test**: `repr(settings)` hides both credentials and still shows the
host, port, database and access-key id.

- [ ] T006 [P] [US4] Write the failing test in `tests/unit/test_settings.py`: with `catalog_uri="postgresql+psycopg://cf:sup3rs3cret@db:5432/cf"`, `repr(settings)` contains neither `sup3rs3cret` nor the S3 secret, and **does** contain `db`, `5432`, `cf` and the access-key id — pinning what is masked and what survives
- [ ] T007 [P] [US4] Write the failing test that `str(settings) == repr(settings)` — one masked spelling, not a masked one and an unmasked one
- [ ] T008 [P] [US4] Write the failing test that `f"{settings}"` and `"{}".format(settings)` are masked too, and that a `catalog_uri` carrying no password is returned unchanged
- [ ] T009 [P] [US4] Write the failing test that a password containing `@` and `:` is still fully masked — the naive split on `@` finds the wrong one
- [ ] T010 [US4] Implement `_mask_password(uri)` and `Settings.__repr__`/`__str__` in `src/channelflow/settings.py` until T006–T009 pass, parsing the URI rather than splitting on punctuation

**Checkpoint**: the live leak is closed.

---

## Phase 4: User Story 1 — The first write route is a red suite (Priority: P1)

**Independent Test**: adding a `POST` handler turns the suite red; adding one to the authenticated allow-list does not.

- [ ] T011 [P] [US1] Write the failing test that walking the app finds **exactly 17** routes — the count is what separates "no offending routes" from "no routes"
- [ ] T012 [P] [US1] Write the failing test that no route's methods exceed `{GET, HEAD}`, and that the one `APIWebSocketRoute` is recognised as a websocket rather than as a method-less route that slips through
- [ ] T013 [P] [US1] Write the failing test that registering a `POST` handler on a fresh app makes `offending_routes` report it, by path and method
- [ ] T014 [P] [US1] Write the failing test that the same `POST`, named in the `authenticated` set, is not reported
- [ ] T015 [US1] Implement `offending_routes(app, *, authenticated)` in `src/channelflow/api/security.py`, descending through `original_router.routes`, until T011–T014 pass

**Checkpoint**: the first unauthenticated write route cannot land quietly.

---

## Phase 5: User Story 2 — A wildcard origin cannot be shipped (Priority: P1)

- [ ] T016 [P] [US2] Write the failing test that `CHANNELFLOW_CORS_ORIGINS="*"` raises `WildcardOrigin` at startup, and that `"https://a.example, *"` raises too — a wildcard among others is still a wildcard
- [ ] T017 [P] [US2] Write the failing test that with no origins configured the app installs no CORS middleware and no response carries `Access-Control-Allow-Origin`
- [ ] T018 [P] [US2] Write the failing test that with `"https://a.example"` configured, a request from that origin gets the header and a request from another does not
- [ ] T019 [US2] Implement `WildcardOrigin` in `src/channelflow/settings.py` and the CORS wiring in `src/channelflow/api/security.py` and `app.py` until T016–T018 pass

---

## Phase 6: User Story 3 — The public read API is rate limited (Priority: P1)

- [ ] T020 [P] [US3] Write the failing test that with `RateLimit(3, 60)` and a controlled clock, three requests are served and the fourth is `429` with a `Retry-After` header
- [ ] T021 [P] [US3] Write the failing test that advancing the clock past the window serves again, and that advancing it part-way does not
- [ ] T022 [P] [US3] Write the failing test that two different client keys do not share a budget
- [ ] T023 [P] [US3] Write the failing test that `/readyz` and `/metrics` are served after the limit is exhausted — a throttled readiness probe is the outage the limiter exists to prevent
- [ ] T024 [P] [US3] Write the failing test that a refused request is a `429` carrying `Retry-After`, and **not** a `200` that arrived late — asserted on the status and headers. A controlled clock does not advance on a real sleep, so a timing assertion here would measure the machine rather than the design; the checkable claim is the status
- [ ] T025 [P] [US3] Write the failing test that `rate_limit is None` installs no limiter and every request is served
- [ ] T026 [US3] Implement `FixedWindowLimiter` and the middleware in `src/channelflow/api/security.py` until T020–T025 pass, taking the clock as a constructor argument

**Checkpoint**: the one §34 item that genuinely did not hold now holds.

---

## Phase 7: User Story 5 — The stack publishes only what it means to (Priority: P1)

- [ ] T027 [P] [US5] Write the failing test in `tests/unit/deploy/test_exposure.py` that every service in `docker-compose.yml` publishing a port uses the `${CHANNELFLOW_BIND_ADDRESS}:<host>:<container>` form, with an explicit list of services allowed to be public and a reason for each
- [ ] T028 [P] [US5] Write the failing test that the list of publishing services in the test matches the compose file — so a new service with a bare mapping fails rather than being silently unlisted
- [ ] T029 [US5] Change every published port in `docker-compose.yml` to bind through `${CHANNELFLOW_BIND_ADDRESS}`, and add `CHANNELFLOW_BIND_ADDRESS=127.0.0.1` to `.env.example` with a comment saying what changing it does
- [ ] T030 [US5] Correct the compose comment above `ingest-binance` that says "§6.2 also names `worker` and `ingest-binance`. Neither exists as code" — it sits directly above the service that exists

---

## Phase 8: User Story 6 — Grafana is not an anonymous admin (Priority: P2)

- [ ] T031 [P] [US6] Write the failing test that `docker-compose.yml` does not set `GF_AUTH_ANONYMOUS_ORG_ROLE: Admin` unconditionally, and that Grafana's admin password comes from a variable
- [ ] T032 [US6] Change the Grafana service to take `GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}` and `GF_AUTH_ANONYMOUS_ENABLED: ${GRAFANA_ANONYMOUS:-false}`, add both to `.env.example`, and replace the comment whose premise a deployment falsifies

---

## Phase 9: User Story 7 — The deployment document says what is exposed (Priority: P2)

- [ ] T033 [P] [US7] Write the failing test extending `tests/unit/docs/test_deployment_doc.py`: the document carries an exposure table naming every publishing compose service, and the two sets match exactly
- [ ] T034 [US7] Add the exposure table to `docs/deployment.md`, and state the limiter's key, scope and exemptions there
- [ ] T035 [US7] Correct the three stale claims: line 13 "Five containers" above a table of nine; lines 28 and 162 saying the API and web app are not containerised

---

## Phase 10: §34, bullet by bullet

**Purpose**: SC-005 — each of the eight bullets fails a test when violated.

- [ ] T036 [P] Write the test that no connector module reads a credential-shaped environment variable (bullet 1)
- [ ] T037 [P] Write the test that the alerting package reads no environment at all, per [[ADR-018]] (bullet 2)
- [ ] T038 [P] Write the test that every RPC endpoint in `tools/record/` carries no key or token in its URL (bullet 3)
- [ ] T039 [P] Write the test that `.env` is ignored by git and `.env.example` holds no value that looks like a live credential (bullet 4)
- [ ] T040 Write the mapping in the implement outcome note: each of §34's eight bullets against the test that now guards it

---

## Phase 11: Polish

- [ ] T040a Confirm every new test runs under `pytest -m "not integration"` with no network and no services — no socket, no `tools.record` import, no live stack
- [ ] T041 `make lint && make typecheck` clean
- [ ] T042 Write `tests/mutations/security.toml` and run the sweep; every survivor is a weak assertion to strengthen
- [ ] T043 Run through `specs/113-security-enforced/quickstart.md`
- [ ] T044 `make test` with the stack up; `make graph && make validate` clean; requirement reaches `implemented`

---

## Dependencies & Execution Order

- **Setup (T001)**: none
- **Foundational (T002–T005)**: blocks US2, US3
- **US4 (T006–T010)**: needs nothing — it is the live defect and goes first
- **US1 (T011–T015)**: independent
- **US2 (T016–T019)**: needs Foundational
- **US3 (T020–T026)**: needs Foundational
- **US5 (T027–T030)**, **US6 (T031–T032)**: independent of the API work
- **US7 (T033–T035)**: needs US5 and US6 settled, since it documents them
- **Phase 10**: independent
- **Polish**: last

### Parallel Opportunities

T003/T005; T006–T009; T011–T014; T016–T018; T020–T025; T027/T028; T036–T039.

---

## Implementation Strategy

### MVP (US4 alone)

T001 → T006–T010. That closes the only defect that exists today: an object that
renders two credentials whenever anything prints it. Everything else in this
requirement prevents a future mistake; this one stops a present one.

### Incremental delivery

US4 → US1 → US3 → US2 → US5 → US6 → US7 → the bullet-by-bullet sweep.

---

## Notes

- Assertions pin exact strings and exact counts. A test asserting "the password
  is not in the repr" without also asserting the host **is** would pass against a
  `repr` that returned the empty string.
- T011's count is load-bearing. Without it the route gate passes on a traversal
  that reaches nothing.
