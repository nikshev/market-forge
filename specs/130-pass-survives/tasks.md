---
description: "Tasks for REQ-INFRA-012 — a background pass that fails is reported and tried again"
---

# Tasks: A background pass that fails is reported and tried again

**Tests**: written first and run RED. Marker `@pytest.mark.trace("REQ-INFRA-012")`.

- [ ] T001 Record the **before**: the worker's and resample's restart counts and the two log excerpts (the `OSError` at 16:38 and the `NoSuchSnapshot` at 01:02); that `run_pass` is called unguarded in both mains
- [ ] T002 Write `tests/unit/pipeline/test_passes.py` (the spec's scenarios through `run_passes`, and both mains in loop and `--once` mode). Run it RED: `ModuleNotFoundError: channelflow.pipeline.passes`. Do not commit while red
- [ ] T003 Write `src/channelflow/pipeline/passes.py`; replace the loop in `channel_main.py` and `resample_main.py` with a call to it. `# @trace: REQ-INFRA-012` in each
- [ ] T004 Run the new tests and the existing worker, resample and pipeline tests: the existing ones pass **unchanged**, and a healthy loop prints what it printed
- [ ] T005 First run `tests/tools/test_mutate.py`. Then write `tests/mutations/passes.toml`: a failure not survived; the interval skipped after a failure; the traceback printed every time; the recovery not reported; `--once` surviving; `BaseException` caught; the next-pass line removed. **A survivor needs a test that kills it or a written reason**
- [ ] T006 A sentence in `docs/deployment.md` (a failed pass is reported and the loop goes on); `make lint`, `make typecheck`, `make test`
- [ ] T007 **Live (SC-003):** start a worker for the test against an object store it cannot reach (`CHANNELFLOW_S3_ENDPOINT` pointing nowhere) with a short loop interval and show that after at least four intervals it is still running and has reported each failure, where today it exits at the first. Record with the date; then remove it
- [ ] T008 Write the implement outcome note; set `implemented`; `make graph && make validate`; commit through the gate naming explicit paths

## Coverage

| requirement | task |
|---|---|
| FR-001 reported, interval, next pass | T002, T003 |
| FR-002 one traceback per run | T002, T005 |
| FR-003 recovery | T002 |
| FR-004 `--once` raises | T002 |
| FR-005 only `Exception` | T002 |
| FR-006 both jobs, healthy output unchanged | T002, T004 |
| FR-007 same interval after failure | T002 |
| SC-001 a failed pass is followed by a pass, both jobs through `main` | T002 |
| SC-002 three failures print one traceback and three lines | T002, T005 |
| SC-003 live | T007 |
| SC-004 healthy output unchanged | T004 |

## Dependencies

T001, T002 first; T003 after the RED; T004, T005, T006 after T003; T007 after T006; T008 last.
