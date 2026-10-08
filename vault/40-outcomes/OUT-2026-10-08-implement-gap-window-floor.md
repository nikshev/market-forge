---
id: OUT-2026-10-08-implement-gap-window-floor
step: implement
records: [REQ-WP-087]
commit: null
---

## What was done

Gave the channel fit a floor after a hole: a window shorter than `min_window_bars` is refused with
`ChannelFitError` (the channel is absent for that bar) instead of reaching `np.polyfit`. The floor is a
field of `RollingOLSChannel` (default 10, capped by the lookback, never below 2), passed to `fit_window`, and
part of the pass config hash.

## What happened

Rebuilding the `worker` image for [[REQ-INFRA-007]] on 2026-10-08 (15:45 UTC) shipped, for the first time,
the gap policy of [[REQ-WP-087]], which had been implemented on 2026-10-07 and never deployed (the previous
image dated from 4 October). **Every series-timeframe then failed** with `LinAlgError: SVD did not converge`,
so the worker produced no channels, signals or extrema from 15:45 until the fix was deployed. Nothing
was written wrongly (a failed series writes nothing), but the data went stale.

The cause: REQ-WP-087 lets a channel restart at a hole and fit "whatever follows". On the real series
**every hole leaves a window of exactly one bar** (nine holes in `binance BTCUSDT 5m` alone), and a line
cannot be fitted through one point: `np.polyfit` divides by a zero column. `BacktestRunner` catches
`ChannelFitError` and moves on; it does not catch `LinAlgError`, so the first hole ended the replay of
the whole series. The tests of REQ-WP-087 used synthetic series whose post-hole windows were already
three or four bars, so they could not see it, and an earlier outcome note even recorded two of its tests as
having "data issues" -- that was the warning, not noise.

I made it worse by not deploying carefully enough: the first evidence of failure was thirty minutes of
silence from the notary's outbox, not a check of the worker's log after the restart. A post-deploy look at
`docker logs` for `FAILED` would have caught it in the first minutes. That check is now part of the deploy
procedure in the tasks.

## What was decided

- **The floor is a configuration field of the model, default 10, and it is a choice, not a derivation.**
  Ten is where the 10th percentile of the residuals stops being their minimum (so the bands are quantiles of
  something). Measured on the real series, windows of 2 bars fit but in some cases to a channel of zero width,
  and windows of 3 or more fit. **The owner may want a different number** -- the REQ-WP-087 specification says
  "absent or flagged short" and does not give one -- and changing it is one field, visible in the config hash
  of every record it affects.
- **Rejected:** catching `LinAlgError` in the runner (it would hide any other numerical failure behind
  "no channel"); making the floor 2 (it admits zero-width channels, and a perfect fit on two points is not a
  channel); restoring the old behaviour by reverting REQ-WP-087 (the gap policy is correct in intent -- the
  detector and the window must not straddle a hole; only the lower end was missing).

## Evidence

- RED: `test_a_series_with_a_hole_replays_to_the_end_with_the_default_runner` raised the production
  `LinAlgError` on the code as deployed; four more tests failed on the missing parameter.
- GREEN: the channel, gap and config-hash tests (109), then **a replay of the real lakehouse, locally and
  without writing: 30 series-timeframes, 0 failures** (the deployed code failed all of them).

## What is still open

- Whether 10 is the right floor, and whether windows between 10 and the lookback (60) should be emitted at all
  -- they are flagged `window_short` and nothing downstream is told to distrust them.
- A guard that would have caught this class of problem: a test that replays a *real* (or realistically gapped)
  series through the default runner. The new regression test is that, for one hole; the real-data replay
  used here is a script, not a suite member (it needs the live lakehouse).
