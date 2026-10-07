"""Channel snapshot and quality (PRD section 13.1).

# @trace: REQ-WP-006
# @trace: REQ-WP-087
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from channelflow.bars import Bar


class ChannelQuality(BaseModel):
    """A score in [0,1], and an honest account of what produced it.

    PRD section 13.9 lists nine submetrics. Three cannot be computed yet --
    forecast calibration needs section 13.8's forecast channel, regime
    compatibility needs section 20's engine, and age needs channel-lifetime
    tracking nothing keeps. ADR-007: the unavailable ones are omitted from the
    average rather than defaulted to a neutral value, because a default would
    move the score toward the middle for a reason no reader could see.

    `contributing` and `unavailable` are carried so a six-part score is never
    silently compared against a later nine-part one as though they meant the
    same thing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    submetrics: dict[str, float]
    contributing: tuple[str, ...]
    unavailable: tuple[str, ...]


class ChannelSnapshot(BaseModel):
    """The channel as it stood at one moment.

    Frozen: PRD section 0.5 forbids rewriting a finalized snapshot, and a value
    that cannot be mutated cannot be rewritten.

    `source_max_event_time_ns <= as_of_ns` is PRD section 13.1's hard invariant
    and the reason this model exists in the shape it does. It is validated here
    as well as in the fitter, so a snapshot constructed by any other route still
    cannot claim to have seen the future.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of_ns: int = Field(ge=0)
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    lookback: int = Field(gt=0)

    #: The bars the fit was actually given: never more than `lookback`, and --
    #: once the channel restarts at a hole (REQ-WP-087 FR-004) -- possibly
    #: fewer, because the window then begins at the first bar after the gap.
    #: `fit_window` has always refused to fit on fewer bars than the lookback
    #: asks for, so a construction that states no window is claiming the full
    #: one, which is exactly what it claimed before this field existed; the
    #: default in `_window_defaults` is that claim, made explicit rather than
    #: assumed.
    window_bars: int = Field(ge=0)
    #: `window_bars < lookback` -- whether the window fell short of what the
    #: fit asked for (REQ-WP-087 FR-005). Filled from `window_bars` when the
    #: producer states no flag, and refused when the stored flag contradicts
    #: the stored count: a snapshot claiming 45 bars while saying the window
    #: was not short is the same dishonesty in two fields, and this model is
    #: the last place it can be caught.
    window_short: bool
    #: Where the window begins after a gap: the time of the first bar in the
    #: window that follows the hole (REQ-WP-087 FR-004). `None` means the
    #: window holds no gap -- the truth for every snapshot until gap detection
    #: reaches the window selection, and for any window fitted across a
    #: continuous series. It is never a bar the fit did not use.
    first_bar_after_gap_ns: int | None = None

    center_now: float
    upper_now: float
    lower_now: float
    slope_normalized: float
    #: The fitted slope in log price per bar, unnormalized. PRD section 13.7's
    #: forecast centre needs it: projecting a channel forward without it means
    #: projecting it flat, which is a different forecast. `slope_normalized`
    #: cannot serve -- it is divided by the residual spread, so two channels with
    #: the same normalized slope move at different speeds.
    slope_log_per_bar: float = 0.0
    width_pct: float

    #: Empty for Baseline A. PRD section 13.7 defines forecasts; fabricating a
    #: plausible-looking list here would be worse than an honest absence.
    forecast_horizons: tuple[float, ...] = ()

    quality: ChannelQuality
    source_max_event_time_ns: int = Field(ge=0)

    @model_validator(mode="before")
    @classmethod
    def _window_defaults(cls, data: object) -> object:
        """The window a producer has not stated (REQ-WP-087).

        `window_bars` falls back to `lookback`, and `window_short` follows
        from the pair, because every snapshot built before this requirement
        said nothing about its window and meant the full one: `fit_window`
        refuses a fit on fewer bars than the lookback asks for, and
        `tables.channels.from_row` rebuilds stored rows with no window columns
        to read. Defaulting `window_bars` to 0 instead would turn each of
        those snapshots into a claim that the fit used no bars, and leaving
        `window_short` at a fixed False would claim a full window for a short
        one the moment gap handling lands.
        """
        if not isinstance(data, Mapping):
            return data
        fields = dict(data)
        lookback = fields.get("lookback")
        if isinstance(lookback, bool) or not isinstance(lookback, int):
            # Field validation reports `lookback` itself; inventing a window
            # for an unusable one would bury that error behind this one.
            return data
        window_bars = fields.setdefault("window_bars", lookback)
        if "window_short" not in fields:
            # A non-int `window_bars` is left for field validation to report;
            # comparing it to `lookback` here would raise before it could.
            if isinstance(window_bars, int) and not isinstance(window_bars, bool):
                fields["window_short"] = window_bars < lookback
        return fields

    def model_post_init(self, _: object) -> None:
        if self.source_max_event_time_ns > self.as_of_ns:
            raise ValueError(
                f"snapshot violates PRD section 13.1: source_max_event_time_ns "
                f"({self.source_max_event_time_ns}) is after as_of_ns ({self.as_of_ns}); "
                "this channel would have seen the future"
            )
        if self.window_bars > self.lookback:
            raise ValueError(
                f"window_bars ({self.window_bars}) exceeds lookback ({self.lookback}); "
                "the window cannot hold more bars than the fit asked for"
            )
        if self.window_short != (self.window_bars < self.lookback):
            raise ValueError(
                f"window_short ({self.window_short}) contradicts window_bars "
                f"({self.window_bars}) against lookback ({self.lookback}); a snapshot "
                "cannot say its window was short and count out a full one"
            )


class ChannelModel(Protocol):
    """What every channel baseline can do (REQ-EXP-001).

    The comparison in REQ-EXP-001 runs five of these side by side, and the
    backtest runner takes one. Naming the shape rather than one class is what
    lets either accept a model it has never heard of -- and what stops the
    runner's type from quietly meaning "baseline A".
    """

    # A read-only property rather than a variable: every baseline is a frozen
    # dataclass, and a protocol asking for a settable attribute would exclude
    # all of them.
    @property
    def lookback(self) -> int: ...

    def fit(self, bars: list[Bar], *, as_of_ns: int) -> ChannelSnapshot: ...
