---
description: "Task list for REQ-WP-080 — the overview and the chart open as a Telegram Mini App, authenticated by Telegram"
---

# Tasks: The overview and the chart open as a Telegram Mini App, authenticated by Telegram

**Input**: Design documents from `/specs/126-telegram-mini-app/`

**Tests**: REQUIRED, written first, and each watched failing for the stated reason. Python tests carry
`@pytest.mark.trace("REQ-WP-080")` and run in the fast gate; they are what the trace graph counts as
verifying. TypeScript tests (vitest) run in CI and with `make web-test` ([[ADR-021]]): they carry the
page's acceptance lines and are marked in the file by a `// @trace: REQ-WP-080` comment. Each task says
which kind it is.

**Where the risk is**: the gate (US1) is the only part that can be wrong in a way a demo would not show.
It is built and tested first, and a verifier is never tested only against its own signer.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

`src/channelflow/api/`, `tests/`, `apps/web/src/`, `apps/web/scripts/`, repository root for compose and docs.

---

## Phase 1: Setup

- [x] T001 Record the **before** in the implement outcome note: that nothing in `apps/web/src` mentions Telegram; the running API's answer to `GET /api/v1/markets` and `GET /api/v1/timeframes` saved byte-for-byte (the "today" that a signed request must still receive, FR-004); and the number of routes under `/api/v1` the API registers

## Phase 2: Foundational

