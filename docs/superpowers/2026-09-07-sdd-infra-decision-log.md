# Decision log — SDD traceability infrastructure

**Date:** 2026-09-07  
**Branch:** `sdd-infra`  
**Plan:** `docs/superpowers/plans/2026-09-07-sdd-traceability-infra.md`  
**Spec:** `docs/superpowers/specs/2026-09-07-sdd-traceability-infra-design.md`

Every decision taken during execution without the repository owner in the loop, in the
order it was made. Each says what it costs if it turns out wrong, so any of them can be
found and reversed. Parked findings — real issues deliberately not fixed — are listed at
the end.

## Rulings

**1. [Preflight]** F1 — Task 1's `.gitignore` gains a `.superpowers/` line. Without it this execution's ledger and every review package get committed. Cost if wrong: none; the directory is pure scratch and the plan already treats it as git-ignored.

**2. [Preflight]** F2 — Task 2 must explicitly confirm `.gitignore` still carries the Task 1 entries after `specify init --force`, and restore them in the same commit if the tool replaced the file. Cost if wrong: a clobbered ignore file silently commits the virtualenv.

**3. [Preflight]** F3 — `pytest_plugins = ["pytester"]` moves out of the test module into a new rootdir `conftest.py`. pytest only honours that setting in the rootdir conftest; declared in a test module it is unreliable and on some versions an error. Cost if wrong: Task 6's four plugin tests error on collection, caught immediately by its own verification step.

**4. [Preflight]** F4 — accepted as-is, not fixed: `make graph` invokes `markers` twice, costing one extra collection pass. Cost if wrong: a second of wall clock. Fixing it means restructuring the target graph for no correctness gain, which is exactly the churn YAGNI forbids.

**5. [Task 1]** the egg-info minor is fixed in Task 2 rather than parked, because Task 14 Step 9 runs `git add -A` and would otherwise commit the setuptools build artifact. Cost if wrong: one extra .gitignore line nobody needed.

**6. [Task 2]** Spec Kit 1.0.4 installs `.claude/skills/speckit-*/SKILL.md` (agent skills, `user-invocable: true`), NOT `.claude/commands/speckit.*.md` slash commands. Verified on disk: ten skill directories, no `.claude/commands/`. The plan's Task 12 command bodies reference `/speckit.specify` etc.; they must instead reference the `speckit-specify`, `speckit-plan`, `speckit-tasks`, `speckit-analyze`, `speckit-implement` SKILLS, invoked via the Skill tool. Carried into the Task 12 dispatch. Cost if wrong: the /sdd-* commands name a non-existent invocation and fail visibly on first use.

**7. [Task 2]** Important 1 (Principle XIV has no PRD §0 basis) — VERIFIED, reviewer is right. PRD §0 has exactly fourteen items and none mention requirement-ID traceability. Fix is NOT to delete XIV: traceability is a genuine project rule (design spec §14, "Everything is traceable"). The defect is the framing — the preamble presents every principle as a restatement of the PRD. Fix the preamble to distinguish the thirteen PRD-derived principles from the one house rule, and label XIV's real source. Cost if wrong: a governing doc carrying one honestly-labelled house rule instead of silently passing it off as the PRD's.

**8. [Task 2]** Important 2 (Principle VII drops "testable") — VERIFIED against the PRD. §0.9 reads "Код повинен бути тестованим, deterministic у backtest mode та максимально однаковим між live і replay". "Testable" is a third requirement and was genuinely lost. Restore it. Cost if wrong: none; it is a straight restoration of source text.

**9. [Task 2]** Minor 1 (missing Governance/Version footer) folded into this fix round rather than deferred — the file is already open, and spec-kit's own speckit-constitution skill uses that footer for amendment version bookkeeping. Cost if wrong: four lines nobody reads.

**10. ["deterministic baselines". Ruling]** enforceable substance (baselines exist, leakage tests pass) is intact; "strong" is unmeasurable as written. Code stands.

**11. [the PRD implies but does not state. Ruling]** a faithful operational reading of "distinguish"; it makes the rule checkable. Code stands.

**12. [Task 4]** Minor (`test_status_is_ordered` uses only `<`, never the `>=`/`>` that Tasks 8 and 9 use) folded into this fix round — same file, one line, and it makes the test state what it protects. Cost if wrong: two extra assertions.

