"""Channel models (REQ-WP-006).

# @trace: REQ-WP-006
# @trace: REQ-CHAN-001
"""

from channelflow.channels.huber import HuberChannel
from channelflow.channels.kalman import KalmanChannel
from channelflow.channels.models import ChannelQuality, ChannelSnapshot
from channelflow.channels.quantile import QuantileChannel
from channelflow.channels.rolling_ols import RollingOLSChannel
from channelflow.channels.window import ChannelFitError, fit_window

__all__ = [
    "ChannelFitError",
    "ChannelQuality",
    "ChannelSnapshot",
    "HuberChannel",
    "KalmanChannel",
    "QuantileChannel",
    "RollingOLSChannel",
    "fit_window",
]
