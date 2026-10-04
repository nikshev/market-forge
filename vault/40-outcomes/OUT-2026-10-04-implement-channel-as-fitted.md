---
id: OUT-2026-10-04-implement-channel-as-fitted
step: implement
records: [REQ-WP-082]
commit: null
---

## What was done

The chart now draws the channel as the model fitted it: three lines, `level_now * exp(slope * (i - last))`, over
the **lookback window only**, ending at the last bar closing at or before the snapshot's instant. The API
returns the missing `slope_log_per_bar` (additive; every earlier field unchanged). With no instant named the
chart opens on the last two lookbacks of bars, so the channel fills the view and a spike days earlier no
longer stretches the axis; the centre is solid and heavy and the bounds take the zones' colours.

## The cause, found by reading

The owner wrote "I do not see the channel". `series.ts` mapped **every** candle to the same three values
(`const at = (value) => candles.map(c => ({time, value}))`), so a channel fitted to the last sixty bars was a
flat stripe across 800 bars, a quarter of a percent wide (84,769 to 84,978) on an axis stretched to
82,000-89,000 by a spike on 28 September, grey, thin and dashed, with `fitContent()` making the window a few
pixels wide. Underneath, the API did not return the slope: `slope_log_per_bar` is stored but `ChannelOut` kept
only `slope_normalized`, which cannot be turned back into it.

## RED, as run (before any source change)

- Python: `KeyError: 'slope_log_per_bar'` (3) and the set of served fields lacking it: 4 failed.
- Web: **17 failed, 3 passed** of 20: `expected [ …(12) ] to have a length of 5 but got 12` and the rest of the
  shapes. The 3 that passed are the unchanged cases (no channel, and the zones).

## After

API tests 266 passed; web 31 files and **297 tests**; `make test` **3232 passed**; mypy, `web-typecheck`,
`web-build` clean. **One existing assertion changed**, the one that encoded the fault
(`Chart.test.tsx`: "one equal point per bar"); it now asserts the last point and the window's length, with a
comment saying why, and its fixture gained the new field.

**Checked against live data (T006, SC-002), 2026-10-04 08:2x UTC.** For BTCUSDT 15m on Binance, Bybit and OKX,
five instants each, in the refit view: the share of a 60-close window lying inside the reconstructed band is
**exactly 0.80 in all fifteen windows**. That is what 10 % and 90 % residual quantiles guarantee, so it is
the reconstruction being exact, not approximately plausible.

`api` and `web` were rebuilt and recreated (`--no-deps`; `worker`, `resample` and the ingest services were not
touched).

## What was decided

- **Reconstruct in the page** from `level_now` and the slope; an endpoint returning the points was rejected
  (the formula is three lines).
- **The window ends at the snapshot's own bar**, so the AS-SEEN-THEN view does not stretch a channel to a time
  it did not exist.
- **No usable slope, no lines**, including from an older server whose response lacks the field.
- **Documents and implementation in two commits, not five**, because the change is small and each gate costs
  a quarter of an hour.

## What is still open

- The channel's *history* — the snapshot stored at each earlier bar — is the fuller as-seen-then picture and
  needs a range endpoint; out of scope.
- A filled band: the library has no primitive for it.
- Whether the colours read on a dark theme: the Material UI work that follows carries the theme.

## Correction, same day: two lookbacks, not three

A screenshot of the deployed page (headless Chromium, 15m, BTCUSDT) showed the channel now drawn as the spec
says — blue centre, red and green bounds, over the last sixty bars — but the default view of **three** lookbacks
(180 bars, 45 hours) still took in a spike from a day and a half earlier, so the axis ran 82,000-88,000 and the
channel, a quarter of a percent wide, was still a thin ribbon. Two lookbacks (120 bars, 30 hours) leave the spike
out. `visibleRangeForChannel` and its test now say two; the spec's "three lookbacks" was a guess that the picture
refuted, and it is corrected rather than left standing. I had called the view "fixed" from the numbers alone before
looking at it.
