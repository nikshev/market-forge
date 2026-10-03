---
id: SPEC-126-telegram-mini-app
requirement: REQ-WP-080
speckit_path: specs/126-telegram-mini-app/spec.md
status: draft
---

## Summary

The existing overview and chart open inside Telegram as a Mini App, modelled on `/opt/lexa-reader`.
The page behaves as a Mini App (ready, expand, theme, back button, vertical swipes disabled) and is
unchanged outside Telegram; the API verifies Telegram's signature on every request when
authentication is required and stores nothing; a link carries the chart state in as a `start_param`
or a query string; and an optional compose profile puts a Cloudflare Tunnel in front of the web
service. Showing it on a phone needs a bot token and a tunnel the owner provides.

## Links

- Requirement: [[REQ-WP-080]]
- Built on: [[REQ-WP-064]], [[REQ-WP-074]], [[REQ-WP-075]]
