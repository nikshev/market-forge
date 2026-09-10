---
id: OUT-2026-09-10-requirement-long-short
step: requirement
records: [REQ-WP-031]
commit: null
---

## What was done

[[REQ-WP-031]] extracted from PRD §45's Phase 3 and §16's derivatives feature
list. It is the last entry in [[REQ-PHASE-3]]'s `not_delivered`.

## What was decided

- **"Squeeze context" is not the ratio.** A crowded book is a condition, and a
  number without a sense of how unusual it is says nothing about crowding. The
  reading is relative to the instrument's own recent positioning: 2.0 is
  ordinary on one instrument and extreme on another.
- **"Where available" is half the requirement.** A venue that does not publish
  positioning is not a balanced market, and a ratio of 1.0 is a real reading that
  means the opposite of an unknown one.
- **"Optional" describes the venue, not the rigour.** A field that is sometimes
  absent is exactly where an absent value silently becoming neutral does the most
  damage, because nothing downstream will ever see a gap.
- **The z-score is the shared one.** [[ADR-026]] settled the refusal for funding
  and open interest, and positioning gets the same treatment through the same
  function rather than a second one that could drift on what "too few
  observations" means.
- **Staleness applies.** Positioning is REST-polled like funding, so
  [[REQ-WP-026]]'s rule is the same rule, not a similar one.

## What is still open

- **Which venue field maps to which ratio** is a connector question this note
  does not settle. Binance publishes a global account ratio and a top-trader
  position ratio, and they measure different populations; carrying both keeps
  that distinction rather than averaging it away.
