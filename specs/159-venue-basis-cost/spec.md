---
traces: [REQ-WP-107]
status: draft
---

# Feature Specification: Venue basis cost

**Input**: [[REQ-WP-107]] -- measured 2026-10-13: repository 0.75 s, HTTP 3.8 s; the difference was `select_venue_basis` scanning every quote for every bar.

## Scenarios

1. **Given** a day of bars and days of quotes, **Then** the basis is found in under a second, with the same answer.
