# Data Model: Telegram Mini App

Nothing is stored.

## Launch data (`initData`)
A URL-encoded string: `query_id`, `user` (JSON), `auth_date` (Unix seconds), `hash`, and others.
**Verified** when `hash` equals `HMAC_SHA256(HMAC_SHA256("WebAppData", bot_token), data_check_string)`
where `data_check_string` is the other fields as `key=value`, sorted by key, joined by `\n`.

## `LaunchData` (verifier's result)
| field | meaning |
|---|---|
| `auth_date` | the launch's Unix time, seconds |
| `has_user` | whether a `user` field was present (the user itself is not kept) |

## `LaunchRefused.reason` (closed set)
`missing_hash` · `bad_signature` · `missing_auth_date` · `malformed` · `too_old` · `from_the_future`

## Authentication mode
`off` (default) · `required`.

## `start_param`
`base64url(path + query)` of a deep link, no padding; valid decoded forms: `/` or
`/chart/<venue>/<symbol>` with an optional `?query`.
