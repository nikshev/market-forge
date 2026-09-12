---
id: OUT-2026-09-12-implement-metrics-serving
step: implement
records: [REQ-WP-055]
commit: null
---

## What was done

`api/metrics_route.py` serving the exposition, `observability/dashboard.py`
defining what to draw, and two mutation specifications. 15 tests, 10 of 10
mutants caught.

## The endpoint was the small half

One route, the content type a scraper expects, and no framing of its own. Three
decisions worth the lines they took:

- **An empty body is the right answer** for a process that has measured nothing.
  `MetricRegistry` creates no series until something observes one — a metric
  nobody writes is absent rather than zero — so an error would make a quiet
  process look broken and a placeholder would be the zero [[REQ-WP-036]] refused,
  arriving at the last possible moment.
- **The route is outside `/api/v1`.** It is operational, its shape is
  Prometheus's rather than this project's, and versioning it alongside the
  endpoints a browser calls would tie two things that change for different
  reasons.
- **The content type carries `version=0.0.4`.** Most scrapers accept bare
  `text/plain`, which is exactly why sending it would go unnoticed until one did
  not.

## The dashboard was the half with the trap

Of §33's eleven metrics, **nine have no producer.** A dashboard with eleven
panels draws nine of them empty — and an empty panel is indistinguishable from a
healthy quiet system. A flat line at the bottom of a chart reads as "nothing is
going wrong", which is precisely what nobody knows.

That is [[REQ-WP-036]]'s own problem one level up. It refused to export those
metrics as zero, because that makes a dashboard lie, and refused to drop them
from the list, because that makes the gap invisible. A dashboard has the same
two temptations and the same answer.

So the definition has two kinds of entry. A `Panel` queries something that can
actually be emitted. An `Absence` states, in the words the code already carries,
why there is nothing to draw — "no connector runs; nothing counts an event" is
worth more than a flat line at zero and worth more than a missing panel.

**The absences are derived, not transcribed.** A copy would go stale the day
somebody implements queue depth, and the dashboard would keep explaining why a
metric that now exists does not. There is a test that removes an entry from
`UNIMPLEMENTED` and checks the derived list shrinks with it.

## One survivor, and it was a test comparing something with itself

`eq=False` on `Panel` survived the first pass. The value-comparison test built
its "same" dashboard from `DASHBOARD.panels` — the same tuple object — so the
comparison passed on identity whether or not the parts compared by value, and
the "changed" case differed in length so it failed on the tuple rather than the
element.

Rebuilding the panels element by element, and asserting they are equal *and* not
the same object, is what tells the two apart.

## What is still open

- **Standing Prometheus and Grafana up.** Deployment work, and Phase 8's next
  item. This is the two halves that must be right before either is worth
  running: something to scrape, and a definition that cannot go stale quietly.
- **Whether an absence should name the work that would close it**, rather than
  only the gap.
