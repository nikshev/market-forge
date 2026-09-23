---
id: OUT-2026-09-23-implement-markets-route
step: implement
records: [REQ-WP-075]
commit: null
---

## What was done

`/markets` and `/` now render the overview §27.1 names, and a row opens the
chart at the chosen timeframe. [[REQ-WP-075]] reaches `implemented`.

- `apps/web/src/markets.ts` (new) — `marketHref`, `scoreLabel`.
- `apps/web/src/Markets.tsx` (new) — the view: two independent reads, the four
  states of `data-model.md`, rows as links.
- `apps/web/src/types.ts` — `MarketOut`.
- `apps/web/src/api.ts` — `fetchMarkets`.
- `apps/web/src/App.tsx` — a mount-stable pathname and the branch order.
- `docs/deployment.md` — the routes a deployment serves.
- Tests: `markets.test.ts`, `Markets.test.tsx`, `routing.test.tsx`, plus the
  `fetchMarkets` case in `api.test.ts`; 222 web tests pass.

`make lint`, `make typecheck`, `npx tsc --noEmit`, `npx vitest run` and
`npx vite build` all pass. No backend change: §28.1's read was already there.

**Two integration tests were added to `tests/integration/test_dev_stack.py`**
(`@pytest.mark.trace("REQ-WP-075")`): the first asserts `/` and `/markets`
reach the application shell on the running stack — the nginx fallback a static
server could 404 — and the second asserts §28.1's response has the field names
the bundle consumes, with null-or-number scores. They are how a Python-side
requirement link exists for a feature whose product code is TypeScript: R2
reads the pytest markers, and the repo's existing frontend requirements
([[REQ-WP-001]] in the same file, [[REQ-US-002]] in
`tests/unit/alerting/test_deep_link_overlays.py`) are linked the same way.

## RED, first, for the right reason

```text
apps/web/src/__tests__/api.test.ts:
    × the markets list > is read from its own route, rows unchanged
apps/web/src/__tests__/markets.test.ts:
    Error: Failed to resolve import "../markets"
apps/web/src/__tests__/Markets.test.tsx:
    Error: Failed to resolve import "../Markets"
apps/web/src/__tests__/routing.test.tsx:
    × serves the markets view at the root
    × serves the markets view at /markets
    (the placeholder and chart cases passed throughout, as designed)
```

Two tests were corrected during the RED phase rather than after: the listitem
queries needed the link to carry the accessible name, and the score assertions
had to match a longer text node (`toHaveTextContent("rank unscored")`). Both
corrections are fixture/test defects, not implementation convenience — the
component did not change to make a test pass.

## Measured on the running stack, 2026-09-23

All four paths serve the rebuilt bundle, so the nginx fallback the plan
verified at `nginx.conf:15-16` is real:

```text
GET /                      200, bundle index-Ch9okvog.js
GET /markets               200, same bundle
GET /nonsense              200, same bundle  (the placeholder renders client-side)
GET /chart/binance/BTCUSDT 200, same bundle
```

`GET /api/v1/markets` on this deployment returns:

```json
{"markets":[]}
```

**So the deployed view shows its empty state — "No markets are configured on
this deployment." — not an error and not rows.** That is the honest measurement
of this stack: the markets table is empty because no scoring run has populated
it. The populated path is proven by `Markets.test.tsx` against a stubbed wire,
not by this deployment, and the difference is recorded rather than papered
over.

## What was decided, beyond the plan

Nothing. The plan's decisions survived contact: no aggregate, no re-sort, no
backend change, no routing dependency, rows as `<a>` elements, and the
offered-set failure not taking the rows down. The two RED-phase test
corrections above are the only deviations.

## What is still open

- **No browser was driven.** As in [[REQ-WP-074]], the interactive claims are
  covered by vitest; `quickstart.md` section 2's rows/href checks remain for
  whoever has a browser. The route serving and the API state were measured.
- **The deployment has no markets**, so the populated view has not been seen on
  real data. Populating `markets` belongs to the scoring pipeline
  ([[REQ-US-001]]); this view will render it when it arrives.
- **`/signals` and `/research/backtests/:runId`** remain placeholders.
