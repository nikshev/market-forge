# Plan: The price moves on the last bar

**Spec**: [spec.md](spec.md) | **Requirement**: [[REQ-WP-108]]

Decisions: **find the latency by measuring each hop** (publisher, broker, consumer, relay, socket, page) rather than lowering an interval:
the consumer's blocking poll was the one-second burst. **Two topics** because the two kinds of message are read differently (finals
replayed, forming only as they arrive). **Retention enforced** on an existing topic, because creating a topic with a retention does not
change one that already exists. Rejected: a faster publish interval alone (the burst was downstream); keeping one topic and filtering on
replay (the replay still reads seven days).
The page opens on the newest 150 bars: a whole-history range makes the last bar a few pixels wide, which is why price movement was invisible.
