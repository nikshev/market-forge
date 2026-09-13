---
id: REQ-WP-064
title: The API and the web app become images that start
type: work-package
prd_ref: "§6.2, §45 Phase 8, §34"
prd_lines: "405-420, 6904-6913, 5250-5270"
phase: 8
status: implemented
depends_on: [REQ-WP-056, REQ-WP-055, REQ-WP-041]
tags: []
---

## Requirement

PRD §6.2 names the MVP deployment's services:

    api / worker / ingest-binance / postgres / clickhouse / redis optional / web

[[REQ-WP-056]] documented and containerised the stateful half — PostgreSQL,
MinIO, Redpanda, Prometheus, Grafana — and ClickHouse is not part of this project
([[ADR-002]]). **Nothing else is containerised, and the reason is worse than an
absent Dockerfile.**

### Nothing in this project can be started as a process

`create_app(repository=...)` is a factory that takes an already-built
repository. There is no module a server can import, no configuration reader, and
no composition root. `LakehouseRepository` needs a `Catalog`, and the only place
one is opened is a test fixture pointing at a temporary directory.

So an image is not the first missing piece; **a way to start is.** The catalog
factory already takes a PostgreSQL URI and an S3 warehouse and deliberately does
not branch on the scheme ([[REQ-WP-041]]), so what is missing is the part that
reads the environment and calls it.

### Configuration is refused, not defaulted

PRD §34 keeps secrets out of the repository and in the environment. A composition
root that fell back to a local directory when `CHANNELFLOW_WAREHOUSE` was unset
would start successfully in production and serve an empty warehouse — which reads
as a quiet market, the failure this project keeps meeting. Missing configuration
therefore refuses to start, naming the variable.

### Readiness is not §32's health

[[REQ-WP-035]]'s `HealthState` grades **feeds**: a stale book disqualifies a
signal. A container probe asks whether *this process can serve*. Answering the
probe with §32's state would have an orchestrator restart a pod because a venue
went quiet, and would report a process that cannot reach its catalog as healthy
whenever the feeds happened to be fine. They are separate questions and get
separate endpoints.

### What is not containerised, and why

`worker` and `ingest-binance` are named by §6.2 and **do not exist as code**.
[[REQ-PIPE-001]] chose a replay over a daemon deliberately and said so: "a live
process attaching the same sinks to a running connector is deployment work and
adds nothing this cannot already show." Writing a service to have something to
put in an image would invert that. They stay named and absent.

Phase 8's remaining deliverable — load generation — needs the API and the web
app, both of which exist.

## Acceptance

- A composition root builds the application from the environment alone, and a
  missing required variable refuses to start, naming it.
- The catalog is opened through [[REQ-WP-041]]'s one factory, with no second
  path for PostgreSQL.
- A readiness endpoint reports whether the catalog answers, and is distinct from
  §32's feed health and from `/metrics`.
- An image exists for the API and for the web app, and **CI builds both** — a
  Dockerfile that is never built is a document.
- CI starts the API image against the live stack and gets a ready response, so
  "it starts" is measured rather than declared.
- No credential is baked into an image or a compose file; both take the
  environment (§34).
- The compose file gains `api` and `web`, and gains no service for a process
  this repository does not have.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-105-production-images]]
- **Tests:**
    - `tests/unit/api/test_startup.py::test_a_blank_variable_counts_as_missing[   ]`
    - `tests/unit/api/test_startup.py::test_a_blank_variable_counts_as_missing[\t]`
    - `tests/unit/api/test_startup.py::test_a_blank_variable_counts_as_missing[]`
    - `tests/unit/api/test_startup.py::test_a_missing_variable_refuses_to_start_and_names_itself[CHANNELFLOW_CATALOG_URI]`
    - `tests/unit/api/test_startup.py::test_a_missing_variable_refuses_to_start_and_names_itself[CHANNELFLOW_WAREHOUSE]`
    - `tests/unit/api/test_startup.py::test_a_store_that_does_not_answer_is_not_ready`
    - `tests/unit/api/test_startup.py::test_an_app_with_no_store_says_so_rather_than_claiming_one_answered`
    - `tests/unit/api/test_startup.py::test_an_unready_process_answers_with_a_status_an_orchestrator_reads`
    - `tests/unit/api/test_startup.py::test_both_missing_variables_are_named_at_once`
    - `tests/unit/api/test_startup.py::test_both_variables_are_required`
    - `tests/unit/api/test_startup.py::test_no_credential_is_written_into_the_compose_file`
    - `tests/unit/api/test_startup.py::test_readiness_is_not_section_32s_feed_health`
    - `tests/unit/api/test_startup.py::test_storage_options_are_read_under_pyicebergs_names`
    - `tests/unit/api/test_startup.py::test_the_api_image_installs_the_project_without_a_path_link`
    - `tests/unit/api/test_startup.py::test_the_application_is_built_from_configuration_alone`
    - `tests/unit/api/test_startup.py::test_the_build_context_excludes_the_developers_environment`
    - `tests/unit/api/test_startup.py::test_the_compose_file_declares_the_services_that_exist`
    - `tests/unit/api/test_startup.py::test_the_required_configuration_is_read`
- **Code:**
    - `src/channelflow/api/main.py`
    - `src/channelflow/api/readiness.py`
- **Outcomes:** [[OUT-2026-09-13-implement-production-images]]
<!-- trace:end -->

## Notes

This closes the first of Phase 8's two remaining entries and unblocks the second:
load generation had nothing to generate load against.
