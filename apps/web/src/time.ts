// @trace: REQ-WP-061
//
// Every instant this application receives is a nanosecond count since the epoch,
// around 1.8e18. `Number.MAX_SAFE_INTEGER` is 9.0e15, so at that magnitude the
// representable doubles are **256 nanoseconds apart**: a mark read as a number is
// rounded, and two marks 100 nanoseconds apart compare equal.
//
// Measured: 1789000000123456789 read as a number comes back
// 1789000000123456768, and `Number(1789000000000005000n) ===
// Number(1789000000000005100n)`.
//
// That reaches four comparisons in this app, and all four err permissively --
// they admit what was not yet knowable, which is the one rule Principle I does
// not bend. So instants are `bigint` here and strings on the wire.

export class BadTime extends Error {}

// Digits only, and no leading zeros beyond a bare "0".
//
// `BigInt("")` is `0n`, not an error: an empty field would become the epoch,
// which is positive, ordered and believable, and would place a bar at the
// beginning of time rather than failing. `BigInt("12.5")` and `BigInt("abc")`
// throw, which without this would reach a reader as a crash inside a render
// instead of REQ-WP-009's stated load failure.
const DIGITS = /^(?:0|[1-9][0-9]*)$/;

export function nanoseconds(raw: unknown, field: string): bigint {
  if (typeof raw !== "string" || !DIGITS.test(raw)) {
    throw new BadTime(`${field} is not a nanosecond timestamp: ${JSON.stringify(raw)}`);
  }
  return BigInt(raw);
}

// The same, for a field the API may legitimately send as null.
export function optionalNanoseconds(raw: unknown, field: string): bigint | null {
  return raw === null ? null : nanoseconds(raw, field);
}

// A duration, which is a number on purpose.
//
// Spans are bounded by the timeframes this system supports -- a week is 6.0e14,
// well inside the safe range -- so the conversion timestamps need would be churn
// here. The bound is checked rather than assumed, because a caller could one day
// pass something that is not a span.
export function duration(raw: unknown, field: string): number {
  if (typeof raw !== "number" || !Number.isSafeInteger(raw) || raw < 0) {
    throw new BadTime(`${field} is not a duration in nanoseconds: ${JSON.stringify(raw)}`);
  }
  return raw;
}

// The one place precision is deliberately given up.
//
// lightweight-charts addresses time as seconds and lays out pixels in floats, so
// nanoseconds cannot reach an axis whatever this app does. Doing it through a
// named function rather than a coercion is what keeps it a decision: the loss is
// 256 nanoseconds at a scale where one pixel is minutes, and the reason it is
// acceptable *here* is the reason it is not acceptable in a comparison.
const NS_PER_SECOND = 1_000_000_000n;

export function chartSeconds(atNs: bigint): number {
  return Number(atNs / NS_PER_SECOND);
}

// Milliseconds, for the places a browser API needs one (a date, a label).
export function chartMilliseconds(atNs: bigint): number {
  return Number(atNs / 1_000_000n);
}

// An ISO instant to nanoseconds, exactly.
//
// `Date.parse` gives milliseconds, and multiplying that by 1e6 in floating point
// lands back above the safe range -- so the multiplication is done in `bigint`.
// Null for an unparseable value, which is what the deep link does with every
// other mangled field (ADR-020).
export function nanosecondsFromIso(value: string): bigint | null {
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? null : BigInt(ms) * 1_000_000n;
}
