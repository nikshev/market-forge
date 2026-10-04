---
id: OUT-2026-10-03-implement-telegram-mini-app
step: implement
records: [REQ-WP-080]
commit: 26bd03d
---

## What was done

The overview and the chart can open as a Telegram Mini App, and the API can refuse what Telegram did
not sign. **Not yet shown on a phone**: that needs the owner's bot token and a tunnel, so the status is
`tested`, not `implemented`.

- **The gate** — `src/channelflow/api/telegram_auth.py`: a pure `verify_init_data`, a `TelegramGate`
  and one ASGI middleware over `/api/v1/` and `/ws/`. Settings: `CHANNELFLOW_TELEGRAM_AUTH` (`off` by
  default), `CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS`, and the existing `TELEGRAM_BOT_TOKEN`, masked in the
  settings text. `required` without a token stops the service.
- **The page** — `apps/web/src/telegram.ts` (script loaded only when the address carries launch data;
  ready, expand, swipes, back button, theme, header), `theme.ts` (and a dark `chartLayout`),
  `startParam.ts` (base64url of the deep link, strictly validated), wired in `main.tsx` and `api.ts`.
- **The stack** — a `telegram` profile with `cloudflared` pinned to 2026.9.3, no ports, `http2` by
  default; three variables forwarded to `api` only; a section in `docs/deployment.md`.
- **The dev tool** — `apps/web/scripts/gen-dev-initdata.mjs`, writing `.env.development.local`, with
  `apps/web/.dockerignore` keeping local env files out of the image.

## RED, as run (before any source change)

- Python US1: `ModuleNotFoundError: No module named 'channelflow.api.telegram_auth'` for the verifier
  and gate tests; `AttributeError: 'Settings' object has no attribute 'telegram_auth'` and `DID NOT RAISE
  MissingConfiguration` for the settings tests.
- Python US4: `KeyError: 'cloudflared'` and `assert None` (variables absent from the example).
- Web: `Failed to resolve import "../telegram"`, `"../theme"`, `"../startParam"`.
- **Green from the start, on purpose:** the public-surface tests (`nginx.conf` proxies only `/api/`;
  the three ungated routes are outside it) — they pin a property that already held by the way two files
  line up, and nothing had checked it; and the TypeScript signer against the vectors, because the signer
  was written (T003) before the tests; its ability to fail is shown by the negative cases in the same file.

## What the work found

- **The spec's SC-001 was unachievable as written.** It asked six refusals to give six distinct reasons;
  a changed field and a wrong token are both `bad_signature` from a verifier's point of view, and should
  be (telling them apart tells an attacker which half of a guess was right). Found while building the
  vectors; SC-001, FR-002 and the tasks now say seven refusals, six reasons.
- **The build test failed, and the failure was the instrument, not the product.** Written to call Vite's
  `build()` inside vitest, it found the sentinel launch string in the "production" bundle. Cause: vitest
  sets `NODE_ENV=test`, so `import.meta.env.DEV` was true inside that build. Built the way
  `npm run build` does it — a child process with `NODE_ENV=production` — the bundle is clean, and a
  development build of the same code does contain the sentinel, which is the control that shows the
  search can find one. A check that runs under different conditions from the thing it checks says
  nothing about it.
- **The mutation sweep found four guards nothing tested**: a launch naming a field twice, a launch of
  absurd size, a non-ASCII hash (a `TypeError`, so a 500, without the `.encode()`), and the *reason* for
  another authorization scheme. The tests were written alongside, after the sweep, and say so.
- **`apps/web` type-checked without Node's types**, so two new tests that read a file and build with
  Vite would have failed `make web-typecheck` in CI. `@types/node` is now a dev dependency.
- **Live, the overview has nothing to show.** `GET /api/v1/markets` returns `{"markets":[]}`. That is
  not this work and not new, but it is the first thing a phone would show. It is the next thing to look at.

## After

`make test`: 3172 passed and one perf timing test failing under load (`test_the_read_stays_linear_as_the_series_grows`,
ratios 1.78 and 4.90; it passed 4 of 4 alone at 1.75–2.14, and the host's load average was 3.5–4). It is
the fourth different timing test to fail a gate this session; none touches this change. `make lint`,
`make typecheck`, `make web-typecheck`, `make web-test` (29 files, 274 tests) and `make web-build` clean.

**Mutation sweep** `telegram_auth.toml`: 14 caught, 1 survived with its reason recorded — signing compared
with `==` instead of in constant time, which accepts and refuses exactly the same strings, so a test
cannot see it.

**Run for real (T021), 2026-10-03 14:24 UTC**, against a temporary API container with
`CHANNELFLOW_TELEGRAM_AUTH=required` and a launch signed by the dev tool: unsigned → 401 `missing_hash`;
wrong token → 401 `bad_signature`; a launch 200,000 s old → 401 `too_old`; signed → **byte-identical** to
the response recorded before the change (14 bytes for `/markets`, 370 for `/timeframes`); `/readyz` and
`/metrics` unsigned → 200. Then `api` and `web` were recreated with the new code (mode `off`); `worker`
and `resample` were not touched and still run from 07:18 UTC, so the [[REQ-WP-079]] measurement is
undisturbed.

## What was decided

- **The websocket is refused by the same middleware** (it covers `/ws/`), so `ws.py` is unchanged.
  The plan had said to change it; one place is simpler and cannot disagree with itself.
- **Status `tested`.** The last acceptance line is "shown on a phone, from a bot", which needs a bot
  token, a tunnel token and a domain that only the owner has. Setting `implemented` before then would be
  the [[REQ-WP-076]] mistake: a green suite and an unshown product.

## What is still open

- **SC-005 / T023**: the phone. Needs the bot token, the tunnel token and a hostname.
- **The overview is empty**, as above.
- **Perf timing tests flake under load** and have cost this session several gate retries; a separate
  piece of work.
- Whether the dark palette is enough: only a phone shows the rest.
