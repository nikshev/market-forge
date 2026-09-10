# Contract — the normalizer

```
instruments_from(payload, *, venue, market_type) -> tuple[Instrument, ...]
```

Every instrument the payload describes, in order. A symbol appearing twice keeps
the later entry — an amendment, not a second instrument.

## Refuses

- a payload describing no instruments (an empty result would read as a claim
  about the venue rather than about the payload);
- an entry missing any rule, naming the symbol and the field as **missing** —
  distinct from zero, which is a different fact;
- a float where a rule belongs, rather than converting it: `Decimal(0.1)` is not
  refused by Python and is not the venue's tick size.

## Does not

Fetch anything. Where the payload came from is the caller's business, as the
rest of this connector keeps the wire behind a `Transport` protocol.
