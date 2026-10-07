---
id: REQ-WP-080
title: "The overview and the chart open as a Telegram Mini App, authenticated by Telegram"
type: work-package
prd_ref: "US-002, §26.1, §27.1, §27.5, §0 secrets rule"
prd_lines: "255-257, 4319-4335, 4388-4405, 4826-4830"
phase: null
status: implemented
depends_on: [REQ-WP-064, REQ-WP-074, REQ-WP-075]
tags: [telegram, web, mini-app]
hard_gated: false
---

## Requirement

PRD US-002: "as a user I want to press a button in Telegram and open the chart exactly at the
signal's timestamp with all active overlays." §27.1 gives the routes and §26 the alert whose button
carries the link. Today the link opens a browser tab. This requirement makes the same pages open
**inside Telegram** as a Mini App — the overview (`/`) and the chart (`/chart/<venue>/<symbol>`),
unchanged in what they show — the way `lexa-reader` runs, so the product can be shown on a phone
from a bot.

Four things have to be true for that to be more than a URL pasted into a WebView:

1. **The page behaves as a Mini App.** It loads Telegram's WebApp SDK, tells Telegram it is ready and
   expands, follows Telegram's light/dark theme, uses Telegram's own back button to return from a
   chart to the overview, and stops Telegram's vertical-swipe gesture from swallowing touches on the
   chart (the one thing `lexa-reader` found out the hard way). Outside Telegram the page works exactly
   as it does today.
2. **The API knows who is asking.** Telegram signs the launch data (`initData`). The API verifies it —
   HMAC-SHA256 with the key `HMAC("WebAppData", bot_token)` over the sorted `key=value` lines, compared
   in constant time, with a bounded age — on every `/api/v1` request when authentication is required.
   The bot token comes from the environment or a secret and is never in the repository (PRD's secrets
   rule). When authentication is required and no token is configured the service **refuses to start**
   rather than serve open.
3. **A link carries the chart state in.** A button opened with Telegram's `start_param` (the form a
   `t.me/<bot>/<app>?startapp=…` link takes) and a button opened with the full deep link both land on the
   same chart state: venue, symbol, timeframe, instant, mode.
4. **It is reachable at a stable HTTPS URL.** Telegram requires HTTPS. The stack gains an optional,
   off-by-default `telegram` profile with a Cloudflare Tunnel in front of the web service — no new host
   ports — and a section of `docs/deployment.md` says how to create the bot, the tunnel and set the URL.

Not here: payments, publishing the Mini App to Telegram's directory, notifying from the bot (the
alert sender exists, [[REQ-WP-008]]), and the on-chain link an alert may later carry
([[REQ-INFRA-008]]).

## Acceptance

- **Verification, against known answers.** A valid `initData` is accepted. A changed field, a wrong bot
  token, a missing hash, a missing `auth_date` and an `auth_date` older than the configured maximum or
  more than a minute in the future are each refused, each for its own reason. The signature is
  computed by an **independent implementation** (the dev tool, in another language) and the two agree:
  a verifier checked only against its own signer proves nothing.
- **The API gate.** With authentication required, a request without a valid `Authorization: tma <initData>`
  header gets 401 and **no market data**; a valid one gets today's response unchanged. With it off (the
  local default) nothing changes. `required` with no token configured refuses to start. `/readyz` and
  `/metrics` are not behind it, and are not reachable through the tunnel.
- **The page in Telegram, with a fake SDK.** Opened with a stand-in for `window.Telegram.WebApp`, the
  page calls ready and expand once, applies the theme parameters, shows the back button on a chart and
  not on the overview (and the button returns to the overview), disables vertical swipes, and attaches
  `initData` to every API request. Without the object it throws nothing and sends no header.
- **Both link forms land on the same state.** A `start_param` and the equivalent query string produce the
  same venue, symbol, timeframe, instant and mode (a test over both parsers).
- **No dev credentials in a production build.** The dev `initData` generator writes only to an ignored
  local file, and a production build is checked to contain no signed `initData`.
- **The stack and the docs.** `docker compose --profile telegram config` is valid and starts `cloudflared`
  pointing at the web service; without the profile nothing new runs; every new environment variable is in
  `.env.example` and the deployment document (the repository's existing documents test).
- **Shown, with the date.** On a phone, in Telegram, from a bot: the overview opens, a market opens its
  chart, the timeframe selector and the channel overlay work. Recorded in the outcome note with the date
  and the URL used. This needs a bot token and a tunnel the owner provides; it is the one item no test
  can stand in for.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-126-telegram-mini-app]]
