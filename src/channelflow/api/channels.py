"""PRD section 27.5's two views of a channel.

# @trace: REQ-API-001

    AS-SEEN-THEN  the immutable channel snapshot at the selected time
    CURRENT REFIT the channel calculated now over current history

The PRD calls this critical, and says it "directly exposes repaint-like
differences and protects research integrity". The two views of one instant can
differ substantially, and the difference is the measurement -- a channel
refitted with a week of hindsight will often look like it predicted what
followed.

This is the one place in the API where a mistake is invisible in the output: a
refit and a stored snapshot are both perfectly plausible channels. Hence its own
module and its own test file.

`as_seen_then` defaults to true, and defaults to true again when the value
cannot be parsed (ADR-020). Every alert this system has ever sent carries a
deep link; a default that drifted would turn all of them into refits, and old
signals would start looking better than they were.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.api.repositories import Repository
from channelflow.channels import ChannelFitError, ChannelSnapshot, RollingOLSChannel

AS_SEEN_THEN = "AS-SEEN-THEN"
CURRENT_REFIT = "CURRENT REFIT"


class ChannelUnavailable(LookupError):
    """No channel can be given for this request, and the reason is named."""


@dataclass(frozen=True)
class ChannelView:
    snapshot: ChannelSnapshot
    mode: str


def channel_at(
    repository: Repository,
    *,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    at_ns: int,
    as_seen_then: bool = True,
    model: RollingOLSChannel | None = None,
) -> ChannelView:
    """The channel for one instant, in one of the two modes."""
    if as_seen_then:
        stored = repository.channel_snapshot_at(
            venue=venue, symbol=symbol, timeframe_ns=timeframe_ns, at_ns=at_ns
        )
        if stored is None:
            raise ChannelUnavailable(
                f"no channel snapshot was stored at or before {at_ns} for "
                f"{venue}/{symbol}; AS-SEEN-THEN cannot be reconstructed after "
                "the fact, which is the guarantee it exists to make"
            )
        return ChannelView(snapshot=stored, mode=AS_SEEN_THEN)

    bars = repository.bars(
        venue=venue,
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        start_ns=None,
        end_ns=at_ns,
        limit=None,
    )
    fitter = model or RollingOLSChannel()
    try:
        # `as_of` is the requested instant, so REQ-WP-006's own guard applies:
        # the fit cannot see past it even if this function were written
        # carelessly. FR-017 twice over.
        refit = fitter.fit(bars, as_of_ns=at_ns)
    except ChannelFitError as exc:
        # Approximating over fewer bars would put a different model beside a
        # real one under the same name -- the reasoning REQ-WP-006 already
        # applies to its own fitter.
        raise ChannelUnavailable(f"cannot refit at {at_ns}: {exc}") from exc
    return ChannelView(snapshot=refit, mode=CURRENT_REFIT)
