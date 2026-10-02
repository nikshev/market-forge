---
id: OUT-2026-10-02-spec-ingest-resilience
step: spec
records: [REQ-WP-078]
commit: null
---

## What was done

Specified [[REQ-WP-078]] as `specs/123-ingest-resilience/spec.md`: five user
stories, seventeen functional requirements, six success criteria. It is a repair
of [[REQ-WP-076]], found by looking at the running deployment six days after that
requirement reached `implemented`.

## What was decided

**One requirement, because the seven defects have one cause.** They could have
been seven notes. They were kept together because each had a passing test beside
it, and the reason is the same each time: the tests exercise a piece and the fault
is in a join. The archive-prefix test builds `FrameArchive` with its default
prefix and cannot see what `build_daemon` hands it; the reconnect tests drive a
`StreamSession` with a fake connector and cannot see that the real readers end
without telling it. Splitting them would have produced seven specifications that
each re-explained one half of that, and a reader would have taken away "seven
bugs" when the finding is "a way of testing". The spec says it in its own words
and then holds every acceptance scenario to it: **a scenario that could pass
against the broken wiring is not a scenario.**

**The symbol goes in the archive key, as a directory after the venue.**
`raw/cex/<venue>/<symbol>/<YYYY>/<MM>/<DD>/<HHMM>.jsonl.gz`. Three Binance
processes were writing one key and the last flush won; sampled minutes each held
exactly one of ETH, BTC, SOL. A directory keeps `raw/cex/<venue>/` valid as a
listing prefix for the one reader that exists (`parity_capture.py`, which must
then select by symbol — written into the spec as part of this work) and makes
"everything for one symbol" a prefix, not a scan. The alternative, the symbol in
the filename, was rejected for that second reason. The key uses the symbol as
configured, not normalised: Binance and Bybit say `BTCUSDT`, OKX says
`BTC-USDT-SWAP`, and normalising could merge two instruments or split one.

**The overwritten frames are not recoverable, and the spec says so.** `store.put`
replaces an object and nothing versioned it. The remedy is to state the extent as
a count per symbol (FR-014, SC-006), not to imply a repair. What *is* recoverable
is the layout: each existing object is attributable to one symbol by the frames
in it, and migration places it by that, not by anything inferred.

**Migration is copy, verify, then remove, and refuses what it cannot attribute.**
An object with frames of more than one symbol, or none, or a stream that names no
symbol, is left where it is with the reason. The worst interrupted state is a
duplicate, never a gap, and a second run converges.

**Silence becomes its own field.** The daemon doubled `idle_timeout_ns`, which is
the venue's tolerance of a silent *client* — tens of seconds for Bybit and OKX —
and for Binance is a stream lifetime of 24 hours, giving a 48-hour threshold. The
session.py original for Binance had `stream_lifetime_ns` and no idle timeout; the
copy in `connectors/venue.py` moved the value into the wrong field and dropped the
lifetime, so the 24-hour reconnect stopped happening. Two registries now define
each venue's policy with different numbers, so a test must fail when they differ.

**Restart in mid-minute stays a known loss.** [[REQ-NRT-PARITY]] fixed the archive
replacing a minute with its tail *within* a process, by remembering what had been
written. That memory is in RAM, so a restart still overwrites. The spec says so as
an edge case rather than letting a reader infer the opposite.

**Metrics stay out.** §33 lists "reconnects" and "stale feed count". They become
log events with a stated reason, because nine of §33's eleven metrics already have
no producer ([[REQ-WP-055]]) and two more with no dashboard would repeat that.

## What is still open

- **The numbers.** The silence default per venue and the log cap per service are
  both left to `/sdd-plan`. Principle X makes the first configuration, and the spec
  requires a stated basis for each default, not a value. SC-004's 10 MB a day is a
  ceiling chosen against a measured 1.1 GB a day, and is a judgement.
- **How a connector reports that its reader has ended.** `VenueConnector` has no
  such question today; the session cannot ask. That is a protocol change touching
  all three connectors and every fake, so the plan must say whether it is a
  property, a callback or a poll.
- **What retrying does under sustained refusal.** FR-008 requires attempts to
  respect the minimum connect interval and the log not to grow without bound. It
  does not say whether the interval grows. A venue refusing every connection at one
  per second is a rate-limit conversation §35.6 names, and the right answer is not
  obvious from here.
- **Whether the archive should be versioned.** Nothing here prevents the next
  overwrite from a different cause. Bucket versioning would, at storage cost and
  with its own retention question. Named so it is decided rather than discovered.
- **The ETH and SOL daemons are overwriting each other right now**, and will until
  this lands. Bars and channels are unaffected; the raw tier loses, for each of
  the three Binance symbols, about two minutes in three of every hour that passes.
