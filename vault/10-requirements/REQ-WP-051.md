---
id: REQ-WP-051
title: One stream lifecycle, three venues, and the differences written down
type: work-package
prd_ref: "§0 item 10, §35.6, §45 Phase 5"
prd_lines: "29, 4897-4903, 6821-6832"
phase: 5
status: implemented
depends_on: [REQ-WP-003, REQ-WP-043, REQ-WP-044]
tags: []
---

## Requirement

PRD §0 item 10 requires that new connectors implement a shared canonical
interface, and §35.6 lists **reconnect** and **rate limits** among what
connector contract tests must cover. Until now only Binance had a session, and
its venue's rules were constants in its own module — so there was no interface to
share and nothing for a second venue to implement.

**Three venues keep a connection alive three different ways**, measured on
2026-09-12 by opening a connection, subscribing to nothing, and timing the
close:

    venue      idle close              keepalive
    ------------------------------------------------------------------
    Binance    -                       the venue pings, the client answers
    Bybit      60.7s, no close frame   the client sends `{"op":"ping"}`
    OKX        30.9s, code 4004        the client sends `ping`, bare text

Three consequences, none of which a documentation page makes obvious:

**Inbound data resets the timer.** Subscribed to a busy channel and sending
nothing, neither venue closed in five and a half minutes. The keepalive is for
quiet subscriptions, and a session that reconnected on every quiet stretch would
churn connections and lose its book each time.

**Bybit sends no close frame.** A client waiting for a clean close waits
forever: the connector looks healthy and receives nothing. On that venue silence
past the idle timeout is the only signal there is, and it has to be read as a
drop. OKX says why it closed, with a code and a message, so inferring a drop
from silence there would be inventing an event the venue reports.

**OKX's ping is a bare string and Bybit's is JSON.** Assembling a payload from a
venue's name would work for one of them.

**One fact here is deliberately not measured.** Both venues cap how often an
address may open a connection, and establishing the cap means exceeding it
against a venue that has done nothing to deserve it. The throttle is built and
tested; the interval in each policy is conservative rather than discovered, and
says so.

## Acceptance

- One session drives all three venues, and what differs between them is data
  rather than code.
- Each venue's keepalive direction, payload, interval and idle timeout are
  recorded as measurements, and a test asserts the three do not agree.
- A client-initiated venue is pinged on a schedule, and ticking inside the
  interval sends nothing.
- A server-initiated venue is never pinged by the client, decided by the
  keepalive direction rather than by whether an interval happens to be set.
- A policy whose ping interval could not keep its own connection alive is
  refused at construction.
- Silence past the idle timeout is treated as a drop on the venue that announces
  nothing, and is not second-guessed on the venue that does announce.
- A reconnect deferred by the connect limit is counted and not forgotten.
- Any reconnect requires a fresh snapshot, on every venue.
- No test opens a socket.

## Notes

Human territory. Never machine-rewritten.

**Binance's own session moves rather than being wrapped.** Its module is deleted
and its five tests now drive the shared one, because a "shared interface" that
one venue opts out of is two interfaces.

**A lifetime of `None` means unmeasured, not unlimited.** Binance closes a
stream at twenty-four hours; nothing similar was observed on the other two,
which is not the same as there being nothing. Absent is not zero, here as
everywhere else in this project.

**This closes Phase 5.**
