# Phase 0 Research: The multi-venue ingest stays connected, files its archive where readers look, and keeps its log bounded

Every decision below answers a question the spec left open or a choice the code
forces. Each carries what was rejected, because in this repository the rejected
option is usually the one that was already tried.

## 1. How the session learns that a reader has ended

**Decision**: `VenueConnector` gains a read-only `alive` property. `StreamSession.tick`
polls it.

**Rationale**: `tick` runs every 200 ms and is already where reconnect decisions are
made; a poll costs one attribute read. The reader logs *why* it ended at the moment it
does, where the exception is in hand; `alive` carries only the fact. Splitting them
means neither has to be perfect: a reader that ends without a log line is still noticed,
and one that logs but is somehow still reported alive is still visible in the log.

**Alternatives rejected**:

- *A callback `on_end(reason)`.* It would run on the reader's thread into session state
  that is not thread-safe, and the reason it adds is already logged.
- *Joining the reader thread with a timeout from `tick`.* It blocks the ingest loop for
  the timeout every pass.
- *Inferring death from silence alone.* That is what exists, and it is slow by design:
  silence must outlast a quiet market. A dead reader is knowable the instant it ends.

## 2. What counts as silence, and its default

**Decision**: `VenuePolicy.max_silence_ns`, **60 s** on Binance, Bybit and OKX,
overridable with `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS`. A policy without one falls back
to `idle_timeout_ns` when the venue does not announce close (the old behaviour, which
HyperCore keeps), otherwise there is no silence reconnect.

**Rationale**: the field `_check_silence` borrowed means different things per venue.
For Bybit and OKX `idle_timeout_ns` is how long the *venue* tolerates a silent *client*
(~60 s and ~31 s). For Binance the repository's second registry set it to 24 hours,
which is the stream's *lifetime* — so the daemon's threshold became 48 hours.

The default is measured. From the raw archive:

| series | window | frames/min | longest gap |
|---|---|---|---|
| Bybit BTCUSDT | last 360 complete minutes | min 43, median 352 | 22.2 s |
| Binance SOLUSDT | 309 sampled minutes | min 30, median 135 | 11.2 s (intra-minute) |

60 s is 2.7× and 5.4× those. A **64.1 s** gap in the Bybit series was found and
**excluded**: it begins at 10:54:50 and the container started at 10:55:50 — a restart
made that morning, not the market. Deriving a limit from our own outage would have
produced a number that looked measured.

**Alternatives rejected**:

- *Keep doubling `idle_timeout_ns`.* It is the defect.
- *A multiplier setting* (the `CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER` of the
  previous change). A multiple of a quantity that means something else per venue is
  still that quantity. It is removed, with its tests, and replaced by a number of
  seconds, which is what an operator reasons in.
- *A per-symbol limit.* A thinner symbol may need more than 60 s; the override is
  per process and each process is one symbol, so it is already per symbol.

**A limit, stated**: silence counts *any* inbound frame, and on Bybit and OKX a pong is
one. A subscription the venue rejected while pongs keep arriving is not silent; the
rejection log (§9) is what catches it.

## 3. What retrying does under sustained refusal

**Decision**: capped exponential backoff inside the session. The *n*th consecutive
failed attempt waits `min_connect_interval × 2ⁿ`, capped by
`max_connect_backoff_ns` (60 s default). The log follows the count: WARNING on
attempts 1, 2, 4, 8…, INFO on recovery with the attempts it took.

**Rationale**: a venue that refuses every connection at one a second is being asked
the same question 86,400 times a day, and §35.6 names rate limits as something connector
tests cover. The logging bound follows from the schedule — log lines grow with the
logarithm of the failures, not their number.

`_reconnect` also **catches a failed `connect()`**. Binance's raises `NotConnected` when
the socket does not open; raised from inside `tick` it leaves the ingest loop and ends
the process. At *start-up* that is right (loud, and compose restarts it); during a
*reconnect* it turns one refused attempt into a dead daemon.

