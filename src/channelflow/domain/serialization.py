"""The encoding convention for canonical events.

# @trace: REQ-WP-002

One module, because the convention is the thing most likely to change and it
should change in one place rather than nine.

Two values must never be emitted as JSON numbers:

* **Nanosecond timestamps.** A current-epoch value is about 1.79e18. JavaScript's
  Number.MAX_SAFE_INTEGER is 9.01e15 -- smaller by more than two orders of
  magnitude -- so a double-based consumer reading it as a number drifts by
  roughly 128ns. PRD sections 27 and 28 put a React UI on this data, so that
  consumer is not hypothetical, and exact `event_time` ordering is the premise
  the whole system rests on.
* **Decimals.** A JSON number is a double. Encoding a price as one discards
  precision that cannot be recovered.

Both are encoded as strings. Pydantic reads them back into `int` and `Decimal`
without help, because the field types say what they are.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


def _encode(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        # Every int in this domain is a nanosecond timestamp, a block number,
        # a sequence or an index. All are ordering-critical and all may exceed
        # a double, so none of them is safe as a JSON number.
        return str(value)
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        # Tuples matter: book levels are tuples so the containing model stays
        # immutable, and a tuple that fell through here reached json.dumps
        # carrying raw Decimals. The round-trip test caught it.
        return [_encode(v) for v in value]
    return value


def dumps(model: BaseModel) -> str:
    """Serialize deterministically. Two calls produce identical bytes."""
    payload = _encode(model.model_dump(mode="python"))
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def loads[ModelT: BaseModel](model_type: type[ModelT], payload: str) -> ModelT:
    """Read back into the given model. Pydantic coerces the strings by type."""
    return model_type.model_validate(json.loads(payload))
