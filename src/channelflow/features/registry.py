"""What every number in this package means.

# @trace: REQ-WP-011
# @trace: REQ-PRIN-008
# @trace: REQ-BIAS-002

PRD section 19: "Every feature definition must be registered", with sixteen
required fields. Constitution Principle VI: "An undocumented feature is not
done."

ADR-015 makes that a gate rather than a habit. `test_registry.py` compares the
set of features this package exposes against `REGISTRY` and fails, by name, on
any difference. A registry nothing checks is a comment that rots.

Python rather than PRD section 19's YAML, deliberately: a registration and its
implementation drift the moment they live in different files, and a test can
only compare what it can import. The fields are section 19's, verbatim.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FeatureSpec(BaseModel):
    """One feature's registration -- PRD section 19's required metadata.

    Frozen: a definition that can be edited at runtime is not a definition.
    Nothing here has a default. A field with a default is a field an author can
    forget to think about, and `availability_lag_ms` or `null_policy` left at
    someone else's guess is exactly the documentation this is meant to prevent.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    version: int = Field(ge=1)
    family: str = Field(min_length=1)
    description: str = Field(min_length=1)
    #: The arithmetic, written out. A reader who disagrees with a value must be
    #: able to check it without opening the implementation.
    formula: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    #: PRD section 19 calls these "required source events".
    source_events: tuple[str, ...] = Field(min_length=1)
    #: Human-readable span the value looks back over; "instant" for none.
    lookback: str = Field(min_length=1)
    cadence: str = Field(min_length=1)
    #: How long after the fact the value can first be known. Zero means it is
    #: available at the event that produces it.
    availability_lag_ms: int = Field(ge=0)
    null_policy: str = Field(min_length=1)
    clipping: str = Field(min_length=1)
    normalization: str = Field(min_length=1)
    #: Whether the value at `t` uses only data with `event_time <= t`. No
    #: default: Constitution Principle I is not something to leave implied.
    #: `Literal[True]`, not `bool`: PRD §41 rule 2 forbids a centred filter in a
    #: live feature, and this registry is the live feature list. A feature that
    #: cannot claim point-in-time safety has no business in it, so it is
    #: unregisterable rather than registered and caught later. The author still
    #: writes the value out, so [[ADR-015]]'s "no field an author can forget to
    #: think about" is unchanged -- what changes is that the only writable value
    #: is the one the rule permits.
    point_in_time_safe: Literal[True]
    #: The test that pins this feature's arithmetic to hand-computed values.
    test_fixture: str = Field(min_length=1)
    entity: Literal["venue_symbol"] = "venue_symbol"


#: Every feature this package exposes. Adding a feature without adding an entry
#: fails `test_every_exposed_feature_is_registered` by name.
REGISTRY: dict[str, FeatureSpec] = {}


def register(spec: FeatureSpec) -> FeatureSpec:
    """Add a registration, refusing a duplicate name.

    Two entries under one name would mean a feature whose definition depends on
    import order.
    """
    if spec.name in REGISTRY:
        raise ValueError(f"feature {spec.name!r} is already registered")
    REGISTRY[spec.name] = spec
    return spec
