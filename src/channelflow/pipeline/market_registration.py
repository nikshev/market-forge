"""Each ingest process registers the market it ingests (REQ-WP-081).

# @trace: REQ-WP-081

`GET /api/v1/markets` answered `{"markets":[]}` with five ingest services delivering bars, because
the list
is read from the `markets` table and **nothing running wrote to it**. The writing code existed (in
the
API's repository) and was called only by tests.

A daemon is configured with one venue and one symbol, so it is the one component that knows what is
being
ingested and can say so. A separate registrar would be told the same list a second time.

**A registered market has the venue's type and no trading rules.** The type comes from the venue
registry
(`VENUE_REGISTRY[venue].market_type`), where each venue's URL and policy already live: Binance's
feed is
the spot stream, not a perpetual one, and a label on the first screen that said otherwise would be
the
convenient answer and a false one. Rules (tick, step, minimum notional) are not registered: nothing
uses
them, only Binance has a normalizer, and a network call at start-up to fill fields nobody reads
would be a
new way for ingest to fail.

**Registering is idempotent and never costs a bar.** The table is read first and a present key is
left
alone (an append-only table that took a row per restart would grow for ever, and a key held with
trading
rules must not be overwritten). Any failure -- the catalog, a commit that does not resolve, an
instrument
OKX's registry entry does not recognise -- is one WARNING naming the venue and the symbol, and
ingest goes
on. It is tried once, at start; the next start tries again.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from channelflow.connectors.venue import VENUE_REGISTRY
from channelflow.lakehouse import Catalog
from channelflow.lakehouse import catalog as open_catalog
from channelflow.tables import features as features_table

logger = logging.getLogger(__name__)


def register_market(catalog: Catalog, *, venue: str, symbol: str, market_type: str) -> bool:
    """Write the market's row unless its key is present; say whether a row was written.

    Racing daemons may each write a row for the same key between one's read and another's append.
    The
    list keeps the latest row per key, so a duplicate cannot reach it, and the table is not made to
    refuse one: that would need a lock this stack does not have.
    """
    table = features_table.markets_table_for(catalog)
    held = {(row["venue"], row["symbol"]) for row in table.read().to_pylist()}
    if (venue, symbol) in held:
        return False
    table.append([features_table.unruled_market_row(venue, symbol, market_type)])
    return True


def register_softly(catalog: Catalog, *, venue: str, symbol: str) -> bool | None:
    """`register_market` with the venue's type, and no exception ever leaves it.

    True: a row was written. False: the key was already there. None: it failed, and said so.
    """
    try:
        market_type = VENUE_REGISTRY[venue].market_type(symbol)
        added = register_market(catalog, venue=venue, symbol=symbol, market_type=market_type)
    except Exception as error:  # noqa: BLE001 -- ingest is the product; the list is not
        logger.warning(
            "%s %s: could not register its market: %s: %s",
            venue,
            symbol,
            type(error).__name__,
            error,
        )
        return None
    if added:
        logger.info("%s %s: registered as a %s market", venue, symbol, market_type)
    return added


def register_own_market(
    *, venue: str, symbol: str, catalog_uri: str, warehouse: str, storage: Mapping[str, str]
) -> bool | None:
    """Open the catalog and register, softly: an unreachable catalog is the same warning."""
    try:
        catalog = open_catalog(uri=catalog_uri, warehouse=warehouse, **dict(storage))
    except Exception as error:  # noqa: BLE001
        logger.warning(
            "%s %s: could not register its market: %s: %s",
            venue,
            symbol,
            type(error).__name__,
            error,
        )
        return None
    return register_softly(catalog, venue=venue, symbol=symbol)
