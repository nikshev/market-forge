# Quickstart: proving the markets route

## Prerequisites

- `make install`; for the stack section, the dev stack up with at least one
  market in `GET /api/v1/markets`.
- `cd apps/web && npm ci` (the web gates are CI-only by ADR-021; run locally).

## 1. The suite

```sh
cd apps/web && npx vitest run     # the helpers, the view, the routing
make test-fast                    # nothing backend changed; confirms it
```

The tests that matter most, by what they would catch:

| test | catches |
|---|---|
| a fixture whose alphabetical and API orders differ | a client-side sort |
| a row with `rank_score: null` | a null rendered as `0.00` |
| the `href` byte for byte against a hand-written deep link | a destination that only "contains" the timeframe |
| `tf` changed, then the row's `href` re-read | a control that changes the screen and not the link |
| markets read 500 → alert, zero rows; markets `[]` → status, no alert | an empty list drawn as a failure, or the reverse |
| pathname `/` and `/markets` | the root serving the placeholder |
| pathname `/nonsense` | the fallback being replaced by a silent redirect |

## 2. Against the running stack

The stack serves the bundle (nginx `try_files` reaches `index.html` for any
path — `apps/web/nginx.conf:15-16`), and the API read already exists:

```sh
curl -s localhost:8000/api/v1/markets
curl -s localhost:8000/api/v1/timeframes
```

Rebuild the web image and open:

- `http://localhost:8080/` — the markets list, not the placeholder;
- `http://localhost:8080/markets` — the same view;
- `http://localhost:8080/nonsense` — the placeholder naming where a chart
  opens.

On a deployment whose `markets` table is empty, the view must read **"no
markets"**, not an error. On one whose API is down, an error, not "no
markets".

Choose `1h`, then activate a market: the address must be
`/chart/<venue>/<symbol>?tf=1h` — pasteable into a fresh tab, where
[[REQ-WP-074]]'s chart opens at the same timeframe.

## 3. What is still out of reach

- Filters (§28.1's `venue`, `market_type`, `quote`, `active`, `min_volume`) are
  not surfaced; a later requirement owns them.
- A price or change column would need a read that does not exist at list scale;
  the spec refuses to invent one.
