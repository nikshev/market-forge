"""The parity capture lists one symbol's archive, not every symbol's (REQ-WP-078).

# @trace: REQ-WP-078

`parity_capture` listed `raw/cex/<venue>/`. With the symbol in the key that prefix
returns every symbol's minutes interleaved, and a replay would be built from the
frames of several instruments and compared against the bars of one.
"""

from __future__ import annotations

import pytest

from tools.record.parity_capture import archive_prefix


@pytest.mark.trace("REQ-WP-078")
def test_the_prefix_names_venue_and_symbol() -> None:
    assert archive_prefix("binance", "BTCUSDT") == "raw/cex/binance/BTCUSDT/"


@pytest.mark.trace("REQ-WP-078")
def test_no_symbols_prefix_is_a_prefix_of_another_symbols_objects() -> None:
    """A prefix without its trailing slash would let `BTC` swallow `BTCUSDT`."""
    a, b = archive_prefix("okx", "BTC-USDT"), archive_prefix("okx", "BTC-USDT-SWAP")

    assert not b.startswith(a) and not a.startswith(b)
