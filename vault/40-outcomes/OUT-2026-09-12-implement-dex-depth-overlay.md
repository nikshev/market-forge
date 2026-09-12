---
id: OUT-2026-09-12-implement-dex-depth-overlay
step: implement
records: [REQ-WP-054]
commit: null
---

## What was done

A point-in-time read on `dex_depth`, a `/api/v1/dex/depth` endpoint, the client
call and types, and `apps/web/src/dexDepth.ts` — the decision about what to
draw, tested, with the drawing left to the library as `volumeProfile.ts` does.
21 new tests across Python and TypeScript, 10 of 10 mutants caught.

PRD §27.2's toggle `dex_liquidity_bands` has been in the overlay vocabulary
since [[REQ-US-002]] with no layer behind it. It has one now.

## Carrying a refusal four boundaries

[[ADR-036]]'s `reachable` had to survive the table, the repository, the
response and the client. Each boundary is a chance to drop it, and dropping it
turns "this pool is too thin to move 100 bps" into "100 bps costs this much
here" — a cheaper-looking market than exists, drawn in the same ink as a real
one.

The half that is easy to miss is that an unreached band is **kept**. Omitting it
is the same lie by absence: a chart with no 100 bps band reads as a chart nobody
asked about 100 bps. So the overlay has two roles, `reached` and `exhausted`,
and a test asserts they differ rather than asserting each separately.

This is also the first overlay in the app that can refuse. Every existing layer
draws a series that either exists or does not; a depth band can exist *and*
decline to answer, which the overlay vocabulary had never had to carry.

## A nanosecond does not fit in a JavaScript number

The staleness test failed by 120 nanoseconds, which was not a rounding error in
the test. Measured:

    Number.MAX_SAFE_INTEGER   9,007,199,254,740,991   (9.0e15)
    a nanosecond timestamp    1,700,000,000,000,000,000 (1.7e18)
    spacing at that magnitude 256 nanoseconds
    (t + 5000) - t            5120

**Every `_ns` field this app already declares is a `number`** — bar times,
`as_of_ns`, `opened_at_ns`, all of them. So each quantises to the nearest 256
nanoseconds, and a deep link carrying `as_of_ns` round-trips to a different
instant than the one displayed.

The argument that settles it is one this project already made: **money crosses
the wire as a string because JSON's number is a float64.** A nanosecond
timestamp has exactly the same problem and a larger margin.

This field is exact — string over the wire, `bigint` in the client. The rest are
not, and the specification records that as an open question with the
measurement rather than my changing every field in the app inside a requirement
about an overlay.

## What the sweep found, and it was the good kind

Five survivors on the first pass, and four of them said the same thing: **the
lakehouse reader was never exercised by any test.** The route tests use the
in-memory repository, so `read_bands` and `latest_curve_at` could have returned
the whole history, the oldest curve, or another pool's bands without a single
assertion noticing.

Worse, the docstring claimed the two repository implementations agree about "as
of" — a claim nothing checked. There is now a test comparing them at five
instants, and that claim is a requirement rather than a comment.

The fifth: a price crossing the wire through a float survived, because
`str(float(Decimal("3000.1666")))` happens to be `"3000.1666"`. The fixture now
uses a value `float64` cannot hold.

## What is still open

- **The `_ns` fields across the app**, above.
- **§27.3's "DEX active liquidity" pane**, a lower pane reading a different
  primitive.
- **Drawing.** This module decides what to draw; nothing renders it yet, which
  is the same division `volumeProfile.ts` has lived with since [[REQ-WP-012]].
