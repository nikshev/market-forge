"""Whether this process can serve.

# @trace: REQ-WP-064

A container probe asks one question: can *this process* answer? [[REQ-WP-035]]'s
`HealthState` answers a different one -- whether a **feed** is good enough to
trade on -- and the two must not share an endpoint.

Answering a probe with §32's state would have an orchestrator restart a pod
because a venue went quiet, and would report a process that cannot reach its
catalog as healthy whenever the feeds happened to be fine. One is about the
market, the other about the deployment.

**A probe that only says "the process is running" is worth very little**, because
a process that started and cannot reach its warehouse serves empty results, and
an empty result is this system's most dangerous shape. So readiness asks the
store a question and reports what it answered.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, Request, Response

#: 503, not 200 with a body saying no. An orchestrator reads the status.
NOT_READY = 503

router = APIRouter()


@dataclass(frozen=True)
class Readiness:
    """The answer, and what was asked."""

    ready: bool
    detail: str

    def as_body(self) -> dict[str, object]:
        return {"ready": self.ready, "detail": self.detail}


#: What a probe does. Returns rather than raises, because "not ready" is an
#: answer and a probe that raised would make every caller write the same
#: try/except.
Probe = Callable[[], Readiness]


def always_ready(detail: str = "no store is configured") -> Probe:
    """For an application built over an in-memory repository.

    Honest rather than convenient: with nothing to reach, there is nothing that
    could be unreachable, and saying so is different from claiming a store
    answered.
    """

    def probe() -> Readiness:
        return Readiness(ready=True, detail=detail)

    return probe


def catalog_probe(list_tables: Callable[[], object]) -> Probe:
    """Ask the catalog to name what it holds.

    A read, not a ping: a connection that opens and a catalog that answers are
    different facts, and the failure this probe exists to catch -- a process
    pointed at a warehouse it cannot read -- passes a ping.
    """

    def probe() -> Readiness:
        try:
            list_tables()
        except Exception as cause:  # noqa: BLE001 -- any failure is not ready
            return Readiness(ready=False, detail=f"the catalog did not answer: {cause}")
        return Readiness(ready=True, detail="the catalog answered")

    return probe


@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, object]:
    """PRD §6.2's `api` service, as an orchestrator sees it.

    Outside `/api/v1`: it is not part of the read API's contract and a client
    has no business calling it.
    """
    probe: Probe = request.app.state.readiness
    answer = probe()
    if not answer.ready:
        response.status_code = NOT_READY
    return answer.as_body()
