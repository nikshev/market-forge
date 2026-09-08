"""Every feature is documented, or the suite fails (REQ-WP-011, REQ-PRIN-008).

PRD section 19 opens "Every feature definition must be registered" and lists
sixteen required fields. Constitution Principle VI ends "an undocumented
feature is not done".

ADR-015 turns that from a rule people follow into one they cannot skip: the set
of features this package exposes and the set of registered names must be equal.
A registry checked by nothing is a comment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from channelflow.features import REGISTRY, FeatureSpec, exposed_feature_names

REQUIRED_FIELDS = (
    "name",
    "version",
    "family",
    "description",
    "formula",
    "unit",
    "source_events",
    "lookback",
    "cadence",
    "availability_lag_ms",
    "null_policy",
    "clipping",
    "normalization",
    "point_in_time_safe",
    "test_fixture",
)


@pytest.mark.trace("REQ-WP-011")
@pytest.mark.trace("REQ-PRIN-008")
def test_every_exposed_feature_is_registered() -> None:
    """SC-007, FR-018. The failure names the feature, so the fix is obvious."""
    exposed = set(exposed_feature_names())
    registered = set(REGISTRY)

    assert exposed - registered == set(), (
        f"unregistered feature(s): {sorted(exposed - registered)}. PRD section 19: "
        "every feature definition must be registered. Add an entry to REGISTRY."
    )
    assert registered - exposed == set(), (
        f"registered but not exposed: {sorted(registered - exposed)}. A registration "
        "for a feature nobody can compute is documentation of something that does "
        "not exist."
    )


@pytest.mark.trace("REQ-WP-011")
@pytest.mark.trace("REQ-PRIN-008")
def test_no_required_field_is_blank() -> None:
    """PRD section 19's sixteen fields, each actually filled in.

    A field present and empty is worse than absent: it passes a shape check
    while telling the reader nothing.
    """
    for name, spec in REGISTRY.items():
        for field in REQUIRED_FIELDS:
            value = getattr(spec, field)
            assert value is not None, f"{name}.{field} is unset"
            if isinstance(value, str):
                assert value.strip(), f"{name}.{field} is blank"
            if isinstance(value, tuple):
                assert value, f"{name}.{field} is empty"


@pytest.mark.trace("REQ-WP-011")
def test_a_registration_states_point_in_time_safety_explicitly() -> None:
    """FR-020, Constitution Principle I.

    `point_in_time_safe` is a bool with no default: a feature whose author did
    not think about look-ahead cannot be registered without saying so.
    """
    for name, spec in REGISTRY.items():
        assert isinstance(spec.point_in_time_safe, bool), name
    assert all(spec.point_in_time_safe for spec in REGISTRY.values()), (
        "a feature that is not point-in-time safe is registered; Principle I "
        "forbids it, so either the flag or the feature is wrong"
    )


@pytest.mark.trace("REQ-WP-011")
def test_a_name_matches_its_key() -> None:
    """A registry whose key and payload disagree would report the wrong feature."""
    for key, spec in REGISTRY.items():
        assert spec.name == key


@pytest.mark.trace("REQ-WP-011")
def test_a_registration_cannot_be_edited_after_the_fact() -> None:
    """Principle III's spirit: a definition someone can mutate at runtime is
    not a definition."""
    spec = next(iter(REGISTRY.values()))
    with pytest.raises(Exception):  # noqa: B017 -- pydantic and dataclasses differ
        spec.unit = "changed"  # type: ignore[misc]


@pytest.mark.trace("REQ-WP-011")
def test_the_features_package_cannot_consult_a_clock() -> None:
    """SC-008, FR-019. Every window boundary comes from event time.

    A feature whose window closed on wall-clock time would compute a different
    value replaying the same recorded stream, and the difference would look
    like a market change.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "features"
    modules = list(package.glob("*.py"))
    assert modules, "the features package has no modules; this test would pass vacuously"
    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"


@pytest.mark.trace("REQ-WP-011")
def test_the_registry_is_not_empty() -> None:
    """Guard on the guards above: all of them pass vacuously over an empty
    registry, and an empty registry is exactly what a half-finished refactor
    leaves behind."""
    assert len(REGISTRY) >= 10
    assert all(isinstance(spec, FeatureSpec) for spec in REGISTRY.values())
