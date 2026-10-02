---
id: OUT-2026-10-02-plan-ingest-resilience
step: plan
records: [REQ-WP-078]
commit: null
---

## What was done

Planned [[REQ-WP-078]] as `specs/123-ingest-resilience/`: plan, research, data model,
three contracts (connector, archive, logging), quickstart. The four questions the spec
left open are answered below. A fifth was found while answering them.

## What was decided

**The session polls a fact, and the reader logs the cause.** `VenueConnector` gains
`alive`. A callback was the obvious alternative and was rejected: it fires on the reader's
thread into session state that is not thread-safe, and the one thing it adds — the reason —
is already in hand where the reader ends. Splitting the two means neither has to be
perfect. A reader that exits without a log line is still noticed; one that logs but is
somehow still reported alive is still visible.

**`announces_close` stops gating behaviour.** `tick` reconnected on silence only when a
venue does *not* announce close, which is Bybit alone. That encoded a belief about what a
venue does when it gives up, and Binance and OKX did something else. The field stays as
documentation of what was measured; three grounds — lifetime, dead reader, silence — now
apply to every venue.

**The silence default is 60 s, and it is grounded in the archive.** Longest real gaps:
22.2 s on Bybit BTCUSDT over 360 minutes, 11.2 s on SOLUSDT over 309. A **64.1 s** gap
turned up in the first and was excluded: it began at 10:54:50 and the container started at
10:55:50. It was the restart made that morning, not the market, and a default taken from it
would have been measured from our own outage. The multiplier setting from the previous
change is removed with its tests: a multiple of a quantity that means something else on
each venue is still that quantity.

**Backoff is capped exponential, and `_reconnect` stops raising.** Planning read the
reconnect path and found it would end the daemon from inside `tick`: Binance's `connect()`
raises `NotConnected`, and nothing between there and the ingest loop catches it. At
start-up that is right and loud; mid-reconnect it turns one refused attempt into a dead
process. Fixed-interval retry satisfies the letter of FR-008 and none of its reason.

**Policy has one home, and it is `session.py`.** Seven definitions in two files. `session.py`
is where the measurements are written down and where Binance's 24-hour lifetime was
originally right; `venue.py` becomes the registry its docstring says it is. The two sets
differ in more places than the spec knew: **OKX's ping interval is 15 s in one and 20 s in
the other**, and `session.py` records that fifteen was measured to survive a hundred. A
test asserts Binance's **24-hour idle timeout** as correct; it is replaced by one asserting
the 24-hour **lifetime**.

**The seams are tested where they join.** The thread running through the plan: every test
that would have caught a defect is driven through `build_daemon`, or through a fake
connector whose reader dies without a close frame, or through a compose file read as
data. A test of the part was green beside every one of the seven.

**The archive key carries the symbol as a directory, and a symbol containing `/` is
refused.** A slash would nest and the key would stop meaning what its parts say.

**The migration is copy, verify, then delete, and refuses what it cannot attribute.**
`copy_object` is server-side and keeps the ETag for single-part objects, which makes the
verification a comparison. 24,825 objects, 487 MB, growing by two a minute. Deleting the
misplaced prefix outright was rejected: it holds the only copy of 8,960 Bybit objects.

**Logging is demoted at the source and configured in `main()`.** `logging.basicConfig` at
import time is a side effect every test importing the module inherits. Raising the level in
compose would hide the per-trade lines and the one line that matters with them.
`FrameArchive.flush` logged on every step with an empty buffer — that is Bybit's 5 Hz line.

**Binance gets no rejection reader.** OKX's and Bybit's refusal frames were captured live
and are pinned. For Binance none was ever observed; the repository records only that an
upper-case name "connects and delivers nothing". A rule written from a description of a
format nobody saw would be an invented frame, so its failure mode is treated as silence.

## Mistakes caught while planning

Four, each of the kind this repository keeps having, so each is recorded.

- **I attributed a rationale to `session.py` that it does not contain.** The first draft of
  the research said its 60.0 s and 30.0 s were observed values minus a safety margin and
  that its docstring said so. It says neither: Bybit's 60 s is the observed 60.7 s rounded
  down, and OKX's 30 s is the venue's own stated limit ("No data received in 30s").
  Corrected, and the OKX ping-interval discrepancy found in the process.
- **The migration tool was placed in `tools/`.** The application image copies `src/` only;
  `docker compose exec api python -m tools.…` would have failed on first use. Caught by
  reading the `Dockerfile` and `.dockerignore`, moved to
  `src/channelflow/pipeline/archive_rekey.py` on the precedent of `maintenance_main.py`.
- **A frame in a "captured live" block was partly from memory.** The OKX error text and
  `"code":"60018"` were right, but the capture I held was truncated at "referr". Re-captured
  in full before the contract was left saying "captured".
- **The quickstart's object counter would have counted nothing.** The new layout has eight
  path parts, not seven.

## What is still open

- **The cap numbers.** `20m × 3` per service is a starting point with a basis (days of
  history at the expected rate, a 35-minute rotation at the noisiest measured), configurable,
  and not otherwise justified.
- **Bucket versioning.** It would have preserved the overwritten frames. With the symbol in
  the key, an overwrite now needs one process to restart inside a minute it had already
  written — a smaller exposure than the one repaired — and versioning costs storage and
  brings its own retention question. Not decided.
- **ETH and SOL keep overwriting each other until the fix lands**, and so does everything
  the three Binance processes write. A stopgap — separate archive URIs per service — was
  considered and rejected: it creates a fourth layout to migrate.
- **A process restart within a minute** still replaces that minute's object with its tail.
  Not fixed; stated.
- **`HYPERCORE`** keeps its old silence behaviour by fallback. It has no live connector, so
  nothing exercises that path.