**Alternatives rejected**:

- *Fixed interval.* Satisfies the letter of FR-008 and none of its reason.
- *Unbounded backoff.* A venue that recovers after an hour would be retried at the end
  of an interval nobody chose. The cap bounds how late a recovery can be noticed.
- *Jitter.* Worth having with many clients behind one address. Here there are five
  processes, and a sixth knob would be a number nobody could justify.

## 4. Where a venue's policy lives

**Decision**: `connectors/session.py` is the single home. `connectors/venue.py` imports
`BINANCE`, `BYBIT`, `OKX` from it; `BINANCE_POLICY`, `BYBIT_POLICY` and `OKX_POLICY` are
deleted. A test imports every module of `channelflow.connectors`, collects every
`VenuePolicy` instance by `.venue`, and fails if one venue has two that differ.

**Rationale**: `session.py` is where the numbers were measured and the measurements are
written down; it is also where Binance's 24-hour lifetime was originally right. The
registry's job is wiring.

The values kept are `session.py`'s, not `venue.py`'s, and they differ in three places for
two venues. Bybit's idle timeout is 60.0 s against 60.7 s: `session.py` comments
that the venue closed an idle connection at 60.7 s and sets 60 s, the observation
rounded down. OKX's is 30.0 s against 30.9 s: the venue's own message on closing is
"No data received in 30s", and 30 s is that. **OKX's ping interval differs too: 15 s in
`session.py`, 20 s in `venue.py`.** `session.py` records that fifteen seconds was
measured to survive a hundred; twenty was not measured against a 30 s limit. The tests
pinning `venue.py`'s values are updated, and the one pinning Binance's 24-hour **idle
timeout** is replaced by a test of the 24-hour **lifetime**.

**Alternatives rejected**:

- *`venue.py` as the home.* It would move measured values into the file whose job is
  wiring and leave `session.py` holding a second set for `HYPERCORE`.
- *Deleting the duplicates without a guard.* Two definitions appeared because nothing
  stopped the second; a deletion without the test is a request for a third.

## 5. The archive key

**Decision**: `raw/cex/<venue>/<symbol>/<YYYY>/<MM>/<DD>/<HHMM>.jsonl.gz`. `FrameArchive`
takes `symbol`. A symbol that is empty or contains `/` is refused at construction.

**Rationale**: three processes on one venue shared a key and the last flush won;
measured by reading the frames in sampled objects, each held one symbol. A directory
keeps `raw/cex/<venue>/` a valid listing prefix and makes everything-for-one-symbol a
prefix, not a scan. The symbol is the configured spelling: Binance and Bybit `BTCUSDT`,
OKX `BTC-USDT-SWAP`, so no normalisation can merge two instruments or split one.

**Alternatives rejected**:

- *The symbol in the filename* (`HHMM.BTCUSDT.jsonl.gz`). Reading one symbol's day would
  list all of them and filter.
- *One process for all symbols of a venue.* Contradicts [[REQ-WP-066]]'s reason — one
  stalled symbol must not stop the others silently — and the refusal `ingest_main` makes.
- *A symbol directory ahead of the venue.* It would break the one existing reader's
  `raw/cex/<venue>/` prefix for no benefit.

## 6. How existing objects are moved

**Decision**: `src/channelflow/pipeline/archive_rekey.py`, **dry-run unless `--apply`**. For each object under
either old layout it reads the frames, attributes the object to the symbol **its own
frames name**, and moves it only if exactly one symbol appears: `copy_object`, then
`head_object` on both and a comparison of size and ETag, and only then `delete_object`.

Refused, with the reason printed and the object left where it is: several symbols; none
attributable; a destination that already holds different bytes; a key that matches
neither old layout.

**Rationale**: the old keys cannot say which symbol an object holds, but the objects
can. Server-side copy avoids a download-and-upload of 487 MB and preserves the ETag for
single-part objects, which is what makes the verification a comparison and not a hope.
Delete-last means the worst interrupted state is a duplicate; a second run finds the
destination equal and finishes the removal.

