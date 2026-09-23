---
id: OUT-2026-09-23-plan-markets-route
step: plan
records: [REQ-WP-075]
commit: null
---

## What was done

[[REQ-WP-075]] planned as `specs/120-markets-route/`: `plan.md`, `research.md`,
`data-model.md`, `contracts/web.md`, `quickstart.md`. Constitution Check passed
before Phase 0 and after Phase 1.

## What was decided

**No backend work.** §28.1's read exists, is ranked, and is already ordered
with unscored markets last. The one deployment question — does `/markets` reach
the bundle? — was **checked rather than assumed**: `apps/web/nginx.conf:15-16`
has `try_files $uri $uri/ /index.html`.

**`App` gains a mount-stable pathname and a fixed branch order.** Markets
first, then the deep link, then the placeholder. Stability matters for the
reason [[REQ-WP-074]] recorded: an identity that changes per render re-fires
effects, and this feature would otherwise reintroduce the loop just fixed.

**The destination is one pure function, asserted byte for byte.**
`marketHref(venue, symbol, token)`; SC-003 is a bytes claim, and "contains
tf=1h" would pass for a URL with the parameter in the wrong place.

**A failed offered set does not take the rows down.** The two reads are
independent; the rows render, their links fall back to the one documented
default, and the control's failure is stated. The reverse — markets failing —
is an alert with no rows, never an empty list.

**Rows are `<a href>` elements.** Middle-click, copy, open-in-new-tab; a click
handler would need a router to be tested against what the browser actually
does.

**`scoreLabel` exists as a function.** FR-002's rule — `null` is unscored, `0`
is a score — lives in one place and is tested without rendering.

**No price, no sparkline, no change column.** The requirement's own sentence is
"the list is the state". A price column needs a read that does not exist at
list scale, and adding an aggregate would create the second source of truth the
spec refuses.

## What was rejected

- **A routing library.** Two string comparisons; ADR-021's bundle concern.
- **Reading `window.location` in render.** The exact identity instability that
  caused [[REQ-WP-074]]'s 316-requests-in-300ms loop.
- **A per-row timeframe menu.** Eight options per row for one view-level
  choice.
- **Sorting rows client-side.** The API's order is §43's rank; re-sorting
  replaces a decision made upstream with one made in the view.
- **Disabling row links when the offered set fails.** Turns a control failure
  into a data outage; a default-timeframe link is what a typed URL would
  produce.
- **Reusing `TimeframeControl`'s component state** for the chosen token: the
  control already is stateless by design; the view owns the choice.

## What is still open

- **Filters.** §28.1 supports five; the spec names their absence.
- **A price/change column** and therefore any "market overview" richer than a
  ranked list, waits on a read nobody has specified.
- **`/signals` and `/research/backtests/:runId`** remain placeholders; §27.1
  lists five routes and this plan builds the second.
