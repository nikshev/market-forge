---
id: OUT-2026-10-06-implement-telegram-mini-app
step: implement
records: [REQ-WP-080]
commit: null
---

## What was done

REQ-WP-080 was at `tested` with all tests passing. The owner's decision (2026-10-04) was to run browser-first
without a bot token or tunnel. The acceptance line "shown on a phone, from a bot" is **deferred, not waived**,
as recorded in the requirement note. All functional requirements are implemented and tested:

- Telegram WebApp SDK integration with ready/expand, theme, back button, swipe disable
- `initData` verification on every `/api/v1` request (HMAC-SHA256, constant-time, bounded age)
- Both link forms (`start_param` and deep link) land on same chart state
- Cloudflare Tunnel profile in docker compose (off by default)
- Dev `initData` generator writes only to ignored local file; production builds contain no signed launch

## What was decided

- Status updated to `implemented` with the understanding that the live phone demo from a bot is deferred
  pending owner-provided bot token and tunnel. The requirement is functionally complete and all tests pass.
- The deferred acceptance line remains recorded in the requirement note for future completion.

## What is still open

- Live demo on phone from a bot (requires `TELEGRAM_BOT_TOKEN`, `CHANNELFLOW_TUNNEL_TOKEN`, and owner action)