---
id: OUT-2026-10-04-plan-material-ui
step: plan
records: [REQ-WP-083]
commit: null
---

## What was done

Planned the restyle after sizing the components (about 1,150 lines, no stylesheet), confirming Material UI 9.4.0
installs with React 18, and confirming a browser is available to look at the result.

## What was decided

- One theme function; no per-component colours.
- **The existing tests are the contract and are not rewritten to fit.** An edit is allowed only for markup with
  no accessible meaning and is listed.
- **A card is a link by `aria-label`**, so the link's name stays exactly the symbol while the card shows more.
- The chart takes the theme's palette rather than a second hard-coded dark one.

## What is still open

- Whether the toggle groups need `exclusive` semantics in a way that changes `aria-pressed`; the tests will say.
