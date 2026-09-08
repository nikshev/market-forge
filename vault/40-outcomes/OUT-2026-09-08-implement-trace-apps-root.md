---
id: OUT-2026-09-08-implement-trace-apps-root
step: implement
records: [REQ-INFRA-001, REQ-WP-001]
commit: null
---

## What was done

`apps/` is now a code-collection root, so frontend files can carry a
`// @trace:` marker and appear in the graph. `dist/` joins the skip list.

## What was decided

- **This was a recorded gap, not a discovery.** REQ-WP-001's outcome note
  closed with "`apps/` is not a collector root, so frontend code can never
  carry a trace link... a real gap, not a preference, and it was left open
  deliberately rather than fixed here." REQ-WP-009 is the first requirement
  whose implementation is largely TypeScript, so R8 would have been
  unsatisfiable for it.
- **`dist/` is skipped even though it is gitignored.** A built bundle's markers
  are copies of the source's; collecting both would double every frontend edge
  and put a build artifact in the traceability graph. The git-tracked filter
  already excludes it today — this makes a repo that ever committed a bundle
  fail safely rather than silently.
- **`App.tsx` gains `// @trace: REQ-WP-001`**, which is what it always should
  have carried: the scaffold is that requirement's deliverable.

## What is still open

- Nothing from this step. The `.ts`/`.tsx` suffixes were in `CODE_SUFFIXES`
  from the beginning; only the root was missing.
