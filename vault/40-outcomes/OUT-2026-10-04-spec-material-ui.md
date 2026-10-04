---
id: OUT-2026-10-04-spec-material-ui
step: spec
records: [REQ-WP-083]
commit: null
---

## What was done

Specified [[REQ-WP-083]] after reading every component to restyle and the roles the 297 web tests query.

## What was decided

- **The accessible contract is the thing to preserve**, written down from the components and tests: a restyle that
  renamed a button would pass for a redesign and fail for a screen-reader user.
- **A theme is a pure function** of the scheme and Telegram's parameters; outside Telegram the scheme follows the
  browser.
- **spot and perp get different colours**, because the market type was exactly what this deployment first got
  wrong ([[REQ-WP-081]]).
- **Looking is an acceptance item.** Eight screenshots from the running build. The previous change drew a correct
  channel and a screenshot still showed the default view was wrong; tests did not say so.

## What is still open

- Dark-mode colours for the chart canvas (plan decides how they come from the theme).
