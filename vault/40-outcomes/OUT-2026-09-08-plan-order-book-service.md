---
id: OUT-2026-09-08-plan-order-book-service
step: plan
records: [REQ-WP-004]
commit: null
---

## What was done

Two modules under `src/channelflow/book/` — the moved reconstruction and a
lifecycle service around it — and four test files, one per user story.

## What was decided

- **The move is its own commit, before any new behaviour.** `git mv` plus an
  import update, with REQ-WP-003's recorded-Binance tests green on both sides
  of it. Mixing a relocation into a feature commit makes every later failure
  ambiguous.
- **State and reads share a file; the lifecycle gets its own.** A read is a
  question about state — putting ADR-011's mid-price rule in one file and the
  prices it reads in another would separate a rule from what it applies to.
  Buffering and rebuild policy are a different responsibility.
- **Bootstrap fails loudly rather than producing a book with a hole.** If the
  first delta surviving the snapshot does not begin at `update_id + 1`, the
  buffer and the snapshot do not belong together. Filling the gap silently is
  the exact failure PRD §8.1 names.
- **Rebuild keeps the cumulative gap count** (SC-003). A book that forgot its
  gaps on every rebuild would report perfect health while flapping.

## What was rejected

- **A compatibility shim at the old import path.** It would put two paths to
  one module into the trace graph, and the only caller is a test we control.
- **A separate exception for "no mid price".** Callers already handle "the book
  cannot answer"; a second type would split one concern across two handlers.

## What is still open

- `top(n)` sorts each side per call. Fine at book sizes we have; a sorted
  structure is the optimisation to make when a profile asks for it, per
  PRD §0.14.