A frame that carries no symbol — a Bybit pong, a subscribe acknowledgement, an OKX
`event` — is ignored for attribution. An object of only such frames is refused, not
guessed at.

**Alternatives rejected**:

- *Rename by key parsing.* The old key has no symbol to parse.
- *Download, rewrite, upload.* Moves the bytes twice and gives up the ETag check.
- *Deleting the misplaced prefix outright.* It holds 8,960 Bybit objects that are the
  only copy of that venue's raw frames.
- *`moto` for the tests.* Not installed, and adding it for one tool is a dependency for
  a dictionary. A hand-written `FakeS3` is the repository's habit (`ReplayTransport`,
  `FakeClock`).

## 7. Logging

**Decision**: per-trade, per-frame and per-step lines move to DEBUG at the source;
`logging.basicConfig` moves from import time into `main()`, level from
`CHANNELFLOW_LOG_LEVEL` (default INFO). Events — connect, close, reconnect, recovery,
rejection — stay at INFO or above.

**Rationale**: the volume is code, not configuration: five services log 300 to 3,216 lines
a minute because every trade writes two or three. Raising the level in compose would
hide them and the one line that matters with them. And `basicConfig` at import is
a side effect every test importing `ingest_main` inherits.

`FrameArchive.flush` logs only when it writes: today it logs on **every** step with an
empty buffer, which is the 5 Hz line in Bybit's log.

**Alternatives rejected**:

- *`LOG_LEVEL=WARNING` in compose.* Treats the symptom, loses connect/recover events.
- *A rate-limiting log filter.* Machinery for output that should not exist.

## 8. Log caps in compose

**Decision**: a shared `x-logging` block, `max-size: ${CHANNELFLOW_LOG_MAX_SIZE:-20m}`,
`max-file: ${CHANNELFLOW_LOG_MAX_FILE:-3}`, on every service. A test reads the file as
YAML.

**Rationale**: 60 MB per service holds days at the expected post-fix rate and rotates
every 35 minutes at the measured pre-fix rate of the noisiest (830 MB a day), which is
what a cap is for. Configuration, because the host is shared and the right number is the
operator's.

**Alternatives rejected**: *a cap on the ingest services only* — the other eleven
services were uncapped for the same reason, and the next noisy one would repeat the
fault with no cap to meet it.

## 9. Reading a venue's refusal

**Decision**: a pure `rejection(venue, frame) -> str | None` in `venue.py`, called by each
connector's reader for every frame. A non-`None` result is logged at WARNING with the
venue and the frame text. **The frame is still queued**, so the archive keeps it.

Pinned against frames **captured live on 2026-10-02**: OKX's
`{"event":"error","msg":"Subscribe failed, …"}` and Bybit's
`{"success":false,"ret_msg":"error:handler not found,topic:…","op":"subscribe"}`.

**Rationale**: item 7 of the spec — a rejected subscription is invisible — is one fault at
the OKX connector and another in the daemon. A pure function over a frame is testable
with the real frame and needs no socket.

**Binance gets no rule.** The repository records, from measurement
(`ingest.py`, `streams_for`), that an upper-case stream name "connects and delivers
nothing" — one malformed name, and no rejection frame was seen. Writing a rule from a
description of an error format that was never observed would be the invented-frame
mistake in a new place; Binance's failure mode is treated as silence.

## 10. What is not decided here

- **Bucket versioning.** Would have preserved overwritten frames. With the symbol in the
  key an overwrite needs one process to restart inside a minute it had already written —
  a smaller exposure than the one repaired — and versioning costs storage and brings its
  own retention rule. Recorded as open in the outcome note.
- **Metrics for reconnects and stale feeds.** Out of scope, as the spec says.
- **A process restart within a minute** still replaces that minute's object with its
  tail, because what was already written lives in memory. Not fixed; stated.
