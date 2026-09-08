"""Order-flow and book features (REQ-WP-011).

# @trace: REQ-WP-011

PRD section 15. Scope is REQ-WP-011's acceptance list: queue and depth
imbalance, microprice, OFI, cumulative volume delta, wall persistence. Section
15.5's remaining shape features and section 15.7's absorption are named in the
PRD but not in this work package, and the distance is deliberate.
"""

from channelflow.features.registry import REGISTRY, FeatureSpec, register


def exposed_feature_names() -> tuple[str, ...]:
    """Every feature a caller can actually compute from this package.

    Derived from the modules rather than from `REGISTRY`, so the two can
    disagree -- which is the whole point of comparing them (ADR-015).

    Every package that produces features is enumerated here, not just this one.
    A second package shipping unregistered features while the gate stayed green
    would be the gate quietly becoming about one module.
    """
    from channelflow import derivatives
    from channelflow.features import flow, instant, ofi, walls

    names: list[str] = []
    for module in (instant, ofi, flow, walls, derivatives):
        names.extend(module.FEATURES)
    return tuple(names)


__all__ = ["REGISTRY", "FeatureSpec", "exposed_feature_names", "register"]