- **Tests:**
    - `tests/unit/api/test_telegram_auth.py::test_a_hash_that_is_not_ascii_is_a_bad_signature_and_not_an_error`
    - `tests/unit/api/test_telegram_auth.py::test_a_launch_a_minute_ahead_is_accepted_and_sixty_one_seconds_ahead_is_refused`
    - `tests/unit/api/test_telegram_auth.py::test_a_launch_exactly_the_maximum_age_is_accepted_and_one_second_older_is_refused`
    - `tests/unit/api/test_telegram_auth.py::test_a_launch_of_absurd_size_is_refused_before_it_is_parsed`
    - `tests/unit/api/test_telegram_auth.py::test_a_launch_that_names_a_field_twice_is_malformed_not_resolved_by_picking_one`
    - `tests/unit/api/test_telegram_auth.py::test_a_malformed_user_field_is_still_a_signed_launch`
    - `tests/unit/api/test_telegram_auth.py::test_a_signed_launch_with_no_user_is_accepted_and_says_so`
    - `tests/unit/api/test_telegram_auth.py::test_an_empty_token_is_refused_not_used_as_a_key`
    - `tests/unit/api/test_telegram_auth.py::test_each_vector_gets_the_verdict_openssl_signed_it_for[auth_date_not_a_number]`
    - `tests/unit/api/test_telegram_auth.py::test_each_vector_gets_the_verdict_openssl_signed_it_for[field_changed]`
    - `tests/unit/api/test_telegram_auth.py::test_each_vector_gets_the_verdict_openssl_signed_it_for[from_the_future]`
    - `tests/unit/api/test_telegram_auth.py::test_each_vector_gets_the_verdict_openssl_signed_it_for[no_auth_date]`
    - `tests/unit/api/test_telegram_auth.py::test_each_vector_gets_the_verdict_openssl_signed_it_for[no_hash]`
    - `tests/unit/api/test_telegram_auth.py::test_each_vector_gets_the_verdict_openssl_signed_it_for[stale]`
    - `tests/unit/api/test_telegram_auth.py::test_each_vector_gets_the_verdict_openssl_signed_it_for[valid]`
    - `tests/unit/api/test_telegram_auth.py::test_each_vector_gets_the_verdict_openssl_signed_it_for[valid_no_user]`
    - `tests/unit/api/test_telegram_auth.py::test_each_vector_gets_the_verdict_openssl_signed_it_for[wrong_token]`
    - `tests/unit/api/test_telegram_auth.py::test_no_refusal_names_the_token_or_the_hash[case0]`
    - `tests/unit/api/test_telegram_auth.py::test_no_refusal_names_the_token_or_the_hash[case1]`
    - `tests/unit/api/test_telegram_auth.py::test_no_refusal_names_the_token_or_the_hash[case2]`
    - `tests/unit/api/test_telegram_auth.py::test_no_refusal_names_the_token_or_the_hash[case3]`
    - `tests/unit/api/test_telegram_auth.py::test_no_refusal_names_the_token_or_the_hash[case4]`
    - `tests/unit/api/test_telegram_auth.py::test_no_refusal_names_the_token_or_the_hash[case5]`
    - `tests/unit/api/test_telegram_auth.py::test_no_refusal_names_the_token_or_the_hash[case6]`
    - `tests/unit/api/test_telegram_auth.py::test_of_nine_launches_two_are_accepted_and_the_seven_refused_give_six_reasons`
    - `tests/unit/api/test_telegram_auth.py::test_the_maximum_age_is_configuration_not_a_constant`
    - `tests/unit/api/test_telegram_auth.py::test_the_result_carries_no_identity`
    - `tests/unit/api/test_telegram_gate.py::test_a_gate_with_no_token_refuses_to_exist`
    - `tests/unit/api/test_telegram_gate.py::test_a_header_that_is_not_a_signed_launch_is_a_401_never_a_500[blank-payload]`
    - `tests/unit/api/test_telegram_gate.py::test_a_header_that_is_not_a_signed_launch_is_a_401_never_a_500[empty]`
    - `tests/unit/api/test_telegram_gate.py::test_a_header_that_is_not_a_signed_launch_is_a_401_never_a_500[enormous]`
    - `tests/unit/api/test_telegram_gate.py::test_a_header_that_is_not_a_signed_launch_is_a_401_never_a_500[garbage]`
    - `tests/unit/api/test_telegram_gate.py::test_a_header_that_is_not_a_signed_launch_is_a_401_never_a_500[not-utf8]`
    - `tests/unit/api/test_telegram_gate.py::test_a_header_that_is_not_a_signed_launch_is_a_401_never_a_500[other-scheme]`
    - `tests/unit/api/test_telegram_gate.py::test_a_header_that_is_not_a_signed_launch_is_a_401_never_a_500[scheme-only]`
    - `tests/unit/api/test_telegram_gate.py::test_a_signed_request_gets_exactly_what_an_unprotected_app_returns`
    - `tests/unit/api/test_telegram_gate.py::test_a_stale_signed_launch_is_refused_at_the_gate_for_the_right_reason`
    - `tests/unit/api/test_telegram_gate.py::test_another_scheme_is_malformed_and_not_a_bad_signature[Basic]`
    - `tests/unit/api/test_telegram_gate.py::test_another_scheme_is_malformed_and_not_a_bad_signature[Bearer]`
    - `tests/unit/api/test_telegram_gate.py::test_another_scheme_is_malformed_and_not_a_bad_signature[TMA]`
    - `tests/unit/api/test_telegram_gate.py::test_another_scheme_is_malformed_and_not_a_bad_signature[tma:]`
    - `tests/unit/api/test_telegram_gate.py::test_every_data_route_refuses_an_unsigned_request_and_returns_no_data`
    - `tests/unit/api/test_telegram_gate.py::test_readiness_and_metrics_answer_without_a_launch`
    - `tests/unit/api/test_telegram_gate.py::test_the_walk_reaches_every_data_route_the_router_registers`
    - `tests/unit/api/test_telegram_gate.py::test_the_websocket_is_refused_when_authentication_is_required`
    - `tests/unit/api/test_telegram_gate.py::test_the_websocket_still_works_with_authentication_off`
    - `tests/unit/api/test_telegram_gate.py::test_with_authentication_off_nothing_changes_for_anyone`
    - `tests/unit/deploy/test_public_surface.py::test_everything_served_under_the_proxied_prefix_is_a_data_route`
    - `tests/unit/deploy/test_public_surface.py::test_nginx_proxies_exactly_one_location_and_it_is_api`
    - `tests/unit/deploy/test_public_surface.py::test_the_routes_that_are_not_gated_are_outside_the_proxied_prefix[/metrics]`
    - `tests/unit/deploy/test_public_surface.py::test_the_routes_that_are_not_gated_are_outside_the_proxied_prefix[/readyz]`
    - `tests/unit/deploy/test_public_surface.py::test_the_routes_that_are_not_gated_are_outside_the_proxied_prefix[/ws/market]`
    - `tests/unit/deploy/test_telegram_profile.py::test_every_new_variable_is_in_the_example_and_the_document[CHANNELFLOW_TELEGRAM_AUTH]`
    - `tests/unit/deploy/test_telegram_profile.py::test_every_new_variable_is_in_the_example_and_the_document[CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS]`
    - `tests/unit/deploy/test_telegram_profile.py::test_every_new_variable_is_in_the_example_and_the_document[CHANNELFLOW_TUNNEL_PROTOCOL]`
    - `tests/unit/deploy/test_telegram_profile.py::test_every_new_variable_is_in_the_example_and_the_document[CHANNELFLOW_TUNNEL_TOKEN]`
    - `tests/unit/deploy/test_telegram_profile.py::test_nothing_else_is_in_the_profile`
    - `tests/unit/deploy/test_telegram_profile.py::test_only_the_api_is_given_the_bot_token`
    - `tests/unit/deploy/test_telegram_profile.py::test_the_api_is_told_the_mode_the_age_and_the_token`
    - `tests/unit/deploy/test_telegram_profile.py::test_the_document_says_how_to_start_it_and_what_the_gate_is`
    - `tests/unit/deploy/test_telegram_profile.py::test_the_example_carries_no_token_for_the_tunnel_or_the_bot`
    - `tests/unit/deploy/test_telegram_profile.py::test_the_image_is_pinned_to_a_version_and_not_latest`
    - `tests/unit/deploy/test_telegram_profile.py::test_the_token_has_an_empty_default_and_is_not_required`
    - `tests/unit/deploy/test_telegram_profile.py::test_the_transport_defaults_to_http2_because_this_host_blocks_quic`
    - `tests/unit/deploy/test_telegram_profile.py::test_the_tunnel_exists_and_belongs_to_the_telegram_profile`
    - `tests/unit/deploy/test_telegram_profile.py::test_the_tunnel_publishes_no_port`
    - `tests/unit/deploy/test_telegram_profile.py::test_the_tunnel_waits_for_the_web_service`
    - `tests/unit/test_settings_telegram.py::test_a_maximum_age_that_is_not_a_positive_whole_number_is_refused[-5]`
    - `tests/unit/test_settings_telegram.py::test_a_maximum_age_that_is_not_a_positive_whole_number_is_refused[0]`
    - `tests/unit/test_settings_telegram.py::test_a_maximum_age_that_is_not_a_positive_whole_number_is_refused[1.5]`
    - `tests/unit/test_settings_telegram.py::test_a_maximum_age_that_is_not_a_positive_whole_number_is_refused[soon]`
    - `tests/unit/test_settings_telegram.py::test_any_other_mode_is_refused_not_guessed[1]`
    - `tests/unit/test_settings_telegram.py::test_any_other_mode_is_refused_not_guessed[REQUIRED]`
    - `tests/unit/test_settings_telegram.py::test_any_other_mode_is_refused_not_guessed[on]`
    - `tests/unit/test_settings_telegram.py::test_any_other_mode_is_refused_not_guessed[optional]`
    - `tests/unit/test_settings_telegram.py::test_any_other_mode_is_refused_not_guessed[true]`
    - `tests/unit/test_settings_telegram.py::test_authentication_is_off_unless_it_is_asked_for`
    - `tests/unit/test_settings_telegram.py::test_required_with_a_token_is_accepted_and_the_age_is_read`
    - `tests/unit/test_settings_telegram.py::test_required_without_a_token_stops_the_service_and_names_the_variable[   ]`
    - `tests/unit/test_settings_telegram.py::test_required_without_a_token_stops_the_service_and_names_the_variable[None]`
    - `tests/unit/test_settings_telegram.py::test_required_without_a_token_stops_the_service_and_names_the_variable[]`
    - `tests/unit/test_settings_telegram.py::test_the_token_never_appears_in_the_settings_text`
