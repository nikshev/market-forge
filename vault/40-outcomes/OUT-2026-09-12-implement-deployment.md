---
id: OUT-2026-09-12-implement-deployment
step: implement
records: [REQ-WP-056]
commit: null
---

## What was done

`docs/deployment.md`, Prometheus and Grafana in the stack with their
configuration, `observability/grafana.py` rendering [[REQ-WP-055]]'s definition,
a generator, and eleven tests holding the document to the repository. 6 of 6
mutants caught.

Verified by running it: both services come up healthy, Grafana loads the folder,
and the dashboard arrives with **two time-series panels and nine text panels**,
each naming why its metric is not measured.

## The document is checked, not proofread

Documentation rots in a way that looks exactly like documentation. A command
renamed, a service removed, a variable spelled differently — each leaves prose
that is confident, plausible and wrong, and none of it fails anything.

So eleven tests read the document and the repository and compare the names: every
`make` command is a real target, every service is in the compose file, every
variable is in `.env.example`. And the reverse in both directions, which is where
the quiet failure lives: **a service in the stack and missing from the document
is one nobody knows is running.**

## The first version of that check asserted the opposite of what it meant

The document has two tables of service names — what runs, and what PRD §6.2
lists that this stack does not — and the first extraction read both. It asserted
that `clickhouse` was in the compose file, which is precisely the thing
[[ADR-002]] removed.

Two sections of identical shape and opposite meaning. The fix is to split the
document at the heading, and the test now fails if that heading is ever renamed
rather than silently reading the whole file again.

## What the document says that a copy of §6.2 would not

§6.2's MVP list names `clickhouse`, `redis`, and four services that run from the
host here. A document repeating it would describe a system that does not exist —
worse than no document, because a reader would look for a service nobody deploys
and conclude the deployment is broken.

So each absence is named with the decision behind it: [[ADR-002]] for ClickHouse
and Pinot, [[ADR-018]] for Redis. And what the deployment does not cover at all —
production images, load tests, scheduled backups — is its own section, because a
gap named is a gap somebody can plan around and a gap unmentioned is one they
find at the worst moment.

## The dashboard is generated

[[REQ-WP-055]] derived its absences rather than transcribing them, so they cannot
go stale. A hand-written Grafana file would go stale the same way — keeping a
panel for a metric that moved to the absence list, or explaining why a metric that
now exists does not. So it is rendered from the definition, committed, and a test
compares the two: a metric gaining a producer fails the build until the file is
regenerated.

The rendering carries the point rather than dropping it. An absence becomes a
**text** panel, not a graph of a metric nothing produces — such a graph draws a
flat line at zero, and a flat line at the bottom of a chart reads as "nothing is
going wrong".

## The harness, once more

A mutation pattern written with `\\n` where the source has `\n`. TOML literal
strings do no escape processing, so the pattern never matched — reported as "the
source moved" rather than skipped, which is the difference between a sweep that
measures less than it claims and one that says so.

## What is still open

- **Load tests**, Phase 8's last item, which needs something deployed to load.
- **Production images and a supervisor.** Nothing is containerised beyond the
  stateful services, and writing an image before there is somewhere to deploy it
  would be guessing at a base and a process manager.
