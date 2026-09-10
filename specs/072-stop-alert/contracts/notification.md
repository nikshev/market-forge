# Contract — the stop-update notification

```python
StopUpdateAlert(position=..., proposal=..., stop_in_force=..., market_price=...,
                event_time_ns=..., chart_base_url=...)
StopUpdateGate(dispatcher=..., debug=False).offer(alert, at_ns=...)
```

## Guarantees

- The message states both stop levels and both risk figures. Neither half is
  ever printed alone.
- The old stop is `stop_in_force` — what the exchange was obeying, never the
  last level the policy decided.
- With `debug=False`, a held or refused proposal is delivered zero times and
  audited once, with the reason.
- With `debug=True`, a hold is announced under a header that is not an update's.
- Every reason reaches the message, including unrecognised ones. An absent
  anchor omits its block rather than dashing it.
- Delivery, retry, dead-lettering and audit are the signal alert's, unchanged.
- Nothing raises into the caller, and nothing sleeps.

## Does not

Decide when to offer. Whether a notification fires at the decision or at the
modelled acknowledgement is the caller's, and is named in the spec's Open
Questions rather than settled by a default here.
