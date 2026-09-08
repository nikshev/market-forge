---
traces: [REQ-WP-008]
status: draft
---

# Feature Specification: Telegram alerting

**Feature Branch**: `wp-008-telegram`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-008 — format alert; inline deep-link button; dedupe; retry;
delivery audit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive a setup you can act on (Priority: P1)

A confirmed candidate becomes a message: which symbol, which direction, where
the channel is, what the order flow says, and what would invalidate it.

**Why this priority**: PRD §26.1 gives the message. Without it the signal engine
produces state transitions nobody sees — which is the system's condition today.

**Independent Test**: Build a confirmed candidate with a known channel and known
features and compare the rendered message against an expected string.

**Acceptance Scenarios**:

1. **Given** a confirmed candidate, **When** the message is rendered, **Then** it names the symbol, direction, venue, timeframe, price and event time.
2. **Given** a channel snapshot, **When** the message is rendered, **Then** it carries direction, slope, width, position and quality.
3. **Given** order-flow features, **When** the message is rendered, **Then** it carries the OFI window, depth imbalance and wall persistence.
4. **Given** no data for a section PRD §26.1 lists, **When** the message is rendered, **Then** that section is absent — not present with a placeholder.
5. **Given** a candidate, **When** the message is rendered twice from the same inputs, **Then** the two messages are identical.

---

### User Story 2 - Not be told the same thing twice (Priority: P1)

The same setup in the same state does not produce a second message. A change of
phase does, and so does a fresh touch after the cooldown.

**Why this priority**: PRD §26.2, and PRD §25.6 counts duplicate alert rate as a
quality metric. An alerter that repeats itself trains its reader to ignore it,
which costs more than sending nothing.

**Independent Test**: Offer the same candidate state repeatedly and count what
is emitted.

**Acceptance Scenarios**:

1. **Given** an alert already sent for a setup, **When** the same state is offered again, **Then** nothing is emitted.
2. **Given** an alert already sent, **When** the setup changes phase, **Then** a new alert is emitted.
3. **Given** an alert already sent, **When** the cooldown has elapsed and a new independent touch occurred, **Then** a new alert is emitted.
4. **Given** an alert already sent, **When** the cooldown has elapsed but nothing new happened, **Then** nothing is emitted.

---

### User Story 3 - Delivery that survives a failing network (Priority: P1)

A send that fails is retried with growing delays. One that keeps failing lands
in a dead-letter record. Every attempt is audited. None of it blocks the engine.

**Why this priority**: PRD §26.4, whose last line — "never block signal engine
on Telegram failure" — is the one that matters most. A messaging outage must not
stop the system from computing signals.

**Independent Test**: A transport scripted to fail a set number of times, and
assertions over what was attempted, what was delivered and what was recorded.

**Acceptance Scenarios**:

1. **Given** a transport that fails once then succeeds, **When** an alert is delivered, **Then** it is retried and the audit records both attempts.
2. **Given** a transport that always fails, **When** the attempt budget is exhausted, **Then** the alert is dead-lettered and the audit says why.
3. **Given** any number of failures, **When** the engine offers the next candidate, **Then** it is accepted — queueing never raises.
4. **Given** a sequence of attempts, **When** the backoff is inspected, **Then** each delay is larger than the last.
5. **Given** a completed delivery, **When** the audit is read, **Then** it names the alert, every attempt, its outcome and the event time it was queued.

---

### User Story 4 - Open the chart at the moment in question (Priority: P2)

The message carries a button linking to the chart for that venue, symbol,
timeframe and instant.

**Why this priority**: PRD §26.1's `[ OPEN CHART ]` and §27.1's deep-link
format. P2 because the message is useful before the chart exists to receive it.

**Independent Test**: Render a message and compare the button's URL against the
§27.1 format with known values.

**Acceptance Scenarios**:

1. **Given** an alert, **When** its button is read, **Then** the URL follows PRD §27.1: venue, symbol, timeframe, instant and signal id.
2. **Given** a configured base URL, **When** the link is built, **Then** it is used — the host is not hard-coded.
3. **Given** the same candidate, **When** the link is built twice, **Then** the signal id is the same both times.

---

### User Story 5 - Never be alerted from stale data (Priority: P1)

An alert whose inputs were stale is not sent.

**Why this priority**: PRD §25.6 lists "stale-data alert count" among the
quality metrics and adds "must be zero" — the only metric in the document
carrying a required value.

**Independent Test**: Offer a candidate whose book was behind by more than the
configured tolerance and assert nothing is emitted.

