"""The context collector: raw observations that become the lower panes' features (REQ-WP-093).

# @trace: REQ-WP-093

One service per venue polls the public derivatives endpoints (and, with REQ-WP-094 and REQ-WP-095,
listens to the liquidation and book streams) and stores what it saw, append-only, with both times.
It computes no feature: the worker is the only writer of `feature_snapshots` ([[ADR-070]]).
"""
