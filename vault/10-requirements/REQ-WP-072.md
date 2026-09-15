---
id: REQ-WP-072
title: Security holds by enforcement, not by absence
type: work-package
prd_ref: "§34"
prd_lines: "4821-4836"
phase: null
status: implemented
depends_on: [REQ-WP-064, REQ-WP-065]
tags: []
---

## Requirement

PRD §34 is the only section of the PRD with **no requirement note at all**. It
opens by saying what the MVP is — *"MVP is read-only market analytics"* — and
lists eight requirements:

> - no exchange trading keys required for public market data;
> - Telegram bot token only via secret/env manager;
> - RPC API keys via secrets;
> - no secrets committed;
> - redact secrets from logs;
> - API write/admin routes authenticated;
> - CORS restricted in production;
> - rate limiting for public web API.

### Seven of the eight already hold. Five hold by accident.

Measured against this checkout, not assumed:

| §34 requirement | today | why |
|---|---|---|
| no exchange trading keys | holds | no connector reads a key; every venue is used through its public endpoints |
| Telegram token via secret manager | holds | [[ADR-018]] — the alerting package reads no environment at all; the transport and its credentials are the caller's |
| RPC API keys via secrets | holds | the capture tools use public endpoints and carry no keys |
| no secrets committed | holds | `.env` is ignored at `.gitignore:10`; only `.env.example` is committed, with empty values |
| redact secrets from logs | holds | **there are no logs.** `import logging` and `logger.` appear **zero** times in `src/` |
| API write/admin routes authenticated | holds | **there are no write routes.** Zero `post`/`put`/`patch`/`delete` handlers; every route is a `GET`, plus one websocket |
| CORS restricted in production | holds | no CORS middleware is installed, so no `Access-Control-Allow-Origin` is ever sent and a browser refuses every cross-origin read |
| rate limiting for public web API | **does not hold** | nothing limits anything |

The last five of those hold **because the thing that could go wrong has not been
built yet**. That is not compliance; it is the absence of an opportunity. The day
somebody adds the first `POST`, the first `logger.info(settings)`, or an
`allow_origins=["*"]` to make a local frontend work, §34 is broken and no test
notices.

### One hypothesis that did not survive measurement

`catalog_probe` returns `detail=f"the catalog did not answer: {cause}"` and
`/readyz` serves that string, so a catalog failure looked like it could echo the
Postgres password out of an unauthenticated endpoint — the catalog URI carries
it. Measured across the three commonest failures — connection refused, wrong
password against a live server, unresolvable host — the password appears in
**none** of the messages: `psycopg` names host and port, and SQLAlchemy does not
put the URL in its exception text. Recorded because a plausible leak that is not
real is worth writing down once, so it is not re-investigated.

### And the stack publishes more than it means to

`docker-compose.yml` publishes every service with a bare `"${PORT}:..."`, which
binds all interfaces. On a host that is not a laptop that offers Postgres, the
MinIO API and console, Redpanda, Prometheus and Grafana to whatever can reach the
host. Grafana in particular runs with `GF_AUTH_ANONYMOUS_ENABLED`,
`GF_AUTH_ANONYMOUS_ORG_ROLE: Admin` and the login form disabled, under a comment
whose stated premise is *"this stack holds no secrets and is not reachable from
anywhere"* — a premise that a deployment falsifies while leaving the setting.

This is §34's spirit rather than its letter: the section says the web API must be
rate limited and CORS restricted, and publishing a database to the internet is
the larger version of the same mistake.

## Acceptance

- A test fails if any route handler outside an authenticated router uses a
  method other than `GET` — so the first write route is a red suite, not a
  silent breach of §34.
- A test fails if CORS is configured with a wildcard origin, and the allowed
  origins are configuration rather than a literal.
- Rate limiting applies to the public read API, with the limit configurable
  (Principle X) and a test that proves the limit is enforced and that exceeding
  it is refused rather than served slowly.
- A test fails if `src/` gains logging that can render a settings object, a
  catalog URI or any value carrying a credential. The rule holds the day logging
  is introduced, not the day somebody remembers §34.
- Every service in `docker-compose.yml` binds its published port to a loopback
  address unless it is deliberately public, and a test reads the compose file and
  refuses a bare `"${PORT}:"` form for anything but the services named public.
- Grafana does not run as an anonymous admin in a configuration intended for a
  server, and whatever it does run as is stated where an operator will read it.
- The deployment document states what is exposed and what is not, and is checked
  against `docker-compose.yml` the way `docs/deployment.md` is already checked
  against the repository.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-113-security-enforced]]
