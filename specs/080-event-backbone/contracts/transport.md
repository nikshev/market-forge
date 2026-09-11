# Contract — the event backbone

```python
Record(topic, key, payload, event_time_ns, ingest_time_ns, producer, sequence=None)

class EventPublisher(Protocol):
    def publish(self, record: Record) -> None
    def flush(self) -> None

class EventConsumer(Protocol):
    def poll(self, *, limit: int) -> list[Record]

InProcessTransport()            -> .publisher(), .consumer(topics)
KafkaTransport(bootstrap, ...)  -> .publisher(), .consumer(topics, group)
materialise_trades(consumer, *, catalog, timeframe_ns, limit) -> Recording
```

## Guarantees

- A topic without an explicit schema version is refused at construction, as is a
  record with no partition key or no producer.
- Event time and ingestion time are separate fields and neither is derived from
  the other.
- A record survives the round trip field for field, on either transport.
- `poll` returning nothing is an answer.
- `materialise_trades` writes through [[ADR-056]]'s watermark, so consuming a
  topic twice writes its rows once.
- Nothing reads a clock: an ingestion time is supplied by whoever ingested.

## Does not

Register schemas, manage offsets beyond what the client does, or create topics
in production. It also does not write tables itself — that belongs to the one
entry point that already knows the rules.
