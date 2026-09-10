"""What the producers produce.

# @trace: REQ-INFRA-003

Values, not messages: nothing here is routed, retried or serialized. They exist
so a producer can say what happened without naming who cares, which is the whole
of [[REQ-INFRA-003]].

This module imports no bus and the bus imports no event, so a live process can
publish the same three without reaching through the replay path.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.bars import Bar
from channelflow.channels import ChannelSnapshot
from channelflow.signals import Candidate


@dataclass(frozen=True)
class BarFinalized:
    """A window closed and cannot change.

    Published from `BarBuilder.on_final`, which is where "cannot change" is
    decided -- a bar still open is not a fact yet, and [[REQ-PIPE-001]] refuses
    to record one.
    """

    bar: Bar


@dataclass(frozen=True)
class ChannelFitted:
    """A channel was fitted on a bar.

    Carries the bar as well as the snapshot because a consumer that wants both
    would otherwise have to keep the last bar itself, and two consumers would
    keep it twice.
    """

    bar: Bar
    snapshot: ChannelSnapshot


@dataclass(frozen=True)
class CandidateUpdated:
    """A signal's state advanced.

    Named for what it is. The machine emits the same signal on every bar it is
    alive for, each time a more complete version of it, so `SignalOpened` would
    say something this does not mean -- the distinction [[REQ-PIPE-001]]'s
    recorder already had to make, in the one place a reader would otherwise
    count bars and call them signals.
    """

    candidate: Candidate
