# Phase 0 Research: The timeframe is chosen on the chart

The spec fixed the behaviours; this resolves the choices they leave open. Each
decision names what was rejected, because the rejections are the load-bearing
part: several alternatives here are the defect the feature exists to remove,
wearing a different shape.

## Where the frontend learns the offered set

**Decision**: a new read, `GET /api/v1/timeframes`, reporting the deployment's
offered timeframes. The frontend carries no list.

**Rationale**: [[REQ-WP-073]]'s FR-002 says no component may carry the set as a
constant, and its acceptance for this requirement says the frontend's half is
settled here "including whatever API surface it needs". The set is runtime
configuration; only the deployment knows it.

**Alternatives considered**:

| alternative | why not |
|---|---|
| a `ts` constant beside the control | The exact second list FR-002 forbids. It would pass every test written against the default configuration and disagree silently on a deployment that changed one line of `.env`. |
| Vite build-time env (`VITE_TIMEFRAMES`) | The value would be baked into the bundle at build time, so one image could not serve two configurations, and a rebuilt frontend would be needed for a config change. It also puts the set in a second variable that can disagree with `CHANNELFLOW_TIMEFRAMES`. |
| infer the set from data (e.g. probe each known token) | Probes for eight timeframes per page load; becomes wrong the moment configuration names one the probe list lacks; and turns a configuration question into a data question. |
| serve it from `/api/v1/markets` | §28.1's markets response is about instruments and ranking. Widening it would make every consumer of that response pay for a field one consumer uses. |

## Does the endpoint carry durations, or only tokens?

**Decision**: both — `{token, timeframe_ns}`.

**Rationale**: the chart needs a duration for its requests (`timeframe_ns` is
what §28.2 takes). If only tokens crossed the wire, the frontend would need a
token→duration table — a second list again, with units. Carrying the duration
removes the need for the table entirely: the link's token is matched against
what the deployment reported, and its duration is used as given.

**Alternatives considered**: a `Record<string, number>` in the frontend
(rejected: the second list); parsing tokens arithmetically in TS
(`1h` → `3_600_000_000_000`) — rejected because it would re-implement
[[REQ-WP-073]]'s vocabulary in another language, where the week's Monday origin
and the calendar-period refusal would each have to be re-derived, and the
markets view is named in that requirement's data model as needing the same
arithmetic "in TypeScript" — a concern for whoever builds that view, not a
reason to duplicate the table here.

## Is `1m` offered?

**Decision**: yes. The offered set is the source timeframe plus the configured
targets.

**Rationale**: §5.1 lists `1m` first among the Phase 1 timeframes, and the
ingest daemon produces it always; `CHANNELFLOW_TIMEFRAMES` deliberately names
what *resampling* builds and excludes the source (its `.env.example` comment
says so). A control that omitted the one series guaranteed to exist would be
visibly wrong.

**Alternatives considered**: offering only what the variable names (rejected:
hides the source series); offering nothing when the variable is unset
(rejected: a deployment that resamples nothing still has one-minute bars, and
the chart can show them).

## How the endpoint gets its configuration

**Decision**: `Settings.timeframes`, parsed by `channelflow.timeframes.parse_list`
in `settings_from_env`; `create_app` receives the tuple and stores it on
`app.state`, as `repository` and `metrics` already are.

**Rationale**: one parser, so an unknown token or a calendar period refuses at
API startup exactly as it refuses at resampler startup — a misconfiguration is
loud in both processes rather than quiet in one. Unset means the source alone,
which is honest for a process whose deployment configured no targets.

**Alternatives considered**: reading `os.environ` inside the route (rejected:
re-reads the environment per request, bypasses `Settings`, and cannot be tested
without mutating the process); a required variable (rejected: it would break
every existing API test and local run for a value with a safe, honest meaning
when absent).

## How the address is updated

**Decision**: `history.replaceState`, with a helper that edits only its own
query key on the current `URLSearchParams`.

**Rationale**: two requirements meet here — FR-007/FR-008 want the address to
describe the screen, FR-009 wants everything else preserved. Rebuilding from the
current search satisfies both. `replaceState` rather than `pushState` because
changing a timeframe is not navigation; a back button that walks through
timeframes is a worse interface, and `pushState` would also make every control
change a history entry in a page whose back gesture is meant to leave it.

For the mode, the parameter is **removed** when AS-SEEN-THEN is in force.
`as_seen_then=false` is the only value that changes meaning (ADR-020), so
absence is the default already; writing `true` would put noise in every copied
link.

**Alternatives considered**: `pushState` (rejected above); a router library
(rejected: one mechanism does not need a dependency, and ADR-021's gates exist
partly to keep the bundle small); `location.hash` (rejected: §27.1's link is
path + query, and alerts carry it that way).

## A stale response must not win

**Decision**: a sequence number held in a ref; a response whose number is not
the current one is discarded, and the effect's cleanup releases it on unmount.

**Rationale**: FR-012 is observable with two quick clicks, and the failure mode
is a chart drawn at a timeframe the reader clicked away from — the same class of
lie as the current constant, only intermittent. jsdom can drive it with mocked
promises resolved in reverse order.

**Alternatives considered**: `AbortController` (rejected as the primary
mechanism: the API client reports failures as values, and an aborted fetch would
surface as a `failed` state for a request the reader deliberately superseded;
aborting is an optimisation, sequencing is the correctness rule);
`useLatest`-style ref of the token compared on arrival (equivalent, but compares
values where a sequence also covers two clicks on the same token).

## What the page shows while the set is in flight

**Decision**: no requests; the existing `LoadState` renders its loading state.
The offered-set read and the bars read are sequential by construction — the
duration comes from the set, so there is nothing to request before it arrives.

**Rationale**: a request issued at a guessed duration is exactly the defect being
removed. The window is one local request.

## Testing the requests, not the components

**Decision**: the App-level tests mock `global.fetch` and assert on the URLs
that reached it — the parameters, for at least two timeframe values. The
pure helpers (`matchTimeframe`, the query writers) are tested directly.

**Rationale**: SC-001 is stated as "the parameters that reached the network",
because a component test asserting internal state would pass with the constant
still in place. Capturing fetch calls is the closest a unit test gets to the
wire, and it is how the existing `api.test.ts` already works.

## What runs in which gate

**Decision**: pytest tests join the fast gate (no service needed); the vitest
tests run in CI's `make web-test` and locally for this feature, per ADR-021.

**Rationale**: ADR-021 keeps `npm ci` out of the pre-commit hook; the web gates
are CI-only by design, and this feature does not change that. The API tests do
run in the fast gate, so a broken endpoint fails a commit.
