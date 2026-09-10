"""Filling the canonical plane from a replay.

# @trace: REQ-PIPE-001

PRD §25.1 has two modes, live and replay. This is the replay one, wired to the
tables §29.B names: trades in, finalized bars out; bars in, channel snapshots
and signals out. Every one of those tables was empty until this existed, and
each of [[REQ-STORE-001]], [[REQ-TBL-001]] and [[REQ-STORE-002]] recorded that
in its own open questions.

A live process attaching the same sinks to a running connector is deployment
work. The sinks are the ones the producing subsystems already offer --
`BarBuilder.on_final` and the runner's observers -- so there is no second path
for a live feed to take.
"""

from channelflow.pipeline.replay import (
    ChannelRecorder,
    ExtremumRecorder,
    MixedSeries,
    Recording,
    SignalRecorder,
    record_bars,
    record_replay,
    watermark,
)
from channelflow.pipeline.study import NothingScorable, StudyResult, run_study

__all__ = [
    "NothingScorable",
    "StudyResult",
    "run_study",
    "ChannelRecorder",
    "ExtremumRecorder",
    "MixedSeries",
    "Recording",
    "SignalRecorder",
    "record_bars",
    "record_replay",
    "watermark",
]
