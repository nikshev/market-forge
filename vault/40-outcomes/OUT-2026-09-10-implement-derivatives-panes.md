---
id: OUT-2026-09-10-implement-derivatives-panes
step: implement
records: [REQ-WP-030]
commit: null
---

## What was done

Four entries in `PANES` and a cross-language check. 5 new tests, 1639 in the
Python suite and 73 in the web one, every gate clean, 6 of 6 mutants caught.

## What the sweep found

**The guard against a vacuous check was itself unevidenced.** Deleting the
"no panes were parsed" line changed no result, because no test ever handed the
parser a source it could not read. That is exactly the shape this whole
requirement is about, one level up: a check that passes while checking nothing.
The parser is now a separate function, and two tests give it a source that
declares no `PANES` and one that declares an empty list.

Worth noticing that the sweep caught the same class of defect in the test that
was written to catch it in the code.

## What is still open

- **Nothing writes derivative features into the feature table.** A pane over an
  empty table says "no feature points in this window" — honest, and it will read
  as a bug to whoever opens it first. Named in the spec rather than discovered.
- **Two of PRD §27.3's nine panes remain**, both DEX, both waiting on Phase 4's
  data for the reason [[REQ-WP-027]] gave for these four.
- **The check is a regex over source.** It survives reformatting and would not
  survive the list being built programmatically. That is a real limit, and the
  parser fails loudly rather than quietly if it happens.
