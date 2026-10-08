"""The worker's notary configuration (REQ-INFRA-007).

# @trace: REQ-INFRA-007

Off unless switched on, and when on, explicit: there is no default epoch, because a default of
"when the process started" would move on every restart and silently leave a hole. The commit comes
from the image build, never from `git` at run time (the container has none) and is carried as
*absent* when the build did not provide it -- the context then refuses to hash a blank.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass

ENABLED = "CHANNELFLOW_NOTARY_ENABLED"
FROM = "CHANNELFLOW_NOTARY_FROM"
CODE_COMMIT = "CHANNELFLOW_CODE_COMMIT"
CODE_DIRTY = "CHANNELFLOW_CODE_DIRTY"

_TRUE = {"1", "true", "yes", "on"}


class ConfigError(ValueError):
    """A variable is missing or malformed; the message names it."""


@dataclass(frozen=True)
class WorkerNotary:
    #: Records whose bar closed before this instant are not registered (no backfill).
    from_ns: int
    code_commit: str | None
    code_dirty: str | None


def parse_instant_ns(text: str, *, name: str) -> int:
    try:
        parsed = dt.datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError as error:
        raise ConfigError(f"{name} is not an ISO-8601 instant: {text!r}") from error
    if parsed.tzinfo is None:
        raise ConfigError(f"{name} must carry a timezone (a trailing Z or +00:00): {text!r}")
    return int(parsed.timestamp()) * 1_000_000_000


def parse_duration_s(text: str, *, name: str) -> float:
    """`30m`, `6h`, `1d`, or a plain number of seconds: the grammar every loop here uses."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    raw = text.strip()
    try:
        if raw and raw[-1] in units:
            return float(raw[:-1]) * units[raw[-1]]
        return float(raw)
    except ValueError as error:
        raise ConfigError(f"{name} is not a duration like 30, 5m, 1h or 1d: {text!r}") from error


def worker_notary_from_env(env: Mapping[str, str]) -> WorkerNotary | None:
    """`None` when the notary is off; otherwise what the pass needs to register records."""
    if env.get(ENABLED, "").strip().lower() not in _TRUE:
        return None
    raw = env.get(FROM, "").strip()
    if not raw:
        raise ConfigError(f"{FROM} must be set when {ENABLED} is on (an ISO-8601 instant)")
    return WorkerNotary(
        from_ns=parse_instant_ns(raw, name=FROM),
        code_commit=env.get(CODE_COMMIT, "").strip() or None,
        code_dirty=env.get(CODE_DIRTY, "").strip() or None,
    )
