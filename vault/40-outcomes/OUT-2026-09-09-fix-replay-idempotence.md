---
id: OUT-2026-09-09-fix-replay-idempotence
step: implement
records: [REQ-PIPE-001]
commit: null
---

## What was done

A defect found in [[REQ-PIPE-001]] after it reached `implemented` with a green
CI run (34376050957): a second run over the same input wrote the rows again, on
an append-only plane that rejects nothing.

    first wrote 2 | second wrote 2 | table holds 4

Both entry points now read a per-series watermark and write only past it, and
count what they skipped. `_recording` names the tables a run is answerable for
rather than the tables that hold something. Eight new tests, all of which start
from a store that has already been written to. [[ADR-056]] carries the rule and
the reasoning.

## What was decided

- **The requirement's Scope was wrong, and is amended rather than worked
  around.** It listed resumability as out of scope on the grounds that "one
  replay is one batch per table" — true within a run, false across runs, and the
  sentence did not make the distinction. Resumability is in, and the note says
  which way it moved and why.
- **A fully-skipped run still names its dataset.** The alternative — a re-run
  that names nothing — would make it impossible to recover a lost citation by
  re-running, which is the main thing idempotence buys.
- **Skips are counted, not silent.** A number that stays at zero is a run that
  added something.

## What the mutation sweep found

23 mutants over `pipeline/replay.py` and the runner's observers; 21 caught.

- **W14 (a table nobody wrote to is named anyway) survived, and was a real gap
  in the test, not in the code.** The test reached for the bars table, which
  `record_replay` never puts in `accounted` at all, so it never exercised the
  guard. Rewritten to replay BTCUSDT and then record for ETHUSDT on the same
  store — the case where a table is full and this run is answerable for none of
  it. Caught after the rewrite.
- **S5 (a table with no snapshot is referenced anyway) survived and is
  non-behavioural.** With the row-count guard in front of it, `rows > 0` implies
  the run either appended to that table or skipped rows it already held, and
  both leave a snapshot; a candidate always carries at least one transition
  (`signals/machine.py:129`), so the transitions table cannot be the exception.
  The arm is unreachable from both callers. It stays as the thing that keeps a
  future third caller from getting a fabricated `(snapshot_id, hash)` pair, and
  the docstring now says a mutation of it survives and should.

## What is still open

- **A watermark is a full table scan per run.** Honest at these row counts,
  not at production ones. The plane's snapshots carry per-file bounds; a
  watermark should read those instead of the rows.
- **Nothing enforces [[ADR-056]] on the next entry point.** It is a rule in a
  note, not a rule a validator checks. The live sink is the first one that will
  inherit it, and it does not exist yet.
- **The repository's single-item writers are exempt, and the exemption is a
  judgement.** They append literally, exactly as the in-memory repository does,
  which is what keeps the two answering alike under the conformance suite; a
  caller looping over them can still double a series. ADR-056 puts idempotence
  on the entry point doing the looping. If a caller ever loops over them
  *without* being such an entry point, that reasoning fails and nothing will
  say so.
- **Feature and score tables are still empty**, unchanged from [[REQ-PIPE-001]]'s
  own open questions.
