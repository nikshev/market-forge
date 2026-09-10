# Phase 0 — Research

## 1. Which packages actually need an exemption?

**Decision**: one module, `extrema/causality.py`.

**Rationale**: a scan of all 27 packages for the five forbidden helpers returns
exactly one file, and it is the one that defines the list. `research/` does not
appear — `derivative_turning` implements its centred labeller directly rather
than importing `savgol_filter`.

**Alternatives considered**:
- *Pre-exempt every research package*, since PRD §13A.6 permits centred filters
  there. Rejected: it weakens the rule today for a case that does not exist, and
  an exemption nobody needed is indistinguishable from one nobody checked.
- *Exempt the `extrema` package.* Rejected: it would exempt every module beside
  `causality.py`, and `extrema` is where this rule most wants to look.

## 2. Should the scan skip strings and comments?

**Decision**: no. A plain substring match over the source, with an explicit
per-module exemption for the file that names the helpers.

**Rationale**: this is the existing Test D's approach and it is right for the
reason [[ADR-022]] gives — the check is a tripwire, not a parser. Parsing imports
properly would miss `getattr(scipy.signal, "savgol_filter")` while gaining the
ability to ignore a docstring, which trades a real hole for a cosmetic one. A
docstring that mentions a forbidden helper is a file that should say so out loud
and be exempted, or should not mention it.

**Alternatives considered**:
- *An AST walk over import statements.* Precise about imports and blind to every
  other way of reaching the same function.

## 3. How is `point_in_time_safe` enforced?

**Decision**: narrow the field to `Literal[True]`.

**Rationale**: a required field nothing reads is documentation, and [[ADR-015]]
made this registry a gate rather than a habit. The type makes an unsafe feature
unregisterable rather than registerable-and-caught-later, and the author still
has to write the value, so the "no field an author can forget to think about"
property is unchanged.

**Alternatives considered**:
- *A test asserting every entry is `True`.* Catches it one step later and only
  for features that reach the registry through the checked path. Kept anyway as
  a second statement of the rule in words rather than types — the type says what
  is allowed, the test says why.
