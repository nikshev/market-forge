---
id: OUT-2026-09-14-implement-read-cost
step: implement
records: [REQ-WP-068]
commit: null
---

## What was done

A shared bounded read pool, a flush policy counted in bars, `compact()`, and a
maintenance tool. 5 of 5 mutants caught. **Phase 8 closes.**

Measured on the deployment [[REQ-WP-067]] failed against:

    read of the bars table    6478ms  ->    45ms
    chart load, 1 client       4431ms ->    78ms
    chart load, 16 clients    20207ms ->   944ms   target met, 2.1x headroom

## Three causes, and I had named only one

Yesterday I wrote the cause down as small files and blamed [[REQ-WP-066]]'s
flush policy. That was one of three, and not the largest.

Breaking the read path into stages showed `scan().to_arrow()` at 1411ms against
`IcebergTable.read()` at 6478ms — five seconds in **our own** code.
`_in_commit_order` opened and parsed each data file one after another, because
that is what a list comprehension does. Nothing justified it: sorting the paths
and concatenating in that order is what preserves commit order, and the waiting
can be concurrent. Measured: 4394ms serial, 654ms at sixteen workers, results
byte-identical.

## Measuring the fix found the next mistake

The first pool was bounded **per read**. One client got faster and sixteen got
slower — 20.2s to 29.1s — because sixteen requests each opening sixteen files is
256 connections to one object store. That is congestion, not concurrency, and
reasoning had not caught it; the load test reported it on the next run.

The pool is now one per process.

## Neither fix helped the table that was already broken

685 files remained 685 files. pyiceberg 0.12's maintenance surface is
`expire_snapshots` alone, so the plane needed a compaction of its own: read the
live rows in commit order, write them back as one commit.

That is the change that mattered. Read time fell from 6478ms to 45ms — which is
the 42ms [[REQ-WP-057]] measured originally, so the entire deficit was file
count all along.

**Order is what makes it safe rather than merely faster.** `read` guarantees
commit order and every "latest row wins" reader depends on it, so a compaction
that reordered would change answers, not timings. The test asserts equality with
the rows from before, and the live table's 721 rows compared equal.

## The sweep found a guard that could not fire

`compact` refused an empty table before overwriting. With `before > 1` there are
at least two data files and Iceberg does not write one with no rows, so the
branch was unreachable. It is gone, and the mutation that revealed it went with
it rather than being recorded as an explained survivor.

## What a flush interval cannot express

The old `FLUSH_INTERVAL_NS` was sixty seconds beside a sixty-second bar. An
interval cannot keep `BarSink`'s rule, because whether it does depends on a bar
size the flush knows nothing about. A count can, and the ceiling in time is what
keeps a quiet symbol committing — each alone fails on the market the other
suits.

The count reads the sink's own buffer rather than keeping a second tally: it is
the number of rows a commit would actually write, and a second counter would be
a second answer to one question.

## What is left

Compaction runs when an operator runs it. `make compact` exists and the
deployment document says what it is for; nothing schedules it, and a deployment
that never runs it drifts back — more slowly, at one file per fifteen bars
instead of one per bar.
