---
id: OUT-2026-10-04-spec-pass-survives
step: spec
records: [REQ-INFRA-012]
commit: null
---

## What was done

Specified [[REQ-INFRA-012]] as `specs/130-pass-survives/spec.md`: three stories, seven requirements. The
two loops were read first; they are identical (`while True: run_pass(...); sleep`) and `maintenance` was
checked and already guards each table.

## What was decided

- **The next pass is the retry.** A pass is cheap against its interval and idempotent over unchanged data;
  retrying inside it would be a second loop inside the first.
- **No backoff.** A growing delay would hide how long recovery takes behind a number that grows.
- **One traceback per run of failures.** A storage outage of an hour would otherwise print a dozen; the
  repository already has the rule (a repeated condition does not repeat its report).
- **`--once` still fails.** With no next pass, surviving would turn a failure into a silent success.
- **Only `Exception`.** An interrupt or an exit must stop the process.
- **Honest scope note:** the 16:38 worker restarts were caused by load the owner's tooling (an experiment of
  mine) generated; the fix is warranted by the shape, not by that event being a production fault.

## What is still open

- Where the shared loop lives and how it is injected so a test needs no real sleep (plan).
- Whether to also emit a metric; out of scope, a failure line is the behaviour.
