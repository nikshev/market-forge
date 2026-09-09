"""Channel models (REQ-WP-006).

# @trace: REQ-WP-006
# @trace: REQ-CHAN-001
"""

from channelflow.channels.features import (
    FEATURES,
    channel_position,
    channel_quality_score,
    channel_slope_normalized,
    channel_width_pct,
)
from channelflow.channels.huber import HuberChannel
from channelflow.channels.kalman import KalmanChannel
from channelflow.channels.models import ChannelModel, ChannelQuality, ChannelSnapshot
from channelflow.channels.quantile import QuantileChannel
from channelflow.channels.rolling_ols import STD_MODEL_NAME, RollingOLSChannel
from channelflow.channels.window import ChannelFitError, fit_window

__all__ = [
    "FEATURES",
    "STD_MODEL_NAME",
    "ChannelFitError",
    "ChannelModel",
    "ChannelQuality",
    "ChannelSnapshot",
    "HuberChannel",
    "KalmanChannel",
    "QuantileChannel",
    "RollingOLSChannel",
    "channel_position",
    "channel_quality_score",
    "channel_slope_normalized",
    "channel_width_pct",
    "fit_window",
]
