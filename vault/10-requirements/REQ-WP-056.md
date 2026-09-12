---
id: REQ-WP-056
title: The stack can be run by somebody who did not build it
type: work-package
prd_ref: "§6.2, §33, §45 Phase 8"
prd_lines: "405-437, 4783-4800, 6910"
phase: 8
status: implemented
depends_on: [REQ-WP-001, REQ-WP-055]
tags: []
---

## Requirement

PRD §45's Phase 8 lists deployment documentation, and this repository documents
development: `make install`, `make up`, `make test`. Nothing says what runs in
front of a user, what it needs, or what it does not do.

[[REQ-WP-055]] left the same gap one level in. The exposition is served and the
dashboard is defined, and **nothing scrapes or renders either** — so the work
that makes them real is the same work, and splitting it would leave both halves
describing something nobody can start.

**The documented profile is not §6.2's.** §6.2 names `api`, `worker`,
`ingest-binance`, `postgres`, `clickhouse`, `redis` optional and `web`.
[[ADR-002]] dropped ClickHouse before any of it was built, the canonical plane
became Iceberg in [[REQ-WP-039]], and Redpanda arrived in [[ADR-063]]. A document
repeating §6.2 would describe a system that does not exist, which is worse than
no document: a reader following it would look for a service nobody deploys and
conclude the deployment is broken.

**Documentation rots in a way that looks exactly like documentation.** A command
renamed, a service removed, a variable spelled differently — each leaves prose
that is confident, plausible and wrong, and none of it fails anything. So the
document is checked against the repository by tests rather than by somebody
reading it: every command it names must exist, every service must be in the
compose file, every variable must be in `.env.example`.

**The dashboard is generated, not written twice.** [[REQ-WP-055]] made the
absences derived rather than transcribed for a reason that applies again here: a
hand-written Grafana file would go stale the day a metric gains a producer, and
would keep explaining why a metric that now exists does not.

## Acceptance

- A deployment document describes what actually runs: the services, what each is
  for, what must be supplied, and what the stack deliberately does not include.
- Every command the document names is a real target, asserted mechanically.
- Every service it names is in the compose file, and every variable it names is
  in `.env.example`.
- Prometheus scrapes the exposition, and the scrape path is asserted equal to
  the route's rather than repeated.
- Grafana is provisioned with a dashboard generated from [[REQ-WP-055]]'s
  definition, carrying both its panels and its stated absences.
- The generated file is checked against the definition, so a metric gaining a
  producer fails the check until the file is regenerated.
- The document names what §6.2 lists and this stack does not run, with the
  decision that removed each.
- No test starts a container.

## Notes

Human territory. Never machine-rewritten.

**Secrets stay out.** §34 requires the Telegram token via a secret manager and
no secrets committed; the document says where each value comes from and
`.env.example` keeps carrying names with empty values, as it has since
[[REQ-WP-001]].

**Load testing is not here.** Phase 8's third item is its own work and needs
something deployed to load.
