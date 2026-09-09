# Specification Quality Checklist: The `bars` canonical table

**Created**: 2026-09-09 | **Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

FR-004 looks like a column choice and is a look-ahead rule. A bar becomes
knowable when it closes; a point-in-time read filtered on the open would return
a window whose high, low and close had not happened at the instant asked for.
Every leakage check upstream would already have passed, because the leak is in
the storage read.

FR-001's insistence on decimals is not fastidiousness. `Decimal("0.1")` is the
standard example and it is the literal case here: a bar is money, float64 cannot
represent a tenth, and a canonical table is the last place a rounding should be
introduced silently.

FR-003 asks for a field *not* to exist. `is_final` would be `true` on every row
of this table, which makes it a column nobody reads and a door held open for the
row that says otherwise. The refusal on the way in carries the same meaning and
cannot be bypassed by writing a row directly.
