"""The context a record is bound to: config, input dataset, code commit (REQ-INFRA-007).

# @trace: REQ-INFRA-007

PRD §0.13 asks a result to be reproducible from a versioned dataset, a config and a code commit.
Each of the three is either **present or explicitly absent, never merely missing** (ADR-037): a
context with anything absent is *unnotarizable*, carries the reason, and hashes nothing -- a blank
commit folded into a hash would claim a provenance that does not exist.

**The config is an explicit list of fields, not a walk over the objects.** `SignalMachine` holds
its own mutable state (`candidate`, `_awaiting_zone_exit`) beside its parameters; a recursive walk
would put the state into the hash and give every bar a different one, binding nothing. So each
component has a list of configuration fields and a list of state fields, and a test enumerates
every field of every component and fails unless each is in exactly one list: a parameter added
tomorrow and not classified fails the suite rather than silently staying out of the hash.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass

from channelflow.backtest import BacktestRunner
from channelflow.channels.rolling_ols import RollingOLSChannel
from channelflow.experiments import config_hash, dataset_reference
from channelflow.experiments.hashing import UnhashableConfig
from channelflow.notary.scheme import Context
from channelflow.signals import SignalMachine
from channelflow.signals.rejection import CloseBackInside

#: What a component is configured with. A change to any of these changes what the pass computes.
CONFIG_FIELDS: dict[type, tuple[str, ...]] = {
    RollingOLSChannel: (
        "lookback",
        "min_window_bars",
        "quantile_low",
        "quantile_high",
        "weights",
        "bands",
        "band_sigmas",
    ),
    SignalMachine: (
        "zone_upper",
        "zone_lower",
        "zone_middle",
        "overshoot_tolerance",
        "min_quality",
        "slope_threshold",
        "expiry_bars",
        "opens",
        "detector",
    ),
    CloseBackInside: ("min_distance_pct_of_width",),
}

#: Configuration fields that hold another component rather than a value, so that an
#: unclassified one is named (and refused) instead of being repr'd or half-hashed.
COMPONENT_FIELDS: dict[type, tuple[str, ...]] = {SignalMachine: ("detector",)}

#: What a component remembers between bars. Never part of the config.
STATE_FIELDS: dict[type, tuple[str, ...]] = {
    RollingOLSChannel: (),
    SignalMachine: ("candidate", "_awaiting_zone_exit"),
    CloseBackInside: (),
}

_COMMIT = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class NotaryContext:
    config_hash: str
    dataset_ref: str
    dataset_snapshot_id: int
    code_commit: str
    #: Why the context cannot be hashed into a record, or `None` when it can.
    reason: str | None

    @property
    def notarizable(self) -> bool:
        return self.reason is None

    def as_scheme(self) -> Context:
        return Context(
            config_hash=self.config_hash, dataset_ref=self.dataset_ref, code_commit=self.code_commit
        )


def _component(obj: object) -> dict[str, object]:
    cls = type(obj)
    if cls not in CONFIG_FIELDS:
        raise UnhashableConfig(
            f"{cls.__name__} has no classified configuration fields; add it to "
            "channelflow.notary.context.CONFIG_FIELDS and STATE_FIELDS"
        )
    out: dict[str, object] = {"class": cls.__name__}
    for name in CONFIG_FIELDS[cls]:
        value = getattr(obj, name)
        # A component inside a component (the machine's detector) is described, not repr'd.
        out[name] = _component(value) if name in COMPONENT_FIELDS.get(cls, ()) else value
    return out


def pass_config(runner: BacktestRunner, *, gap_threshold: int) -> dict[str, object]:
    """The configuration of the pass that produced a record, as a mapping `config_hash` accepts."""
    return {
        "channel": _component(runner.channel),
        "machine": _component(runner.machine),
        "gap_threshold": gap_threshold,
    }


def build_context(
    runner: BacktestRunner,
    *,
    gap_threshold: int,
    dataset: tuple[int, str],
    code_commit: str | None,
    code_dirty: str | None,
) -> NotaryContext:
    """Assemble the context once per pass; anything absent makes it unnotarizable."""
    snapshot_id, content_hash = dataset
    reason: str | None = None
    commit = ""
    digest = ""
    ref = ""

    if code_commit is None or not _COMMIT.match(code_commit):
        reason = "code commit is absent or is not 40 lowercase hexadecimal digits"
    elif code_dirty != "false":
        reason = (
            f"the working tree the image was built from is dirty or unknown ({code_dirty!r}); "
            "a commit from such a tree names code that exists nowhere"
        )
    else:
        commit = code_commit

    try:
        digest = config_hash(pass_config(runner, gap_threshold=gap_threshold))
    except (UnhashableConfig, TypeError) as error:
        reason = reason or f"the pass config cannot be hashed: {error}"
        digest = ""

    try:
        ref = dataset_reference({"bars": (snapshot_id, content_hash)})
    except ValueError as error:
        reason = reason or f"the input dataset has no usable reference: {error}"

    if reason is not None:
        commit = ""
    return NotaryContext(
        config_hash=digest,
        dataset_ref=ref,
        dataset_snapshot_id=snapshot_id,
        code_commit=commit,
        reason=reason,
    )


__all__ = [
    "CONFIG_FIELDS",
    "STATE_FIELDS",
    "NotaryContext",
    "build_context",
    "dataclasses",
    "pass_config",
]
