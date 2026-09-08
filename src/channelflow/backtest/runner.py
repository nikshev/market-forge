"""Bar replay through the production signal engine.

# @trace: REQ-WP-010

This module owns no strategy logic. PRD section 25.2 says to avoid a separate
backtest implementation, and Constitution Principle VII says live and replay are
the same code -- so the runner imports `RollingOLSChannel` and `SignalMachine`
and does nothing but feed them.

That claim is checked rather than asserted: `test_parity.py` drives the engine
directly over the same bars and demands identical candidate paths. Inlining even
one transition rule here makes that test fail.

There is no clock. Every timestamp comes from the bars, which is what makes a
run today and a run tomorrow the same run.

Refitting the channel at every bar is O(n * lookback) and plainly wasteful. PRD
section 0.14 puts correctness before performance, and an incremental fit is an
optimisation worth making once there is something to measure.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from channelflow.backtest.report import BacktestReport
from channelflow.bars import Bar
from channelflow.channels import ChannelFitError, RollingOLSChannel
from channelflow.signals import TERMINAL, CandidateState, SignalMachine, Transition


@dataclass
class BacktestRunner:
    """One pass over one bar series under one configuration."""

    channel: RollingOLSChannel = field(default_factory=RollingOLSChannel)
    machine: SignalMachine = field(default_factory=SignalMachine)

    def run(self, bars: list[Bar]) -> BacktestReport:
        """Replay `bars`. Repeatable: the same input gives the same report.

        The machine is copied rather than driven in place. It carries the live
        candidate, so a second run over the same bars would otherwise begin
        mid-lifecycle and report something else -- and the caller's machine
        would come back holding a candidate from history.
        """
        machine = deepcopy(self.machine)

        # A bar still forming can still change, so only finalized bars replay
        # (FR-001). Sorting is what makes arrival order irrelevant.
        ordered = sorted((b for b in bars if b.is_final), key=lambda b: b.close_time_ns)

        transitions: list[Transition] = []
        # A terminal candidate is replaced, not extended: `history` restarts at
        # length one. Tracking a running index into it silently swallowed every
        # second candidate's opening transition. `opened_at_ns` is a sound
        # identity because FR-018 forbids reopening on the bar that closed one.
        current_open_ns: int | None = None
        seen_history = 0

        skipped = 0
        opened = 0
        confirmed = 0
        by_direction: dict[str, int] = {}
        by_boundary: dict[str, int] = {}
        terminal_reasons: dict[str, int] = {}

        for i, bar in enumerate(ordered):
            try:
                # as_of is this bar: REQ-WP-006 refuses to look past it, so the
                # loop cannot leak the future even if written carelessly.
                snapshot = self.channel.fit(ordered[: i + 1], as_of_ns=bar.close_time_ns)
            except ChannelFitError:
                skipped += 1
                snapshot = None

            candidate = machine.on_bar(bar, snapshot)
            if candidate is None:
                continue

            if candidate.opened_at_ns != current_open_ns:
                current_open_ns = candidate.opened_at_ns
                seen_history = 0
                opened += 1
                by_direction[candidate.direction] = by_direction.get(candidate.direction, 0) + 1
                by_boundary[candidate.boundary] = by_boundary.get(candidate.boundary, 0) + 1

            for transition in candidate.history[seen_history:]:
                transitions.append(transition)
                if transition.to_state is CandidateState.CONFIRMED:
                    confirmed += 1
                if transition.to_state in TERMINAL:
                    terminal_reasons[transition.reason] = (
                        terminal_reasons.get(transition.reason, 0) + 1
                    )
            seen_history = len(candidate.history)

        return BacktestReport(
            bars_replayed=len(ordered),
            bars_skipped_no_channel=skipped,
            first_bar_close_ns=ordered[0].close_time_ns if ordered else 0,
            last_bar_close_ns=ordered[-1].close_time_ns if ordered else 0,
            candidates_opened=opened,
            by_direction=by_direction,
            by_boundary=by_boundary,
            confirmed=confirmed,
            terminal_reasons=terminal_reasons,
            transitions=tuple(transitions),
            configuration=self._configuration(),
        )

    def _configuration(self) -> dict[str, str]:
        """PRD section 13.11 calls the zone bounds research defaults. Two runs
        whose reports cannot be told apart are two runs whose difference cannot
        be attributed to anything."""
        return {
            "channel_model": self.channel.__class__.__name__,
            "channel_lookback": str(self.channel.lookback),
            "quantile_low": str(self.channel.quantile_low),
            "quantile_high": str(self.channel.quantile_high),
            "zone_upper": str(self.machine.zone_upper),
            "zone_lower": str(self.machine.zone_lower),
            "zone_middle": str(self.machine.zone_middle),
            "min_quality": str(self.machine.min_quality),
            "slope_threshold": str(self.machine.slope_threshold),
            "expiry_bars": str(self.machine.expiry_bars),
            "detector": self.machine.detector.name,
        }
