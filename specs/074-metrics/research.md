# Phase 0 — Research

## 1. Why not a Prometheus client library?

**Decision**: render the text format directly.

**Rationale**: the official client's design assumes a long-running process: a
module-level global registry, a process collector reading `/proc`, and a clock.
This codebase has spent requirements removing exactly those three — [[ADR-018]]
forbids the clock, and a global registry makes a test's metrics leak into the
next test's. The exposition itself is a name, optional labels, a value and a
`# TYPE` line.

**Alternatives considered**: the client with its registry passed explicitly. It
would still default a registered counter to zero, which is the one behaviour
this requirement exists to prevent.

## 2. What makes a metric exist?

**Decision**: an observation, not a registration.

**Rationale**: every mainstream metrics library initialises a registered counter
to zero. That is convenient in a process where everything is eventually
incremented and dishonest in one where half the producers are not written yet: a
dashboard cannot tell a quiet counter from an absent one, and neither can an
alert.

## 3. Derived, or incremented?

**Decision**: derived, where the data already exists.

**Rationale**: a counter someone must remember to bump silently stops when a new
code path forgets it, and the metric stays flat while the thing it measures gets
worse — a monitoring failure that looks exactly like good news. The dispatcher
already keeps an append-only audit and [[REQ-WP-035]] already produces health
assessments; counting those cannot drift from them.

## 4. What does the format actually require?

**Decision**: `# TYPE` per metric family, escaped label values, numeric values,
names matching `[a-zA-Z_:][a-zA-Z0-9_:]*`.

**Rationale**: it is a contract with something outside this repository. A
subtly malformed exposition fails at scrape time, in production, where the
failure mode is a dashboard that stops updating rather than an error anybody
sees. Names are validated at registration instead, which is where it can be
fixed.

Label values need escaping for backslash, quote and newline. A symbol or a
reason string reaching a label unescaped would break the line, and Prometheus
would either drop the sample or read it as a different series.

## 5. Counters that go down

**Decision**: refuse.

**Rationale**: a clamped decrement is a lie told quietly — the counter keeps
serving a plausible number. A refusal is a bug report at the call site, and a
counter going backwards is always a bug.
