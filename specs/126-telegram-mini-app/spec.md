---
traces: [REQ-WP-080]
status: draft
---

# Feature Specification: The overview and the chart open as a Telegram Mini App, authenticated by Telegram

**Feature Branch**: `126-telegram-mini-app`

**Created**: 2026-10-03

**Status**: Draft

**Input**: [[REQ-WP-080]] — PRD US-002 ("press a button in Telegram and open the chart exactly at the
signal's timestamp"), §26.1, §27.1, §27.5 and the secrets rule.

## Context

The pages this specification is about exist and work: the overview at `/` ([[REQ-WP-075]]) and the
chart at `/chart/<venue>/<symbol>` with its timeframe selector and channel overlay ([[REQ-WP-074]]),
served by nginx with `/api` proxied to the API ([[REQ-WP-064]]). They open in a browser tab. The
point of this change is to open them **inside Telegram**, from a bot, so the product can be shown on
a phone — the way `/opt/lexa-reader` already runs.

Nothing here changes what a page shows. It adds four things around the pages: that they behave as a
Mini App, that the API can tell a launch Telegram signed from one anybody typed, that a link carries
the chart state in, and a stable HTTPS address for Telegram to open.

### What `lexa-reader` taught, and what is not copied

It is a React and Vite single-page app behind Caddy, reached through a Cloudflare Tunnel, whose
backend verifies Telegram's `initData` and exchanges it for tokens kept in a database. Three of its
lessons carry over directly: Telegram's WebView **swallows vertical swipes**, so taps on a chart never
fire unless the gesture is disabled; a **dev tool that signs a launch locally** is what makes the
authentication loop testable in a plain browser; and an **HTTPS origin with no open ports** is simpler
than certificates on the box.

One thing is not copied. `lexa-reader` has users, a database and tokens. This API has none of those
and the market view is read-only, so **the launch is verified on every request** and nothing is
stored: no token, no user row. That also means the user's identity is not needed — only that Telegram
signed this launch for this bot — so it is neither stored nor logged.

### What the gate protects, and what it does not

The data is public market data. The gate is not a secret-keeper; it is what stops the tunnel's public
address from being a free read API for anyone who finds it, and what makes "opens inside Telegram"
mean something. A signed launch stays valid for a bounded time, so a captured one can be replayed for
that long; for read-only public data that is accepted, stated, and bounded by a configurable age.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The API accepts what Telegram signed and nothing else (Priority: P1)

**Why this priority**: it is the security property of the whole change, and the only part that can be
wrong in a way a demo would not show.

**Independent Test**: sign launches with the dev tool (another language from the verifier) and hand
them to the API in each state of wrongness.

**Acceptance Scenarios**:

1. **Given** a launch signed with the configured bot token and fresh, **When** it is verified,
   **Then** it is accepted — and the two independent implementations agree on the signature.
2. **Given** a launch with one field changed, **or** signed with another token, **or** with the hash
   missing, **or** the `auth_date` missing or not a number, **or** older than the configured age, **or**
   more than a minute in the future, **When** it is verified, **Then** each is refused, for the reason
   that names what was wrong. A changed field and a wrong token are one reason, a bad signature, **on
   purpose**: telling them apart would tell an attacker which half of a guess was right.
3. **Given** authentication is required, **When** a request to a market route has no valid
   `Authorization: tma <initData>` header, **Then** it gets 401 and **no market data**.
4. **Given** authentication is required, **When** the request has a valid header, **Then** the response
   is exactly what it is today.
5. **Given** authentication is off (the local default), **Then** nothing changes for anyone.
6. **Given** authentication is required and no bot token is configured, **When** the service starts,
   **Then** it refuses to start rather than serve open.
7. **Given** the readiness and metrics routes, **Then** they are not behind the gate and are **not
   reachable through the public address**.

---

### User Story 2 - The page behaves as a Mini App, and as itself outside Telegram (Priority: P1)

**Independent Test**: open the page with a stand-in for Telegram's WebApp object, and without one.

**Acceptance Scenarios**:

1. **Given** the stand-in, **When** the page loads, **Then** it tells Telegram it is ready and
   expands, once each.
2. **Given** the stand-in's theme parameters and colour scheme, **Then** they are applied to the page.
3. **Given** the chart route, **Then** Telegram's back button is shown and returns to the overview;
   **given** the overview, **Then** it is not shown.
4. **Given** the stand-in, **Then** vertical swipes are disabled so touches reach the chart.
5. **Given** the stand-in's launch data, **Then** every API request carries it as `Authorization: tma …`.
6. **Given** no Telegram object, **Then** the page loads, throws nothing, sends no such header, and
   behaves as it does today.

---

### User Story 3 - A link carries the chart state in, in either form (Priority: P1)

**Why this priority**: US-002 is the reason a Mini App exists here: the alert's button must open the
chart *at the signal*.

**Independent Test**: parse the same chart state expressed both ways.

**Acceptance Scenarios**:

1. **Given** a launch with a `start_param` encoding a chart state, **and** the page opened with the
   equivalent query string, **Then** both produce the same venue, symbol, timeframe, instant, mode and
   overlays.
2. **Given** a `start_param` that cannot be read, **Then** the page opens the overview and says nothing
   false: the default is the one ADR-020 gives a mangled link (AS-SEEN-THEN, never a silent refit).

---

### User Story 4 - It has a stable HTTPS address (Priority: P2)

**Independent Test**: validate the stack's configuration with and without the profile.

**Acceptance Scenarios**:

1. **Given** the `telegram` profile, **Then** the stack also starts a tunnel to the web service and
   opens **no new host port**.
2. **Given** no profile, **Then** nothing new runs.
3. **Given** the production build, **Then** it contains no signed launch data from the dev tool.
4. **Given** the deployment document, **Then** it explains the bot, the tunnel and where the URL is
   set, and names every new environment variable (the repository's existing documents test).

---

### User Story 5 - It is shown on a phone (Priority: P2)

**Why this priority**: it is the reason for the work, and the one acceptance item no test can stand in
for. It needs a bot token and a tunnel that the owner provides.

**Acceptance Scenarios**:

1. **Given** the bot and the tunnel, **When** the bot's Mini App is opened in Telegram on a phone,
   **Then** the overview shows, a market opens its chart, the timeframe selector works and the channel
   overlay shows. Recorded with the date and the URL used.

### Edge Cases

- A launch with **no `user` field** (some launch sources omit it): accepted, because identity is not
  used. A launch with a malformed `user` is still a signed launch.
- The **websocket** `/ws/market` cannot carry an `Authorization` header from a browser. It is not under
  `/api`, so the web service's proxy does not reach it, but the API port can be bound directly. When
  authentication is required it must be closed to an unsigned caller by some means; which, the plan
  decides.
- **Clock skew**: Telegram's `auth_date` against this host's clock; a minute either way tolerated.
- **A header that is not valid UTF-8, or enormous**: refused, not a 500.
- **The bot token in a log or an error message**: never.
- Telegram's **`start_param` alphabet and length limit** (letters, digits, `_`, `-`; 512 characters)
  constrain what a link can carry and may require a short encoding.
- Telegram clients older than the Bot API version that provides a given method: calls are guarded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The API MUST verify a launch as Telegram defines it: HMAC-SHA256 over the sorted
  `key=value` lines with the key `HMAC("WebAppData", bot_token)`, compared in constant time.
- **FR-002**: A launch MUST be refused when a field was changed, the token differs, the hash is
  missing, `auth_date` is missing or not a number, the launch is older than the configured maximum age,
  or is more than a minute in the future — each with the reason that names what was wrong (a changed
  field and a wrong token share the reason `bad_signature`), and none of them naming the token.
- **FR-003**: The signature computed by the dev tool and the one the verifier expects MUST agree,
  proven by two implementations in two languages over the same inputs.
- **FR-004**: With authentication required, every route that serves market data — including the
  websocket — MUST refuse an unsigned caller with no market data in the answer; a signed caller MUST
  get today's response unchanged.
- **FR-005**: Authentication MUST be configurable (off, required), default off, and `required` without
  a configured bot token MUST stop the service at start.
- **FR-006**: The bot token MUST come from the environment or a secret and never from the repository.
- **FR-007**: Readiness and metrics MUST NOT be behind the gate and MUST NOT be reachable through the
  public address.
- **FR-008**: The user's identity MUST NOT be stored or logged.
- **FR-009**: The page MUST signal ready and expand once, apply the theme, manage the back button by
  route, disable vertical swipes, and send the launch data with every API request, when and only when
  running inside Telegram.
- **FR-010**: Outside Telegram the page MUST behave as it does today and send no authorization header.
- **FR-011**: A `start_param` and the equivalent query string MUST yield the same chart state.
- **FR-012**: A `start_param` that cannot be read MUST open the overview, not guess a chart.
- **FR-013**: The stack MUST offer an off-by-default `telegram` profile that adds a tunnel to the web
  service and no host port.
- **FR-014**: A production build MUST NOT contain signed launch data from the dev tool.
- **FR-015**: Every new environment variable MUST be in `.env.example` and the deployment document.

### Key Entities

- **Launch data (`initData`)**: what Telegram hands the page when the Mini App opens, signed for one
  bot, carrying an `auth_date` and optionally a user.
- **Bot token**: the secret that both signs and verifies a launch; never leaves the environment.
- **Authentication mode**: off or required.
- **`start_param`**: the string a Mini App link carries into the page.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Of nine launch variants (valid; valid with no user; field changed; wrong token; no hash;
  no `auth_date`; `auth_date` not a number; stale; future), exactly two are accepted, and the seven
  refused give six distinct reasons — the two bad-signature cases being one by design. *(The first
  wording said six refusals, six reasons; building the vectors showed two of the six cannot differ.)*
- **SC-002**: With authentication required, 0 of the market routes return data to an unsigned request
  (counted by walking every route, and asserting how many were walked — a walk that reaches none
  reports success, which [[REQ-WP-072]] already found once).
- **SC-003**: The page, with the stand-in, makes zero API requests without the header and, without the
  stand-in, zero with it.
- **SC-004**: A production build contains zero occurrences of a signed launch string.
- **SC-005**: The Mini App is shown on a phone, from a bot, once, with the date recorded.

## Assumptions

- A bot exists or will, created with BotFather by the owner; its token is supplied as a secret, not by
  this work.
- The owner has, or will provide, a domain and a Cloudflare Tunnel token (as `lexa-reader`'s deployment
  does); without them the work stops at SC-004 and SC-005 waits.
- The data served is public market data, read-only; the gate is access control and not
  confidentiality, and a captured launch can be replayed until it ages out.
- The existing pages' behaviour is correct and unchanged; this specification does not touch what they
  show.
- Principle I is untouched: nothing here changes which data a chart reads or when.
