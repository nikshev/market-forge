"""The chart's real-time feed (REQ-WP-102).

# @trace: REQ-WP-102

What goes into the bars table is the record and is committed in batches ([[REQ-WP-068]]); what the
chart draws is a view, and gets its own feed: the ingest publishes the bars it holds, the API relays
them over a WebSocket. Best effort end to end -- losing a live bar costs a candle that the table
supplies a few minutes later, never a fact.
"""
