---
id: OUT-2026-09-08-tasks-telegram-alerting
step: tasks
records: [REQ-WP-008]
commit: null
---

## What was done

14 tasks in six phases, with a coverage table mapping every FR and SC to one.

## What was decided

- **T011's five mutations are the guards whose removal leaves plausible
  behaviour**: a duplicate alert, delivery from a stale book, a swallowed dead
  letter, an escaping transport exception, and a random signal id.
- **The random-id mutation is the one that would pass review.** A random UUID
  looks *more* correct than a derived one — it is what a UUID field usually
  holds — and everything keeps working until someone replays a stream and gets
  a different audit from identical input.
- **T012 adds only names and empty values to `.env.example`.** A placeholder
  that looks like a token invites someone to paste a real one next to it.

## What is still open

- Nothing from this step.