**13. [since the task is one commit. Ruling]** the RED output is corroborated by the fact that `ModuleNotFoundError` is the only failure the base tree could produce, and the GREEN counts match the diff exactly. Not worth splitting commits to prove. Code stands.

**14. [Task 5]** Important 1 (`collect_tests` has zero coverage) — NOT a real gap. The plan schedules exactly two tests for it in Task 6 Step 5 (plan lines 1595, 1610: test_collect_tests_reads_the_plugin_dump, test_collect_tests_tolerates_a_missing_dump). The reviewer could not know this; the omission was mine in the dispatch. Parked, and I will verify those two tests exist at Task 6. Cost if wrong: caught one task later.

**15. [Task 5]** Important 2 (no letter-bearing token test) — REAL, and worse than reported. Verified: narrowing REQ_ID to [0-9]+ turns "REQ-PHASE-1A" into "REQ-PHASE-1", a different valid-looking ID, so the failure mode is silent MIS-ATTRIBUTION of a trace link, not a dropped one. Fixing in round 1. Cost if wrong: one extra test.

**16. [needs a second root. Ruling]** checked Task 7's tests — the only call is `vault.source("channelflow/bars.py", ...)`, and build_graph skips a missing `tools/` root via its `is_dir()` guard. No change needed; generalizing now would be speculative.

**17. [Ruling]** intentional — code and test ids are already path-shaped and must match what the markers say. Not worth a change; the inconsistency is visible in the collector signatures.

**18. [Task 5]** one code path, already guarded by the __pycache__ test. Table-driven expansion is churn.

**19. [Task 6]** the ruff findings are real defects in MY plan text, not implementer error. Verified: 6x E501 (a 103-char `pytester.makeini` one-liner) and 1x B018 (`result.ret`, a bare expression I wrote purely to hang a comment on). `make lint` and Task 10's pre-commit hook both run ruff, so a brief's "use verbatim" instruction yields to the project-wide constraint that lint passes. Fixing in round 1.

**20. [Task 6]** scanned every python block in the remaining plan for the same defect class before dispatching the fix. Found 2 more E501 in Task 7 and 2 in Task 10; fixed all in the plan (commit below) so tasks 7 and 10 do not each burn a fix round on it. One flagged Task 7 line (`n.id`) was a false positive — a set comprehension, not a bare expression. Cost if wrong: reformatted lines that were already fine.

**21. [Task 6]** both are real. Verified the reviewer's reasoning: the two tests that inspect entries do so order-insensitively (a dict comprehension and an all()/len() pair), so removing entries.sort() breaks nothing; and no test passes a repeated ID to one marker, so deleting dict.fromkeys breaks nothing. Fixing in round 2. Note the reviewer's own caveat that collect_tests re-dedups independently, so a plugin dedup regression would corrupt only the dump artifact, not the graph — the contract still specifies it, so it gets a guard. Cost if wrong: two extra tests.

**22. [Task 7]** the "vacuous determinism guard" finding is CONFIRMED independently. I removed both `graph.edges.sort(...)` and the `sorted(graph.nodes.values(), ...)` in to_dict and reran test_graph.py: 8 passed. The determinism PROPERTY does hold without them (collectors use sorted() internally and build_graph invokes them in fixed order), so the test's claim is true but it does not guard the lines it appears to guard. What the sorts actually buy is a CANONICAL order independent of collector invocation order. The fix is therefore to assert the canonical order, not to strengthen the two-runs-agree comparison. Cost if wrong: a test pinning an order we later want to change.

**23. [Task 7]** `phase=` filter and to_mermaid's dangling-edge exclusion have zero coverage, and Task 9 calls `to_mermaid(graph, phase=...)` directly for its per-phase dashboard sections. Untested code that a later task depends on is exactly the gap this process exists to close. Fixing both in round 1.

**24. [Task 7]** `_safe()` is tested only for hyphens; the brief's own motivating characters (`::`, `/`, `.`) are untested. Fixing.

**25. [to_mermaid. Ruling]** two call sites is not duplication worth an abstraction, and the canonical- order test added this round pins both. Code stands.

**26. [Task 7]** a defensive default whose only effect is arrow shape in a diagram. Not worth a test.

