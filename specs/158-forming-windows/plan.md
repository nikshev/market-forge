# Plan: Live windows on every timeframe

**Spec**: [spec.md](spec.md) | **Requirement**: [[REQ-WP-106]]

Decisions: **on the page, not the server.** The minutes are already on the page (the 1m socket) and the table serves the rest; a server-side
aggregator would be a second implementation of the resampler's windows to keep in step. Rejected: asking the API for forming windows per
timeframe over the socket; deriving windows from the venue's own kline stream (different trade numbers from the stored bars).
The one request added is the minutes from the first window without a stored bar, up to 10,000 (the route's cap), made once per load and per
reload.
