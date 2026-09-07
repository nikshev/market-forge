"""ChannelFlow: crypto market-structure and signal radar.

The product package. Everything under here is subject to `mypy --strict` and to
the constitution in `.specify/memory/constitution.md` -- in particular Principle
I (no look-ahead) and Principle II (event_time, exchange_time, block_time,
ingest_time, bar_open_time and bar_close_time are distinct and never conflated).

Empty by design: REQ-WP-001 provisions the environment, REQ-WP-002 brings the
domain model.
"""

# @trace: REQ-WP-001

__all__: list[str] = []