**27. [Task 7]** I re-ran my own mutation after the fix. Removing both sorts now FAILS test_export_order_is_canonical_not_collector_insertion_order (test_graph.py:117) where before all 8 tests passed. The guard is load-bearing, and the re-reviewer separately confirmed the fixture's insertion order genuinely differs from canonical order in both nodes and edges.

**28. [Task 8]** R6 self-loop is REAL but currently correct. Verified: networkx 3.6.1's simple_cycles returns [['A']] for a self-edge, and R6 does report "dependency cycle: REQ-WP-001 -> REQ-WP-001". The behavior is right but rests entirely on a third-party detail nothing pins. A requirement depending on itself is a plausible human error, and R6 exists to catch exactly that. Fixing in round 1. Cost if wrong: one test.

**29. [Task 8]** folding the Minor "R3 tested for only 2 of 6 edge kinds" into the same round. The reviewer judged the risk low because all kinds share one conditional — true, but the real risk is not the conditional, it is REQUIREMENT_TARGETED itself: a future edit dropping a kind from that tuple would silently stop checking it. A parametrized test over all six kinds guards the list rather than the branch. Cost if wrong: one parametrized test.

**30. [differential test. Ruling]** it IS proven, and duplicating it under an R2 name is bookkeeping, not coverage. Code stands.

**31. [Consumes line implies. Ruling]** the brief's Consumes block lists what the task's code and tests together touch; validate.py itself needs neither. No functional gap — verified no requirement-targeting edge kind ever targets PRD. Code stands.

**32. [Task 9]** the CRITICAL marker-injection finding is CONFIRMED and is worse than reported. The reviewer's trigger was a YAML typo containing the marker text — unlikely. I found a far more realistic one and verified it: a requirement note that merely MENTIONS the marker in prose. Because replace_between_markers uses first-occurrence find() for both markers: Scenario A (BEGIN and END both in one prose sentence): the generated block is written INTO the middle of the human's sentence, and the real Trace section is left stale. Content written outside the intended region — a direct violation of property 1. Scenario B (BEGIN in prose, real pair further down): the entire "## Acceptance" section and the "## Trace" heading are SILENTLY DESTROYED. No error raised. Verified by running it. This is not hypothetical for this project: Task 14 creates REQ-INFRA-001, a requirement note about the traceability tooling itself, and CLAUDE.md documents the marker convention. A note describing how the markers work is exactly the note this bug eats. Fix: require EXACTLY ONE BEGIN and EXACTLY ONE END, raise otherwise. update_requirement_notes already catches ValueError and routes the note to `skipped`, so silent destruction becomes a loud, skippable warning — which is the behavior the spec already describes. Cost if wrong: a note legitimately containing two marker pairs is skipped instead of written.

