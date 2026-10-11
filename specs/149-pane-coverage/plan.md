# Implementation Plan: Every lower pane the deployment can fill has data, and the rest say why

**Branch**: `149-pane-coverage` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: `specs/149-pane-coverage/spec.md`. Acceptance of specs 145-148.

## Summary

`tools/panes/` (`python -m tools.panes --api http://127.0.0.1:8000`) queries the running API and prints the three-state table; the classification is a pure function with offline tests. The run, the service listing and the image revision go in the outcome note.

## Technical Context

Python 3.12; `httpx` (a dependency). A developer tool under `tools/` like `tools/images/` and `tools/notary/`.

## Constitution Check

XIV: traces. The tool reads only; it writes nothing and changes no state.

## Project Structure

```text
tools/panes/{__init__,classify,fetch,__main__}.py
tests/tools/panes/test_classify.py       # three states, reasons from answers, NO PRODUCER exit 1, API down exit 2
tests/mutations/panes_classify.toml
```

Touched: `Makefile` (`panes-report`), `docs/deployment.md`.

## Design decisions, with what was rejected

1. **Reasons come from the system**: the venue-basis read's refusal reason; a spot market with no consensus peers; the collector heartbeat (via the features endpoint's absence plus the collector's `/metrics` age); a DEX pane reports "no DEX source" only because `PANES` names a DEX feature and no source is configured. Rejected: a dictionary of excuses in the script.
2. **Range** defaults to the last 24 h at each timeframe, adjustable.
3. **Exit codes**: 0 all cells data-or-reasoned; 1 any `NO PRODUCER`; 2 API unreachable.

## Phases

1. Classifier + tests. 2. Fetch + CLI. 3. Run against the deployed stack after specs 145-148 are live; record in the outcome note with screenshots.
