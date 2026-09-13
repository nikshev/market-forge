---
id: OUT-2026-09-13-implement-nanosecond-precision
step: implement
records: [REQ-WP-061]
commit: null
---

## What was done

`WireTime` in `api/schemas.py`, `time.ts` and a conversion boundary in `api.ts`,
and every instant in the web app is now a `bigint`. 16 Python tests, 35 web
tests, **9 of 9 mutants caught**.

This closes [[REQ-WP-054]]'s open question, which had been carried for four
sessions and recommended in three of them.

## What was actually wrong

A nanosecond mark is around 1.8e18 and `Number.MAX_SAFE_INTEGER` is 9.0e15, so at
that magnitude the representable doubles are 256 nanoseconds apart. Measured:

    served   1789000000123456789
    read     1789000000123456768
    Number(1789000000000005000n) === Number(1789000000000005100n)   true

Fourteen of sixteen `_ns` fields in the web app were numbers, and four
comparisons read them:

    extrema.ts    known_at_ns <= atNs           admitted what was not knowable
    extrema.ts    observed_at_ns <= atNs        the same, for candidates
    stopPath.ts   anchor.known_at_ns > at_ns    a look-ahead guard, blind to 256ns
    panes.ts      Map keyed by at_ns            two instants, one key

**All four erred permissively**, which is the direction Principle I does not
allow, and `make validate` could not see any of it. A fifth site was in the deep
link: `Date.parse(iso) * 1_000_000` is floating-point multiplication landing back
above the safe range, so the link rounded the instant it existed to name.

It was latent rather than live — present sources timestamp in milliseconds or
microseconds — so this was a guard with a blind spot, not a wrong number on
screen. The reason to fix it now is that each new pane adds a consumer.

## One rule instead of eight parsers

`api.ts` converts every key ending in `_ns` by one rule: **a string is an instant
and becomes a `bigint`; a number is a duration and stays one.**

That rule is only safe because the other end enforces it, and the two halves are
what make each other work. `tests/unit/api/test_wire_time.py` asserts, field by
field, which `_ns` field of which schema is a string and which is an integer, and
fails when a new one appears without choosing. So a timestamp cannot arrive in the
browser as a number and be silently accepted as a span.

Durations are deliberately not converted: `timeframe_ns` and `hindsight_ns` are
bounded by the timeframes this system supports, and a week is 6.0e14. The bound
is asserted rather than assumed, because that is what makes the distinction
legitimate instead of convenient.

## `BigInt("")` is `0n`

Not an error. An empty field would become the epoch — positive, ordered,
believable — and place a bar at the beginning of time. The `WireTime` pattern
refuses it at the schema, and `time.ts` refuses it again on the way in, because
the two ends are separately reachable.

`"007"` is refused too: a canonical mark has no leading zeros, and two spellings
of one instant must not both be servable.

The conversion lives inside `api.ts`'s `Result` boundary. `BigInt("abc")` thrown
in a component gets an empty React tree, which is precisely the indistinguishable
blank REQ-WP-009's FR-016 forbids — so a bad payload becomes a named failure
instead, carrying the field's path (`points[0].at_ns`).

## The narrowing is named, not avoided

lightweight-charts addresses time in seconds and lays out pixels in floats, so
nanoseconds cannot reach an axis whatever this app does. `chartSeconds` and
`chartMilliseconds` divide in `bigint` first, so the *input* is exact and what is
given up is resolution the drawing never had. Both SVG panes go through them.

Doing it through a named function is the point: the loss is acceptable there for
the same reason it is unacceptable in a comparison, and a bare `Number(x)` would
not have said which case it was.

## Two mistakes of mine worth recording

**A patch script with a no-op entry.** I included an assertion that
`import { toSeconds` already existed in `Chart.tsx`; it did not, the script
aborted, and the three patches after it silently did not apply. I only noticed
because `tsc` still reported the same errors. A batch of edits that stops halfway
and reports success is worse than one that fails loudly — the later patches now
run independently.

**A demonstration that hung.** Showing the quantisation, I wrote
`while (next === x) next = next + 1` to find the grid step. At 1.8e18 adding 1 to
a double does not change it, so the loop was infinite — I had written the bug I
was demonstrating, as the demonstration.

## What this does not change

`PositionOut` and the stop shapes are served by no route yet, and are converted
anyway: `stopPath.ts`'s look-ahead guard is one of the four sites, and the route
that eventually serves them now has a declaration to match. Nothing outside this
repository consumed the eleven fields whose wire format changed.