**33. [Task 9]** folding in three Importants — an isolated BEGIN-without-END test, a multi-phase grouping test (phases "1A"/"7A" are this project's real vocabulary and Task 11 generates them, yet no test exercises them), and write_dashboard's missing no-op write guard which update_requirement_notes already has one function above it.

**34. [Task 9]** a generic durability concern for any write_text-based tool, mitigated by the vault being in git. Adding it now is scope the plan did not ask for.

**35. [partial progress. Ruling]** no note is left half-written (each write_text follows a fully computed string), so the failure is loud and non-corrupting. Acceptable.

**36. [Task 9]** a reporting nicety in a line of CLI output. Not worth the churn.

**37. [Task 9]** the re-review surfaced a residual — a requirement `title` containing the marker text would leak through graph.py's _label into the rendered dashboard, so the NEXT run raises inside write_dashboard, which has no try/except. That is a crash rather than a graceful skip. It is strictly better than the silent corruption it replaces, and graph.py was out of Task 9's scope. CARRIED INTO TASK 10: the CLI must catch ValueError from the dashboard command, not just from build_graph. Cost if wrong: a traceback instead of a message on a rare input.

**38. [Task 10]** it is what guarantees no path returns None implicitly. Defensive, harmless, stays.

**39. [Task 11]** measured the PRD before dispatching. Only 18 of the 61 heading-derived sections carry an explicit acceptance cue ("Acceptance:", "Done when:", "Metric", "Deliverables:"): all 11 phases, 4 work packages, 3 experiments. The other 43 headings state no criteria, and the 25 constraint one-liners (PRIN/BIAS) ARE their own criterion. Two consequences: (a) The plan's Step 6 treats all 86 as a uniform hand-enrichment pass. That is wrong on the 18 where the PRD already states the criteria verbatim — those should be EXTRACTED, not retyped, so the note cannot drift from the PRD. Strengthening extract_prd.py to pull them. (b) For the ~43 with no stated criteria, I will NOT invent authoritative-looking acceptance text and pass it off as the PRD's. Where the section body implies checkable conditions the note derives them and says so; where it does not, the note says plainly that the PRD states none. The /sdd-spec command already refuses to specify a requirement whose Acceptance is unfilled, so the gate lands when someone actually works on it — which is also when the person filling it has the context to do it honestly. This is not a scope reduction: all 86 notes still get reviewed and filled. It changes WHERE the text comes from. Cost if wrong: some notes say "the PRD states no acceptance criteria" instead of carrying invented ones, which is the safer failure.

**40. [Task 11]** splitting Task 11 into 11a (extractor + tests + 86 generated skeletons, plan Steps 1-5) and 11b (the enrichment pass and validation, Steps 6-8). They are separately rejectable — a reviewer can approve the extractor while rejecting the note contents — and one dispatch covering 86 hand-written notes plus a new module is too large to review as a unit.

**41. [Task 11a]** the "Deliverables mislabelled as Acceptance" finding is CONFIRMED, and the root cause is MY dispatch, not the implementer. I listed `Deliverables:` among the acceptance cues. Verified: the PRD has 8 `Acceptance:` blocks but 11 `Deliverables:` blocks; Phases 5, 6 and 8 have deliverables and no acceptance. So REQ-PHASE-5's "## Acceptance" currently reads "- Bybit; - OKX; - consensus mid; ..." — a list of things to BUILD, presented as the criteria for knowing they work. That is exactly the fabricated-authority failure I told the reviewer to hunt for, and my own cue list caused it.

**42. [Ruling]** `Deliverables:` is never an acceptance criterion. It may only bound where a higher-priority cue's text ends; it can never be selected on its own. Phases 5, 6, 8 get the no-cue marker. Cost if wrong: three phase notes say the PRD states no criteria — which is true. Corrected split: 15 extracted (8 phases, 4 WP, 3 EXP), 25 constraint-as-criterion, 46 no-cue.

**43. [Task 11a]** the no-cue marker is semantically clear but contains neither "TO BE FILLED" nor an empty section, so /sdd-spec's literal check ("empty or still says TO BE FILLED") would fail open on all 46. Fix at the source: the marker gains a machine-recognizable token, ACCEPTANCE-NOT-SPECIFIED, and Task 12's /sdd-spec will check for that token. Carried into the Task 12 dispatch. Cost if wrong: a token in a line humans also read.

**44. [criteria for cued sections. Ruling]** intentional — Requirement is frozen provenance, Acceptance is the maintained field. Adding a template comment saying so, but not deduplicating.

**45. [Task 11a]** verified no PRD heading or numbered item contains a colon or quote, so it is safe today; the PRD is read-only, so it cannot drift. Code stands.

**46. [Task 11b]** measured what actually remains. 21 of 86 notes carry Ukrainian in their ## Requirement body, and all 86 have an empty depends_on. On language: the global constraint says artifacts are English, but the ## Requirement body is documented as frozen verbatim PRD provenance — and the PRD is Ukrainian. These conflict.

**47. [Ruling]** TRANSLATE the body. Provenance is already carried by prd_ref + prd_lines, the PRD is read-only and in git, so the exact original is always recoverable at named line numbers. Keeping a second Ukrainian copy in every note doubles its size for no traceability gain, and the English constraint exists so the notes, the code and Graphify's index share one vocabulary. Formulas, thresholds, identifiers and field names stay verbatim. Cost if wrong: the notes paraphrase where a reader wanted the original, one `sed -n` away in the PRD.

**48. [Task 11b]** the 5 Minors are small but they ARE the class I told the reviewer I cared most about — text in a requirement note that the PRD does not say. "strict" inserted into EXP-014, "(one factor at a time)" defining a term the PRD never defines in EXP-015, "against baselines" in WP-018, "joined onto the signal/feature pipeline" in WP-013. Each is one phrase, each is cheap to remove, and leaving them would mean the standard I set applies only to large lapses. Fixing in round 1. Cost if wrong: four notes read slightly more tersely.

**49. [derivatives edge (WP-013) was added, no DeFi one. Ruling]** the reviewer notes this is the safe direction — an omitted edge, not an invented one. There is no DeFi-context work package that cleanly matches; WP-014/015 are ingestion, not context. Leave it.

**50. [Task 12]** Important 1 (R5 attribution) CONFIRMED. CLAUDE.md says R5 enforces "Principle XIV"; validate.py's own violation message says "PRD section 0.2"; sdd-trace.md says "PRD §0.2". Checked the constitution: Principle XIV is "Everything is traceable", a general statement, not about constraint-type requirements needing tests. PRD §0.2 is "no future leakage, look-ahead or repainting even if it improves the backtest" — the actual motivation. Align CLAUDE.md to §0.2, which is also the string a user sees when the rule fires. (My own grep for "Principle XIV" missed this because the text wraps mid-phrase; the reviewer read the document rather than grepping it.)

**51. [Task 12]** Important 2 (R7 omission) CONFIRMED and load-bearing. Duplicate requirement IDs ARE rejected — TraceGraph.add raises, cli.py turns it into "trace: cannot build graph: duplicate node id: 'X'" and exit 1, and there is a named test (test_r7_is_raised_by_the_graph_itself). But CLAUDE.md's "six rules" framing and sdd-trace.md's R1-R6 remediation list mention it nowhere, so a session hitting that hard failure has no documented guidance and would reasonably conclude duplicate IDs are unchecked. Fix is the reviewer's: one sentence after the table (NOT a seventh table row, which would misdescribe validate.py's output) plus a line in sdd-trace.md for the hard-fail case.

