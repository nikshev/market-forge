---
id: OUT-2026-10-08-tasks-signal-notary-contract
step: tasks
records: [REQ-INFRA-006]
commit: null
---

## What was done

Broke [[REQ-INFRA-006]] into 24 tasks in `specs/142-signal-notary-contract/tasks.md`, in five phases: setup,
the contract and its offline suite, the tooling for a checkable deployment, the deploy itself (the one
outward-facing step), and close-out. Tests come before the code they exercise; the stub-contract task (T005)
exists so the RED run fails by assertion rather than by compile error. Then ran the analysis across `spec.md`,
`plan.md` and `tasks.md`.

## What was decided

The analysis found no constitution conflict and every FR and SC mapped to at least one task. It did find
seven things that would have bitten during implementation, all fixed in the artifacts rather than carried:

1. **Ordering contradiction (HIGH).** The deploy refuses a dirty `contracts/` tree and so needs the contract
   committed first, but the only commit task was the last one. Added T017: commit Phases 2–3 (`status:
   tested`) before any deployment. The deployment record then lands in the final commit.
2. **FR-007 required an `owner()` getter that no test exercised.** Added
   `test_owner_is_the_constructor_argument`; the suite is thirteen tests, not twelve, and the ABI document and
   the driver's expected-name list say so.
3. **The constructor's owner had no configuration.** FR-006 says the owner is configuration (Principle X),
   but the deploy tool had no variable for it. Added `MONAD_NOTARY_OWNER`, defaulting to the signer, to T013
   and the `.env.example` task.
4. **Key mechanism stated two ways.** `plan.md` allowed a signer environment variable while `research.md`
   chose a keystore. Plan decision 8 now says keystore, matching the research; the keystore password sits in a
   mode-600 file outside the repository, referenced by path.
5. **SC-001 says "with no network" but nothing ran offline.** T007 now ends with a `forge test --offline`
   run after `solc` is cached.
6. **SC-002 counted wrongly.** It said "six reverts" and listed five plus the zero hash. Reworded in the spec
   to name them.
7. **Plan decision 8 was muddled** by an "`ETH_PRIVATE_KEY`-style" remark (see 4); removed.

Two things were looked at and left as they are: T003 (baseline) and T017/T024 (commits) map to no FR, which
is correct for process tasks; and the spec does not name `deployments/monad-testnet.json`, which the plan and
data model add as the machine-readable form of the "Deployment record" key entity the spec already has.

## What is still open

- T002 may find that Foundry 1.7.1's keystore flow differs from what the plan assumes; then research R5 and
  plan decision 8 are amended and the tests assert on the real argv.
- Whether `tests/contracts/` and `tests/tools/notary/` need `__init__.py` to match their neighbours is for
  T006/T009 to settle against `tests/tools/` (which has one) and `tests/tools/trace/` (which does not).
- The deploy (T019) is explicitly outward-facing; it is reached only through a clean, committed tree and a
  reviewed dry-run.
