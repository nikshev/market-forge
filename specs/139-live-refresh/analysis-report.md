## Specification Analysis Report: REQ-WP-090 (139-live-refresh)

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Duplication | LOW | tasks.md:T010, T021 | T021 notes "already covered in T010" — the implementation task is listed again under US3 | Remove T021 (it's a verification note, not a separate task) |
| B1 | Ambiguity | MEDIUM | spec.md:FR-007, tasks.md:T015 | "visible range" preservation: the spec says "visible range the reader set" but the implementation relies on `isInitialLoad` prop alone — does not explicitly address whether the chart's internal range state (pan/zoom) is captured and restored, or simply never reset | Add explicit note in spec: the range is preserved by never calling `fitContent`/`setVisibleLogicalRange` on refresh; the library retains the reader's pan/zoom |
| C1 | Underspecification | MEDIUM | spec.md:FR-005, tasks.md:T010 | In-flight skip: "a refresh does not start while the previous one is in flight" — the boolean `isLoading` covers the initial load and refresh, but what about a timeframe/mode change that supersedes via `loadId` while a refresh is in flight? The `loadId` guard discards the refresh answer, but the refresh load was already started | Add clarification: a timeframe/mode change supersedes via `loadId` (existing behavior); the refresh tick that started before the change will run but its answers will be discarded — acceptable |
| C2 | Underspecification | MEDIUM | tasks.md:T005, T006 | `isInitialLoad` prop: how does `App.tsx` know whether the `load()` call was triggered by mount/timeframe/mode vs timer? The spec says "only the initial load (and timeframe/mode change) may set the range" but the task doesn't specify the signaling mechanism | Add in T005/T010: `App.tsx` passes `isInitialLoad` based on trigger — mount + deps change = true; timer = false |
| D1 | Constitution | CRITICAL | spec.md:Principle I, tasks.md:T010 | No look-ahead: the timer callback calls `load()` which fetches bars with `limit: 500` — must ensure the API's `at_ns`/`as_of_ns` semantics are preserved on refresh (they are: same `load()` function, same `link.atNs` for pinned, same `mode` for extrema) | Verify in T010: refresh uses same `link.atNs` (pinned) or no `at_ns` (live latest); extrema `asOfNs` from `mode` — already correct |
| D2 | Constitution | HIGH | spec.md:Principle X, tasks.md:T002 | Thresholds configurable: `VITE_CHART_REFRESH_MS` is a build-time Vite env (not runtime). The requirement says "configuration value" and the acceptance says "the interval is a configuration value (Principle X)" — build-time is acceptable per repo precedent (`VITE_API_BASE`) | No change; document in spec that it's build-time via Vite |
| E1 | Coverage Gap | MEDIUM | spec.md:SC-001, tasks.md | SC-001 requires "on the running stack" validation but T024/T025 only cover screenshots; no automated integration test against running stack | Add integration test task (or note that running stack test is manual per quickstart) |
| E2 | Coverage Gap | LOW | spec.md:FR-008 | "The refresh MUST NOT alter history: channel snapshots and confirmed extrema already drawn are never rewritten" — covered by T011 (state unchanged) but no explicit test that a past channel/extremum is byte-identical after refresh | Add assertion in T019 or new test: compare pre-refresh and post-refresh channel/extrema for bars before the new one |
| F1 | Inconsistency | MEDIUM | spec.md:US1 "volume profile re-read", tasks.md | US1 acceptance says "the profile is re-read for the same window" but tasks don't explicitly mention `fetchVolumeProfile` in the refresh load — it's implied by "same load" but should be explicit | In T010: confirm `load()` includes `fetchVolumeProfile` when `wantsProfile` (existing logic) |
| F2 | Inconsistency | LOW | plan.md:R4 "compare data identity" vs tasks.md:T005 `isInitialLoad` prop | Plan considered comparing data identity as alternative; tasks use explicit prop — acceptable but plan should note the decision | Update plan.md R4 to reflect chosen approach |

### Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | ✅ | T010 | Refresh re-runs load |
| FR-002 | ✅ | T002 | Interval config via VITE env |
| FR-003 | ✅ | T010, T017 | Pinned chart check |
| FR-004 | ✅ | T004, T018 | Visibility listener |
| FR-005 | ✅ | T010, T020 | In-flight skip via `isLoading` |
| FR-006 | ✅ | T011, T019 | Failure handling via `LoadState` |
| FR-007 | ✅ | T015, T016 | Reader state preserved |
| FR-008 | ✅ | T011, T012 | History immutable (no rewrite) |
| FR-009 | N/A | — | Stage 2 explicitly out |
| SC-001 | ✅ | T007, T024 | New bar in interval + live stack |
| SC-002 | ✅ | T014 | Five states unchanged |
| SC-003 | ✅ | T017, T018, T020 | Zero/one requests |
| SC-004 | ✅ | T011, T012, T019 | Failure then recovery |
| SC-005 | ✅ | T027 | Existing tests pass |

### Constitution Alignment Issues

- **D1 (CRITICAL)**: Principle I (no look-ahead) — verified satisfied by using same `load()` with same parameters
- **D2 (HIGH)**: Principle X (thresholds configurable) — satisfied via build-time Vite env; document in spec

### Unmapped Tasks

- T001: Baseline recording (setup, not requirement-mapped — acceptable)
- T009, T025: Trace marker verification (cross-cutting, acceptable)
- T026-T028: Polish/commit (cross-cutting, acceptable)

### Metrics

- Total Requirements (FR + SC): 14
- Total Tasks: 28
- Coverage % (requirements with ≥1 task): 100%
- Ambiguity Count: 1
- Duplication Count: 1
- Critical Issues Count: 1

## Next Actions

1. **CRITICAL (D1)** is verified satisfied — no action needed, but add a note in spec confirming API parameters on refresh
2. **MEDIUM (B1, C1, C2, E2, F1)** — minor clarifications in spec/tasks; can be addressed during implementation or in a quick spec amendment
3. **LOW (A1, D2, F2)** — cleanup; can be done anytime

**Recommendation**: Proceed to `/speckit-implement` — the tasks are complete, testable, and constitution-aligned. The MEDIUM items are clarifications that will be resolved naturally during test-first implementation (the RED tests will force the exact behavior).

## Remediation Offer

Would you like me to suggest concrete edits for the top 5 issues (B1, C1, C2, E2, F1) before implementation?