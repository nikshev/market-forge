---
traces: [REQ-WP-105]
status: draft
---

# Feature Specification: Compact the tail

**Input**: [[REQ-WP-105]] -- measured 2026-10-13: a compaction pass over `feature_snapshots` took 1,612 s to fold 68 small files into a 1.3-million-row file.

## Scenarios

1. **Given** a large file followed by small ones, **When** compaction runs, **Then** the small ones become one file and the large one is untouched, rows in the same order.
2. **Given** a pass that just ran, **When** more small files arrive and it runs again, **Then** only those are merged.
3. **Given** all files small, **Then** they are merged whole (as before). **Given** one small file after a large one, **Then** nothing is written.
4. **Given** a small file before a large one, **Then** it is not merged with files after it.
