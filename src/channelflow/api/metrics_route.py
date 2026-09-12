"""The Prometheus exposition, over HTTP.

# @trace: REQ-WP-055

[[REQ-WP-036]] built the exposition PRD §33 asks for and nothing served it. This
is the smaller half of closing that: one endpoint, the content type a Prometheus
scraper expects, and no framing of its own.

**An empty body is the right answer for a process that has measured nothing.**
`MetricRegistry` creates no series until something observes one, deliberately --
a metric nobody writes is absent rather than zero -- so a scrape before anything
has happened returns nothing at all. Returning an error instead would make a
quiet process look like a broken one, and inventing a zero would be the lie the
registry exists to refuse.

The route is outside `/api/v1` because it is not part of PRD §28's read API: it
is operational, its shape is Prometheus's rather than this project's, and
versioning it alongside the endpoints a browser calls would tie two things that
change for different reasons.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from channelflow.metrics import MetricRegistry

#: What a Prometheus scraper expects. Sent explicitly rather than left to the
#: framework's default: `text/plain` without the version parameter is accepted
#: by most scrapers and is not what the exposition format specifies.
CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

router = APIRouter()


@router.get("/metrics")
def get_metrics(request: Request) -> Response:
    registry: MetricRegistry = request.app.state.metrics
    return Response(content=registry.render(), media_type=CONTENT_TYPE)