- **Code:**
    - `apps/web/src/Chart.tsx`
    - `apps/web/src/__tests__/buildHasNoInitData.test.ts`
    - `apps/web/src/__tests__/chartTheme.test.ts`
    - `apps/web/src/__tests__/startParam.test.ts`
    - `apps/web/src/__tests__/telegram.test.ts`
    - `apps/web/src/__tests__/telegramVectors.test.ts`
    - `apps/web/src/api.ts`
    - `apps/web/src/main.tsx`
    - `apps/web/src/startParam.ts`
    - `apps/web/src/telegram.ts`
    - `apps/web/src/theme.ts`
    - `src/channelflow/api/app.py`
    - `src/channelflow/api/main.py`
    - `src/channelflow/api/telegram_auth.py`
    - `src/channelflow/settings.py`
- **Outcomes:** [[OUT-2026-10-03-implement-telegram-mini-app]], [[OUT-2026-10-03-plan-telegram-mini-app]], [[OUT-2026-10-03-spec-telegram-mini-app]], [[OUT-2026-10-03-tasks-telegram-mini-app]], [[OUT-2026-10-06-implement-telegram-mini-app]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Reference implementation: `/opt/lexa-reader` (`web/src/telegram.ts`, `backend/app/auth/telegram.py`,
`docs/DEPLOY.md`, `web/scripts/gen-dev-initdata.mjs`). It exchanges `initData` for tokens once; this
requirement verifies it per request instead, because the API here has no user store and a read-only
market view needs none — a decision for the plan to confirm or reverse.

### 2026-10-04: browser first, no token — the owner's decision

The owner chose to run the product in a browser for now, without a bot token or a tunnel. That is already
supported and is the default: `CHANNELFLOW_TELEGRAM_AUTH` is `off`, the page behaves exactly as it does
outside Telegram, and the web service is reachable at `http://127.0.0.1:8081/` on the host (from another
machine, through an SSH tunnel: `ssh -L 8081:127.0.0.1:8081 <host>`). It is bound to loopback on purpose:
with authentication off the API is open, and nothing here opens it to the network.

So the acceptance line "shown on a phone, from a bot" is **deferred, not waived**: the status stays `tested`.
The page's heading and title now say "Market Forge", the product's name.
