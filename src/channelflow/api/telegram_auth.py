"""Who may read the API when it is opened from Telegram (REQ-WP-080).

# @trace: REQ-WP-080

A Telegram Mini App is handed `initData`: a URL-encoded string of fields, signed for one bot. This
module verifies it and gates the API on it. Three decisions shape everything below.

**The launch is verified on every request and nothing is stored.** `lexa-reader` exchanges
`initData`
for tokens kept in a database. This API has no users and serves read-only public market data, so a
token, a refresh path and a user row would protect nothing they are worth. The consequence is that
identity is not needed: only that Telegram signed this launch for this bot. So the user is never
parsed, kept or logged -- `LaunchData` has no field for it.

**The gate is access control, not secrecy.** It stops a public address being a free read API and
makes
"opens inside Telegram" mean something. A captured launch can be replayed until it ages out
(`max_age_seconds`); for public data that is accepted, stated, and bounded.

**It is a prefix rule, in one middleware.** Every HTTP route under `/api/v1/` and every websocket
under
`/ws/` is covered, including the one added next month. A per-route dependency would cover the routes
someone remembered; REQ-WP-072 found a naive walk of an app's routes reaches 5 of 17.

The algorithm is Telegram's: ``secret = HMAC_SHA256("WebAppData", bot_token)``, ``hash =
HMAC_SHA256(secret, data_check_string)`` where the data-check-string is every field but `hash`, as
`key=value`, sorted, joined by newlines. It exists three times in this repository -- here, in the
TypeScript dev signer, and in the `openssl` commands that made `tests/vectors/` -- and each is
checked
against the others' answers, never only its own.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import parse_qsl

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

#: Why a launch was refused. A closed set: it is what the 401 body says and what a test pins. A
#: changed
#: field and a wrong token are both `bad_signature`, deliberately -- telling them apart would tell
#: an
#: attacker which half of a guess was right.
REASONS = (
    "missing_hash",
    "bad_signature",
    "missing_auth_date",
    "malformed",
    "too_old",
    "from_the_future",
)

#: Telegram's clock and this host's may differ by this much, either way.
SKEW_SECONDS = 60

#: A launch is a few hundred characters. Anything near this is not one, and is refused before it is
#: parsed or hashed.
MAX_LAUNCH_CHARS = 8192

SCHEME = "tma "


class LaunchRefused(Exception):
    """A launch that is not what Telegram signed. Carries a reason and nothing else.

    The message is the reason alone: no token, no hash, no field of the launch -- anything put here
    can
    end up in a log.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class LaunchData:
    """What a verified launch tells us. Deliberately no user: identity is not used, so not kept."""

    auth_date: int
    has_user: bool


def verify_init_data(
    init_data: str, bot_token: str, *, now: float, max_age_seconds: int = 86_400
) -> LaunchData:
    """Verify one launch, or raise `LaunchRefused`.

    Pure: the clock is an argument, there is no I/O. An empty token is refused rather than used as a
    key -- HMAC with an empty key works, and would accept anyone who signed with an empty one.
    """
    if not bot_token.strip():
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured; there is nothing to verify against")
    if len(init_data) > MAX_LAUNCH_CHARS:
        raise LaunchRefused("malformed")

    pairs = parse_qsl(init_data, keep_blank_values=True)
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        # Two `auth_date`s, say: which one was signed is not a question to answer by picking one.
        raise LaunchRefused("malformed")
    fields = dict(pairs)

    provided = fields.pop("hash", None)
    if not provided:
        raise LaunchRefused("missing_hash")

    check_string = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    # Bytes, not str: `compare_digest` raises on a non-ASCII str, and a refusal must not be a 500.
    if not hmac.compare_digest(expected.encode(), provided.encode()):
        raise LaunchRefused("bad_signature")

    raw_date = fields.get("auth_date")
    if raw_date is None:
        raise LaunchRefused("missing_auth_date")
    try:
        auth_date = int(raw_date)
    except ValueError:
        raise LaunchRefused("malformed") from None

    if now - auth_date > max_age_seconds:
        raise LaunchRefused("too_old")
    if auth_date - now > SKEW_SECONDS:
        raise LaunchRefused("from_the_future")
    return LaunchData(auth_date=auth_date, has_user="user" in fields)


class TelegramGate:
    """The configured check: a token, a maximum age and a clock."""

    def __init__(
        self,
        *,
        bot_token: str,
        max_age_seconds: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not bot_token.strip():
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is not configured; refusing to build a gate that could not "
                "verify anything and would serve open"
            )
        self._token = bot_token
        self._max_age = max_age_seconds
        self._clock = clock

    def check(self, authorization: str | None) -> LaunchData:
        """Verify an `Authorization: tma <initData>` header value."""
        if not authorization:
            raise LaunchRefused("missing_hash")
        if not authorization.startswith(SCHEME):
            raise LaunchRefused("malformed")
        return verify_init_data(
            authorization[len(SCHEME) :],
            self._token,
            now=self._clock(),
            max_age_seconds=self._max_age,
        )


def _in_scope(scope: Scope) -> bool:
    path = str(scope.get("path", ""))
    if scope["type"] == "http":
        return path == "/api/v1" or path.startswith("/api/v1/")
    if scope["type"] == "websocket":
        return path.startswith("/ws/")
    return False


class TelegramAuthMiddleware:
    """Refuses an unsigned caller on everything under `/api/v1/` and `/ws/`.

    Pure ASGI rather than `BaseHTTPMiddleware`, because one class has to cover both an HTTP request
    and
    a websocket. A websocket is **closed**, not authenticated: a browser cannot send an
    `Authorization`
    header on one, the page does not use it, and launch data in the URL would land in logs.
    """

    def __init__(self, app: ASGIApp, *, gate: TelegramGate) -> None:
        self.app = app
        self.gate = gate

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not _in_scope(scope):
            await self.app(scope, receive, send)
            return

        if scope["type"] == "websocket":
            await receive()  # the `websocket.connect` event, which a close must answer
            await send({"type": "websocket.close", "code": 1008})
            return

        try:
            self.gate.check(_authorization(scope))
        except LaunchRefused as refused:
            response = JSONResponse(
                {"reason": refused.reason}, status_code=401, headers={"WWW-Authenticate": "tma"}
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _authorization(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            # latin-1 maps every byte to a character, so a header that is not UTF-8 cannot raise
            # here.
            return str(value.decode("latin-1"))
    return None


__all__ = [
    "REASONS",
    "LaunchData",
    "LaunchRefused",
    "TelegramAuthMiddleware",
    "TelegramGate",
    "verify_init_data",
]
