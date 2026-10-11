# @trace: REQ-INFRA-013
"""Is an image still served? `served`, `gone` or `unknown` (REQ-INFRA-013).

`docker manifest inspect` is a registry read; its exit status says only that it failed. What it
failed *with* is what separates "the registry does not have this" from "the registry could not be
asked": a pull rate limit or a dropped connection is not evidence that an image is gone, and a check
that cried wolf on those would be switched off the second time. The classification therefore
reads the error text, and the texts it knows are the real ones -- the first two `gone` cases are
what CI and a local `manifest inspect` printed for the MinIO images on 2026-10-11.

Anything unrecognised is `unknown`: a failure nobody has seen before is a reason to look, and not a
reason to fail the build or to declare the image gone.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable

Runner = Callable[[str], tuple[int, str]]

#: Checked first: these mean "could not ask", whatever else the text says.
_UNKNOWN = (
    "toomanyrequests",
    "429",
    "rate limit",
    "timeout",
    "timed out",
    "no such host",
    "connection refused",
    "connection reset",
    "temporary failure",
    "tls handshake",
    "network is unreachable",
    "service unavailable",
    "503",
    "502",
    "504",
)
#: The registry answered, and the answer is "not here" (or "not for you", which an anonymous client
#: cannot tell apart from "not here": quay answers a removed repository with "authentication
#: required").
_GONE = (
    "unauthorized",
    "access denied",
    "pull access denied",
    "denied: requested access",
    "repository does not exist",
    "manifest unknown",
    "no such manifest",
    "name unknown",
    "not found",
    "authentication required",
    "requires authentication",
)


def classify(returncode: int, text: str) -> str:
    if returncode == 0:
        return "served"
    lowered = text.lower()
    if any(marker in lowered for marker in _UNKNOWN):
        return "unknown"
    if any(marker in lowered for marker in _GONE):
        return "gone"
    return "unknown"


def docker_runner(reference: str) -> tuple[int, str]:
    try:
        done = subprocess.run(
            ["docker", "manifest", "inspect", reference],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        return 1, "i/o timeout"
    except FileNotFoundError:
        return 1, "docker is not installed: connection refused to the CLI"
    return done.returncode, (done.stderr or done.stdout)
