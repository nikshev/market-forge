---
id: OUT-2026-10-04-spec-trade-flow-features
step: spec
records: [REQ-WP-088]
commit: null
---

## What was decided

- **Derive the flow features from the stored bars, not from trades.** The first draft of this specification planned a
  trade-level producer in the ingest. Reading `tables/bars.py` showed every bar already stores
  `aggressive_buy_base`, `aggressive_sell_base`, `delta_base`, `trade_count`, `first_trade_id` and `last_trade_id`,
  and that `resample.fold` sums them over complete windows. So the data exists at every timeframe since each
  series' ingest started, with no change to ingest or resample. The requirement was amended in this step.
- **Base units, recorded as a deviation from PRD §15.4** in [[ADR-068]]: the bar stores the side split in base
  units and only the quote total. New features are named `*_base`; nothing is named `cvd` or `delta_notional`.
- **Runs, with breaks read from the bars.** A missing bar breaks the run. For venues with sequential trade ids a
  jump between bars, or an id span that differs from `trade_count` inside a bar, breaks it too.
- **Measured before relying on the id checks** (2026-10-04, live bars): Binance BTCUSDT 1m, 18,591 of 18,597 bars
  have span == count and 18,586 of 18,587 consecutive pairs are contiguous; ETHUSDT 15,665 of 15,672 and 15,663
  of 15,664. Bybit ids are not numeric; OKX ids are numeric but not sequential (2,682 of 2,734 bars disagree). So
  the checks are a registry flag, true for Binance only.
- Out of scope: book features, derivatives, the price-bin volume profile (needs trades by price; not in a bar),
  CVD-price divergence (ADR-013), a notional split.

## What is still open

- The notional version (store the quote split in the bar; [[ADR-068]]'s way back).
- Bybit and OKX cannot detect a missed trade inside a bar.
