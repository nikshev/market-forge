---
traces: [REQ-WP-103]
status: draft
---

# Feature Specification: Loading indicators

**Input**: [[REQ-WP-103]] -- owner's report 2026-10-13.

## Context

1. The page had no indicator of any kind: an empty chart, pane or control was both "still loading" and "nothing there".
2. On 2026-10-13 a bars request took 54 s and the profile 82 s on the loaded host, so the question "bug or slow?" was a real one.
3. The page already states the *answers* in words (empty, failed, disconnected, no data); what was missing is the state before the answer.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - I can tell slow from broken (P1)

**Acceptance Scenarios**:

1. **Given** a request that has not answered, **Then** the part of the page made of it shows a named spinner and says nothing about the data.
2. **Given** it answers with data, nothing or a failure, **Then** the spinner is gone and the page says what the answer was.
3. **Given** a chart on screen and a reload in flight, **Then** a small mark by the title, not a spinner over the chart.

### Edge Cases

- The live feed already has bars while the history is loading: the spinner covers the chart, which is drawing underneath.
- A layer that is off asks for nothing and shows no spinner.