**52. [Task 14]** the plan's Steps 2-3 say to run the /sdd-spec, /sdd-plan and /sdd-tasks slash commands. A subagent cannot invoke this project's slash commands or its Spec Kit skills.

**53. [Ruling]** the implementer follows the /sdd-* command FILES as written instructions and produces the same artifacts by hand — the spec at specs/<NNN-slug>/spec.md with traces:, the vault spec note, the outcome notes, the status transitions. The dogfood's purpose is to prove the graph closes from requirement through spec and test to code, not to exercise Spec Kit's own text generation. Cost if wrong: the spec is written rather than generated, which does not change whether the trace graph closes.

**54. [Task 14]** Important 1 (`make lint` runs only `ruff check` while pre-commit also runs `ruff-format`, so a green `make lint` does not predict a passing commit) — REAL and pre-existing. Fix: add `ruff format --check` to the lint target, non-mutating. A build command that promises less than the gate enforces will mislead every future contributor once.

**55. [Task 14]** Important 2 (the `tested` rung) — the reviewer is right that nothing reads

**56. [Status.TESTED and that CLAUDE.md and sdd-implement.md disagree. Ruling]** KEEP the rung and fix CLAUDE.md, not the reverse. `tested` means failing tests exist, carry the marker, and were committed BEFORE any implementation — that commit is the only artifact proving a test was written first, which is the discipline the whole project rests on. Deleting the rung would remove the checkpoint. But CLAUDE.md must also say plainly that no validator enforces it: the ladder is a discipline, not a gate, and implying enforcement would be the same false-promise defect as Important 1. Cost if wrong: a documented rung people may skip.

**57. [sits awkwardly on retroactive infrastructure specs. Ruling]** the template is vendored Spec Kit content; branching it for retroactive specs is scope this plan did not ask for.

**58. [Final]** both Criticals are the exact failure this branch exists to prevent — a green build that does not mean what it appears to mean. They go in the fix wave, not the merge note.

**59. [Ruling]** all five are small, well-specified, and three of them defeat fixes made minutes ago or leave a gap that passes silently. Closing them is the adjudication, not an open-ended second wave. The 8 Minors are parked.

## Parked findings

Real issues found in review and deliberately not fixed, with the reason.

**1. [Task 1]** minor (deferred, folded into Task 2): `market_forge_tools.egg-info/` is untracked and un-ignored after the editable install.

**2. [Task 2]** minor (parked): Principle IV drops the PRD's "сильних"/"strong" qualifier before "deterministic baselines". Ruling: enforceable substance (baselines exist, leakage tests pass) is intact; "strong" is unmeasurable as written. Code stands.

