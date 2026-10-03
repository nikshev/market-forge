"""Catalogs that make a race between two loads of a table happen on every call (REQ-WP-079).

On the deployment the fault took about four seconds of window and five writers, and showed up
fourteen times in thirteen hours. A test that waits for that is not a test. These wrappers make
the window exact: a commit lands between *every* two loads, so code that loads twice and trusts
the second answer against the first fails on its first call instead of on its thousandth.

Both delegate everything but `load_table` to the catalog they wrap, so they can stand wherever
`IcebergTable` expects a `Catalog`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any


class CountingCatalog:
    """Counts `load_table` calls per table identifier."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.loads: Counter[str] = Counter()

    def load_table(self, identifier: Any, *args: Any, **kwargs: Any) -> Any:
        self.loads[str(identifier)] += 1
        return self._inner.load_table(identifier, *args, **kwargs)

    def reset(self) -> None:
        self.loads.clear()

    @property
    def total(self) -> int:
        return sum(self.loads.values())

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class RacingCatalog:
    """Runs `compete` before returning every load after the first one made once armed.

    Armed explicitly, because a test's own set-up appends load tables too and none of those should
    race. After `arm()` the first `load_table` is returned clean -- that is the version a reader
    starts from -- and every later one is preceded by a competing commit, so each answer is one
    commit newer than the last.

    `compete` must commit through the **unwrapped** catalog: through this one it would count as a
    load and race itself.
    """

    def __init__(self, inner: Any, compete: Callable[[], None]) -> None:
        self._inner = inner
        self._compete = compete
        self._armed = False
        self._seen_first = False
        self.competing_commits = 0

    def arm(self) -> None:
        self._armed = True
        self._seen_first = False

    def disarm(self) -> None:
        self._armed = False

    def load_table(self, identifier: Any, *args: Any, **kwargs: Any) -> Any:
        if self._armed:
            if self._seen_first:
                self._compete()
                self.competing_commits += 1
            self._seen_first = True
        return self._inner.load_table(identifier, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