**Acceptance Scenarios**:

1. **Given** a candidate whose book staleness exceeds the tolerance, **When** it is offered, **Then** no alert is emitted and the reason is recorded.
2. **Given** a candidate whose book is invalid, **When** it is offered, **Then** no alert is emitted.
3. **Given** a suppressed alert, **When** the audit is read, **Then** the suppression is visible — a silent drop is indistinguishable from no setup.

---

### Edge Cases

- What happens when the transport succeeds but reports an unexpected response? It is treated as a failure and retried. A delivery nobody can confirm is not a delivery.
- What happens when a candidate terminates before its alert is delivered? Delivery proceeds. The alert states what was true when it was queued, and PRD §0.5 forbids rewriting that after the fact.
- What happens when two candidates for the same symbol produce the same signal id? They cannot: the id derives from venue, symbol, timeframe and the candidate's opening event time, and one machine cannot open two candidates at one instant for one symbol.
- What happens when the chart base URL is not configured? Message rendering fails loudly at construction rather than emitting a message with a broken button.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An alert MUST render symbol, direction, venue, timeframe, price and event time.
- **FR-002**: An alert MUST render the channel's direction, slope, width, position and quality when a channel snapshot is supplied.
- **FR-003**: An alert MUST render order-flow values when supplied, and MUST omit the section entirely when they are not.
- **FR-004**: An alert MUST NOT render a section of PRD §26.1 for which no data exists, and MUST NOT substitute a placeholder value.
- **FR-005**: Rendering MUST be deterministic: identical inputs give an identical message.
- **FR-006**: A repeated alert for the same setup in the same state MUST NOT be emitted.
- **FR-007**: A change of candidate state MUST allow a new alert.
- **FR-008**: A new alert after a cooldown MUST require both the elapsed cooldown and a new touch.
- **FR-009**: Delivery MUST retry on failure, with each delay larger than the previous.
- **FR-010**: An alert exceeding its attempt budget MUST be recorded as dead-lettered.
- **FR-011**: Every delivery attempt MUST be audited with its outcome.
- **FR-012**: Queueing an alert MUST NOT raise, whatever the transport is doing.
- **FR-013**: An alert MUST carry a deep link following PRD §27.1, built from a configured base URL.
- **FR-014**: A signal id MUST be derived from the candidate's identity, so the same candidate gives the same id on every run.
- **FR-015**: An alert whose inputs are stale beyond a configured tolerance MUST NOT be sent, and the suppression MUST be recorded.
- **FR-016**: No module in this feature may consult a system clock or perform network I/O. Time comes from event times; the transport is supplied by the caller.
- **FR-017**: No credential may appear in source, in a rendered message, or in the audit.

### Key Entities

- **Alert**: what is being said, about which setup, at what event time.
- **Delivery attempt**: one try, its outcome, and when it happened in event time.
- **Audit**: the sequence of everything attempted, delivered, suppressed or dead-lettered.
- **Dedupe state**: what has already been said about a setup.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A rendered message matches an expected string, field for field, for a known candidate.
- **SC-002**: A section with no data is absent from the message rather than empty or placeheld.
- **SC-003**: The same candidate state offered repeatedly produces exactly one alert.
- **SC-004**: A phase change produces a second alert; an elapsed cooldown alone does not.
- **SC-005**: A transport failing twice then succeeding produces one delivery and three audited attempts.
- **SC-006**: A transport that always fails produces a dead-letter record, and queueing never raises.
- **SC-007**: The deep link matches PRD §27.1's format, and the signal id is stable across runs.
- **SC-008**: A stale or invalid book produces no alert and one recorded suppression.
- **SC-009**: No module in the package references a system clock or an HTTP client, verified over the source.

## Assumptions

- **No score, so no severity tiers.** PRD §26.3's WATCH/ALERT/HIGH bands are score ranges, and the score comes from PRD §22.3 and §43's alert ranker, which is not built. Confirmed candidates alert; nothing else does.
- **§26.1's derivatives and DeFi sections are omitted**, not filled: WP-013 and WP-014/015 are unbuilt, and a section of placeholders would read as data.
- **Model probability is omitted** for the same reason — Principle IV forbids a model before deterministic baselines, and there is none.
- The chart the deep link points at is REQ-WP-009 and does not exist yet. The link is correct by construction; its target arrives later.
- Delivery is in-process and in-memory. A durable dead-letter table is PRD §29's storage, unbuilt.
- The bot token and chat id come from the environment. Neither is committed, and `.env.example` carries placeholders only.
