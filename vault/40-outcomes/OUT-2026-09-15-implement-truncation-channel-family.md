---
id: OUT-2026-09-15-implement-truncation-channel-family
step: implement
records: [REQ-NRT-LEAK]
commit: null
---

## What was done

Built PRD §35.4's comparison and enumeration, and covered the first family.

- `src/channelflow/features/truncation.py` — `TruncationCase`, `Refusal`,
  `Divergence`, `uncovered`, `divergence`, `RELATIVE_TOLERANCE`.
- `tests/unit/features/test_truncation_parity.py` — 20 tests, four real cases
  (the `channel` family) and a deliberately leaking one.
- `tests/mutations/truncation.toml`.

**[[REQ-NRT-LEAK]] moves to `tested`, not `implemented`.** 4 of 55 features have
cases. The remaining 51 are in `NOT_YET_COVERED`, and that list being non-empty
is the reason. It is a debt register, not a permission.

### RED, before the module existed

    $ .venv/bin/python -m pytest tests/unit/features/test_truncation_parity.py -q
    E   ModuleNotFoundError: No module named 'channelflow.features.truncation'
    1 error in 0.13s

Written before the implementation this time. The previous cycle's note records
the opposite, and recording it is what made this one go in the right order.

## What was decided

**The module compares and counts; it does not compute.** A `FeatureSpec` carries
no callable, and the 55 features share no signature. So each case supplies both
of its own runs, and what lives in `src/` is the comparison and the set
difference that makes "for every feature" checkable.

**`uncovered` raises on a name the registry does not hold.** A misspelled feature
in a case would otherwise read as coverage — the one direction this must never
fail in.

**A refusal costs a written reason, and whitespace is not one.** A skip reports
green, and green is what a leak needs to survive.

**The tolerance is relative, `1e-9`, and integers do not get it.** These features'
units run from a ratio to a notional, so one absolute epsilon cannot mean
anything across both. `10**12` and `10**12 + 1` differ by 1e-12 relative — inside
any float tolerance worth having, and a whole unit of whatever is being counted.

### The mutation sweep found three weak assertions

13 mutations. First run **10 caught, 3 survived**; all three were weak tests:

- *A whitespace reason counts as a reason.* The test passed only `""`. It now
  parametrises `""`, `"   "`, `"\t"`, `"\n  "`.
- *Refusals do not count as coverage.* `REFUSALS` is empty, so dropping the term
  changed nothing. A test now refuses a real outstanding feature and asserts the
  debt register shrinks by exactly that name.
- *Integers get the floating-point tolerance too.* The test compared `5` and `6`,
  which no sane tolerance calls equal. Two large integers one apart do the job.

Second run: **13 caught, 0 survived.**

## Two defects found by running the full gate, not by looking for them

Neither belongs to [[REQ-NRT-LEAK]]. Both were found because `make validate`
runs the integration suite for real, and both had been invisible.

### A test suite that leaked topics until the broker refused to make more

`tests/integration/test_transport_on_redpanda.py` took a fresh uuid topic per
test and never removed it. A broker outlives a test run, so the cost accumulated:
**259 abandoned topics**, at which point the development broker said

    Refusing to create 1 new partition replicas as total partition replica count
    263 would exceed memory limit of 262 partition replicas

and stopped creating them. The consumer then subscribes to a topic that does not
exist, the poll returns nothing, and the failure reads `assert [] == [1, 2, 3]` —
which says nothing whatever about topics. Two tests failed, the run took **624
seconds**, and the message pointed at a shared conformance helper.

The fixture now deletes its topic. With the leftovers cleared, the same three
tests pass in **24.77 seconds** and the topic count returns to one.

**CI never saw this and never could.** Its broker is new every run. That is the
shape of defect a disposable environment hides, and the reason a long-lived local
stack is worth keeping rather than resetting whenever it misbehaves.

### A security default of mine that failed open

[[REQ-WP-072]] bound every published port with `"${CHANNELFLOW_BIND_ADDRESS}:…"`
and put the default in `.env.example`. An `.env` written before that variable
existed leaves it blank, and compose then parses `":19092:9092"` as a published
port with **no host_ip** — every service on every interface, which is the exact
opposite of what the file and the deployment document say. Verified with
`docker compose config`: `published: "19092"` and no `host_ip` at all.

`.env.example` is documentation, not a default. The default now lives in the
substitution — `${CHANNELFLOW_BIND_ADDRESS:-127.0.0.1}` — so an unset variable
binds loopback, and a test asserts the bare form appears nowhere.

`GRAFANA_ADMIN_PASSWORD` had the same shape and a worse ending: blank is not a
password, and Grafana falls back to `admin`. It now uses `:?`, so compose refuses
to start and names the missing variable. Confirmed: `exit=1`, *"required variable
GRAFANA_ADMIN_PASSWORD is missing a value: set it in .env; see .env.example"*.

**Both were mine, both shipped green through CI**, because CI does
`cp .env.example .env` and therefore never has a stale environment file. A gate
that always starts from the template cannot see a defect that only affects
environments which do not.

## What is still open

**51 features.** `derivatives` 19, `order_book` 15, `trade_flow` 5, `order_flow`
5, `volume_structure` 5, `defi` 2. Measured cost of the first family: four cases
in one small helper, because all four read a field off a `ChannelSnapshot` and
the truncated/full distinction is which bars the model was given. The families
that take a stateful tracker or a book service will cost more per case, and that
estimate is still a guess rather than a measurement.

**The debt register is the honest part and the weak part.** It keeps a new
feature from widening the gap silently — a feature added tomorrow lands in
`uncovered()` and not in the literal, so the suite goes red by name. It does not
make today's 51 fail, and it must not be mistaken for the gate. The gate is the
list being empty.
