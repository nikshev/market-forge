---
id: OUT-2026-09-12-implement-shared-session
step: implement
records: [REQ-WP-051]
commit: null
---

## What was done

`connectors/session.py` holding one lifecycle and three venue policies,
`binance/session.py` deleted and its tests migrated, a mutation specification.
27 tests over the session, 18 of 18 mutants caught.

**This closes Phase 5.**

## Three venues, three keepalives, measured

Opened a connection, subscribed to nothing, timed the close:

    Binance    -                       the venue pings, the client answers
    Bybit      60.7s, no close frame   the client sends `{"op":"ping"}`
    OKX        30.9s, code 4004        the client sends `ping`, bare text

Then the same with a busy subscription: **neither closed in five and a half
minutes** without a client ping. So inbound data resets the timer, and the
keepalive is for quiet subscriptions rather than for every connection. A session
that reconnected on every quiet stretch would churn connections and lose its book
each time.

Then with client pings and no subscription: both survived a hundred seconds.
Bybit answers `{"success":true,"ret_msg":"pong",...}` and OKX answers the bare
string `pong`.

## The finding that shaped the design

**Bybit sends no close frame.** A client waiting for a clean close waits forever:
the connector looks healthy and receives nothing, which is the worst failure a
market-data process has, because every downstream figure simply stops moving and
nothing says why.

So on that venue silence past the idle timeout *is* the drop. On OKX it is not —
OKX says why it closed, with a code and a message, so inferring a drop from
silence there would be this session inventing an event the venue reports.

The same silence means different things on two venues, and either single rule
would be wrong for one of them. That is why `announces_close` is a field.

## What was deliberately not measured

**The connect rate limit.** Both venues cap how often an address may open a
connection, and establishing the cap means exceeding it against a venue that has
done nothing to deserve it. The throttle is built and tested; the interval in
each policy is conservative rather than discovered and is marked as such.

This is the first time in this phase that "measure it" was the wrong answer, and
it is worth naming: the method has limits, and they are about what the
measurement costs somebody else.

## Binance moved rather than being wrapped

Its module is deleted and its five lifecycle tests now drive the shared session.
A shared interface that one venue opts out of is two interfaces, and the venue
that already worked is exactly the one that would have been left alone.

## What the sweep found

Sixteen of eighteen died immediately. Both survivors were gaps in the tests:

- **The keepalive direction was never actually consulted.** Binance's policy
  carries no ping interval, so replacing `keepalive is CLIENT_INITIATED` with
  `True` changed nothing — the `interval is not None` check still guarded it. The
  new test uses a policy that is server-initiated *and* carries an interval, a
  mistake nothing refuses because the two fields are independent.
- **The ping schedule was never actually a schedule.** Never advancing the
  ping clock makes the session ping on *every* tick, and the original test ticked
  once after the interval — so it saw one ping either way. Ticking five times
  inside the interval is what tells them apart.

## What is still open

- **Whether Bybit and OKX have a stream lifetime**, which means holding a
  connection open for a day. Nothing has needed it.
- **HyperCore has no policy yet.** It has a normalizer ([[REQ-WP-048]]) and no
  session, and its socket recovery is [[REQ-PHASE-4]]'s remaining item rather
  than this one.
