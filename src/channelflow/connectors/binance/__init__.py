"""Binance connector (REQ-WP-003).

# @trace: REQ-WP-003

Native rather than a library, per ADR-004: PRD section 8.1 forbids hiding
sequence gaps and order-book reconstruction, which are the things a feed library
exists to abstract away.
"""
