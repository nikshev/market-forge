---
id: SPEC-125-no-unfinalized-upsample
requirement: REQ-NRT-UPSAMPLE
speckit_path: specs/125-no-unfinalized-upsample/spec.md
status: draft
---

## Summary

PRD §13A.17's prohibition on handing an unfinished higher-timeframe close to anything computed
earlier, stated as a property of a seam and not of one function. `resample` already refuses closed
windows that are short of minutes; probing it showed it counts minutes instead of identifying them
and never reads finality, so a duplicated minute standing in for a missing one, or a non-final
source bar, still yields a bar. Neither occurs on the deployment today. The spec asks for
identification, for a read-path guarantee that nothing inside an open window is readable, and for a
mutation sweep that makes the constraint see the violation it forbids.

## Links

- Requirement: [[REQ-NRT-UPSAMPLE]]
- Built on: [[REQ-WP-073]]
