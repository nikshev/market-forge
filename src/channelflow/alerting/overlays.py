"""PRD section 27.2's toggleable chart layers.

# @trace: REQ-US-002

    "Toggle layers: candles; channel center; upper/lower; forecast corridor;
     signal zones; signal marker; volume profile; POC/VAH/VAL; VWAP; large LOB
     walls; DEX liquidity bands; liquidation levels."

REQ-US-002 asks that "all overlays active at signal time are restored" when the
alert's button is pressed. A link that does not carry them restores nothing: the
reader lands on a chart configured however their last visit left it, looking at
a different picture from the one the setup was judged on, with nothing saying
so.

The vocabulary is the PRD's full list even though the chart draws a subset of it
today, so a link written now stays valid as layers are added. A name outside the
list is refused at the alert rather than discarded at the chart -- otherwise the
alert records a state that silently cannot be restored.
"""

from __future__ import annotations

from enum import StrEnum


class Overlay(StrEnum):
    """Section 27.2's layers, in the PRD's own order."""

    CANDLES = "candles"
    CHANNEL_CENTER = "channel_center"
    CHANNEL_BOUNDS = "channel_bounds"
    FORECAST_CORRIDOR = "forecast_corridor"
    SIGNAL_ZONES = "signal_zones"
    SIGNAL_MARKER = "signal_marker"
    VOLUME_PROFILE = "volume_profile"
    POC_VAH_VAL = "poc_vah_val"
    VWAP = "vwap"
    LOB_WALLS = "lob_walls"
    DEX_LIQUIDITY_BANDS = "dex_liquidity_bands"
    LIQUIDATION_LEVELS = "liquidation_levels"