- **Tests:**
    - `tests/unit/api/test_security.py::test_a_configured_origin_is_allowed_and_another_is_not`
    - `tests/unit/api/test_security.py::test_a_refusal_says_how_long_to_wait`
    - `tests/unit/api/test_security.py::test_a_refused_request_is_a_refusal_not_a_late_success`
    - `tests/unit/api/test_security.py::test_a_write_route_behind_authentication_is_permitted`
    - `tests/unit/api/test_security.py::test_a_write_route_is_reported_by_path_and_method`
    - `tests/unit/api/test_security.py::test_every_write_method_is_caught_not_only_post[delete]`
    - `tests/unit/api/test_security.py::test_every_write_method_is_caught_not_only_post[patch]`
    - `tests/unit/api/test_security.py::test_every_write_method_is_caught_not_only_post[put]`
    - `tests/unit/api/test_security.py::test_no_route_does_anything_but_read`
    - `tests/unit/api/test_security.py::test_readiness_and_metrics_are_never_throttled`
    - `tests/unit/api/test_security.py::test_the_limiter_keeps_one_row_per_key_not_one_per_request`
    - `tests/unit/api/test_security.py::test_the_walk_reaches_every_route`
    - `tests/unit/api/test_security.py::test_the_websocket_is_recognised_rather_than_slipping_through`
    - `tests/unit/api/test_security.py::test_the_window_has_to_pass_entirely`
    - `tests/unit/api/test_security.py::test_these_tests_reach_nothing_outside_the_process`
    - `tests/unit/api/test_security.py::test_three_are_allowed_and_the_fourth_is_not`
    - `tests/unit/api/test_security.py::test_two_clients_do_not_share_a_budget`
    - `tests/unit/api/test_security.py::test_with_no_origins_no_cors_header_is_ever_sent`
    - `tests/unit/api/test_security.py::test_without_a_limit_nothing_is_refused`
    - `tests/unit/deploy/test_exposure.py::test_a_public_service_has_to_give_a_reason`
    - `tests/unit/deploy/test_exposure.py::test_every_published_port_binds_an_address_we_chose`
    - `tests/unit/deploy/test_exposure.py::test_grafana_is_not_an_unconditional_anonymous_admin`
    - `tests/unit/deploy/test_exposure.py::test_grafanas_credentials_are_named_in_the_env_template`
    - `tests/unit/deploy/test_exposure.py::test_the_bind_address_defaults_to_loopback`
    - `tests/unit/deploy/test_exposure.py::test_the_compose_file_no_longer_says_ingest_binance_does_not_exist`
    - `tests/unit/deploy/test_exposure.py::test_the_compose_file_still_publishes_ports`
    - `tests/unit/deploy/test_section_34.py::test_no_connector_reads_a_trading_credential`
    - `tests/unit/deploy/test_section_34.py::test_no_rpc_endpoint_carries_a_key_in_its_url`
    - `tests/unit/deploy/test_section_34.py::test_the_alerting_package_reads_no_environment`
    - `tests/unit/deploy/test_section_34.py::test_the_environment_file_is_ignored_and_the_template_holds_no_live_secret`
    - `tests/unit/test_settings.py::test_a_configured_limit_is_read_with_its_window`
    - `tests/unit/test_settings.py::test_a_limit_that_forbids_everything_is_not_a_limit[-1-60.0]`
    - `tests/unit/test_settings.py::test_a_limit_that_forbids_everything_is_not_a_limit[0-60.0]`
    - `tests/unit/test_settings.py::test_a_limit_that_forbids_everything_is_not_a_limit[5--1.0]`
    - `tests/unit/test_settings.py::test_a_limit_that_forbids_everything_is_not_a_limit[5-0.0]`
    - `tests/unit/test_settings.py::test_a_limit_without_a_window_gets_the_documented_default`
    - `tests/unit/test_settings.py::test_a_password_full_of_punctuation_is_still_fully_masked[::@@::]`
    - `tests/unit/test_settings.py::test_a_password_full_of_punctuation_is_still_fully_masked[]weird[]`
    - `tests/unit/test_settings.py::test_a_password_full_of_punctuation_is_still_fully_masked[a:b:c]`
    - `tests/unit/test_settings.py::test_a_password_full_of_punctuation_is_still_fully_masked[p@ss:w@rd]`
    - `tests/unit/test_settings.py::test_a_password_full_of_punctuation_is_still_fully_masked[p@ssword]`
    - `tests/unit/test_settings.py::test_a_password_full_of_punctuation_is_still_fully_masked[with@at:and:colons]`
    - `tests/unit/test_settings.py::test_a_sub_second_window_is_allowed`
    - `tests/unit/test_settings.py::test_a_uri_with_no_password_is_unchanged`
    - `tests/unit/test_settings.py::test_a_user_with_no_password_keeps_its_at_sign`
    - `tests/unit/test_settings.py::test_a_wildcard_is_refused_where_configuration_is_read[ * ]`
    - `tests/unit/test_settings.py::test_a_wildcard_is_refused_where_configuration_is_read[*,https://a.example]`
    - `tests/unit/test_settings.py::test_a_wildcard_is_refused_where_configuration_is_read[*]`
    - `tests/unit/test_settings.py::test_a_wildcard_is_refused_where_configuration_is_read[https://a.example, *]`
    - `tests/unit/test_settings.py::test_no_origins_means_no_allowance_at_all`
    - `tests/unit/test_settings.py::test_origins_are_read_as_a_list`
    - `tests/unit/test_settings.py::test_something_that_is_not_a_uri_is_returned_unchanged`
    - `tests/unit/test_settings.py::test_string_formatting_is_masked_too`
    - `tests/unit/test_settings.py::test_the_password_and_the_s3_secret_are_masked`
    - `tests/unit/test_settings.py::test_the_values_themselves_are_untouched`
    - `tests/unit/test_settings.py::test_there_is_one_masked_spelling_not_a_masked_and_an_unmasked_one`
    - `tests/unit/test_settings.py::test_unlimited_is_a_state_that_must_be_chosen`
    - `tests/unit/test_settings.py::test_what_survives_the_mask_is_what_makes_it_readable`
- **Code:**
    - `src/channelflow/api/app.py`
    - `src/channelflow/api/main.py`
    - `src/channelflow/api/security.py`
    - `src/channelflow/settings.py`
- **Outcomes:** [[OUT-2026-09-14-implement-security-enforced]], [[OUT-2026-09-14-plan-security-enforced]], [[OUT-2026-09-14-spec-security-enforced]], [[OUT-2026-09-14-tasks-security-enforced]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
