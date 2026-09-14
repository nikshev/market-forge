# Phase 1 — Data model

## `Settings` (modified, frozen)

Fields are unchanged — `catalog_uri`, `warehouse`, `storage` — and gain two
settings plus a rendering rule.

| new field | type | meaning |
|---|---|---|
| `allowed_origins` | `tuple[str, ...]` | CORS origins; empty means no allowance at all |
| `rate_limit` | `RateLimit \| None` | `None` means unlimited, and must be chosen rather than defaulted into |

**Rendering rule.** `__repr__` and `__str__` are the same masked text:

- `catalog_uri` keeps scheme, user, host, port and database; the password becomes
  `***`. A URI with no password is unchanged.
- `storage['s3.secret-access-key']` renders as `***`.
- `storage['s3.access-key-id']` is an identifier, not a secret, and is shown.
- Every other field is shown.

A mask that hid everything would push somebody to log the fields one by one, so
what stays visible is part of the contract, not an oversight.

## `RateLimit` (frozen)

| field | type | meaning |
|---|---|---|
| `requests` | `int` | how many are allowed in a window; must be > 0 |
| `window_seconds` | `float` | the window's length; must be > 0 |

**Validation**: a limit of zero is refused. "Allow nothing" is not a rate limit,
and configuring it by accident would take the API down in a way that reads as a
bug in the API.

## `Exposure`

Not a runtime type — the shape the compose test reads.

| field | meaning |
|---|---|
| service | the compose service |
| published | the host side of its port mapping |
| bound | the address it binds, or `all interfaces` |
| deliberate | whether that is intended, and where that intent is recorded |

## Exceptions

| type | means |
|---|---|
| `WildcardOrigin` | CORS was configured with `*`; refused at startup, never warned about |
| `InvalidRateLimit` | a limit or window that is not positive |
| `MissingConfiguration` | unchanged — reused rather than duplicated |

## Route rule

A route is permitted when its methods are a subset of `{GET, HEAD}`, or it is a
websocket route, or it appears in the authenticated-route allow-list — which is
**empty today**, and is the seam a future write route must pass through.

`HEAD` is in the permitted set because Starlette adds it to every `GET` route;
excluding it would fail on four documentation routes nobody wrote.
