"""No centred filter reaches a live feature (REQ-BIAS-002).

[[ADR-024]] gave PRD §41 rule 2 a home and refused to claim coverage for it "on
the strength of one engine's guard". The refusal was right. `require_causal` had
one call site in the repository and it was inside a research comparison; the
forbidden-import scan read one package out of twenty-eight; and every feature
declared `point_in_time_safe=True` with no rule reading the field.

These are the checks that make the rule reach the live path. They are tripwires
rather than detectors -- [[ADR-022]] settled that a general detector is not
achievable -- and a transform that lies about being causal is still Test A's
business, not theirs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from channelflow.extrema.causality import EXEMPT, FORBIDDEN_IMPORTS, forbidden_in
from channelflow.features import REGISTRY, exposed_feature_names
from channelflow.features.registry import FeatureSpec

PACKAGE = Path(__file__).resolve().parents[3] / "src" / "channelflow"


def live_modules() -> list[Path]:
    """Every module under `src/channelflow/` that is not exempt."""
    return [
        module
        for module in sorted(PACKAGE.rglob("*.py"))
        if str(module.relative_to(PACKAGE)) not in EXEMPT
    ]


@pytest.mark.trace("REQ-BIAS-002")
def test_no_live_module_reaches_for_a_centred_helper() -> None:
    """The realistic mistake: someone reaches for `savgol_filter` because a
    causal filter is not smoothing enough.

    Before this, that was caught in `extrema/` and nowhere else -- the same
    import in `features/flow.py`, which computes live values, passed every check
    in the repository.
    """
    modules = live_modules()
    assert modules, "no modules were scanned; this would pass vacuously"

    offenders = {
        str(module.relative_to(PACKAGE)): forbidden_in(module.read_text()) for module in modules
    }

    assert not {name: found for name, found in offenders.items() if found}


@pytest.mark.trace("REQ-BIAS-002")
def test_the_scan_covers_every_package_and_not_just_one() -> None:
    """The gap this closes, asserted rather than described.

    A regression here would not fail anything else: a scan narrowed back to one
    package would still find nothing and still pass.
    """
    scanned = {str(m.relative_to(PACKAGE)).split("/")[0] for m in live_modules()}

    packages = {
        entry.name for entry in PACKAGE.iterdir() if entry.is_dir() and entry.name != "__pycache__"
    }
    assert packages <= scanned
    assert len(packages) > 20


@pytest.mark.trace("REQ-BIAS-002")
def test_a_forbidden_helper_is_found_wherever_it_appears() -> None:
    """`forbidden_in` is the tripwire itself, so it is worth testing directly
    rather than only through a tree that currently has nothing to find.

    The five are named here rather than only looped over. A loop across the
    constant shrinks with it: delete an entry and the loop checks one fewer thing
    and still passes, which is how a list like this empties without anyone
    noticing. Membership is asserted, not equality -- adding a helper is how the
    rule grows, and removing one needs an argument.
    """
    assert {
        "argrelextrema",
        "find_peaks",
        "savgol_filter",
        "filtfilt",
        "centered_rolling",
    } <= set(FORBIDDEN_IMPORTS)

    for helper in FORBIDDEN_IMPORTS:
        assert forbidden_in(f"from scipy.signal import {helper}\n") == (helper,)

    assert forbidden_in("import numpy as np\n") == ()


@pytest.mark.trace("REQ-BIAS-002")
def test_every_exemption_names_a_module_that_exists() -> None:
    """A list that has stopped describing anything still reads as authority, and
    the next person takes it as one."""
    for module in EXEMPT:
        assert (PACKAGE / module).is_file(), module


@pytest.mark.trace("REQ-BIAS-002")
def test_every_exemption_carries_a_reason() -> None:
    """An exemption without one is indistinguishable from an oversight."""
    for module, reason in EXEMPT.items():
        assert reason.strip(), module


@pytest.mark.trace("REQ-BIAS-002")
def test_the_exemption_is_one_module_wide_and_not_one_package() -> None:
    """Exempting `extrema` would exempt every module beside the one that needed
    it -- and `extrema` is where this rule most wants to look."""
    assert "extrema/causality.py" in EXEMPT

    neighbours = [m for m in live_modules() if str(m.relative_to(PACKAGE)).startswith("extrema/")]
    assert neighbours, "the whole package was exempted, not the one module"


@pytest.mark.trace("REQ-BIAS-002")
def test_every_registered_feature_is_point_in_time_safe() -> None:
    """The field was required and unread: every feature declared `True` and
    nothing asked it to.

    `exposed_feature_names()` first, because `REGISTRY` fills as a side effect of
    importing the modules that register into it -- and an empty registry would
    make `all(...)` below pass while checking nothing. That is the same "absent
    is not zero" trap the feature gate was built around, and this test hit it
    before the call was added.
    """
    exposed = exposed_feature_names()

    assert exposed
    assert REGISTRY
    assert len(REGISTRY) == len(exposed)
    assert all(spec.point_in_time_safe for spec in REGISTRY.values())


@pytest.mark.trace("REQ-BIAS-002")
def test_a_feature_that_is_not_point_in_time_safe_cannot_be_registered() -> None:
    """Unregisterable rather than registered-and-caught-later.

    The author still writes the value out, so ADR-015's "no field an author can
    forget to think about" is unchanged; what changes is that the only value the
    rule permits is the only one that can be written.
    """
    fields = {
        "name": "probe",
        "version": 1,
        "family": "probe",
        "description": "d",
        "formula": "f",
        "unit": "u",
        "source_events": ("trade",),
        "lookback": "instant",
        "cadence": "per_trade",
        "availability_lag_ms": 0,
        "null_policy": "n",
        "clipping": "c",
        "normalization": "z",
        "test_fixture": "t",
    }

    assert FeatureSpec(point_in_time_safe=True, **fields)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        FeatureSpec(point_in_time_safe=False, **fields)  # type: ignore[arg-type]