- [x] T002 Make the vectors with a **third implementation**: `tests/vectors/make_vectors.sh` computes each signature with `openssl dgst -sha256 -hmac` (the commands are the file's documentation) and writes `tests/vectors/telegram_init_data.json`: a fixed fake token (`123456:TEST-TOKEN-NOT-A-SECRET`), a fixed `now`, and nine launches — valid; valid with no `user`; one field changed; signed with another token; no hash; no `auth_date`; `auth_date` not a number; older than the maximum age; more than a minute in the future — each with its expected verdict and, for the seven refusals, its reason (six distinct: a changed field and a wrong token are both `bad_signature`, deliberately). Commit the script and the output
- [x] T003 [P] Write `apps/web/scripts/gen-dev-initdata.mjs` (Node's `crypto`): `--token`, `--id`, `--name`, `--auth-date`, `--print` (to stdout) and the default of writing `VITE_DEV_INITDATA` to **`.env.development.local`**, never `.env.local`. Add `dev:init` to `apps/web/package.json`. Carry `// @trace: REQ-WP-080`
- [x] T004 [P] Write `apps/web/.dockerignore` excluding `.env*`, `node_modules`, `dist`, so no developer's local file is copied into the image by `COPY . .`

## Phase 3: User Story 1 — the API accepts what Telegram signed and nothing else (P1) 🎯 MVP

**Independent test**: the nine vectors give two accepted and seven refused for six distinct reasons; with authentication required every `/api/v1` route refuses an unsigned request and answers a signed one as today.

- [x] T005 [P] [US1] Write the failing tests in `tests/unit/api/test_telegram_auth.py` (pytest): the nine vectors (SC-001); the boundaries — an `auth_date` exactly the maximum age old is accepted and one second older refused; exactly 60 s ahead accepted and 61 s refused; a launch with no `user` accepted and a malformed `user` still a signed launch; no refusal message and no log record (`caplog`) contains the token or the `hash`; a non-integer `auth_date` is `malformed`. Fails today: the module does not exist
- [x] T006 [P] [US1] Write the failing tests in `tests/unit/api/test_telegram_gate.py` (pytest): **walk every route under `/api/v1` through `include_router`'s `original_router`, assert the count walked equals the count of the routers' routes (T001) and is above zero** (SC-002), and for each: unsigned → 401 with a closed-set `reason` and a body holding no market data, signed → 200 and equal to the mode-off response; mode off → unchanged for everyone; header that is not valid UTF-8, empty, enormous, or of another scheme → 401, never 500; `/readyz` and `/metrics` answer unsigned; `/ws/market` refused (close 1008) when required; `required` with no token raises at construction naming `TELEGRAM_BOT_TOKEN` *Done, with one change from the plan: the websocket is refused by the same middleware (it also covers `/ws/`), so `ws.py` is untouched.*
- [x] T007 [P] [US1] Write the failing test in `tests/unit/deploy/test_public_surface.py` (pytest): `apps/web/nginx.conf` has **one** proxy location, `/api/`; the API registers `/readyz`, `/metrics` and `/ws/market` **outside** `/api/`; so none is reachable through the public address (FR-007). The test fails if either file changes in a way that exposes them
- [x] T008 [US1] Run T005–T007 and record the RED output in the implement outcome note. Do not commit while red
- [x] T009 [US1] Implement `src/channelflow/api/telegram_auth.py`: `LaunchRefused` with a closed set of reasons, the pure `verify_init_data(init_data, bot_token, now, max_age)`, `compare_digest`, and the middleware scoped to `/api/v1/`; add the three settings to `src/channelflow/settings.py` (reusing `TELEGRAM_BOT_TOKEN`, `CHANNELFLOW_TELEGRAM_AUTH`, `CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS`); wire into `create_app` and `src/channelflow/api/main.py`; refuse the websocket in `src/channelflow/api/ws.py` when required. `# @trace: REQ-WP-080` in each changed file
- [x] T010 [US1] Run the three new files and the existing API tests: the existing ones pass **unchanged**

## Phase 4: User Story 2 — the page behaves as a Mini App, and as itself outside Telegram (P1)

**Independent test**: with a stand-in `window.Telegram.WebApp` the page signals ready and expand once, themes itself, manages the back button and sends the header; without it nothing Telegram-related happens.

- [x] T011 [P] [US2] Write the failing tests in `apps/web/src/__tests__/telegram.test.ts(x)` (vitest): with the stand-in — `ready` and `expand` called once each, `disableVerticalSwipes` called when present and not when absent, **the back button and the swipe call both absent on an older client without anything throwing**, theme parameters applied as CSS variables and the colour scheme set, back button shown on a chart route and hidden on the overview with a press navigating to `/`, **every** API request carries `Authorization: tma <initData>`; without it — no script requested (the hash lacks `tgWebAppData`), no header, no throw, the existing tests unchanged; and `Chart` given `scheme="dark"` hands the chart library a dark layout (the existing `Chart.test.tsx` mock shows what it was given). **Run it and record the RED** (`cd apps/web && npx vitest run`) before T012. Fails today: the module does not exist *Done; the dark-scheme assertion is on `chartLayout`, a pure function, because `lightweight-charts` cannot draw in jsdom and the existing tests assert on extracted decisions, not on the library.*
- [x] T012 [US2] Implement `apps/web/src/telegram.ts` (stand-in-friendly accessors, the conditional script loader, init), `apps/web/src/theme.ts`, the header in `apps/web/src/api.ts` (`get()` adds it when launch data exists), the `scheme` prop and a dark palette in `apps/web/src/Chart.tsx`, and the call in `apps/web/src/main.tsx`. Read `VITE_DEV_INITDATA` **only** under `import.meta.env.DEV`. `// @trace: REQ-WP-080` in each

## Phase 5: User Story 3 — a link carries the chart state in, in either form (P1)

**Independent test**: a `start_param` and the equivalent query string produce the same state; an unreadable one opens the overview.

- [x] T013 [P] [US3] Write the failing tests in `apps/web/src/__tests__/startParam.test.ts` (vitest): the same venue, symbol, timeframe, instant, signal, mode and overlays from both forms through `deepLink.ts`'s own parser; an unreadable value, a decoded `//evil`, `javascript:…`, `/chart/../…`, a non-base64url string and an oversize one each open the overview; the **longest realistic** link encoded is at most 512 characters and uses only `[A-Za-z0-9_-]`. **Run it and record the RED** before T014
- [x] T014 [US3] Implement `apps/web/src/startParam.ts` and call it in `main.tsx` **before** the page reads the address: decode, validate against the strict pattern, `replaceState`. `// @trace: REQ-WP-080`
- [x] T015 [P] [US3] Write `apps/web/src/__tests__/telegramVectors.test.ts` (the TypeScript signer reproduces the hash of every vector in `tests/vectors/`) and `apps/web/src/__tests__/buildHasNoInitData.test.ts` (build for production with a sentinel in `VITE_DEV_INITDATA`, then search every file of the output for it — FR-014, SC-004). **Run both and record the RED** — the vectors test fails until the signer exists (T003), the build test passes today only if no code reads the variable outside development, which it does not yet, so it is a guard written before the reader exists *Done, and the build test was rewritten after it failed: see the outcome note (vitest sets `NODE_ENV=test`, so a build run from inside a test is a different build).*
- [x] T016 Run `make web-install`, `make web-test`, `make web-typecheck`, `make web-build`: the **green** after T012 and T014, with the existing web tests unchanged

## Phase 6: User Story 4 — a stable HTTPS address (P2)

**Independent test**: the compose file read as data: the profile, no ports, the variables.

- [x] T017 [P] [US4] Write the failing tests in `tests/unit/deploy/test_telegram_profile.py` (pytest): `cloudflared` exists under `profiles: [telegram]` with no `ports`, `depends_on: web`, `TUNNEL_TOKEN` from `CHANNELFLOW_TUNNEL_TOKEN` with an empty default (not `:?`) and `TUNNEL_TRANSPORT_PROTOCOL` defaulting to `http2`; **no other service is in the profile**; the `api` service forwards `TELEGRAM_BOT_TOKEN`, `CHANNELFLOW_TELEGRAM_AUTH` and `CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS` (compose forwards only named variables); every new variable is in `.env.example` and in `docs/deployment.md` (the existing documents test)
- [x] T018 [US4] Implement it: `docker-compose.yml`, `.env.example`, and a `docs/deployment.md` section — create the bot with BotFather, create the tunnel with its public hostname at `http://web:8080`, which three variables to set, how to set the Mini App URL, how to run `docker compose --profile telegram up -d --build`, and what to check. State that the gate is access control for public data, not secrecy

## Phase 7: Mutations, gate, local run

- [x] T019 First run `tests/tools/test_mutate.py`. Then write `tests/mutations/telegram_auth.toml` (source `src/channelflow/api/telegram_auth.py`; tests the two new API test files): signature compared with `==`; the age check removed; the future check removed; the key order of the data-check-string not sorted; the token put into a refusal message; the gate scoped to a narrower prefix; the websocket not refused; mode `required` treated as `off`; a missing hash treated as valid. **A survivor needs a test that kills it or a written reason** — the constant-time comparison cannot be observed from a test and is expected to survive, with that as its reason
- [x] T020 `make lint`, `make typecheck`, `make test`, `make web-typecheck`, `make web-test`, `make web-build`. FR-007 and FR-008 are checked by T006/T007 and the `caplog` assertion of T005
- [x] T021 **Run it locally with a signed launch**, recorded: `npm run dev:init`, the API started with `CHANNELFLOW_TELEGRAM_AUTH=required` and the same token, `curl` without the header → 401 and no data, with the header → data; then the built stack (`docker compose up -d --build --no-deps api web`, so `worker` and `resample` keep running and the [[REQ-WP-079]] measurement is not disturbed) answering through the web service's `/api`
- [x] T022 Write the implement outcome note and set the requirement's status to **`tested`**, not `implemented`: the last acceptance line (shown on a phone, from a bot) needs the owner's bot token and tunnel and cannot be tested. `make graph && make validate`; commit through the gate naming explicit paths
- [ ] T023 **Shown on a phone** (US5, SC-005), when the owner provides the bot token and the tunnel token and domain: bring the stack up with the profile, set the Mini App URL, open it, and record the date, the URL, what was seen (overview, a market's chart, the timeframe selector, the channel overlay) and what was wrong. Then `implemented`. If something looks wrong in the dark theme this is where it shows, and it is a finding, not noise

---

## Coverage

| requirement | task |
|---|---|
| FR-001 verify as Telegram defines it | T005, T009 |
| FR-002 each refusal, its own reason, no token | T005, T009 |
| FR-003 two implementations agree | T002, T005, T015 |
| FR-004 every data route gated, signed unchanged | T001, T006, T009 |
| FR-005 mode off/required, refuse start | T006, T009 |
| FR-006 token from environment | T009, T018 |
| FR-007 readiness and metrics not reachable | T006, T007 |
| FR-008 identity not stored or logged | T005 |
| FR-009 page behaves as a Mini App | T011, T012 |
| FR-010 outside Telegram unchanged | T011, T012 |
| FR-011 both link forms agree | T013, T014 |
| FR-012 unreadable → overview | T013, T014 |
| FR-013 profile, no host port | T017, T018 |
| FR-014 no dev launch in a build | T004, T015 |
| FR-015 variables documented | T017, T018 |
| SC-001 eight variants | T005 |
| SC-002 walked routes, none open | T006 |
| SC-003 header exactly when in Telegram | T011 |
| SC-004 no launch string in a build | T015 |
| SC-005 shown on a phone | T023 |

## Dependencies & Execution Order

T001 first. T002 → T005. T003, T004 beside T002. T005–T007 in parallel, then T008 → T009 → T010.
US2 and US3 tests (T011, T013, T015) can be written beside US1's, each run for its RED where it is written;
their implementation (T012, T014) waits for that RED, and T016 is the green after both. T017 beside them; T018 after. T019 needs T009. T020 follows all of it; T021 follows
T020; T022 follows T021; T023 waits for the owner.

## Parallel opportunities

T003 and T004 beside T002; T005, T006, T007 together; T011, T013, T015, T017 together.

## Implementation Strategy

**MVP is US1 and T019–T022**: a gate that is tested against known answers and a page that sends the
header. US2–US4 make it a Mini App and give it an address. The status stays `tested` until the phone
shows it, on purpose: this requirement's last line is something only the owner's bot can supply.