**3. [Task 2]** minor (parked): Principle II adds "every model names which timestamp it holds", which the PRD implies but does not state. Ruling: a faithful operational reading of "distinguish"; it makes the rule checkable. Code stands.

**4. [Task 2]** complete (commits 3b81de5..b8e9378, review clean, 2 minors parked)

**5. [Task 4]** minor (parked): reviewer noted the RED step is not independently checkpointed in git, since the task is one commit. Ruling: the RED output is corroborated by the fact that `ModuleNotFoundError` is the only failure the base tree could produce, and the GREEN counts match the diff exactly. Not worth splitting commits to prove. Code stands.

**6. [Task 4]** complete (commits 13b2675..ff46be0, review clean, 1 minor parked)

**7. [Task 5]** minor (parked): VaultBuilder.source() hardcodes the "src" root; reviewer worried Task 7 needs a second root. Ruling: checked Task 7's tests — the only call is `vault.source("channelflow/bars.py", ...)`, and build_graph skips a missing `tools/` root via its `is_dir()` guard. No change needed; generalizing now would be speculative.

**8. [Task 5]** minor (parked): Node.path is absolute for note kinds and relative for code/test kinds. Ruling: intentional — code and test ids are already path-shaped and must match what the markers say. Not worth a change; the inconsistency is visible in the collector signatures.

**9. [Task 5]** complete (commits ff46be0..057183d, review clean, 4 parked)

**10. [Task 5]** parked ruling CLOSED — verified test_collect_tests_reads_the_plugin_dump (line 136) and test_collect_tests_tolerates_a_missing_dump (line 151) now exist. The Task 5 "Important" was correctly rejected.

**11. [Task 7]** minor (parked): `sorted(graph.nodes.values(), key=...)` duplicated in to_dict and to_mermaid. Ruling: two call sites is not duplication worth an abstraction, and the canonical- order test added this round pins both. Code stands.

**12. [Task 7]** complete (commits 5d303a5..98673bd, review clean, 2 minors parked)

**13. [Task 8]** minor (parked): R2's "does not fire below implemented" is proven only via the R5 differential test. Ruling: it IS proven, and duplicating it under an R2 name is bookkeeping, not coverage. Code stands.

**14. [Task 8]** minor (parked): validate.py does not import PRD_NODE_ID/build_graph as the brief's Consumes line implies. Ruling: the brief's Consumes block lists what the task's code and tests together touch; validate.py itself needs neither. No functional gap — verified no requirement-targeting edge kind ever targets PRD. Code stands.

**15. [Task 8]** complete (commits 98673bd..8fa4257, review clean, 2 minors parked)

**16. [Task 9]** minor (parked): mid-loop exception aborts update_requirement_notes rather than returning partial progress. Ruling: no note is left half-written (each write_text follows a fully computed string), so the failure is loud and non-corrupting. Acceptable.

**17. [Task 9]** complete (commits 8fa4257..80a02da, review clean, 3 minors parked)

**18. [Task 11a]** minor (parked): `## Requirement` (verbatim PRD body) and `## Acceptance` duplicate the criteria for cued sections. Ruling: intentional — Requirement is frozen provenance, Acceptance is the maintained field. Adding a template comment saying so, but not deduplicating.

**19. [Task 11a]** complete (commits fc725c5..368c0a4, review clean, 2 minors parked)

**20. [Task 11b]** minor (parked): WP-020's step 12 names "derivatives/DeFi context adapters" but only a derivatives edge (WP-013) was added, no DeFi one. Ruling: the reviewer notes this is the safe direction — an omitted edge, not an invented one. There is no DeFi-context work package that cleanly matches; WP-014/015 are ingestion, not context. Leave it.

**21. [Task 11b]** complete (commits 368c0a4..2d1f4c5, review clean, 1 minor parked)

**22. [Task 14]** minor (parked): Spec Kit's override template forces a User Story P1/P2/P3 framing that sits awkwardly on retroactive infrastructure specs. Ruling: the template is vendored Spec Kit content; branching it for retroactive specs is scope this plan did not ask for.

**23. [Task 14]** complete (commits 53a48f3..190105e, review clean, 2 minors parked)

