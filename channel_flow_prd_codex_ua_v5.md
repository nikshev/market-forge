# PRD — ChannelFlow: Crypto Market Structure & Signal Radar

**Версія:** 1.0  
**Дата:** 2026-09-06  
**Статус:** Implementation-ready PRD for Codex  
**Основна мова реалізації:** Python 3.12+ для backend/research, TypeScript для web UI  
**Принцип:** analytics/alerts first; автоматичне виконання угод не входить у MVP

---

## 0. Інструкція для Codex

Цей документ є джерелом істини для реалізації. Codex повинен:

1. Реалізовувати систему інкрементально, за фазами та acceptance criteria з цього PRD.
2. Не додавати future leakage, look-ahead або repainting навіть якщо це покращує backtest.
3. Усі індикатори/ознаки на timestamp `t` повинні використовувати тільки дані з `event_time <= t` і тільки ті значення, які були доступні в реальному часі на момент прийняття рішення.
4. Розрізняти `event_time`, `exchange_time`, `block_time`, `ingest_time`, `bar_open_time`, `bar_close_time`.
5. Не переписувати історичні channel snapshots і signal snapshots після їх фіналізації.
6. Будь-яку модель ML/GMDH додавати лише після наявності сильних deterministic baselines та leakage tests.
7. Будь-який сигнал з probabilistic score повинен мати calibration metrics, а не лише accuracy.
8. Кожен feature повинен мати опис семантики, одиниці виміру, cadence, source, freshness та leakage policy.
9. Код повинен бути тестованим, deterministic у backtest mode та максимально однаковим між live і replay.
10. Нові exchange/DEX connectors мають реалізовувати спільний canonical interface.
11. У Phase 1–3 система не має автоматично відкривати позиції. Вона лише формує сигнали й alerts.
12. Всі числові пороги повинні бути конфігурованими; hard-coded trading thresholds заборонені, крім test fixtures.
13. Усі результати backtest/research повинні відтворюватися з versioned dataset + config + code commit hash + model artifact hash.
14. Перед оптимізацією продуктивності — correctness, replay parity і data integrity.

---

# 1. Executive Summary

## 1.1. Проблема

Потрібна система, яка автоматично сканує крипторинки та знаходить ситуації, де:

- ціна знаходиться поблизу верхньої/нижньої межі статистичного каналу;
- ціна тестує середню лінію каналу в напрямку тренду;
- є ознаки rejection / absorption / continuation / breakout-retest;
- order-flow, depth, volume profile, derivatives та DeFi liquidity підтверджують або спростовують сетап;
- сигнал не базується на індикаторі, який перемальовує історію;
- користувач отримує повідомлення в Telegram з deep-link на інтерактивний графік;
- кожний сигнал потім можна незалежно backtest-ити і перевірити walk-forward.

Початкова ідея “канал + відскок” повинна перетворитися на модульну **market-structure intelligence platform**, у якій канал — лише один тип структури, а рішення формується на основі кількох незалежних груп даних.

## 1.2. Основна гіпотеза продукту

Канал сам по собі не є достатнім edge. Потенційний edge може з’являтися в умовній ймовірності:

`P(rejection_success | channel_state, order_flow, volume_structure, derivatives, cross_venue, DeFi_liquidity, regime)`

Тому система повинна не лише відповідати “ціна біля upper boundary”, а приблизно:

```text
BTCUSDT PERP / 15m
Setup: upper-boundary rejection short
Channel direction: DOWN
Channel quality: 0.83
Position in channel: 0.94
OFI: bearish
Book persistence: bearish
CVD divergence: bearish
Volume profile: below VAH, rejected HVN edge
OI change: +3.1%
Funding z-score: +1.8
Liquidation pressure: long-heavy
DEX↔CEX basis: normalized
DEX liquidity above spot: thin
Estimated setup probability: 0.71
Expected path: middle line before invalidation
```

Система повинна вміти сказати й протилежне:

```text
NO ALERT
Reason: apparent ask wall has low persistence and high cancellation rate;
channel confidence low;
price is expanding beyond forecast interval.
```

---

# 2. Research conclusions, що впливають на дизайн

## 2.1. Repainting / look-ahead — критичний ризик

Багато chart-indicators можуть виглядати набагато точніше на історії, ніж у live, через:

- використання незакритого realtime bar;
- майбутні pivot confirmation bars;
- higher-timeframe data, яке історично виглядає “готовим” раніше, ніж було реально доступно;
- negative plotting offsets;
- recalculation на повній історії;
- використання майбутніх локальних extrema для побудови trend/channel lines.

### Product decision

ChannelFlow використовує **append-only signal/channel snapshots**. Коли бар фіналізовано:

- `channel_snapshot(t)` стає immutable;
- `signal_decision(t)` стає immutable;
- перерахунок моделі в майбутньому не має права змінити те, що система “бачила” на `t`.

В UI можна показати поточну модель каналу, але backtest і audit повинні використовувати historical snapshots, а не реконструйований сьогодні канал.

## 2.2. Order Flow Imbalance має емпіричну цінність

Література з market microstructure показує, що short-horizon price changes пов’язані з дисбалансом bid/ask queues та order flow. Multi-level OFI за кількома рівнями LOB містить більше інформації, ніж лише best bid/ask.

### Product decision

Має бути окремий `OrderFlowFeatureEngine`, що рахує:

- L1 queue imbalance;
- depth imbalance на 5/10/20/50 levels;
- OFI за змінами best bid/ask;
- multi-level OFI;
- add/cancel/trade decomposition;
- microprice;
- book slope/convexity;
- replenishment;
- persistence;
- cancellation bursts;
- absorption candidates.

Snapshot “велика стіна = support/resistance” не вважається достатнім сигналом.

## 2.3. Spoofing/phantom liquidity

Великі passive orders можуть швидко зникнути. Тому статична heatmap або snapshot imbalance можуть створювати фальшиве відчуття ліквідності.

### Product decision

Для кожної значної wall/price band рахувати:

- lifetime;
- cumulative displayed size;
- cancellation fraction;
- refill count;
- refill-to-trade ratio;
- executed fraction;
- distance from mid;
- wall migration speed;
- persistence score.

`wall_score` не повинен дорівнювати просто size.

## 2.4. Volume Profile — context, не прогноз

Volume Profile добре описує, де історично відбувалася торгова активність, але є backward-looking structural feature.

### Product decision

Використовувати:

- POC;
- VAH;
- VAL;
- HVN;
- LVN;
- distance to each node;
- whether channel boundary overlaps a volume node;
- whether middle-line overlaps POC/VWAP;

як contextual features, а не як standalone buy/sell generator.

## 2.5. DeFi не можна зводити до ще одного OHLCV feed

AMM market structure принципово відрізняється від CLOB:

- ціна визначається state/liquidity curve;
- у concentrated liquidity depth неоднорідна по price ticks;
- price impact залежить від активної ліквідності;
- LP mint/burn змінює майбутню depth map;
- арбітраж CEX↔DEX синхронізує ціни;
- gas/block latency/priority змінюють швидкість price discovery.

### Product decision

Для Uniswap v3-like CLMM будувати **virtual liquidity map**:

- active liquidity at current tick;
- liquidity per price band;
- liquidity to ±10/25/50/100 bps;
- USD notional needed to move price by X bps;
- tick crossings;
- net LP liquidity added/removed near spot;
- swap imbalance;
- price deviation from CEX consensus;
- inferred arbitrage pressure.

## 2.6. Price prediction як point estimate — неправильна головна мета

Система повинна прогнозувати не “BTC буде 113,421”, а:

- channel survival probability;
- rejection probability;
- breakout probability;
- target-before-invalidation probability;
- expected favorable/adverse excursion;
- uncertainty interval.

Для forecast channel бажано мати uncertainty-aware envelope, наприклад rolling quantile/conformal calibration.

---

# 3. Product Goals

## 3.1. Primary goals

1. Побудувати non-repainting adaptive price channel.
2. Виявляти high-quality boundary/middle-line setups.
3. Додати CEX microstructure confirmation.
4. Додати derivatives confirmation.
5. Додати DeFi market-structure confirmation.
6. Показувати все на інтерактивному графіку.
7. Надсилати alert у Telegram із URL на конкретний market/time/setup.
8. Мати replay/backtest, що максимально повторює live logic.
9. Створити foundation для GMDH/ML ranking.
10. Вміти пояснити, чому сигнал отримав score.

## 3.2. Secondary goals

- cross-exchange comparison;
- research notebook/export layer;
- signal analytics dashboard;
- configurable universe ranking;
- later optional dry-run execution.

## 3.3. Non-goals MVP

Не реалізовувати в MVP:

- auto trading real funds;
- HFT latency arbitrage;
- MEV bundle submission;
- private mempool execution;
- portfolio optimizer;
- options volatility surface;
- social/news sentiment;
- wallet copy trading;
- prediction-market integration.

---

# 4. User Stories

## US-001 — Scan markets

Як користувач, я хочу бачити список markets, відсортований за setup score, щоб швидко знайти найцікавіші ситуації.

## US-002 — Open exact chart state

Як користувач, я хочу натиснути кнопку в Telegram і відкрити графік саме на timestamp сигналу з усіма active overlays.

## US-003 — Verify non-repainting

Як researcher, я хочу порівняти historical snapshot каналу, який реально існував у той момент, із пізнішим станом моделі.

## US-004 — Explain setup

Як користувач, я хочу бачити contribution factors: channel, OFI, volume profile, derivatives, DeFi.

## US-005 — Backtest a setup family

Як researcher, я хочу backtest-ити `upper_rejection_short` окремо від `middle_continuation_short`.

## US-006 — Compare feature families

Як researcher, я хочу провести ablation:

- channel only;
- channel + order flow;
- channel + derivatives;
- channel + DEX;
- all combined.

## US-007 — Train ML/GMDH only on point-in-time features

Як researcher, я хочу гарантію, що training dataset не містить feature leakage.

---

# 5. Initial Market Scope

## 5.1. Phase 1 universe

Venue:

- Binance USDⓈ-M perpetuals;
- Binance Spot для spot/perp basis.

Symbols:

- BTCUSDT;
- ETHUSDT;
- SOLUSDT.

Timeframes:

- 1m;
- 5m;
- 15m;
- 1h.

Default alerts:

- 5m;
- 15m;
- 1h.

## 5.2. Phase 2 universe

- Top 20–50 liquid Binance USDⓈ-M perpetuals;
- Bybit linear perps;
- OKX swaps.

## 5.3. Phase 3 DeFi universe

Initial CLMM:

- Uniswap v3;
- Ethereum;
- Arbitrum;
- Base.

Initial pairs should be selected by overlap with CEX liquidity, preferably:

- WETH/USDC;
- WETH/USDT where economically meaningful;
- WBTC/WETH / WBTC-stable where sufficient liquidity;
- selected SOL exposure only when a suitable EVM representation is not misleading; Solana-native DEX support is separate.

Future:

- Uniswap v4;
- Aerodrome;
- PancakeSwap v3;
- Raydium/Orca/Meteora;
- Hyperliquid CLOB/perps.

---

# 6. System Architecture

## 6.1. Logical architecture

```text
                         ┌──────────────────────┐
                         │ Market Configuration │
                         └──────────┬───────────┘
                                    │
        ┌───────────────────────────┼──────────────────────────┐
        │                           │                          │
        ▼                           ▼                          ▼
┌───────────────┐          ┌────────────────┐        ┌────────────────┐
│ CEX Connectors│          │ EVM/DEX Adapter│        │ Optional Data  │
│ WS + REST     │          │ RPC + logs     │        │ Providers      │
└───────┬───────┘          └────────┬───────┘        └────────┬───────┘
        │                           │                         │
        └──────────────┬────────────┴─────────────┬───────────┘
                       ▼                          ▼
              ┌────────────────┐        ┌──────────────────┐
              │ Canonical Bus  │        │ Backfill Pipeline │
              └───────┬────────┘        └────────┬─────────┘
                      │                          │
                      └─────────────┬────────────┘
                                    ▼
                        ┌──────────────────────┐
                        │ Raw/Normalized Store │
                        │ ClickHouse + Parquet │
                        └──────────┬───────────┘
                                   │
                 ┌─────────────────┼────────────────────┐
                 │                 │                    │
                 ▼                 ▼                    ▼
          ┌─────────────┐   ┌───────────────┐   ┌───────────────┐
          │ Bar Builder │   │ LOB/OF Engine │   │ DEX State     │
          └──────┬──────┘   └───────┬───────┘   └───────┬───────┘
                 │                  │                   │
                 └──────────┬───────┴───────────┬──────┘
                            ▼                   ▼
                    ┌────────────────┐   ┌───────────────┐
                    │ Feature Engine │   │ Channel Engine│
                    └────────┬───────┘   └───────┬───────┘
                             │                   │
                             └────────┬──────────┘
                                      ▼
                              ┌──────────────┐
                              │Signal Engine │
                              └───────┬──────┘
                                      │
                           ┌──────────┴───────────┐
                           ▼                      ▼
                    ┌─────────────┐        ┌────────────┐
                    │ Telegram Bot│        │ API / Web  │
                    └─────────────┘        └─────┬──────┘
                                                ▼
                                        Lightweight Charts
```

## 6.2. Deployment stages

### MVP deployment

Docker Compose:

- `api`
- `worker`
- `ingest-binance`
- `postgres`
- `clickhouse`
- `redis` optional
- `web`

Без Kafka у першій runnable версії.

### Scale deployment

Коли universe/venues зростають, перейти до target product profile:

- Kafka-compatible durable event backbone;
- Apache Pinot як HOT realtime analytics layer;
- S3 + Parquet + Iceberg як canonical/history layer;
- Trino для distributed research SQL;
- DuckDB для local/notebook/CI analytics;
- separate feature workers;
- separate signal service;
- optional Kubernetes.

Redpanda може використовуватись як Kafka-compatible broker implementation.

## 6.3. Why not start with Kafka immediately

MVP повинен перевірити edge, а не distributed-systems design. Але interfaces будуються так, щоб `EventPublisher/EventConsumer` мали in-process та Kafka implementations.

## 6.4. Target Product Data Architecture — Pinot + Iceberg Lakehouse

Це **цільова продуктова архітектура** після MVP. Вона походить із окремого design decision щодо альтернатив ClickHouse: гарячий realtime-serving шар відокремлюється від довготривалого lakehouse/research шару.

Ключовий принцип:

- **Kafka** — центральний durable event log та replay boundary;
- **Apache Pinot** — HOT analytics для секундних/хвилинних запитів, scanner, dashboard та alerting;
- **S3 + Parquet + Iceberg** — immutable/canonical історія та довготривале сховище;
- **Trino** — distributed SQL поверх Iceberg для великих research/backtest joins;
- **DuckDB** — локальний/CI/notebook engine для дешевих ad-hoc експериментів по Parquet/Iceberg extracts;
- feature/research layer не повинен залежати від одного query engine.

### 6.4.1. Product architecture

```text
                CEX exchanges                    blockchain / DeFi nodes
          Binance / Bybit / OKX / ...       EVM RPC / WS / logs / Solana ...
                    │                                  │
                    └──────────────┬───────────────────┘
                                   │
                                   ▼
                         ┌──────────────────┐
                         │ Canonical Kafka  │
                         │ event backbone   │
                         └────────┬─────────┘
                                  │
                      ┌───────────┴────────────┐
                      │                        │
                      ▼                        ▼
              ┌──────────────┐          ┌──────────────┐
              │ Apache Pinot │          │      S3      │
              │     HOT      │          │ canonical/raw│
              │ realtime     │          └──────┬───────┘
              └──────┬───────┘                 │
                     │                         ▼
                     │                  ┌──────────────┐
                     │                  │   Parquet    │
                     │                  └──────┬───────┘
                     │                         │
                     │                         ▼
                     │                  ┌──────────────┐
                     │                  │   Iceberg    │
                     │                  │  Lakehouse   │
                     │                  └──────┬───────┘
                     │                         │
                     │                  ┌──────┴───────┐
                     │                  ▼              ▼
                     │             ┌────────┐     ┌────────┐
                     │             │ Trino  │     │ DuckDB │
                     │             └────┬───┘     └───┬────┘
                     │                  │             │
                     └──────────────────┴──────┬──────┘
                                               ▼
                                  ┌─────────────────────────┐
                                  │ Unified Analytics /     │
                                  │ Feature Access Layer    │
                                  └────────────┬────────────┘
                                               │
                  ┌────────────────────────────┼────────────────────────────┐
                  │                            │                            │
                  ▼                            ▼                            ▼
          ┌───────────────┐           ┌────────────────┐          ┌────────────────┐
          │ Live Scanner  │           │ Research /     │          │ Backtest /      │
          │ Signal Engine │           │ Feature Lab    │          │ Replay Engine   │
          └──────┬────────┘           └───────┬────────┘          └───────┬────────┘
                 │                            │                           │
                 │                            └────────────┬──────────────┘
                 │                                         ▼
                 │                                ┌─────────────────┐
                 │                                │ ML / GMDH /     │
                 │                                │ calibration     │
                 │                                └────────┬────────┘
                 │                                         │
                 └──────────────────────┬──────────────────┘
                                        ▼
                              ┌────────────────────┐
                              │ API / Web / Alerts │
                              │ Telegram / Signal  │
                              └────────────────────┘
```

### 6.4.2. Why split HOT and historical analytics

Не змушувати одну БД однаково добре виконувати дві дуже різні задачі:

**HOT path — Pinot**

- останні хвилини/години/дні залежно від dataset;
- low-latency scanner queries;
- current feature snapshots;
- cross-symbol ranking;
- dashboard drill-down;
- alert candidate selection;
- fast group-by/filter over streaming events.

**Historical/research path — Iceberg**

- повна історія market events;
- order-book derived datasets;
- DeFi logs/state snapshots;
- point-in-time feature datasets;
- walk-forward training sets;
- reproducible backtests;
- model training and experiment datasets.

Pinot є serving store, а Iceberg — canonical analytical history. Pinot не є єдиним source of truth.

### 6.4.3. Kafka topic families

Topic naming must preserve source, semantic type and schema version. Мінімальний набір:

```text
market.trade.v1
market.book_delta.v1
market.book_snapshot.v1
market.ticker.v1
market.mark_price.v1
derivatives.funding.v1
derivatives.open_interest.v1
derivatives.liquidation.v1

defi.raw.block.v1
defi.raw.log.v1
defi.raw.receipt.v1
defi.protocol.pool_discovered.v1
defi.protocol.swap.v1
defi.protocol.liquidity_change.v1
defi.protocol.state_checkpoint.v1
defi.protocol.reorg.v1
defi.normalized.swap.v1
defi.normalized.liquidity_state.v1
defi.normalized.depth_curve.v1
defi.normalized.price.v1
defi.gas.v1
hyperliquid.book.v1
hyperliquid.trade.v1
hyperliquid.asset_context.v1

feature.microstructure.v1
feature.channel.v1
feature.volume_profile.v1
feature.derivatives.v1
feature.defi.v1
feature.cross_venue.v1

signal.candidate.v1
signal.confirmed.v1
signal.invalidated.v1
```

Requirements:

- schema version is explicit;
- partition key normally `venue:symbol` or `chain:pool`;
- event time and ingestion time are separate;
- producer id and sequence/gap metadata are retained;
- all consumers must be replay-safe and idempotent where materialization occurs;
- raw topics may have shorter Kafka retention because canonical copies are persisted to S3, but retention must be long enough for operational replay/recovery.

### 6.4.4. S3 / Iceberg zones

```text
s3://channel-flow/raw/
    cex/trades/...
    cex/book_deltas/...
    derivatives/...
    defi/blocks/...
    defi/logs/...
    defi/receipts/...
    defi/protocol_events/...
    defi/state_checkpoints/...

s3://channel-flow/normalized/
    trades/...
    books/...
    swaps/...
    pool_liquidity/...
    executable_depth/...
    cex_dex_basis/...
    asset_registry/...

s3://channel-flow/features/
    microstructure/...
    channels/...
    volume_profile/...
    derivatives/...
    defi/...
    cross_venue/...

s3://channel-flow/research/
    datasets/...
    labels/...
    backtests/...
    experiments/...

s3://channel-flow/models/
    registry/...
    artifacts/...
    calibration/...
```

Iceberg tables are created for normalized, feature and research-grade datasets where snapshot isolation, schema evolution, partition evolution and reproducibility matter. Raw immutable payloads may remain plain compressed objects/Parquet when Iceberg metadata adds no value.

### 6.4.5. Query routing

Application code must not scatter Pinot/Trino/DuckDB-specific SQL throughout domain logic. Introduce explicit ports:

```python
class HotAnalyticsRepository(Protocol):
    ...

class HistoricalAnalyticsRepository(Protocol):
    ...

class FeatureRepository(Protocol):
    ...
```

Routing rule:

```text
"What is happening now?"
        -> Pinot

"What happened over a long period / across large history?"
        -> Trino + Iceberg

"I have a bounded research extract locally / in CI"
        -> DuckDB
```

Examples:

| Workload | Default engine |
|---|---|
| Top 20 current signal candidates | Pinot |
| BTC order-flow features for last 30 min | Pinot |
| Current DEX/CEX basis across universe | Pinot |
| 2-year walk-forward feature extraction | Trino/Iceberg |
| Join CEX trades + DEX swaps + funding over months | Trino/Iceberg |
| Local hypothesis test on a 20 GB Parquet extract | DuckDB |
| CI replay validation on fixture datasets | DuckDB |

### 6.4.6. Role of ClickHouse

ClickHouse remains supported as:

1. **MVP shortcut** when a single-node analytical database reduces implementation time;
2. optional deployment profile for users who prefer one analytical engine;
3. benchmark/reference backend behind repository interfaces.

It is **not** the mandatory long-term product architecture. The target scale architecture is Kafka + Pinot + S3/Parquet/Iceberg + Trino/DuckDB.

### 6.4.7. Point-in-time correctness across the platform

The split architecture must not break non-repainting guarantees. Every derived record must retain at least:

- `event_time`;
- `available_at`;
- `ingested_at`;
- `computed_at`;
- `source_sequence` where applicable;
- `feature_version`;
- `model_version`;
- `dataset_snapshot_id` for training/backtest materializations.

A backtest at logical time `t` may query only rows with:

```text
event_time <= t
available_at <= t
```

where `available_at` models when the system could actually have observed the data. This is required for CEX feeds, delayed provider data, on-chain finality and any asynchronously computed feature.

### 6.4.8. Live vs research parity

Feature transformations must be shared between live and offline execution. Preferred pattern:

```text
Canonical event
      │
      ▼
Pure/stateful feature operator
      │
      ├── live consumer -> Kafka/Pinot
      │
      └── replay reader -> Iceberg/DuckDB -> same operator
```

Do not maintain one Python implementation for live and a logically different SQL notebook implementation for backtests unless equivalence tests exist.

### 6.4.9. Retention tiers

Retention must be configurable per event family. Suggested semantics, not hard-coded durations:

- **Tier A / Pinot HOT:** enough history for live dashboards, feature windows and alert drill-down;
- **Tier B / Iceberg normalized:** full research history;
- **Tier C / raw archive:** source-of-truth payloads where re-normalization may be required;
- **Tier D / derived research artifacts:** retained by experiment/model lineage policy.

Do not retain full-depth order-book deltas indefinitely in Pinot solely because they exist. Pinot should contain the subset needed for HOT queries; full history belongs in object storage/Iceberg.

---

# 7. Technology Decisions

## Backend

- Python 3.12+
- FastAPI
- asyncio
- uvloop where supported
- Pydantic v2
- Polars for offline data processing
- NumPy/SciPy/statsmodels/scikit-learn
- SQLAlchemy or asyncpg for Postgres metadata
- clickhouse-connect or official driver

## Frontend

- React
- TypeScript
- Vite
- Lightweight Charts v5.x
- custom primitives/plugins for:
  - volume profile;
  - liquidity heatmap;
  - forecast bands;
  - channel areas;
  - signal annotations.

## Storage

### MVP profile

- ClickHouse: single-node time-series/events/features/research store for fastest path to validating edge
- PostgreSQL: configs, users, alerts, model registry metadata, signal state
- local/S3-compatible object storage: raw archives, model artifacts, experiment exports

### Target product profile

- Apache Pinot: HOT realtime analytical serving
- S3-compatible object storage: canonical durable data plane
- Parquet: columnar physical format
- Apache Iceberg: lakehouse table/catalog semantics for normalized/features/research data
- Trino: distributed historical/research SQL
- DuckDB: local/notebook/CI analytics over Parquet/Iceberg extracts
- PostgreSQL: transactional metadata/control plane
- ClickHouse: optional MVP/compatibility backend, not mandatory at scale

## Messaging

- MVP: in-process asyncio queues
- Target product: Kafka-compatible durable event backbone
- Redpanda may be used as a Kafka-compatible deployment choice when operationally preferable

## Notifications

- Telegram Bot API
- Signal integration only as optional later adapter

---

# 8. Build-vs-Borrow Decision

## 8.1. CEX feeds

Evaluate `cryptofeed` as a normalized public-feed adapter because it already supports trade/L2/funding/OI/liquidations across many crypto exchanges.

However:

- critical feeds must still have connector-level integration tests against exchange docs;
- do not hide sequence gaps or order-book reconstruction rules;
- native Binance connector may be preferred for Phase 1 if it yields clearer correctness/auditability.

## 8.2. Trading engine frameworks

NautilusTrader is a useful architectural reference because it emphasizes event-driven replay/live parity. Do not adopt it automatically unless it reduces complexity.

Freqtrade is useful as a reference for backtest UX, Telegram and lookahead-analysis, but its candle-centric strategy model is not sufficient by itself for microstructure + DeFi.

Hummingbot is useful as a connector/reference layer for CEX/DEX integration and cross-venue semantics.

### Decision

ChannelFlow owns its **analytics domain model**, signal semantics and historical snapshot invariants. External libraries are implementation dependencies, not domain authority.

---

# 9. Canonical Time Semantics

Every event must include:

```python
class EventMeta(BaseModel):
    source: str
    venue: str
    market_type: str
    symbol: str
    event_time_ns: int
    ingest_time_ns: int
    sequence: int | None
    source_event_id: str | None
```

Rules:

- `event_time`: timestamp assigned by exchange/blockchain where available;
- `ingest_time`: local receive timestamp;
- `sequence`: exchange sequence/update id;
- blockchain events also include `block_number`, `tx_index`, `log_index`, `tx_hash`;
- all normalized storage in UTC;
- UI may render local timezone.

No feature is allowed to depend on `ingest_time` as market information unless explicitly researching latency.

---

# 10. Canonical Market Data Models

## 10.1. Trade

```python
class TradeEvent:
    venue: str
    symbol: str
    event_time_ns: int
    trade_id: str
    price: Decimal
    qty_base: Decimal
    notional_quote: Decimal
    aggressor_side: Literal["buy", "sell", "unknown"]
    is_buyer_maker: bool | None
```

## 10.2. Order book delta

```python
class BookDelta:
    venue: str
    symbol: str
    event_time_ns: int
    first_update_id: int | None
    final_update_id: int | None
    prev_update_id: int | None
    bids: list[PriceLevel]
    asks: list[PriceLevel]
```

## 10.3. Book snapshot

```python
class BookSnapshot:
    venue: str
    symbol: str
    event_time_ns: int
    update_id: int
    bids: list[PriceLevel]
    asks: list[PriceLevel]
```

## 10.4. Derivatives state

```python
class DerivativesState:
    venue: str
    symbol: str
    event_time_ns: int
    mark_price: float | None
    index_price: float | None
    funding_rate: float | None
    next_funding_time: int | None
    open_interest_base: float | None
    open_interest_usd: float | None
    basis_bps: float | None
```

## 10.5. Liquidation

```python
class LiquidationEvent:
    venue: str
    symbol: str
    event_time_ns: int
    side: Literal["long_liquidated", "short_liquidated", "unknown"]
    price: float
    qty: float
    notional_usd: float
```

## 10.6. DEX swap

```python
class DexSwapEvent:
    chain_id: int
    dex: str
    pool: str
    token0: str
    token1: str
    block_number: int
    block_time: int
    tx_hash: str
    log_index: int
    amount0: Decimal
    amount1: Decimal
    price_token1_per_token0: Decimal
    notional_usd: Decimal | None
    sqrt_price_x96: int | None
    tick: int | None
    liquidity: int | None
```

## 10.7. DEX liquidity change

```python
class DexLiquidityEvent:
    chain_id: int
    dex: str
    pool: str
    event_type: Literal["mint", "burn", "collect", "modify"]
    block_number: int
    block_time: int
    tick_lower: int | None
    tick_upper: int | None
    liquidity_delta: int
    amount0: Decimal | None
    amount1: Decimal | None
```

---

# 11. Data Integrity Requirements

## 11.1. Local order book reconstruction

For exchanges with snapshot + delta semantics:

1. Start WS and buffer deltas.
2. Fetch REST snapshot.
3. Discard obsolete deltas.
4. Apply deltas by exact sequence rules.
5. On gap, mark book `STALE` and rebuild.
6. Never emit OFI/book features from an invalid/stale book.

Required status:

```python
BookHealth(
    valid: bool,
    gap_count: int,
    last_sequence: int,
    latency_ms: float,
    stale_ms: float,
)
```

## 11.2. Duplicate handling

Unique identity:

- CEX trade: `(venue, symbol, trade_id)`;
- DEX log: `(chain_id, tx_hash, log_index)`;
- bars: `(venue, symbol, timeframe, open_time)`;
- channel snapshot: `(model_version, venue, symbol, timeframe, bar_close_time)`;
- signal: immutable UUID plus deterministic `dedupe_key`.

## 11.3. Chain reorg handling

EVM connector must:

- mark logs as `pending` until confirmation threshold;
- support rollback of reorged raw events;
- produce finalized analytical events after configurable confirmations;
- allow low-latency “unconfirmed mode” separately, never mixing it silently with final historical data.

---

# 12. Bar Builder

Build OHLCV from normalized trades where possible instead of trusting only exchange klines.

Per bar store:

- open/high/low/close;
- base volume;
- quote volume;
- trade count;
- aggressive buy volume;
- aggressive sell volume;
- delta volume;
- VWAP;
- high/low timestamps;
- first/last trade IDs;
- `is_final`.

Timeframes:

- 1s optional research;
- 10s optional research;
- 1m;
- 5m;
- 15m;
- 1h;
- 4h future.

Signal generation default: only finalized bars unless strategy explicitly declares `intrabar=true`.

---

# 13. Channel Engine

## 13.1. Interface

```python
class ChannelModel(Protocol):
    def fit_predict(self, history: Frame, as_of: datetime) -> ChannelSnapshot: ...
```

```python
class ChannelSnapshot:
    as_of: datetime
    model_name: str
    model_version: str
    lookback: int
    center_now: float
    upper_now: float
    lower_now: float
    slope_normalized: float
    width_pct: float
    forecast_horizons: list[ChannelForecastPoint]
    quality: ChannelQuality
    source_max_event_time: datetime
```

Hard invariant:

```text
source_max_event_time <= as_of
```

## 13.2. Baseline A — Rolling Log-Price OLS

Input:

`y_i = log(close_i)`

Model:

`y_i = a + b * i + epsilon_i`

Center:

`center_i = exp(a + b*i)`

Width options:

- residual standard deviation baseline;
- robust MAD;
- empirical residual quantiles preferred.

Upper/lower:

`upper = exp(center_log + Q_high(residuals))`

`lower = exp(center_log + Q_low(residuals))`

Default quantiles:

- lower q=0.10;
- upper q=0.90.

Must be configurable.

## 13.3. Baseline B — Robust Regression Channel

Candidate estimators:

- Huber regression;
- Theil-Sen;
- RANSAC only as experimental due discontinuous model changes.

Goal: reduce sensitivity to liquidation wicks/outliers.

## 13.4. Baseline C — Quantile Regression Channel

Fit conditional quantiles directly:

- q10 lower;
- q50 center;
- q90 upper.

This supports asymmetric channels.

Required checks:

- quantile crossing correction;
- minimum width;
- slope consistency;
- numerical stability.

## 13.5. Baseline D — Kalman Local Linear Trend

State:

```text
level_t
slope_t
```

Observation:

`log_price_t = level_t + noise`

Use recursive filtering only. Smoother that uses future observations is forbidden for live-compatible features.

Potential outputs:

- level;
- slope;
- state uncertainty;
- adaptive band based on innovation variance.

## 13.6. Experimental E — Robust Trend Filter

Optional batch/online approximation using robust loss and first/second-difference regularization.

Must not use centered filters that implicitly consume future data in live mode.

## 13.7. Forecast channel

For horizon `h`:

- forecast center;
- forecast lower/upper;
- uncertainty;
- calibrated empirical coverage.

No UI claim “точний прогноз”. UI terminology:

- `forecast corridor`;
- `expected channel`;
- `uncertainty band`.

## 13.8. Conformal calibration layer

Optional after baseline:

- rolling residual calibration;
- adaptive conformal or time-series aware interval calibration;
- target coverage 80/90/95% configurable.

Track:

- empirical coverage;
- mean interval width;
- conditional coverage by volatility regime.

## 13.9. Channel Quality Score

`channel_quality` in `[0,1]` composed from normalized submetrics:

1. `coverage_score` — fraction of closes inside channel;
2. `touch_consistency` — meaningful interactions with boundaries;
3. `slope_stability` — low violent sign flipping;
4. `width_stability`;
5. `residual_structure_penalty` — reduce score if residuals trend strongly;
6. `outlier_penalty`;
7. `forecast_calibration_score`;
8. `age_score` — channel has existed long enough;
9. `regime_compatibility`.

Initial formula should be transparent weighted average. ML scoring later.

## 13.10. Channel Position

Normalized coordinate:

`position = (price - lower) / (upper - lower)`

Interpretation:

- `<0`: below channel;
- `0`: lower boundary;
- `0.5`: center;
- `1`: upper boundary;
- `>1`: above channel.

Use log-price equivalent if channel is defined in log space.

## 13.11. Zones

Default config:

```yaml
zones:
  lower: [0.00, 0.12]
  middle: [0.44, 0.56]
  upper: [0.88, 1.00]
  overshoot_tolerance: 0.08
```

These are research defaults, not “proven” parameters.

---


# 13A. Price Extremum / Turning Point Engine

This subsystem detects and forecasts meaningful local price maxima/minima without violating the project's non-repainting and point-in-time guarantees.

It must explicitly distinguish three concepts that are often incorrectly mixed by technical indicators:

1. **Observed running extreme** — the highest/lowest price seen so far in a causal window.
2. **Confirmed structural extremum** — a swing high/low that can only be confirmed after sufficient reversal evidence has appeared.
3. **Forecast turning point** — a probabilistic real-time statement that a local maximum/minimum is forming now or is likely within a future horizon.

The engine must never label a bar as a real-time confirmed maximum/minimum using information that was unavailable at that bar.

## 13A.1. Core semantic rule

For every extremum-related output store both:

- `extremum_time` — time of the price point that eventually became the high/low;
- `known_at` — first timestamp when the system was legally able to know/confirm that fact.

Therefore:

```text
extremum_time != known_at
```

is expected for confirmed pivots.

Example:

```text
10:00 price makes a local high
10:15 price starts falling
10:30 reversal threshold is exceeded

extremum_time = 10:00
known_at      = 10:30
confirmation_lag = 2 bars
```

Any backtest that acts on the 10:00 label before 10:30 is invalid.

## 13A.2. Required output states

Every potential turning point moves through an append-only lifecycle:

```text
OBSERVING
   ↓
CANDIDATE_HIGH / CANDIDATE_LOW
   ↓
FORECAST_HIGH / FORECAST_LOW
   ↓
CONFIRMED_HIGH / CONFIRMED_LOW
   ↓
RESOLVED
```

Alternative branches:

```text
CANDIDATE_* → INVALIDATED
FORECAST_*  → INVALIDATED
```

Historical rows are never rewritten to make the prediction appear earlier.

Use correction/invalidation events where required by exchange corrections or chain reorg semantics.

## 13A.3. Extremum classes

The engine supports multiple scales simultaneously.

### Micro extremum

Typical horizon:

- seconds to a few minutes;
- L2/order-flow dominated;
- useful for entry timing.

### Local swing extremum

Typical horizon:

- 5–100 bars;
- channel/volatility/volume structure dominated;
- useful for channel rejection and continuation setups.

### Regime extremum

Typical horizon:

- hours to days or longer;
- larger trend/regime transition;
- requires multi-timeframe confirmation.

No single extremum definition is allowed to silently serve all three scales.

## 13A.4. Ground-truth labels for research only

Retrospective research labels may use symmetric neighborhoods:

For radius `k`, a local maximum at `t` is:

```text
high[t] >= max(high[t-k : t+k])
```

and a local minimum:

```text
low[t] <= min(low[t-k : t+k])
```

These labels are **offline targets only** because they use future observations.

Store metadata:

```text
label_method = SYMMETRIC_K_NEIGHBORHOOD
radius_bars = k
future_bars_used = k
live_eligible = false
```

Do not expose such labels to live feature generation.

## 13A.5. Structural baseline A — Directional Change / volatility-adaptive swing

The primary non-ML structural baseline should be an event-based directional-change detector.

Maintain a running high during an upswing and a running low during a downswing.

A high becomes confirmed only after price reverses by a threshold `theta` from that running high.

A low becomes confirmed only after price reverses upward by `theta` from the running low.

Threshold modes:

```text
FIXED_BPS
ATR_MULTIPLE
REALIZED_VOL_MULTIPLE
CHANNEL_WIDTH_FRACTION
HYBRID
```

Example adaptive threshold:

```text
theta_t = max(
    min_bps,
    atr_multiplier * ATR_t / price_t,
    vol_multiplier * realized_vol_t,
)
```

Required outputs:

- current directional-change state;
- running extreme price/time;
- reversal distance in bps;
- threshold in bps;
- overshoot size;
- bars/time since last confirmed extremum;
- extremum prominence;
- confirmation lag.

The threshold must be point-in-time and cannot be retroactively optimized per swing.

## 13A.6. Structural baseline B — prominence-aware causal pivots

Noise can create many tiny extrema. Add prominence filtering.

A candidate extremum becomes structurally meaningful only if its excursion from the surrounding causal baseline exceeds configurable minimum significance.

Possible significance units:

- bps;
- ATR;
- channel-width fraction;
- realized-vol sigma;
- traded-volume-normalized move.

Example:

```text
prominence_atr >= 0.8
AND
bars_since_previous_extremum >= 3
```

For research diagnostics, SciPy-like peak concepts such as prominence, width and plateau size may be reproduced, but production logic must remain causal. Centered/offline peak-finding may only create labels and diagnostics, never live signals.

## 13A.7. Structural baseline C — channel-conditioned extrema

ChannelFlow has an advantage over generic peak detectors because extrema can be interpreted relative to the active channel.

Store:

```text
extremum_channel_position
extremum_distance_to_upper_bps
extremum_distance_to_lower_bps
extremum_distance_to_mid_bps
extremum_channel_slope
extremum_channel_width
```

Useful classes:

```text
UPPER_BOUNDARY_HIGH
LOWER_BOUNDARY_LOW
MIDLINE_REJECTION_HIGH
MIDLINE_REJECTION_LOW
BREAKOUT_EXHAUSTION_HIGH
BREAKOUT_EXHAUSTION_LOW
INTERNAL_NOISE_EXTREMUM
```

The classifier is deterministic first; ML may later refine confidence.

## 13A.8. Causal slope and curvature estimator

A turning point can be represented as a change in the sign of local trend velocity.

For a causal smooth price estimate `m(t)` compute:

```text
v_t = dm/dt

a_t = d²m/dt²
```

Candidate maximum:

```text
v crosses from positive to <= 0
AND
a < 0
```

Candidate minimum:

```text
v crosses from negative to >= 0
AND
a > 0
```

However raw finite differences of price are too noisy. Production implementations must estimate slope/curvature from a causal smoother.

Allowed causal baselines:

- trailing local polynomial regression;
- Kalman local-linear-trend model;
- EWMA-derived slope;
- one-sided robust regression;
- one-sided Savitzky-Golay-equivalent coefficients if implemented and tested explicitly as causal.

**Forbidden in live mode:** centered smoothing windows that consume future bars.

Centered Savitzky-Golay may be used only for retrospective label diagnostics and must be marked `live_eligible=false`.

## 13A.9. Preferred causal local-polynomial baseline

For each bar `t`, fit only the trailing window:

```text
x ∈ {-N+1, ..., -1, 0}
```

on log-price:

```text
p(x) = b0 + b1*x + b2*x² [+ b3*x³]
```

At current time `x=0`:

```text
level        = b0
slope        = b1
curvature    = 2*b2
jerk         = 6*b3   # optional
```

Normalize:

```text
slope_norm = slope / recent_volatility
curvature_norm = curvature / recent_volatility
```

This provides stable derivative features without future data.

Default polynomial order must remain low (`2` or `3`) to reduce oscillatory overfit.

## 13A.10. Kalman turning-point baseline

Implement an optional local-linear-trend state-space model:

```text
level_t = level_{t-1} + slope_{t-1} + noise_level
slope_t = slope_{t-1} + noise_slope
price_t = level_t + observation_noise
```

Expose filtered, not smoothed, state in live mode:

- `kalman_level`;
- `kalman_slope`;
- `kalman_slope_variance`;
- `P(slope > 0)` approximation;
- `P(slope < 0)` approximation.

A possible maximum candidate occurs when posterior slope probability moves from strongly positive toward negative.

A possible minimum candidate is symmetric.

Offline Kalman smoothing may not be used in live/replay feature generation because smoothing uses future observations.

## 13A.11. GMDH derivative hypothesis

GMDH is explicitly allowed as a candidate turning-point forecaster.

Preferred use: GMDH predicts a smooth **forward conditional price path or return path** over bounded horizon `h ∈ [0,H]`.

Example polynomial path:

```text
P_hat(h) = c0 + c1*h + c2*h² + c3*h³
```

Then:

```text
dP_hat/dh  = c1 + 2*c2*h + 3*c3*h²

d²P_hat/dh² = 2*c2 + 6*c3*h
```

Forecast maximum candidate at `h*` if:

```text
dP_hat/dh(h*) = 0
AND
d²P_hat/dh²(h*) < 0
AND
0 < h* <= H
```

Forecast minimum candidate if:

```text
dP_hat/dh(h*) = 0
AND
d²P_hat/dh²(h*) > 0
AND
0 < h* <= H
```

The engine outputs:

```text
turn_type
predicted_turn_horizon_bars
predicted_turn_time
predicted_extreme_price
first_derivative_at_now
second_derivative_at_turn
turn_probability
path_uncertainty
```

### Critical limitation

A zero derivative of a polynomial forecast is **not sufficient evidence** of a tradable extremum.

Reasons:

- polynomial extrapolation may oscillate;
- a root can appear from tiny coefficient changes;
- the forecast may be poorly calibrated;
- multiple derivative roots may exist;
- the predicted root may be outside the region supported by data;
- price can plateau rather than reverse;
- market microstructure can invalidate the smooth path immediately.

Therefore GMDH derivative output is one feature/family in the turning-point ensemble, not the final truth.

## 13A.12. GMDH derivative root filtering

Only accept a derivative root candidate when all required conditions hold:

1. `0 < h* <= H_max`;
2. predicted path remains within configured extrapolation bounds;
3. derivative root is stable across bootstrap/ensemble members;
4. root-time dispersion is below threshold;
5. predicted excursion from current price exceeds fees/noise floor;
6. second derivative magnitude exceeds minimum curvature threshold;
7. no gross conflict with data-quality state;
8. model passed current walk-forward promotion gate.

Example stability metrics:

```text
root_presence_rate      >= 0.70
root_horizon_iqr_bars   <= 3
turn_type_agreement     >= 0.80
```

These are research defaults, not assumed production constants.

## 13A.13. Direct ML targets — required even if GMDH derivative works

Do not depend only on a derivative-based target. Build direct supervised targets too.

### Target E — turning point within horizon

Classification:

```text
P(local_max_within_H | state_t)
P(local_min_within_H | state_t)
```

Use only labels defined by a predeclared structural/offline rule.

### Target F — extremum time

Conditional regression/survival target:

```text
E[time_to_next_max]
E[time_to_next_min]
```

or hazard formulation:

```text
P(turn occurs at h | no turn before h, state_t)
```

### Target G — extremum price / excursion

Predict distributions, not only point estimates:

```text
Q10/Q50/Q90(next_H_max_return)
Q10/Q50/Q90(next_H_min_return)
```

Equivalent trading-oriented targets:

- MFE within H;
- MAE within H;
- maximum upside excursion before next structural low;
- maximum downside excursion before next structural high.

### Target H — no-turn regime

Classification:

```text
P(no meaningful extremum within H)
```

This prevents the model from being forced to invent a top/bottom in strong trends.

## 13A.14. Turning Point feature families

The turning-point model may consume point-in-time features from all existing engines.

### Price/channel structure

- channel position;
- distance to upper/middle/lower;
- channel slope;
- channel slope change;
- channel width;
- width expansion/contraction;
- trailing return by horizon;
- causal slope;
- causal curvature;
- distance from running high/low;
- directional-change overshoot.

### Order book / flow

- L1 queue imbalance;
- multi-level depth imbalance;
- OFI and OFI change;
- CVD and CVD divergence;
- microprice deviation;
- spread expansion;
- wall persistence;
- cancellation rate;
- replenishment;
- absorption score.

Example maximum hypothesis:

```text
price near upper boundary
+ positive price momentum decelerating
+ aggressive buys continue
+ ask replenishment persists
+ OFI turns negative
→ possible absorption/exhaustion high
```

Example minimum hypothesis is symmetric.

### Volume structure

- POC/VAH/VAL distance;
- HVN/LVN distance;
- local volume spike;
- failed auction / low-volume rejection context;
- volume-price divergence.

### Derivatives

- funding z-score;
- OI level/change;
- basis;
- liquidation imbalance;
- liquidation burst distance;
- long/short squeeze context where available.

### DeFi / cross-venue

- DEX-CEX executable basis by notional;
- DEX depth asymmetry;
- liquidity within ±bps;
- swap imbalance;
- LP mint/burn around current price;
- tick/liquidity migration;
- inferred arbitrage pressure;
- gas/finality state.

## 13A.15. Turning Point ensemble

The first production-capable score should be interpretable.

Example families:

```text
structural_reversal       0..25
derivative_state          0..15
channel_location          0..15
order_flow_exhaustion     0..20
volume_context            0..10
derivatives_context       0..10
defi_crossvenue_context   0..5
```

Return separate scores for:

```text
P_MAX_SCORE
P_MIN_SCORE
```

Do not force them to sum to 100 because `NO_TURN` is a valid state.

Later ML outputs should expose calibrated probabilities:

```text
P(max within H)
P(min within H)
P(no turn within H)
```

## 13A.16. Multi-horizon output

A maximum/minimum prediction without horizon is meaningless.

Required horizons should be configurable, e.g.:

```text
H = 3 bars
H = 6 bars
H = 12 bars
H = 24 bars
```

Store predictions independently by horizon.

Example:

```text
BTCUSDT 15m

P(max <= 3 bars)   = 0.31
P(max <= 6 bars)   = 0.58
P(max <= 12 bars)  = 0.74
P(min <= 12 bars)  = 0.12
P(no turn <=12)    = 0.14
```

Never present a single probability without its horizon and model version.

## 13A.17. Multi-timeframe hierarchy

Extrema should be computed independently on each timeframe and optionally linked.

Example:

```text
5m  candidate high
15m candidate high
1h  still strong positive slope
```

This is not equivalent to a 1h top.

Create optional confluence features:

- lower-TF top inside higher-TF upper zone;
- higher-TF slope sign;
- higher-TF distance to boundary;
- nested directional-change state;
- time since higher-TF extremum.

Do not upsample a higher-timeframe future close into lower-timeframe features before that higher-timeframe bar is finalized.

## 13A.18. Online Change Point detector

Add an optional regime-change detector separate from extrema.

Candidate methods:

- Bayesian Online Change Point Detection;
- CUSUM/Page-Hinkley variants;
- state transition detector over volatility/slope/liquidity features.

Purpose:

```text
P(current trend-generating regime changed)
```

A change point is not automatically a max/min, but it can strengthen a turning-point candidate.

Example:

```text
slope deceleration
+ BOCPD regime-change probability spike
+ OFI sign reversal
+ upper-channel location
→ higher maximum-candidate confidence
```

Only online/filtering variants are allowed in live mode.

## 13A.19. Canonical domain models

```python
class ExtremumCandidate:
    candidate_id: UUID
    instrument_id: str
    venue_scope: str
    timeframe: str
    candidate_type: Literal["HIGH", "LOW"]
    candidate_time: datetime
    observed_at: datetime
    price: Decimal
    method: str
    horizon_bars: int | None
    structural_score: float
    derivative_score: float | None
    channel_position: float | None
    feature_snapshot_id: UUID
    model_version: str | None
    data_quality: str


class TurningPointForecast:
    forecast_id: UUID
    candidate_id: UUID | None
    instrument_id: str
    timeframe: str
    as_of: datetime
    horizon_bars: int
    p_max: float
    p_min: float
    p_no_turn: float
    predicted_turn_bars: float | None
    predicted_extreme_price: Decimal | None
    predicted_return: float | None
    derivative_now: float | None
    curvature_at_turn: float | None
    uncertainty_low: float | None
    uncertainty_high: float | None
    feature_snapshot_id: UUID
    model_version: str


class ConfirmedExtremum:
    extremum_id: UUID
    instrument_id: str
    timeframe: str
    extremum_type: Literal["HIGH", "LOW"]
    extremum_time: datetime
    known_at: datetime
    price: Decimal
    confirmation_method: str
    confirmation_lag_bars: int
    reversal_bps: float
    prominence_bps: float | None
    prominence_atr: float | None
    channel_class: str | None
    source_candidate_id: UUID | None
```

All models are immutable after finalization.

## 13A.20. Kafka events

Add event families:

```text
extremum.candidate.v1
extremum.forecast.v1
extremum.confirmed.v1
extremum.invalidated.v1
extremum.resolved.v1
```

Partition key:

```text
canonical_instrument_id + timeframe
```

Ordering must be preserved per instrument/timeframe stream.

## 13A.21. HOT / historical storage

Pinot HOT datasets:

```text
hot_extremum_candidates
hot_turning_point_forecasts
hot_confirmed_extrema
```

Iceberg canonical tables:

```text
extremum_candidates
turning_point_forecasts
confirmed_extrema
extremum_outcomes
```

Required point-in-time columns:

```text
event_time
observed_at
available_at
computed_at
known_at
model_version
feature_snapshot_id
```

## 13A.22. Extremum outcome

Forecast performance must be measured separately from original immutable forecast.

```python
class ExtremumForecastOutcome:
    forecast_id: UUID
    horizon_end: datetime
    realized_max_price: Decimal
    realized_max_time: datetime
    realized_min_price: Decimal
    realized_min_time: datetime
    structural_turn_occurred: bool
    realized_turn_type: str | None
    turn_time_error_bars: float | None
    turn_price_error_bps: float | None
    max_excursion_bps: float
    min_excursion_bps: float
```

Outcome generation runs only after the horizon is complete.

## 13A.23. Evaluation metrics

### Confirmed structural extrema

- average confirmation lag;
- median confirmation lag;
- false swing rate;
- prominence distribution;
- extrema per day/bar count;
- scale stability.

### Turning-point classification

- PR-AUC separately for high and low;
- ROC-AUC only as secondary metric;
- Brier score;
- log loss;
- calibration/ECE;
- precision at alert threshold;
- recall of meaningful extrema;
- false alarms per 1000 bars.

### Time prediction

- MAE in bars to extremum;
- median absolute error;
- interval coverage;
- conditional error by volatility regime.

### Price prediction

- extreme-price error in bps;
- quantile pinball loss;
- interval coverage;
- MFE/MAE forecast calibration.

### Trading relevance

Do not optimize only classification accuracy. Also evaluate:

- post-alert excursion before invalidation;
- target-before-stop probability;
- expected R after fees/slippage;
- value added over channel-only setup;
- value added over a simple directional-change baseline.

## 13A.24. Alert semantics

Turning point alerts must not say:

```text
"BTC TOP CONFIRMED"
```

when only a forecast exists.

Use explicit language in the product payload:

```text
POTENTIAL_LOCAL_MAX
POTENTIAL_LOCAL_MIN
CONFIRMED_SWING_HIGH
CONFIRMED_SWING_LOW
```

Example payload:

```text
BTCUSDT 15m — POTENTIAL LOCAL MAX

P(max within 6 bars): 72%
P(min within 6 bars): 9%
Channel position: 0.96
Causal slope: + but decelerating
Curvature: negative
OFI: turned negative
Ask replenishment: high
OI: rising
DEX liquidity above spot: thin

Predicted turn: 2–5 bars
Model: tp-gmdh-2026-09-xx
```

The chart deep-link must open the exact point-in-time state.

## 13A.25. UI requirements

Chart overlays:

- hollow marker = candidate extremum;
- probability cone/band = forecast window;
- filled marker = confirmed extremum;
- visually distinct `known_at` marker/line;
- optional derivative/slope pane;
- optional P(max)/P(min) pane.

In `AS-SEEN-THEN` mode:

- a confirmed marker must not appear before `known_at`;
- retrospective labels must be hidden by default;
- forecasts show the model values as they existed at that timestamp.

In `RESEARCH LABELS` mode only:

- symmetric future-aware local extrema may be displayed with a strong visual warning.

## 13A.26. API

Suggested endpoints:

```text
GET /api/v1/extrema/current
GET /api/v1/extrema/history
GET /api/v1/extrema/{extremum_id}
GET /api/v1/turning-points/forecasts
GET /api/v1/turning-points/forecast/{forecast_id}
GET /api/v1/turning-points/metrics
```

Filters:

- instrument;
- venue scope;
- timeframe;
- type high/low;
- horizon;
- min probability;
- confirmation method;
- model version;
- time range.

## 13A.27. Configuration

```yaml
extrema:
  enabled: true

  directional_change:
    enabled: true
    threshold_mode: hybrid
    min_bps: 15
    atr_multiplier: 0.8
    vol_multiplier: 0.5

  local_polynomial:
    enabled: true
    lookback_bars: 31
    order: 2
    robust: true

  kalman:
    enabled: true

  prominence:
    min_atr: 0.6
    min_bars_between: 3

  horizons_bars: [3, 6, 12, 24]

  forecast:
    enabled: false   # enable after Phase 7 validation
    model: gmdh
    min_probability_alert: 0.70

  gmdh_derivative:
    max_root_horizon_bars: 24
    min_root_presence_rate: 0.70
    max_root_horizon_iqr_bars: 3
    min_turn_type_agreement: 0.80
```

Config values above are research defaults and must not be treated as optimized constants.

## 13A.28. Non-repainting tests

Mandatory automated tests:

### Test A — future-bar invariance

Compute live outputs up to `t`.

Append arbitrary bars after `t`.

Assert all finalized outputs with `available_at <= t` remain byte-equivalent.

### Test B — candidate chronology

A candidate may be invalidated later, but its original snapshot cannot change.

### Test C — confirmation legality

```text
known_at >= extremum_time
```

and the confirmation logic must not read events with `available_at > known_at`.

### Test D — centered filter prohibition

Production feature path fails validation if a transform declares symmetric/centered future dependence.

### Test E — replay parity

Live recorded outputs and deterministic replay outputs must match for the same event stream/config/model artifact.

### Test F — GMDH derivative root stability

Small perturbations within a configured tolerance must not create silently unstable promoted roots. Record root sensitivity metrics.

## 13A.29. Failure modes

Explicitly protect against:

1. tiny noisy pivots generating alert spam;
2. fixed threshold failing across volatility regimes;
3. centered smoothing causing hidden look-ahead;
4. polynomial derivative producing unstable roots;
5. strong trend being misclassified repeatedly as a top/bottom;
6. liquidation wick becoming a fake structural extremum;
7. stale order book producing false exhaustion evidence;
8. DEX state lag/finality causing false cross-venue confluence;
9. multi-timeframe leakage from unfinished higher-timeframe candles;
10. threshold selection overfitting to historical PnL.

## 13A.30. Recommended implementation order

1. Offline symmetric labels for evaluation only.
2. Directional-change confirmed swing baseline.
3. Causal local-polynomial slope/curvature.
4. Kalman filtered slope baseline.
5. Channel-conditioned extremum classes.
6. Order-flow/volume/derivatives/DeFi confluence features.
7. Turning-point scoring baseline.
8. Walk-forward evaluation.
9. Direct probabilistic baseline models.
10. GMDH turning-point model.
11. GMDH derivative roots and stability ensemble.
12. Alert promotion only after calibration and incremental-value tests.

The product must remain useful even if steps 10–11 produce `NO_EDGE`.


# 14. Volume Structure Engine

## 14.1. Volume Profile

Compute true trade-based volume by price bins from exchange trades where available.

Do not infer buy/sell direction from candle color if aggressor-side trades are available.

Outputs:

- POC;
- VAH;
- VAL;
- value-area percentage configurable, default 70%;
- HVNs;
- LVNs;
- profile entropy;
- profile skew;
- distance-to-POC bps;
- distance-to-VAH/VAL bps;
- nearest HVN/LVN;
- node overlap with channel boundaries.

Profiles:

- rolling 4h;
- rolling 24h;
- rolling 7d;
- anchored session/day;
- anchor from significant impulse optional.

## 14.2. VWAP family

- rolling VWAP;
- daily/session VWAP;
- anchored VWAP optional;
- deviations in bps and volatility units.

## 14.3. Volume anomaly

Compute:

- volume z-score;
- aggressive buy/sell volume z-score;
- trade count z-score;
- large trade share;
- average trade size;
- percentile vs trailing distribution.

---

# 15. CEX Order Flow / LOB Engine

## 15.1. Queue Imbalance

L1:

`QI = (bid_qty - ask_qty) / (bid_qty + ask_qty)`

Multi-depth generalized:

`DI_k = (sum_bid_depth_k - sum_ask_depth_k) / total_depth_k`

Compute at:

- top 1;
- 5;
- 10;
- 20;
- 50 levels;
- fixed distance bands: ±5/10/25/50 bps.

## 15.2. Microprice

Approximate microprice from best bid/ask weighted by opposite queue size.

Features:

- microprice-mid spread;
- microprice direction;
- microprice momentum.

## 15.3. Order Flow Imbalance

Implement Cont-style top-of-book OFI and multi-level extensions.

Required event components:

- bid price increases/decreases;
- ask price increases/decreases;
- bid size change;
- ask size change.

Aggregate windows:

- 1s;
- 5s;
- 30s;
- 1m;
- one signal timeframe bar.

## 15.4. Trade imbalance / CVD

Signed trade notional:

`delta_t = aggressive_buy_notional - aggressive_sell_notional`

CVD:

`CVD_t = CVD_{t-1} + delta_t`

Features:

- delta per bar;
- CVD slope;
- CVD-price divergence;
- CVD acceleration;
- normalized delta / total volume.

## 15.5. Book shape

- spread bps;
- depth within X bps;
- bid/ask depth ratio;
- slope of cumulative depth curve;
- convexity;
- depth concentration;
- gap to next significant liquidity level.

## 15.6. Liquidity wall lifecycle

Define dynamic wall candidates from anomalous size relative to neighboring levels.

Store lifecycle:

```python
WallState:
    side
    price_band
    first_seen
    last_seen
    max_size
    avg_size
    executed_size_est
    cancelled_size_est
    refill_count
    move_count
    persistence_ms
```

Scores:

- size z-score;
- persistence;
- execution fraction;
- cancellation penalty;
- proximity;
- refill behavior.

## 15.7. Absorption

Candidate bearish absorption near upper boundary:

- strong aggressive buys;
- price fails to advance materially;
- ask depth replenishes;
- microprice weakens;
- local high fails.

Candidate bullish absorption symmetric.

Absorption is a feature/event, not a guaranteed signal.

---

# 16. Derivatives Feature Engine

## 16.1. Funding

Features:

- current funding;
- trailing mean/std;
- funding z-score;
- funding acceleration;
- cross-venue funding dispersion;
- predicted/next funding when source provides it.

## 16.2. Open Interest

- OI absolute USD;
- OI change 1m/5m/15m/1h;
- OI z-score;
- OI/volume ratio;
- price/OI regime.

Interpretation matrix stored as feature, not hard-coded trading truth:

```text
price up + OI up    => new risk entering / trend participation candidate
price up + OI down  => short-covering candidate
price down + OI up  => new shorts / risk build candidate
price down + OI down=> long liquidation/de-risk candidate
```

## 16.3. Basis

- perp vs spot basis bps;
- mark vs index premium;
- CEX-to-CEX basis dispersion;
- DEX marginal price vs CEX consensus.

## 16.4. Liquidations

Aggregate:

- long liquidation USD 1m/5m/15m;
- short liquidation USD;
- net liquidation imbalance;
- liquidation intensity / volume;
- liquidation clusters by price;
- time since liquidation spike.

## 16.5. Long/short ratios

Optional feature family when reliable/public:

- global account ratio;
- top-trader account ratio;
- top-trader position ratio.

Must be labeled provider-specific and not assumed to represent the whole market.

---

# 17. Cross-Venue Engine

## 17.1. Consensus price

Create robust consensus mid from selected high-liquidity venues.

Possible method:

- median of normalized mids;
- volume/depth weighted median experimental.

## 17.2. Lead-lag features

For same underlying:

- Binance return last 1/5/10s;
- Bybit return;
- OKX return;
- DEX marginal return;
- pairwise lagged correlations;
- event-based lead-lag research offline.

Do not convert correlation to trading rule without OOS validation.

## 17.3. Cross-venue basis

`basis_bps(venue_i) = 10000 * (mid_i / consensus_mid - 1)`

## 17.4. Fragmentation / liquidity

- depth by venue at 10/25/50bps;
- best effective execution venue for fixed notional sizes;
- concentration of liquidity across venues.

---


# 18. DeFi Ingestion Architecture

This section defines the **canonical on-chain ingestion subsystem**. It is intentionally separate from the DeFi feature engine: ingestion must reconstruct protocol state faithfully before any predictive feature or signal is calculated.

Core principle:

```text
Do not normalize away protocol semantics too early.

raw chain/exchange event
        ↓
protocol-native decoded event/state
        ↓
protocol-specific state reconstruction
        ↓
normalized market/liquidity primitives
        ↓
features / cross-venue analytics / signals
```

A Uniswap v3 tick, a Curve amplification parameter, an Aerodrome v2 reserve update and a Hyperliquid L2 level are **not** equivalent raw objects. They may become comparable only after conversion into common primitives such as executable depth, marginal price, signed flow, slippage and liquidity asymmetry.

## 18.1. High-level DeFi ingestion topology

```text
                           ┌──────────────────────────────────────────────┐
                           │              SOURCE LAYER                    │
                           └──────────────────────────────────────────────┘

 EVM RPC / WS                Archive RPC               Hyperliquid API
 blocks + logs               historical state          WS + Info API
      │                           │                         │
      │                           │                         │
      ▼                           ▼                         ▼
┌──────────────┐           ┌──────────────┐          ┌──────────────┐
│ Chain Head   │           │ Backfill /   │          │ HyperCore    │
│ Follower     │           │ State Reader │          │ CLOB Adapter │
└──────┬───────┘           └──────┬───────┘          └──────┬───────┘
       │                          │                         │
       └──────────────┬───────────┘                         │
                      ▼                                     │
              ┌─────────────────┐                           │
              │ Raw Block / Log │                           │
              │ Canonicalizer   │                           │
              └────────┬────────┘                           │
                       │                                    │
                       ▼                                    │
              ┌─────────────────┐                           │
              │ Reorg / Finality│                           │
              │ Manager         │                           │
              └────────┬────────┘                           │
                       │                                    │
                       ▼                                    │
              ┌─────────────────┐                           │
              │ Protocol Router │                           │
              └────────┬────────┘                           │
                       │                                    │
       ┌───────────────┼───────────────────────┐            │
       │               │                       │            │
       ▼               ▼                       ▼            │
┌────────────┐   ┌────────────┐        ┌────────────┐       │
│ Uniswap    │   │ Curve      │        │ Aerodrome  │       │
│ v3/v4      │   │ family     │        │ v2/Slipstr.│       │
└─────┬──────┘   └─────┬──────┘        └─────┬──────┘       │
      │                │                     │              │
      ▼                ▼                     ▼              │
┌──────────────────────────────────────────────────────────┐ │
│            Protocol-native State Reconstruction          │ │
│ ticks / balances / invariants / fees / LP changes       │ │
└────────────────────────────┬─────────────────────────────┘ │
                             │                               │
                             └──────────────┬────────────────┘
                                            ▼
                              ┌──────────────────────────┐
                              │ Normalized Market Model  │
                              │                          │
                              │ marginal price           │
                              │ executable depth ±bps    │
                              │ signed trade/swap flow   │
                              │ liquidity add/remove     │
                              │ impact curve             │
                              │ venue freshness/finality │
                              └────────────┬─────────────┘
                                           │
                                           ▼
                                     Canonical Kafka
                                           │
                      ┌────────────────────┴────────────────────┐
                      ▼                                         ▼
                 Pinot HOT                           S3 / Parquet / Iceberg
                      │                                         │
                      └────────────────────┬────────────────────┘
                                           ▼
                             Cross-venue / DeFi Feature Engine
                                           │
                                           ▼
                               Scanner / Backtest / ML / GMDH
```

## 18.2. Source modes

The subsystem supports four source modes behind common interfaces.

### 18.2.1. Live EVM head follower

Responsibilities:

- subscribe to new heads;
- fetch block header, transactions when required, receipts and matching logs;
- preserve `block_number`, `block_hash`, `parent_hash`, `transaction_hash`, `transaction_index`, `log_index`;
- timestamp receipt at local ingestion time;
- detect missed blocks and fill gaps over HTTP RPC;
- emit raw immutable records before decoding;
- never mark a block irreversible immediately.

### 18.2.2. Historical/backfill reader

Use:

- block-range `eth_getLogs` where reliable;
- archive state calls for point-in-time contract reads;
- provider-specific bulk endpoints only behind an adapter;
- optional Substreams/subgraph/indexer for discovery or accelerated backfill, with verification against canonical chain data.

Historical data must produce the **same canonical event schema** as live ingestion.

### 18.2.3. Periodic state sampler

Events alone are not sufficient for every protocol and for operational recovery. Periodically record state checkpoints.

Examples:

- Uniswap current `slot0`/equivalent state and active liquidity;
- Curve pool balances, `A`, `gamma`, fee parameters, oracle/price scale where applicable;
- Aerodrome reserves or Slipstream active state;
- token decimals/rates;
- pool implementation/version metadata.

A checkpoint is not allowed to rewrite history. It is a new point-in-time observation.

### 18.2.4. Native exchange API adapter

Some on-chain exchanges expose economically relevant state through protocol APIs rather than AMM logs. HyperCore is the primary example.

Use protocol-native APIs for:

- order book;
- trades;
- mids/BBO;
- funding;
- OI/asset contexts;
- liquidations or user events when relevant.

Do not fake an AMM representation for a CLOB venue.

## 18.3. Canonical raw chain envelope

Every EVM-originated item must preserve enough information for deterministic replay.

```json
{
  "chain_id": 1,
  "network": "ethereum",
  "block_number": 12345678,
  "block_hash": "0x...",
  "parent_hash": "0x...",
  "block_time": "...",
  "transaction_hash": "0x...",
  "transaction_index": 42,
  "log_index": 7,
  "address": "0x...",
  "topic0": "0x...",
  "topics": ["0x..."],
  "data": "0x...",
  "removed": false,
  "observed_at": "...",
  "available_at": "...",
  "provider": "rpc-provider-a",
  "schema_version": 1
}
```

Raw chain records are immutable append-only data.

## 18.4. Reorg and finality model

On-chain data has a different availability model from CEX websocket data.

Required concepts:

```text
SEEN
  ↓
HEAD_CONFIRMED
  ↓
SAFE
  ↓
FINALIZED
```

The exact mapping is chain-specific and configurable.

Every on-chain derived record stores:

- `block_number`;
- `block_hash`;
- `finality_status`;
- `confirmation_count` where meaningful;
- `orphaned_at` if later removed by reorg;
- `source_event_id`.

Rules:

1. Low-latency scanner may use `SEEN/HEAD_CONFIRMED` data with an explicit quality penalty.
2. Research datasets default to `SAFE` or stronger.
3. Backtests must model the actual availability policy used live.
4. Reorg rollback must invalidate downstream materializations deterministically.
5. A reorg cannot silently mutate an existing signal snapshot; emit an invalidation/correction event instead.

## 18.5. Pool and protocol discovery registry

Never rely only on hardcoded pool lists.

Registry fields:

```text
chain_id
protocol
protocol_version
factory_or_manager
pool_id
pool_address nullable
pool_key nullable
currency0/token0
currency1/token1
additional_tokens[]
fee_model
tick_spacing nullable
hook_address nullable
implementation_address nullable
created_block
discovery_source
verified
active
metadata_version
```

Discovery methods:

- factory creation events;
- Uniswap v4 `PoolManager.Initialize` events / PoolId + PoolKey mapping;
- protocol registries/factories;
- curated seed list for bootstrapping;
- governance/factory updates;
- periodic reconciliation against official deployments.

Unknown pools may be indexed in raw form before they become eligible for analytics.

## 18.6. ABI and decoder registry

Decoder selection is versioned and deterministic.

```python
class ProtocolDecoder(Protocol):
    protocol: str
    version: str

    def matches(self, raw_log, registry_entry) -> bool: ...
    def decode(self, raw_log, registry_entry) -> list[ProtocolEvent]: ...
```

Registry records:

- ABI hash/version;
- deployment range;
- implementation/proxy metadata;
- event signatures;
- decoder code version;
- migration notes.

If an implementation changes unexpectedly, ingestion must fail closed for semantic state reconstruction while continuing to retain raw logs.

## 18.7. Uniswap v3 adapter

Uniswap v3-style concentrated liquidity is reconstructed from pool-native state and events.

Track at minimum:

- pool address;
- `token0`, `token1`;
- fee tier;
- tick spacing;
- current tick;
- `sqrtPriceX96`;
- active liquidity;
- initialized ticks and `liquidityGross`/`liquidityNet` where available;
- `Swap`;
- `Mint`;
- `Burn`;
- optional `Collect` for LP economics, not for liquidity state itself.

State transition principle:

```text
previous pool state
      +
ordered block/log events
      ↓
new pool state
```

Do not reconstruct state by sorting only on timestamp. Canonical event ordering is:

```text
block_number
transaction_index
log_index
```

### 18.7.1. Tick liquidity map

Maintain a sparse tick structure:

```text
tick -> liquidity_net
```

Given current active liquidity, traverse initialized ticks above/below spot to build the executable liquidity curve.

Materialize periodically:

- active liquidity;
- initialized tick count around spot;
- nearest ticks;
- cumulative notional required for ±10/25/50/100 bps;
- local price impact curve.

### 18.7.2. Recovery

At configurable intervals compare reconstructed state with direct contract reads. On divergence:

- raise integrity incident;
- record mismatch details;
- checkpoint authoritative state;
- rebuild from latest known-good checkpoint;
- never silently patch historical derived rows.

## 18.8. Uniswap v4 adapter

Uniswap v4 must **not** be implemented as “v3 with a different factory”. v4 uses a singleton `PoolManager`, where pools are identified by `PoolId` and pool configuration includes currencies, fee, tick spacing and an optional hook.

Official v4 architecture also permits dynamic fees, hooks and custom accounting. Therefore the adapter must capture enough metadata to know whether standard concentrated-liquidity assumptions remain valid.

Track:

- `PoolManager` address;
- `PoolId`;
- full `PoolKey` mapping;
- currency0/currency1;
- fee or dynamic-fee flag;
- tick spacing;
- hook address;
- `Initialize`;
- `Swap`;
- `ModifyLiquidity`;
- `Donate` when relevant;
- current sqrt price/tick/liquidity;
- hook permissions;
- effective LP fee history;
- hook-specific metadata where supported.

### 18.8.1. Hook safety classification

Each pool receives a reconstruction class:

```text
STANDARD_CL
DYNAMIC_FEE_CL
HOOK_AUGMENTED_CL
CUSTOM_ACCOUNTING
UNKNOWN
```

Rules:

- `STANDARD_CL`: standard concentrated-liquidity depth reconstruction allowed.
- `DYNAMIC_FEE_CL`: depth allowed; effective fee must be point-in-time.
- `HOOK_AUGMENTED_CL`: reconstruction allowed only after hook behavior is classified.
- `CUSTOM_ACCOUNTING`: do not assume the standard curve; prefer executable quoting/simulation adapter.
- `UNKNOWN`: raw data only; exclude from predictive depth features.

This is necessary because v4 hooks can alter fee behavior and custom accounting can change economic semantics.

### 18.8.2. Singleton event routing

Because many pools emit through the same manager contract, filtering by contract address is insufficient.

Required key:

```text
(chain_id, pool_manager, pool_id)
```

Every v4 event is routed using `PoolId`; the registry resolves it back to full PoolKey and normalized asset pair.

## 18.9. Curve adapter family

Curve must be modeled as an invariant/quote-based AMM family rather than as a tick-based AMM.

At minimum distinguish:

```text
STABLESWAP
STABLESWAP_NG
CRYPTOSWAP
CRYPTOSWAP_NG
META_POOL
OTHER/UNKNOWN
```

Track as applicable:

- pool coins and coin indices;
- balances;
- stored/normalized rates;
- amplification coefficient `A`;
- `gamma` for Cryptoswap;
- invariant-related state;
- base fee and dynamic/off-peg fee parameters;
- `price_scale`;
- current spot price;
- `price_oracle` / EMA;
- liquidity add/remove events;
- exchange/swap events;
- pool implementation type;
- metapool/base-pool linkage.

### 18.9.1. Curve executable depth

Do **not** derive a fake tick map.

Build the depth curve by quote simulation for a configured notional grid:

```text
$1k
$5k
$10k
$25k
$50k
$100k
$250k
$500k
...
```

or inversely solve for the notional that moves price by:

```text
±5 / ±10 / ±25 / ±50 / ±100 bps
```

Use protocol quote math or verified view functions at a point-in-time state.

For Stableswap-NG, dynamic fees and token rate types are part of state and must be included in quoting.

### 18.9.2. Curve-specific predictive primitives

Materialize:

- balance imbalance ratio;
- distance from balanced composition;
- spot-vs-EMA/oracle divergence;
- `price_scale` staleness for Cryptoswap;
- effective dynamic fee;
- marginal depth asymmetry;
- depth deterioration around peg/current reference;
- recent liquidity add/remove notional;
- large one-sided swap flow.

These become normalized features later; they are not hardcoded trading rules.

## 18.10. Aerodrome adapter family

Aerodrome currently exposes more than one AMM shape, so one decoder is insufficient.

At minimum model:

```text
AERODROME_V2_VOLATILE
AERODROME_V2_STABLE
SLIPSTREAM_CL
FUTURE_AERO/METADEX_ADAPTER
```

Aerodrome documentation describes both classic AMM pools and the concentrated-liquidity design Slipstream. Slipstream is derived from Uniswap v3-style concentrated-liquidity contracts, so the state model can reuse a common CL kernel while retaining Aerodrome-specific metadata.

### 18.10.1. Aerodrome v2

Track:

- reserves;
- stable/volatile pool type;
- swap events;
- mint/burn/sync state transitions;
- fee configuration;
- LP/gauge metadata where useful;
- emissions eligibility and gauge id as optional liquidity-persistence context.

Depth is calculated from the correct pool invariant, not from CL ticks.

### 18.10.2. Slipstream

Reuse concentrated-liquidity primitives for:

- current tick;
- active liquidity;
- tick liquidity net;
- Swap/Mint/Burn;
- depth ±bps;
- LP migration.

Keep protocol metadata separate:

- gauge;
- staking/emissions status;
- custom fee modules where present;
- pool version.

### 18.10.3. Forward compatibility

Aerodrome documentation indicates protocol evolution toward Aero/MetaDEX03. Do not bake current contract assumptions into the normalized layer. New deployments receive a new protocol adapter/version, while the downstream normalized schema remains stable.

## 18.11. Hyperliquid dual adapter

Hyperliquid must be split into **HyperCore market data** and **HyperEVM chain data**.

### 18.11.1. HyperCore CLOB adapter

Use official WebSocket/Info APIs for:

- `l2Book`;
- `bbo`;
- `trades`;
- `allMids`;
- candles when useful for reconciliation only;
- `activeAssetCtx` / asset contexts;
- funding history/current funding;
- open interest;
- mark/oracle context;
- liquidation/user-event streams where semantically appropriate.

Normalized output maps into the same CEX/CLOB primitives used for Binance/Bybit/OKX:

```text
market.trade
market.book_snapshot
market.bbo
derivatives.funding
derivatives.open_interest
market.reference_price
```

Therefore HyperCore participates in order-flow, depth imbalance, OFI and derivatives analytics—not the AMM liquidity-map path.

### 18.11.2. HyperEVM adapter

HyperEVM is EVM-compatible execution integrated with the Hyperliquid chain. DeFi contracts deployed there enter the standard EVM raw-block/log pipeline.

Track separately:

- HyperEVM block identity;
- EVM tx/log/receipt data;
- deployment/protocol registry;
- HyperCore↔HyperEVM transfer events where they matter for asset-flow context;
- protocol-specific pool events for DEXs deployed on HyperEVM.

A HyperEVM AMM is analyzed according to **its AMM protocol**, not according to the Hyperliquid CLOB model.

### 18.11.3. Cross-layer features

Potential research features:

- HyperCore CLOB mid vs HyperEVM DEX marginal price;
- HyperCore depth vs HyperEVM executable depth;
- transfer flow from HyperCore to HyperEVM before/after large DEX activity;
- convergence latency;
- cross-layer arbitrage pressure.

These are hypotheses only until validated OOS.

## 18.12. Common normalized DeFi market model

Protocol adapters emit common **economic primitives**, not a fake common state model.

### 18.12.1. `NormalizedSwap`

```text
venue
protocol
chain_id
pool_or_market_id
base_asset
quote_asset
event_time
available_at
side / signed_flow
base_amount
quote_amount
usd_notional
price_before nullable
execution_price
price_after nullable
fee_usd nullable
price_impact_bps nullable
tx_hash nullable
block_number nullable
finality_status nullable
source_event_id
```

### 18.12.2. `LiquidityState`

```text
venue
protocol
pool_id
reference_price
state_time
available_at
model_type
active_liquidity nullable
reserve_state nullable
invariant_state nullable
fee_state
finality_status
reconstruction_quality
```

### 18.12.3. `ExecutableDepthCurve`

```text
pool_id
reference_price
side
bps
input_notional_usd
output_notional_usd
average_execution_price
marginal_price
fee_usd
gas_estimate_usd nullable
state_time
available_at
quality
```

Required bps defaults:

```text
5, 10, 25, 50, 100, 200
```

These are configurable by liquidity regime.

### 18.12.4. `LiquidityChange`

```text
pool_id
provider nullable
kind = ADD | REMOVE | REBALANCE | UNKNOWN
price_lower nullable
price_upper nullable
liquidity_delta
usd_value_estimate nullable
block_number
transaction_hash
available_at
```

For invariant AMMs without ranges, `price_lower/price_upper` stay null.

## 18.13. Asset identity and normalization

Cross-chain/venue comparison is impossible without a strict asset registry.

Required entities:

```text
Asset
AssetRepresentation
MarketPair
Pool
Venue
ProtocolDeployment
```

Examples:

```text
ETH
  ├── native ETH Ethereum
  ├── WETH Ethereum
  ├── WETH Base
  └── Hyperliquid ETH market representation
```

Do not merge wrapped, bridged or synthetic assets only by ticker.

Asset mapping carries:

- canonical economic asset id;
- chain id;
- contract address/native marker;
- decimals;
- wrapper/underlying relationship;
- bridge issuer if relevant;
- stablecoin family;
- pricing source priority;
- confidence.

## 18.14. CEX↔DEX normalization

The common comparison unit is **executable economics**, not raw price.

For each venue/pool compute at target notional `N`:

```text
buy_exec_px(N)
sell_exec_px(N)
buy_slippage_bps(N)
sell_slippage_bps(N)
all_in_cost_bps(N)
```

All-in DEX cost may include:

```text
AMM fee
+ price impact
+ estimated gas
+ optional MEV safety margin
```

CEX cost may include:

```text
spread
+ taker/maker fee assumption
+ order-book impact
```

Then calculate comparable basis:

```text
executable_basis_bps(N) =
    10000 * (dex_exec_px(N) / cex_exec_px(N) - 1)
```

Never compare a CEX top-of-book quote against an AMM infinitesimal spot quote and call it arbitrage.

## 18.15. Arbitrage-pressure inference

The scanner may infer pressure without executing arbitrage.

Inputs:

- CEX consensus mid;
- CEX executable price at notional N;
- DEX executable price at N;
- gas estimate;
- AMM/CEX fees;
- observed cross-venue latency;
- recent signed flow;
- available depth on both sides.

Outputs:

```text
arb_direction
raw_basis_bps
executable_basis_bps
estimated_cost_bps
net_basis_bps
persistence_ms
convergence_velocity
confidence
```

Do not label a state “arbitrageable” unless estimated net basis is positive after modeled costs.

## 18.16. Price and USD valuation policy

A DeFi feature must not become circular by valuing everything from the same pool being analyzed.

Price hierarchy example:

1. cross-CEX robust consensus for major assets;
2. independent liquid on-chain reference;
3. oracle reference where appropriate;
4. pool-local price only as last resort and marked `self_valued=true`.

All valuations store:

- pricing source;
- source time;
- staleness;
- confidence.

## 18.17. Multi-RPC provider strategy

RPC is infrastructure, not a source of unquestioned truth.

Implement provider abstraction:

```python
class ChainDataProvider(Protocol):
    async def get_block(...): ...
    async def get_logs(...): ...
    async def eth_call(...): ...
    async def get_receipts(...): ...
```

Operational rules:

- at least two providers for production-critical chains where budget allows;
- health score by latency/error/gap rate;
- per-method routing;
- provider cooldown on rate-limit/error storms;
- sampled cross-provider consistency checks;
- archive capability tracked separately from live capability;
- no provider-specific payload leaks into domain model.

## 18.18. Checkpoints and deterministic replay

For stateful protocols, replaying from genesis is impractical.

Checkpoint record:

```text
protocol
chain_id
pool_id
block_number
block_hash
state_blob_version
state_blob
created_at
code_version
checksum
```

Recovery:

```text
latest verified checkpoint <= target block
              ↓
replay canonical events in exact chain order
              ↓
validate against sampled direct state read
              ↓
materialize reconstructed state
```

Backtests may choose a historical checkpoint but must never use a checkpoint created from a future state.

## 18.19. Event-time and availability semantics

For each derived DeFi row:

```text
event_time       = chain block/event time
observed_at      = when collector first saw it
available_at     = when live strategy was allowed to use it
safe_at          = when selected confirmation policy was reached
computed_at      = feature/state computation time
```

Example:

```text
swap in block B at 12:00:01.100
collector receives head at 12:00:02.000
receipt/log complete at 12:00:02.250
policy allows head-confirmed features at 12:00:02.250

available_at = 12:00:02.250
```

A historical backtest at 12:00:01.500 must not see that swap even though `block_time` is earlier.

## 18.20. Data quality state machine

Each pool/market has quality state:

```text
HEALTHY
DELAYED
GAP_DETECTED
REORG_RECOVERY
STATE_MISMATCH
UNSUPPORTED_HOOK
UNKNOWN_IMPLEMENTATION
DISABLED
```

Feature engine behavior:

- `HEALTHY`: normal weight;
- `DELAYED`: decay contribution by freshness;
- `GAP_DETECTED`: no stateful feature emission until repaired;
- `REORG_RECOVERY`: provisional only;
- `STATE_MISMATCH`: disable predictive features;
- unsupported/unknown protocol semantics: raw indexing only.

## 18.21. Kafka topics for DeFi ingestion

Expand canonical topic families to distinguish raw, decoded, state and normalized layers:

```text
defi.raw.block.v1
defi.raw.log.v1
defi.raw.receipt.v1

defi.protocol.pool_discovered.v1
defi.protocol.swap.v1
defi.protocol.liquidity_change.v1
defi.protocol.state_checkpoint.v1
defi.protocol.reorg.v1

defi.normalized.swap.v1
defi.normalized.liquidity_state.v1
defi.normalized.depth_curve.v1
defi.normalized.price.v1

hyperliquid.book.v1
hyperliquid.trade.v1
hyperliquid.asset_context.v1
```

Partition guidance:

- raw EVM: `chain_id:block_partition` or chain-specific ordered strategy;
- protocol events: `chain_id:pool_id`;
- normalized pool state: `chain_id:pool_id`;
- HyperCore market data: `venue:symbol`.

Preserve ordering guarantees required by each state reducer.

## 18.22. Iceberg tables for DeFi

Minimum canonical analytical tables:

```text
raw_evm_blocks
raw_evm_logs
raw_evm_receipts
protocol_pools
protocol_swaps
protocol_liquidity_changes
pool_state_checkpoints
pool_state_snapshots
executable_depth_curves
dex_prices
reorg_events
asset_representations
cross_venue_executable_basis
```

Recommended partitioning should be tested rather than hardcoded. Typical dimensions include:

- chain/date;
- protocol/date;
- venue/date;
- bucketed pool id for high-cardinality state tables.

Avoid partitioning directly by millions of pool ids.

## 18.23. Pinot HOT datasets for DeFi

Pinot should serve only bounded realtime datasets needed by scanner/UI:

```text
realtime_dex_swap_1s
realtime_pool_state
realtime_dex_depth
realtime_liquidity_change
realtime_cex_dex_basis
realtime_defi_feature_snapshot
```

Keep deep raw chain history in Iceberg, not Pinot.

## 18.24. Protocol adapter interface

```python
class LiquidityVenueAdapter(Protocol):
    venue_type: str
    protocol: str
    version: str

    async def discover(self, cursor) -> list[PoolDescriptor]: ...
    def decode_event(self, raw_event) -> list[ProtocolEvent]: ...
    def apply_event(self, state, event) -> State: ...
    async def read_checkpoint(self, at_block) -> State: ...
    def marginal_price(self, state, direction) -> Decimal: ...
    def quote(self, state, direction, notional) -> Quote: ...
    def depth_curve(self, state, bps_grid) -> DepthCurve: ...
    def quality(self, state) -> ReconstructionQuality: ...
```

CLOB adapters implement a parallel `OrderBookVenueAdapter`; both emit normalized execution/depth primitives.

## 18.25. Tests required per protocol adapter

Every adapter must include:

1. golden decoded-event fixtures;
2. ordering test for multiple events in one transaction/block;
3. state transition unit tests;
4. checkpoint -> replay equivalence test;
5. direct-state reconciliation test;
6. historical quote comparison at known blocks;
7. reorg rollback fixture;
8. decimals/token-order inversion test;
9. missing event/gap failure test;
10. malformed/unknown implementation fail-closed test.

Additional:

**Uniswap v3/Slipstream**
- tick crossing changes active liquidity correctly;
- mint/burn outside active range does not incorrectly alter active liquidity;
- depth curve agrees with trusted quote within tolerance.

**Uniswap v4**
- PoolId routes to correct PoolKey;
- dynamic fee is point-in-time correct;
- unsupported hook/custom-accounting pools are excluded safely.

**Curve**
- multi-coin indices handled correctly;
- dynamic fee included;
- Stableswap/Cryptoswap implementation classification tested;
- quote curve matches contract view within tolerance.

**HyperCore**
- reconnect/snapshot recovery;
- book freshness;
- trade de-duplication;
- market symbol normalization.

## 18.26. DeFi ingestion observability

Metrics:

```text
chain_head_lag_blocks
chain_head_lag_seconds
rpc_request_latency
rpc_error_rate
rpc_rate_limit_count
raw_log_rate
unknown_log_rate
reorg_count
reorg_depth
pool_state_reconstruction_lag
pool_state_mismatch_count
protocol_decoder_error_count
depth_curve_compute_latency
hyperliquid_ws_reconnect_count
hyperliquid_book_age_ms
```

Alerts:

- head lag exceeds SLA;
- detected chain gap;
- state mismatch;
- unknown implementation for tracked high-volume pool;
- reorg deeper than configured normal threshold;
- no swaps observed for a normally active tracked venue while external price moves;
- HyperCore book stale/disconnected.

## 18.27. DeFi ingestion MVP order

Implement in this order:

```text
1. Ethereum/Base EVM raw block+log ingestion
2. reorg/finality + deterministic ordering
3. Uniswap v3 state reducer
4. concentrated-liquidity depth ±bps
5. Aerodrome Slipstream adapter via shared CL kernel
6. Aerodrome v2 invariant adapter
7. Curve Stableswap-NG/Cryptoswap quote adapter
8. Uniswap v4 PoolManager + PoolId registry
9. v4 hook safety classification
10. HyperCore native CLOB adapter
11. HyperEVM generic EVM ingestion profile
12. CEX↔DEX executable-basis normalization
```

This order maximizes reuse and gives useful market features before protocol coverage is complete.

---

# 18A. DeFi / AMM Feature Engine

## 18A.1. Data ingestion modes

### Realtime

Preferred:

- WebSocket RPC logs;
- direct contract event decoding;
- periodic state reads via eth_call/multicall.

### Historical

- `eth_getLogs` block ranges;
- archive RPC for historical state if needed;
- Subgraph/The Graph for discovery and accelerated backfill where exact semantics are verified.

Subgraphs are not the sole low-latency source of truth.

## 18A.2. Uniswap v3 pool state

Track:

- token0/token1;
- fee tier;
- tick spacing;
- current tick;
- sqrtPriceX96;
- active liquidity;
- tick liquidityNet;
- swap events;
- mint events;
- burn events.

## 18A.3. Virtual DEX liquidity profile

For a normalized reference price grid compute:

- active liquidity by tick/price band;
- cumulative base/quote required to move up/down;
- effective notional depth to ±10/25/50/100 bps;
- local liquidity gradient;
- nearest liquidity cliff;
- nearest concentrated-liquidity wall;
- asymmetry above vs below current price.

## 18A.4. DEX order-flow analogue

Since AMM does not expose a traditional bid/ask queue, compute:

- signed swap USD flow;
- swap count;
- large swap share;
- price impact per USD;
- tick velocity;
- tick crossing count;
- directional swap imbalance;
- volume-to-active-liquidity ratio.

## 18A.5. LP behavior

- gross liquidity minted near current price;
- gross burned near current price;
- net liquidity delta;
- liquidity migration direction;
- width of new LP positions;
- concentration changes;
- time since large liquidity withdrawal.

Potential signal:

“liquidity above spot removed while CEX ask depth also thins”

is a research feature, not a hard-coded bullish rule.

## 18A.6. DEX↔CEX price discovery features

- DEX marginal price minus CEX consensus;
- DEX transaction VWAP minus CEX;
- divergence duration;
- divergence area under curve;
- gas-adjusted arbitrage threshold;
- blocks until convergence;
- inferred arbitrage direction.

## 18A.7. Network state

- base fee;
- priority fee estimate;
- block interval;
- recent reorg flag;
- RPC latency;
- pending-block optional.

## 18A.8. DeFi signal quality

DeFi features get freshness metadata. If RPC/subgraph lag exceeds threshold, reduce contribution or disable confirmation rather than using stale data silently.

---

# 19. Feature Registry

Every feature definition must be registered.

```yaml
name: ofi_5s
family: order_flow
entity: venue_symbol
value_type: float64
unit: normalized
cadence: 1s
lookback: 5s
source: order_book_deltas
freshness_sla_ms: 1500
point_in_time_safe: true
version: 1
```

Required metadata:

- name;
- version;
- family;
- description;
- formula;
- units;
- required source events;
- lookback;
- update cadence;
- availability lag;
- null policy;
- clipping/winsorization policy;
- normalization;
- point-in-time safety;
- test fixture.

---

# 20. Market Regime Engine

Do not treat all channel touches equally.

## 20.1. Deterministic regime baseline

Features:

- realized volatility percentile;
- ATR percentile;
- trend strength;
- channel slope;
- channel width percentile;
- volume percentile;
- spread/depth regime.

States:

- TREND_UP_LOW_VOL;
- TREND_UP_HIGH_VOL;
- TREND_DOWN_LOW_VOL;
- TREND_DOWN_HIGH_VOL;
- RANGE_LOW_VOL;
- RANGE_HIGH_VOL;
- BREAKOUT_EXPANSION;
- DISLOCATION.

## 20.2. HMM / clustering experimental

Later experiment:

- HMM;
- Gaussian mixture;
- change-point detection.

Must be fitted point-in-time / expanding or rolling; no full-series smoothing for live feature labels.

---

# 21. Signal Engine

## 21.1. Signal families

### A. Upper Boundary Rejection — Short

Preconditions:

- channel direction <= configured bearish slope threshold;
- channel quality >= minimum;
- price enters upper zone;
- no active channel invalidation.

Trigger sequence:

1. `APPROACHING_UPPER`
2. `TOUCH_UPPER`
3. optional overshoot within tolerance
4. `REJECTED_BACK_INSIDE`
5. confirmation
6. `SIGNAL_SHORT`

### B. Lower Boundary Rejection — Long

Symmetric.

### C. Middle-Line Continuation — Short

Preconditions:

- bearish channel;
- price previously below middle;
- retracement into middle zone;
- failure to hold above middle;
- bearish confirmation.

### D. Middle-Line Continuation — Long

Symmetric.

### E. Channel Breakout + Retest — Long

- confirmed close above upper envelope;
- expansion metrics support breakout;
- retest holds above former upper boundary;
- channel transitions or old channel invalidates.

### F. Channel Breakdown + Retest — Short

Symmetric.

## 21.2. Candidate vs signal

A “zone touch” is only a candidate.

```text
NONE
→ APPROACH
→ TOUCH
→ REJECTION_PENDING
→ CONFIRMED
→ ALERTED
→ RESOLVED / INVALIDATED / EXPIRED
```

Persist state transitions.

## 21.3. Rejection definition baseline

Example configurable bearish rejection:

- high enters/overshoots upper zone;
- close ends below `upper_now - x * channel_width`;
- upper wick/body ratio above threshold OR next bar closes lower;
- no close beyond hard invalidation band.

Implement multiple rejection detectors as plugins:

- close-back-inside;
- wick rejection;
- two-bar confirmation;
- microstructure-confirmed rejection.

## 21.4. Confirmation features

Possible confirmation score components:

- OFI agrees;
- CVD divergence;
- microprice agrees;
- wall persistence agrees;
- volume-profile confluence;
- OI/funding regime;
- liquidation imbalance;
- DEX flow/liquidity asymmetry;
- cross-venue basis normalization.

## 21.5. Invalidation

Examples:

- close beyond outer tolerance;
- channel slope flips materially;
- channel quality collapses;
- high-volatility expansion regime;
- data health degraded.

## 21.6. Expiration

Candidate expires after configurable bars if no confirmation.

---

# 22. Signal Scoring

## 22.1. Deterministic score v1

Score `[0,100]`.

Feature groups:

```text
channel_structure       0..30
rejection_quality       0..20
order_flow_confirmation 0..20
volume_confirmation     0..10
derivatives_context     0..10
defi_crossvenue_context 0..10
```

Missing family must not automatically equal zero; score should account for data availability with explicit confidence downgrade.

## 22.2. Example

```text
Channel structure        26/30
Rejection                17/20
Order flow               16/20
Volume                     7/10
Derivatives                8/10
DeFi/Cross venue           7/10
-------------------------------
Raw score                 81/100
Data quality multiplier   0.96
Final score               77.8
```

## 22.3. Alert threshold

Configurable per symbol/timeframe/setup.

Default research value only:

`score >= 75`

## 22.4. Explainability

Every signal stores:

- top positive factors;
- top negative factors;
- missing factors;
- raw feature snapshot;
- model/version used.

---

# 23. GMDH / ML Layer

## 23.1. Role of GMDH

GMDH is not the first channel estimator. Preferred roles:

1. interaction discovery;
2. feature selection;
3. setup success probability;
4. channel survival prediction;
5. future regime/width/slope classification or regression;
6. turning-point probability;
7. bounded forward-path forecasting for derivative-based extremum hypotheses;
8. time-to-extremum and extreme-price distribution forecasting.

## 23.2. Primary target A — Rejection success

At candidate time `t`:

`y=1` if target is reached before invalidation within horizon `H`.

Target definitions configurable:

- middle line;
- fixed R multiple;
- channel fraction;
- opposite boundary.

Use triple-barrier-like labels:

- profit barrier;
- stop/invalidation barrier;
- time barrier.

## 23.3. Target B — Channel survival

`y=1` if channel remains statistically valid for next H bars according to predefined criteria.

Do not define survival using a criterion that is itself refitted on future data without careful semantics.

## 23.4. Target C — Expected excursion

Regression:

- MFE within H;
- MAE within H;
- return at H;
- time to target.

## 23.5. Target D — Breakout probability

Classification:

`P(confirmed_breakout_before_rejection | current state)`

Useful to prevent fading a strong breakout.


## 23.5A. Target E — Turning point probability

Classification by explicit horizon `H`:

```text
P(local_max_within_H | point_in_time_state)
P(local_min_within_H | point_in_time_state)
P(no_turn_within_H | point_in_time_state)
```

Labels may be future-aware because they are targets, but feature generation and fold construction must remain strictly point-in-time.

## 23.5B. Target F — Time and price of next extremum

Regression / quantile regression targets:

- bars to next meaningful maximum;
- bars to next meaningful minimum;
- next maximum return;
- next minimum return;
- Q10/Q50/Q90 of maximum/minimum excursion.

## 23.5C. Target G — GMDH derivative turning point

When GMDH is configured to forecast a bounded smooth path, compute first and second derivatives analytically where possible.

Derivative roots are **candidate features**, subject to the root-stability gates defined in §13A.12, and may not be promoted solely because `dP/dh=0`.

## 23.6. Baseline models before GMDH

Every GMDH result must beat:

- no-skill base rate;
- logistic regression;
- regularized logistic regression;
- simple decision tree;
- gradient boosted trees;
- optionally LightGBM/XGBoost if dependency allowed.

## 23.7. GMDH candidate interactions

Input groups may include:

- channel_position × OFI;
- channel_slope × OI_change;
- funding_z × OI_change;
- CVD_divergence × wall_persistence;
- DEX_liquidity_asymmetry × CEX_depth_asymmetry;
- volume_node_distance × channel_boundary_distance;
- volatility_regime × rejection_wick_strength;
- causal_slope × causal_curvature;
- distance_to_running_high × OFI_change;
- upper_channel_distance × ask_replenishment;
- lower_channel_distance × bid_replenishment;
- derivative_root_horizon × channel_position;
- derivative_root_stability × volatility_regime;
- DEX_liquidity_asymmetry × turning_point_direction.

Do not manually inject future labels into features.

## 23.8. Calibration

For probabilistic outputs report:

- Brier score;
- log loss;
- reliability diagram;
- Expected Calibration Error;
- precision/recall at alert threshold;
- PnL/expectancy by probability decile.

## 23.9. Model registry

Model artifact includes:

- model type;
- feature set versions;
- train start/end;
- validation start/end;
- code commit;
- hyperparameters;
- scaler parameters;
- calibration model;
- metrics;
- artifact hash;
- deployment status.

---

# 24. Point-in-Time Dataset Construction

This is one of the most important components.

## 24.1. Feature snapshot table

Each row:

```text
entity
as_of_time
feature_name/version
value
source_max_event_time
computed_at
```

Invariant:

`source_max_event_time <= as_of_time`

## 24.2. Training join

Labels may use future data. Features may not.

```text
features(t) ---------------> model input
      |
      | no feature after t
      v
label(t, t+H) -------------> target only
```

## 24.3. Overlapping labels

Because candidate events can overlap in time:

- prefer chronological walk-forward splits;
- apply purge/embargo where overlapping horizon would contaminate validation;
- never random-shuffle train/test for primary evaluation.

---

# 25. Backtesting Engine

## 25.1. Two modes

### Bar replay

Use finalized bars + feature snapshots.

Purpose:

- fast strategy iteration;
- channel/rejection testing.

### Event replay

Use trades/order-book deltas/liquidations/on-chain events.

Purpose:

- microstructure validation;
- realistic signal timing;
- absorption/wall research.

## 25.2. Core replay requirement

The same production feature/signal code should run in replay mode using a virtual clock.

Avoid separate “backtest implementation” of strategy logic.

## 25.3. Costs

Even though MVP does not execute trades, research simulation must support:

CEX:

- maker/taker fee;
- spread;
- slippage model;
- latency;
- funding payments;
- partial fills later.

DEX:

- pool fee;
- price impact;
- gas;
- priority fee;
- block inclusion latency;
- failed/reverted transaction scenario later.

## 25.4. Fill models

Phase 1:

- market-at-next-bar-open;
- market-at-signal-close + configurable slippage.

Phase 2:

- trade-through limit fill approximation;
- L2-aware simulation.

## 25.5. Metrics

Per setup:

- number of candidates;
- number of alerts;
- win rate;
- average return;
- median return;
- expectancy in R;
- profit factor;
- Sharpe;
- Sortino;
- max drawdown;
- average MFE;
- average MAE;
- target hit probability;
- time-to-target;
- turnover;
- exposure time;
- fees;
- slippage;
- funding cost;
- DEX gas where applicable.

## 25.6. Alert-quality metrics

- precision;
- recall vs defined candidate outcomes;
- false alert rate per day;
- alert frequency;
- duplicate alert rate;
- stale-data alert count — must be zero.

## 25.7. Walk-forward example

```text
Train         Validate       Test
2024 Q1-Q4 -> 2025 Q1   ->   2025 Q2
2024 Q2-2025Q1 -> 2025Q2 ->  2025Q3
...
```

For deterministic parameters, treat “train” as parameter selection only.

## 25.8. Required anti-overfit reports

- parameter sensitivity heatmap;
- performance by year/quarter;
- performance by symbol;
- performance by volatility regime;
- performance before/after fees;
- ablation by feature family;
- alert threshold sensitivity;
- probability calibration drift.

---

# 26. Telegram Alerting

## 26.1. Message structure

```text
🔴 BTCUSDT — SHORT SETUP

Venue: Binance Perp
TF: 15m
Price: 112,480
Time: 2026-09-06 11:15 UTC

Setup: Upper Channel Rejection
Score: 82/100
Model probability: 0.71

Channel
Direction: DOWN
Slope: -0.37% / lookback
Width: 2.4%
Position: 0.94
Quality: 0.83

Order Flow
OFI 30s: bearish
Depth imbalance 25bps: -0.31
CVD divergence: bearish
Ask-wall persistence: high

Derivatives
OI 15m: +3.1%
Funding z: +1.8
Liquidation pressure: long-heavy

DeFi
DEX-CEX basis: +4 bps
Liquidity above: thin
Swap imbalance: sell

Invalidation: 113,080
Research target: middle channel 111,900

[ OPEN CHART ]
```

## 26.2. Dedupe

No repeated alert for same setup state unless:

- score improves by configurable delta;
- signal changes phase;
- cooldown elapsed and a new independent touch occurred.

## 26.3. Severity

- INFO candidate — normally no Telegram;
- WATCH score 60–74 optional;
- ALERT score 75–84;
- HIGH score 85+.

## 26.4. Failure handling

- retry with exponential backoff;
- dead-letter table;
- alert delivery audit;
- never block signal engine on Telegram failure.

---

# 27. Web UI / Chart

## 27.1. Routes

```text
/markets
/chart/:venue/:symbol
/signals
/signals/:signalId
/research/backtests/:runId
```

Deep-link:

```text
/chart/binance/BTCUSDT?tf=15m&at=2026-09-06T11:15:00Z&signal=<uuid>
```

## 27.2. Main chart overlays

Toggle layers:

- candles;
- channel center;
- upper/lower;
- forecast corridor;
- signal zones;
- signal marker;
- volume profile;
- POC/VAH/VAL;
- VWAP;
- large LOB walls;
- DEX liquidity bands;
- liquidation levels.

## 27.3. Lower panes

Selectable panes:

- volume;
- CVD;
- OFI;
- OI;
- funding;
- basis;
- liquidations;
- DEX swap imbalance;
- DEX active liquidity.

## 27.4. Signal explanation panel

Show:

- score breakdown;
- model probabilities;
- raw feature values;
- data freshness;
- model/channel versions;
- historical outcome after resolution, but visually separated so it cannot be confused with information available at signal time.

## 27.5. Historical-vs-current channel mode

Critical UI feature:

- `AS-SEEN-THEN`: immutable channel snapshot at selected time;
- `CURRENT REFIT`: channel calculated now over visible/current history.

Default when opening signal deep-link: `AS-SEEN-THEN`.

This directly exposes repaint-like differences and protects research integrity.

---

# 28. API Specification

## 28.1. Markets

`GET /api/v1/markets`

Filters:

- venue;
- market_type;
- quote;
- active;
- min_volume.

## 28.2. Bars

`GET /api/v1/bars`

Params:

- venue;
- symbol;
- timeframe;
- start;
- end;
- limit.

## 28.3. Channel snapshots

`GET /api/v1/channels`

- model;
- historical `as_seen_then=true` default.

## 28.4. Features

`GET /api/v1/features/snapshot`

`GET /api/v1/features/timeseries`

## 28.5. Signals

`GET /api/v1/signals`

Filters:

- symbol;
- timeframe;
- setup_type;
- min_score;
- status;
- time range.

## 28.6. Signal details

`GET /api/v1/signals/{id}`

Returns:

- decision snapshot;
- channel snapshot;
- feature snapshot;
- explanation;
- later outcome separately.

## 28.7. WebSocket

`/ws/market`

Subscribe:

```json
{
  "op": "subscribe",
  "venue": "binance",
  "symbol": "BTCUSDT",
  "timeframe": "15m",
  "channels": ["bars", "channel", "features", "signals"]
}
```

---

# 29. Analytical Storage Data Model

## 29.0. Deployment profiles

The logical schemas below are domain schemas, not a requirement that ClickHouse is the final system of record.

- **MVP:** materialize them in ClickHouse where convenient.
- **HOT production:** materialize query-critical subsets/aggregates in Pinot.
- **Canonical/history:** persist normalized and derived history as Parquet/Iceberg.
- **Research:** query Iceberg with Trino or bounded extracts with DuckDB.

Any backend-specific DDL must live behind migrations/adapters and must not leak into signal/channel domain code.

## 29.A. Pinot HOT datasets

Prioritize datasets needed by the scanner/UI rather than mirroring all raw events:

- `hot_trades`;
- `hot_book_features`;
- `hot_bars`;
- `hot_derivatives`;
- `hot_dex_state`;
- `hot_cross_venue`;
- `hot_channel_snapshots`;
- `hot_signal_candidates`;
- `hot_signals`.

Recommended design principles:

- explicit event-time column;
- time partitioning/segment strategy appropriate to query horizon;
- primary dimensions: venue, chain, symbol/pool, timeframe, feature/model version;
- precompute expensive stable features rather than reconstructing raw L2 in dashboard queries;
- use upsert/realtime semantics only for entities that are genuinely mutable; immutable events stay append-only.

## 29.B. Iceberg canonical tables

At minimum:

- `cex_trades`;
- `cex_book_deltas`;
- `cex_book_snapshots`;
- `derivatives_funding`;
- `derivatives_open_interest`;
- `derivatives_liquidations`;
- `defi_swaps`;
- `defi_pool_state`;
- `defi_liquidity_changes`;
- `bars`;
- `feature_snapshots`;
- `channel_snapshots`;
- `signal_candidates`;
- `signals`;
- `labels`;
- `backtest_runs`;
- `experiment_membership`.

Every research-grade table must support dataset lineage/snapshot reproducibility.

## 29.C. ClickHouse MVP mapping

The following subsections describe the initial ClickHouse mapping for the MVP profile. They should remain semantically compatible with Pinot/Iceberg materializations.

## 29.1. `trades`

Partition:

- monthly by event date.

Order key:

`(venue, symbol, event_time_ns, trade_id)`

## 29.2. `book_deltas`

For Tier-1 symbols only initially.

Potential strategy:

- compressed arrays of changed price levels;
- TTL to S3 cold storage.

## 29.3. `book_features_1s`

Store derived features for broader universe.

Columns:

- mid;
- spread_bps;
- qi_l1;
- depth_imbalance_5/10/25/50bps;
- microprice_delta_bps;
- ofi_1s/5s/30s;
- bid_depth_usd_*;
- ask_depth_usd_*;
- wall scores;
- book health.

## 29.4. `bars`

Order:

`(venue, symbol, timeframe, open_time)`

## 29.5. `feature_snapshots`

Prefer wide table for stable production feature set plus optional long table for experimental registry.

## 29.6. `channel_snapshots`

Immutable append-only.

Important columns:

- as_of;
- model/version;
- lookback;
- lower/center/upper;
- slope;
- width;
- quality components;
- forecast arrays;
- source_max_event_time.

## 29.7. `signals`

Immutable decision core plus separate resolution/outcome table.

Never update original feature values after signal.

## 29.8. `dex_swaps`, `dex_liquidity_events`, `dex_pool_state`

Use `(chain_id, pool, block_number, tx_index, log_index)` ordering.

---

# 30. PostgreSQL Data Model

Tables:

- `market_config`;
- `strategy_config`;
- `alert_subscription`;
- `signal_state_machine`;
- `model_registry`;
- `backtest_runs` metadata;
- `experiments`;
- `notification_delivery`;
- `feature_definition`;
- `connector_health`.

---

# 31. Configuration

Example:

```yaml
app:
  timezone: UTC
  mode: live

markets:
  - venue: binance
    type: perp
    symbols: [BTCUSDT, ETHUSDT, SOLUSDT]
    timeframes: [1m, 5m, 15m, 1h]

channel:
  default_model: quantile_regression
  models:
    rolling_ols:
      lookbacks: [60, 100, 150]
      residual_quantiles: [0.10, 0.90]
    quantile_regression:
      lookbacks: [80, 120]
      quantiles: [0.10, 0.50, 0.90]
    kalman:
      enabled: true

signals:
  upper_rejection_short:
    enabled: true
    min_channel_quality: 0.70
    upper_zone_start: 0.88
    overshoot_tolerance: 0.08
    confirmation_bars: 2
    min_score: 75
    cooldown_bars: 8

orderflow:
  depth_levels: [1, 5, 10, 20, 50]
  bps_bands: [5, 10, 25, 50]
  windows: [1s, 5s, 30s, 1m]

telegram:
  enabled: true
  min_score: 75

research:
  forbid_random_split: true
  store_feature_snapshots: true
  store_channel_snapshots: true
```

---

# 32. Data Quality Layer

Each feature family has health state:

- GOOD;
- DEGRADED;
- STALE;
- INVALID.

Signal eligibility rules:

- channel data must be GOOD;
- price/bar must be GOOD;
- optional confirmations may be degraded but decrease confidence;
- LOB-dependent signal cannot use stale book;
- DeFi contribution becomes neutral/unknown if delayed.

Health metrics:

- WS reconnect count;
- sequence gap rate;
- event latency p50/p95/p99;
- stale seconds;
- missing bars;
- duplicate rate;
- chain RPC lag;
- subgraph indexing lag;
- ClickHouse insert delay.

---

# 33. Observability

## Metrics

Prometheus-compatible:

- events/sec by connector;
- reconnects;
- book resets;
- ingest latency;
- feature compute latency;
- channel compute latency;
- signal count;
- Telegram delivery failures;
- DB insert latency;
- queue depth;
- stale feed count.

## Logs

Structured JSON.

Every signal log contains:

- signal_id;
- symbol;
- as_of;
- model_version;
- feature_snapshot_id;
- score;
- reason codes.

## Tracing

Optional OpenTelemetry after MVP.

---

# 34. Security

MVP is read-only market analytics.

Requirements:

- no exchange trading keys required for public market data;
- Telegram bot token only via secret/env manager;
- RPC API keys via secrets;
- no secrets committed;
- redact secrets from logs;
- API write/admin routes authenticated;
- CORS restricted in production;
- rate limiting for public web API.

If trading is added later, separate execution service and separate credentials entirely.

---

# 35. Testing Strategy

## 35.1. Unit tests

Required:

- bar aggregation;
- trade side normalization;
- order-book delta application;
- sequence-gap detection;
- OFI formulas;
- volume profile;
- channel formulas;
- quantile ordering;
- channel-position calculation;
- setup state transitions;
- score calculation;
- DEX tick/price math;
- liquidity depth calculations.

## 35.2. Golden fixtures

Store small deterministic event streams.

Test:

- raw events → normalized → features → channel → signal.

Expected output committed as fixture.

## 35.3. Repaint regression test

Critical test:

1. Feed bars one at a time.
2. Store channel snapshots.
3. Continue feeding future bars.
4. Assert all previous snapshots unchanged.

## 35.4. Future leak test

For every feature:

1. Run on truncated dataset through `t`.
2. Run on full dataset but ask for feature at `t`.
3. Values must match exactly within numeric tolerance.

This should be an automated CI suite.

## 35.5. Live/replay parity

Capture a 30–60 minute live event segment.

Replay it offline.

Assert feature/channel/signal parity.

## 35.6. Connector contract tests

Replay exchange sample messages and test:

- snapshot/delta rules;
- reconnect;
- malformed events;
- rate limits;
- time parsing.

## 35.7. DEX reorg fixture

Simulate:

- logs A/B/C;
- reorg removes C;
- replacement C2/D;
- state correctly rolls back/replays.

---

# 36. Performance Targets

MVP:

- 3 symbols × 4 timeframes;
- L2 top 50/100 levels;
- feature update <= 1s;
- signal after bar close <= 2s;
- Telegram delivery attempt <= 3s after signal;
- chart historical load p95 < 2s for 2,000 bars.

Phase 2:

- 50 symbols;
- 3 venues;
- derived LOB feature processing real-time;
- raw L2 retention tiered.

Do not promise sub-millisecond HFT behavior.

---

# 37. Suggested Repository Layout

```text
channelflow/
├── README.md
├── PRD.md
├── pyproject.toml
├── uv.lock
├── docker-compose.yml
├── Makefile
├── .env.example
├── configs/
│   ├── default.yaml
│   ├── dev.yaml
│   └── research.yaml
├── apps/
│   ├── api/
│   └── web/
├── src/channelflow/
│   ├── domain/
│   │   ├── events.py
│   │   ├── markets.py
│   │   ├── features.py
│   │   ├── channels.py
│   │   └── signals.py
│   ├── connectors/
│   │   ├── base.py
│   │   ├── binance/
│   │   ├── bybit/
│   │   ├── okx/
│   │   └── evm/
│   ├── ingestion/
│   ├── orderbook/
│   ├── bars/
│   ├── features/
│   │   ├── price.py
│   │   ├── volume.py
│   │   ├── orderflow.py
│   │   ├── derivatives.py
│   │   ├── crossvenue.py
│   │   └── defi.py
│   ├── channels/
│   │   ├── base.py
│   │   ├── rolling_ols.py
│   │   ├── robust.py
│   │   ├── quantile.py
│   │   ├── kalman.py
│   │   └── conformal.py
│   ├── regimes/
│   ├── signals/
│   │   ├── engine.py
│   │   ├── state_machine.py
│   │   ├── rejection.py
│   │   ├── continuation.py
│   │   └── scoring.py
│   ├── notifications/
│   │   └── telegram.py
│   ├── storage/
│   │   ├── clickhouse.py
│   │   ├── postgres.py
│   │   └── parquet.py
│   ├── replay/
│   ├── backtest/
│   ├── ml/
│   │   ├── datasets.py
│   │   ├── baselines.py
│   │   ├── gmdh.py
│   │   ├── calibration.py
│   │   └── registry.py
│   └── observability/
├── migrations/
├── research/
│   ├── notebooks/
│   ├── experiments/
│   └── reports/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/
│   ├── leak/
│   └── replay/
└── infra/
    ├── clickhouse/
    ├── postgres/
    └── grafana/
```

---

# 38. CLI

```text
channelflow ingest cex --venue binance --symbols BTCUSDT,ETHUSDT
channelflow ingest defi --chain arbitrum --dex uniswap-v3
channelflow backfill bars --venue binance --symbol BTCUSDT --from ...
channelflow replay --dataset ... --speed max
channelflow backtest --strategy upper_rejection_short --config ...
channelflow research build-dataset --target rejection_success
channelflow train --model logistic
channelflow train --model gmdh
channelflow validate no-lookahead
channelflow validate replay-parity
channelflow serve api
channelflow serve worker
```

---

# 39. Research Experiment Matrix

## EXP-001 Channel model comparison

Compare:

- rolling OLS std bands;
- rolling OLS residual quantiles;
- Huber + MAD;
- quantile regression;
- Kalman.

Metrics:

- next-H coverage;
- boundary interaction stability;
- number of false “perfect” historical touches;
- slope stability;
- width stability;
- computational cost;
- rejection strategy expectancy OOS.

## EXP-002 Lookback sensitivity

Lookbacks:

- 40;
- 60;
- 80;
- 100;
- 150;
- 200 bars.

Do not select solely on maximum PnL; evaluate stability plateau.

## EXP-003 Rejection detector

Compare:

- wick only;
- close-back-inside;
- two-bar confirmation;
- order-flow confirmation.

## EXP-004 OFI incremental value

Ablation:

- channel only;
- +L1 imbalance;
- +multi-level imbalance;
- +OFI;
- +persistence/cancellation.

## EXP-005 Volume profile confluence

Question:

Does boundary overlap with VAH/VAL/HVN/LVN materially change target-before-stop probability?

## EXP-006 Derivatives context

Analyze conditional outcomes by:

- funding z-score;
- OI change;
- liquidation imbalance;
- basis.

## EXP-007 DEX incremental value

For ETH:

- CEX only;
- CEX + DEX price divergence;
- + DEX depth asymmetry;
- + swap imbalance;
- + LP liquidity changes.

## EXP-008 GMDH vs baselines

Same point-in-time feature matrix.

Models:

- logistic;
- elastic net;
- gradient boosting;
- GMDH.

Evaluate:

- Brier;
- calibration;
- PR-AUC;
- expectancy by probability bucket;
- feature stability across walk-forward folds.

## EXP-009 Forecast corridor calibration

Compare:

- empirical residual quantile;
- parametric std band;
- conformal-adjusted interval.

Metric:

- target coverage with narrowest stable interval.

## EXP-010 Cross-venue lead/lag

Measure whether divergence contains predictive value after realistic latency/costs.


## EXP-011 Structural extremum detector

Compare non-repainting confirmed swing methods:

- fixed-bps directional change;
- ATR-adaptive directional change;
- realized-vol adaptive directional change;
- channel-width adaptive directional change;
- hybrid threshold.

Metrics:

- confirmation lag;
- extrema per 1000 bars;
- prominence;
- stability across volatility regimes;
- downstream setup expectancy.

## EXP-012 Causal derivative turning points

Compare:

- raw trailing return sign change;
- causal local polynomial order 2;
- causal local polynomial order 3;
- Kalman filtered slope;
- one-sided Savitzky-Golay-equivalent implementation if retained.

Evaluate maximum/minimum forecast precision at horizons 3/6/12/24 bars.

Centered filters are allowed only as retrospective label references, never as live candidates.

## EXP-013 GMDH derivative extrema

Compare:

- direct classifier only;
- GMDH direct turning-point classifier;
- GMDH forward path + derivative roots;
- ensemble of direct probability + derivative root stability.

Report:

- root presence rate;
- root horizon IQR;
- turn-type agreement;
- time-to-turn MAE;
- extreme-price error;
- calibration;
- incremental expectancy after costs.

Reject the derivative method if roots are unstable or add no OOS value.

## EXP-014 Order-flow exhaustion around extrema

Conditional study around future-labeled meaningful extrema:

- OFI sign and slope;
- CVD divergence;
- microprice deviation;
- spread widening;
- wall replenishment/cancellation;
- absorption.

Then repeat point-in-time as a predictive experiment to avoid confusing contemporaneous explanation with forecast value.

## EXP-015 Derivatives/DeFi confluence at turning points

For BTC/ETH and other liquid assets, test whether turning-point probability improves from:

- OI/funding/liquidations;
- DEX-CEX executable basis;
- DEX depth asymmetry;
- swap imbalance;
- LP liquidity migration.

Use strict ablation and same walk-forward folds.

## EXP-016 Multi-scale extrema

Evaluate whether nested extrema improve signals:

- 5m candidate inside 15m upper/lower zone;
- 15m candidate aligned/conflicted with 1h slope;
- directional-change thresholds at multiple scales.

Measure incremental value, not visual appeal.


## EXP-017 Adaptive stop-management policy

Compare position-management policies on the exact same immutable entry signals:

1. fixed initial stop only;
2. naive fixed-percent trailing stop;
3. ATR/volatility trailing stop;
4. confirmed-swing structural trailing stop;
5. channel-conditioned structural stop;
6. structural stop + order-flow confirmation;
7. full Adaptive Stop Management Engine.

Primary metrics:

- expectancy after fees/slippage;
- realized R multiple;
- profit factor;
- stop-out rate;
- percentage of trades stopped before later reaching original target;
- give-back from MFE to realized exit;
- MAE before stop;
- median/95p stop distance;
- average holding time;
- turnover / stop modification count;
- tail loss / worst gap or slippage event;
- regime stability.

Ablations:

- remove swing confirmation;
- remove volatility/noise floor;
- remove order-flow veto;
- remove channel context;
- remove extremum/turning-point forecast;
- remove DeFi/cross-venue context;
- remove hysteresis/cooldown.

The experiment must be able to conclude `NO_EDGE`: a sophisticated trailing policy is rejected if it only looks better visually but does not improve OOS economics or risk-adjusted outcomes.

---

# 40. Signal Outcome Definitions

Every signal later gets `SignalOutcome`, separate from original immutable signal.

```python
class SignalOutcome:
    signal_id: UUID
    horizon_end: datetime
    first_target_time: datetime | None
    first_invalidation_time: datetime | None
    mfe_pct: float
    mae_pct: float
    return_h: float
    outcome: Literal["target", "stop", "timeout", "ambiguous"]
```

If bar data cannot determine whether stop/target happened first inside one bar, mark `ambiguous` unless lower-timeframe/tick replay resolves it.

Never choose the favorable ordering.

---

# 41. Anti-Bias Rules

1. No random train/test primary split.
2. No centered moving filters in live features.
3. No pivot that requires future bars unless the feature availability time is shifted to confirmation time.
4. No using final daily high/low before daily close.
5. No using current funding settlement before it becomes known.
6. No using later corrected/reconstructed DEX state as if known earlier unless audit semantics explicitly allow it.
7. No survivor-only universe without point-in-time listing history.
8. No using current top-volume coin list for historical universe backtest without point-in-time universe reconstruction.
9. Fees/slippage must be included in economic evaluation.
10. Optimize parameters on train/validation; locked test remains untouched.
11. Store all discarded experiment variants to reduce silent cherry-picking.

---

# 42. Universe Selection

MVP static universe is acceptable.

For multi-asset historical research, implement point-in-time universe:

- symbol listing time;
- delisting time;
- volume/liquidity eligibility computed from trailing information only;
- stablecoin/depeg exclusions configured.

---

# 43. Alert Ranker

When many setups exist, ranking should consider:

`rank_score = setup_score * data_quality * liquidity_factor * novelty_factor`

Where:

- `data_quality` penalizes stale/missing sources;
- `liquidity_factor` prevents noisy illiquid assets dominating;
- `novelty_factor` reduces repeated correlated alerts.

Optional correlation suppression:

If BTC, ETH, SOL all produce identical macro move signals, alert each only if score high; otherwise send grouped market alert later.

---

# 44. Risk/Research Guardrails

This system is analytics software, not a guarantee of profitability.

UI should expose:

- sample count;
- OOS period;
- probability calibration;
- fees included yes/no;
- model freshness;
- last retrain;
- data quality.

Never label 80% backtest hit rate as “80% guaranteed probability” unless calibrated out-of-sample probability supports it.

---


# 44A. Adaptive Stop Management Engine

## 44A.1. Purpose

Add an optional position-monitoring and stop-management subsystem for paper trading first and live execution only after separate approval/hardening.

The goal is **not** to trail stop loss mechanically behind every favorable price movement. The goal is to move risk only when the market has created new causal evidence that the original invalidation level can be tightened without placing the stop inside ordinary market noise.

The engine must optimize the following tension:

```text
protect accumulated profit / reduce open risk
                    vs
avoid getting stopped by ordinary retracement, spread, wick, liquidation noise,
or a temporary order-flow imbalance before the original thesis plays out
```

A stop is an invalidation mechanism, not a profit meter.

The module must work with:

- manually entered positions;
- paper positions created from ChannelFlow signals;
- later optional exchange execution positions.

It must be possible to run the module in **shadow mode** where it emits proposed stop changes without sending any exchange order.

---

## 44A.2. Core design principle — separate hard risk from adaptive strategy risk

Every live position has two stop concepts.

### Hard catastrophic stop

A real exchange-native protective order when live trading is enabled.

Purpose:

- protect against application crash;
- protect against lost websocket/RPC connectivity;
- protect against strategy service outage;
- cap catastrophic loss;
- remain active independently of ChannelFlow.

The hard stop must never depend on the availability of the adaptive engine.

### Adaptive strategy stop

A tighter point-in-time stop recommendation/order maintained by ChannelFlow based on:

- confirmed market structure;
- volatility/noise;
- channel geometry;
- order flow;
- derivatives context;
- DeFi/cross-venue context;
- turning-point forecasts;
- position state.

The adaptive stop may tighten risk but must never silently widen the maximum risk beyond the accepted initial-risk contract.

Default rule:

```text
LONG:  new_stop >= current_effective_stop
SHORT: new_stop <= current_effective_stop
```

Any policy that permits widening must be a separate explicitly enabled research policy and must never be enabled in production by default.

---

## 44A.3. Inputs

Required position fields:

```python
class PositionState:
    position_id: UUID
    instrument_id: str
    venue: str | None
    side: Literal["LONG", "SHORT"]
    quantity: Decimal
    entry_time: datetime
    average_entry_price: Decimal
    initial_stop_price: Decimal
    hard_stop_price: Decimal | None
    current_strategy_stop: Decimal
    original_target_price: Decimal | None
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    fees_paid: Decimal
    status: Literal["OPEN", "REDUCED", "CLOSING", "CLOSED"]
```

Point-in-time market inputs:

- last/mark/index price;
- spread;
- recent trade volatility;
- realized volatility by horizon;
- ATR-equivalent true-range statistic;
- recent wick/noise distribution;
- active channel upper/middle/lower/slope/width/quality;
- confirmed extrema and extremum candidates;
- bars/time since confirmed swing;
- OFI / multi-level OFI;
- CVD;
- book imbalance;
- liquidity wall persistence/cancellation/replenishment;
- absorption;
- volume profile POC/VAH/VAL/HVN/LVN;
- VWAP/anchored VWAP if implemented;
- funding/OI/basis/liquidations;
- cross-venue divergence;
- DEX executable-depth asymmetry;
- DEX-CEX executable basis;
- swap imbalance;
- LP liquidity migration;
- turning-point probabilities `P(MAX)`, `P(MIN)`, `P(NO_TURN)`;
- data-quality flags.

All inputs must be available according to `available_at`; no future-confirmed swing may be used before its `known_at`.

---

## 44A.4. Position lifecycle

Use an explicit state machine.

```text
OPENED
  |
  v
INITIAL_RISK
  |
  | favorable excursion + thesis remains valid
  v
PROTECTING
  |
  | new confirmed structure
  v
STRUCTURE_TRAIL
  |
  +--------------------------+
  |                          |
  | strong trend             | target/exit condition
  v                          v
TREND_RIDE                 EXITING
  |                          |
  | exhaustion /             v
  | turning risk           CLOSED
  v
DEFENSIVE_TRAIL
```

States:

### `INITIAL_RISK`

Do not rush the stop toward break-even. The trade is still inside its expected initial noise/MAE envelope.

### `PROTECTING`

The trade has achieved enough favorable excursion that risk can potentially be reduced, but only if a structural anchor exists.

### `STRUCTURE_TRAIL`

At least one post-entry confirmed structural swing supports moving the invalidation point.

### `TREND_RIDE`

A strong trend is active. Prefer wider structure/channel/volatility trailing so normal pullbacks do not exit the position prematurely.

### `DEFENSIVE_TRAIL`

The position remains profitable but evidence of exhaustion/opposite turning point is growing. Tightening may become more aggressive, subject to a minimum noise floor.

### `EXITING`

No more stop optimization. Manage closure/reconciliation.

---

## 44A.5. Initial stop calculation

The initial stop belongs behind the setup invalidation, not at an arbitrary percent distance.

For LONG candidate anchors may include:

- setup swing low;
- lower channel boundary;
- rejection low;
- breakout-retest low;
- structurally relevant LVN/HVN/VAL zone;
- DEX/CEX liquidity support only as secondary context.

For SHORT use symmetric high-side anchors.

Define structural anchor `A_t`.

Define a causal noise buffer:

```text
noise_buffer = max(
    k_atr * ATR,
    k_rv * realized_vol_price_distance,
    k_spread * effective_spread,
    q_noise * recent_adverse_wick_distribution,
    min_stop_bps * price
)
```

Then:

```text
LONG_initial_stop  = anchor_low  - noise_buffer
SHORT_initial_stop = anchor_high + noise_buffer
```

The buffer coefficients are configuration/research parameters and must be estimated only on train/validation periods.

Do not place the stop exactly on an obvious swing level or channel line solely because it is visually convenient.

---

## 44A.6. Why break-even trailing is not automatic

The following rule is forbidden as a default policy:

```text
if profit > X:
    stop = entry
```

Reason: entry price has no necessary structural meaning after the position opens.

A move to break-even is allowed only when both are true:

1. favorable excursion exceeds a configurable activation threshold;
2. the market has produced a new causal invalidation structure that justifies reduced risk.

Example LONG:

```text
entry
  |
  | impulse up
  v
new high
  |
  | pullback
  v
confirmed higher low
  |
  +--> stop may move below higher low + noise buffer
```

If the valid structural stop remains below entry, the engine should keep it below entry rather than forcing an economically meaningless break-even stop.

---

## 44A.7. Structural trailing anchors

Candidate anchors are ranked, not blindly selected.

### LONG anchors

1. most recent confirmed higher low;
2. previous confirmed higher low if the newest one is too close/noisy;
3. lower channel boundary;
4. channel middle only in defensive mode and only when trend/structure supports it;
5. anchored VWAP / volume-profile structural support as optional confluence;
6. volatility trailing floor.

### SHORT anchors

Symmetric confirmed lower-high / upper-channel logic.

Every anchor stores:

```python
class StopAnchor:
    anchor_type: str
    price: Decimal
    event_time: datetime
    known_at: datetime
    confidence: float
    structural_scale: str
    source_id: str | None
```

The engine must never use `event_time` as availability time when `known_at` is later.

---

## 44A.8. Minimum noise distance

Before accepting any proposed stop, calculate a minimum distance from current executable price.

```text
min_noise_distance = max(
    volatility_floor,
    spread_floor,
    wick_noise_floor,
    microstructure_floor,
    execution_slippage_floor
)
```

For LONG:

```text
current_price - proposed_stop >= min_noise_distance
```

For SHORT:

```text
proposed_stop - current_price >= min_noise_distance
```

If not, reject the stop update even if the structural anchor is mathematically valid.

This is the primary anti-"stop too tight" guardrail.

---

## 44A.9. Adaptive volatility buffer

The buffer must react asymmetrically to volatility.

When volatility rises quickly:

- allow the stop buffer to widen **before** tightening around a new anchor;
- do not widen already accepted maximum position risk;
- prefer waiting for a new structural confirmation rather than chasing price.

When volatility falls:

- buffer may contract gradually;
- do not contract instantly after one quiet bar.

Use hysteresis / EWMA:

```text
vol_buffer_t = max(
    fast_vol_estimate,
    slow_vol_estimate * slow_floor_ratio
)
```

or another predeclared causal estimator.

The aim is to avoid:

```text
volatility spike -> huge candle -> stop mechanically jumps too close -> ordinary retrace -> stop-out
```

---

## 44A.10. Channel-aware trailing

The channel engine gives a dynamic structural frame.

For LONG trend ride:

- lower boundary can act as a broad invalidation reference;
- middle line can act as a defensive reference only after sufficient profit/structure;
- channel slope and width determine trail aggressiveness;
- channel-quality deterioration may prevent relying on channel anchors.

Example policy:

```text
if channel_direction == UP
and channel_quality >= q_min
and position_state == TREND_RIDE:
    candidate = lower_channel - channel_noise_buffer
```

Do not move a stop merely because a newly refitted current channel moved. Use immutable `AS-SEEN-THEN` snapshots and explicit update time.

If channel validity drops below threshold, fall back to structural swing + volatility anchors.

---

## 44A.11. Turning-point / extremum integration

The Price Extremum Engine is used to change **aggressiveness**, not to fabricate certainty.

For profitable LONG:

```text
P(MAX within H) rising
P(NO_TURN within H) falling
slope decelerating
curvature negative
```

may transition:

```text
TREND_RIDE -> DEFENSIVE_TRAIL
```

For profitable SHORT use `P(MIN)` symmetrically.

Possible actions in `DEFENSIVE_TRAIL`:

- select a more recent structural anchor;
- reduce buffer multiplier within configured lower bound;
- optional partial-profit recommendation;
- optional exit recommendation when thesis invalidates.

Forbidden:

```text
P(MAX) > threshold -> move stop immediately to last price
```

The turning-point model affects policy state, not direct tick-by-tick stop placement.

---

## 44A.12. Order-flow confirmation and veto

Order flow can confirm that a structural level is meaningful or veto premature tightening.

For LONG, supportive evidence includes:

- positive OFI after pullback;
- bid replenishment below/near higher low;
- sell absorption at support;
- CVD recovery/divergence;
- persistent bid depth;
- reduced aggressive selling.

Adverse evidence includes:

- strongly negative OFI;
- bid cancellations;
- aggressive sell sweep;
- inability to reclaim microprice/VWAP;
- liquidation-driven discontinuity.

Use order flow primarily as:

```text
CONFIRM / NEUTRAL / VETO
```

for a structural stop proposal.

It must not independently produce a stop one tick behind the order book.

Example:

```text
confirmed higher low exists
        +
positive/recovering OFI
        +
bid replenishment
        => anchor confidence increases
```

If L2 data are stale/unhealthy, skip order-flow confirmation rather than reusing old values.

---

## 44A.13. Volume-profile context

Use POC/VAH/VAL/HVN/LVN only as context.

Examples:

- a LONG stop just inside a dense HVN may be vulnerable to ordinary rotation;
- placing an invalidation beyond a structurally relevant low-volume transition may be more meaningful;
- crossing from accepted value into a new value area can indicate a position regime change.

Volume profile must never override a hard maximum-risk constraint.

Do not optimize stops to visually hug POC/VAH/VAL in hindsight.

---

## 44A.14. Derivatives context

Derivatives features modify stop policy only when point-in-time valid.

Examples for LONG:

### Strong continuation context

```text
price up
OI up moderately
funding not extreme
no liquidation cascade
```

May support `TREND_RIDE` with wider structural trail.

### Exhaustion / fragility context

```text
price up
OI surges
funding extreme positive
long-liquidation risk elevated
P(MAX) elevated
```

May support `DEFENSIVE_TRAIL`.

### Liquidation spike

During a liquidation cascade:

- do not mechanically tighten into the wick;
- optionally freeze stop modifications for a short causal cooldown;
- hard catastrophic stop remains active;
- strategy exit rules may still close position if thesis invalidates.

---

## 44A.15. DeFi / cross-venue context

For assets with reliable DeFi liquidity information, use:

- DEX executable-depth asymmetry;
- DEX-CEX executable basis;
- swap imbalance;
- LP withdrawal/migration near price;
- concentration of executable liquidity below/above price;
- inferred arbitrage pressure.

Examples:

For LONG, disappearing DEX liquidity below spot plus worsening CEX OFI may lower confidence in a nearby support anchor.

Conversely, persistent deep executable DEX liquidity below market plus CEX sell absorption can strengthen an existing structural support hypothesis.

These features affect anchor confidence/policy state. They do not directly set the stop price without a market-structure anchor.

---

## 44A.16. Stop proposal algorithm

At each decision event (prefer finalized bar plus selected microstructure events):

```python
def propose_stop(position, market_state):
    assert market_state.as_of <= market_state.available_at_policy_cutoff

    phase = determine_position_phase(position, market_state)

    anchors = build_causal_stop_anchors(position, market_state)
    anchors = [a for a in anchors if a.known_at <= market_state.as_of]

    noise = compute_min_noise_distance(market_state)
    context = compute_stop_context(position, market_state)

    ranked = rank_anchors(
        anchors,
        structure=context.structure,
        channel=context.channel,
        order_flow=context.order_flow,
        derivatives=context.derivatives,
        defi=context.defi,
        turning_point=context.turning_point,
        data_quality=context.data_quality,
    )

    candidate = choose_phase_appropriate_anchor(ranked, phase)
    proposed = apply_noise_buffer(candidate, noise, position.side)

    proposed = enforce_monotonic_risk_tightening(
        proposed,
        current_stop=position.current_strategy_stop,
        side=position.side,
    )

    proposed = enforce_min_distance_from_market(
        proposed,
        current_executable_price=market_state.executable_price,
        min_noise_distance=noise,
        side=position.side,
    )

    proposed = apply_cooldown_and_hysteresis(position, proposed, market_state)
    proposed = apply_max_risk_contract(position, proposed)

    return StopProposal(...)
```

No individual feature is allowed to bypass the safety filters.

---

## 44A.17. Hysteresis, cooldown and anti-churn

Frequent stop modifications are undesirable and can create false precision, exchange load, rate-limit risk and poor fills.

Require configurable:

- `min_stop_improvement_bps`;
- `min_stop_improvement_R`;
- `min_seconds_between_updates`;
- `min_bars_between_structural_updates`;
- optional `max_updates_per_hour`;
- post-liquidation cooldown;
- post-gap/stale-data freeze.

Example:

```text
current stop = 100.00
candidate    = 100.03
minimum useful improvement = 0.10
=> no update
```

The engine should prefer fewer meaningful structural moves over continuous micro-adjustment.

---

## 44A.18. Data-quality freeze

Adaptive stop management must fail safe.

If any required market-state component becomes unhealthy:

```text
L2 sequence gap
stale trade feed
channel compute failure
clock skew
reorg-sensitive DEX state unavailable
model version missing
```

then:

1. do not tighten using stale/invalid data;
2. keep existing exchange hard stop unchanged;
3. optionally keep current strategy stop unchanged;
4. emit `STOP_MANAGEMENT_FROZEN` alert/metric;
5. resume only after explicit health recovery.

Never move a stop based on last-known stale OFI/order-book state.

---

## 44A.19. Stop proposal model

```python
class StopProposal:
    proposal_id: UUID
    position_id: UUID
    as_of: datetime
    side: Literal["LONG", "SHORT"]
    current_stop: Decimal
    proposed_stop: Decimal
    hard_stop: Decimal | None
    anchor: StopAnchor
    position_phase: str
    noise_buffer: Decimal
    distance_to_market_bps: float
    open_risk_before_R: float
    open_risk_after_R: float
    locked_profit_R: float | None
    confidence: float
    action: Literal["NO_CHANGE", "TIGHTEN", "EXIT_RECOMMENDED"]
    reason_codes: list[str]
    veto_codes: list[str]
    feature_snapshot_id: UUID
    policy_version: str
```

A proposal is immutable.

Exchange action, if enabled, is stored separately.

---

## 44A.20. Stop update event model

Kafka/event topics:

```text
position.opened.v1
position.updated.v1
stop.proposal.v1
stop.proposal.rejected.v1
stop.update.requested.v1
stop.update.acknowledged.v1
stop.update.failed.v1
stop.management.frozen.v1
position.closed.v1
```

Do not mutate historical proposal records.

---

## 44A.21. Exchange reconciliation

When live execution is eventually enabled, exchange state is authoritative for actual resting protective orders.

Required reconciliation loop:

```text
local desired stop
       |
       v
exchange current order state
       |
       +--> identical -> no action
       |
       +--> missing -> repair according to safety policy
       |
       +--> different -> reconcile/idempotent modify
```

Requirements:

- idempotency key per stop update;
- client order id;
- acknowledgement timeout;
- retry with bounded backoff;
- cancel/replace race handling;
- partial-fill handling;
- position-size reconciliation;
- reduce-only where supported;
- exchange precision/tick-size normalization;
- audit of requested vs acknowledged stop price;
- never assume REST success means websocket/account state has converged.

---

## 44A.22. Trigger-price semantics

The engine must explicitly configure which price triggers the stop:

- last price;
- mark price;
- index price;
- exchange-specific trigger semantics.

Backtests must reproduce the selected trigger semantics as closely as available data permit.

Do not backtest a mark-price stop using candle low/high from last trade data without marking the approximation.

---

## 44A.23. Gap/slippage-aware risk

A stop price is not a guaranteed fill price.

Research/backtest must model:

- spread;
- taker fee;
- expected slippage;
- order-book depth at stop time;
- discontinuous move/gap;
- liquidation cascades;
- venue outage when relevant.

Store:

```text
requested_stop_price
trigger_price
first_executable_price
realized_exit_price
stop_slippage_bps
```

Risk metrics use realized executable exit when available, not ideal stop price.

---

## 44A.24. Position-level R accounting

Define initial risk per unit:

For LONG:

```text
R0 = entry_price - initial_stop_price
```

For SHORT:

```text
R0 = initial_stop_price - entry_price
```

Track:

- current open risk in `R`;
- locked profit in `R`;
- MFE in `R`;
- MAE in `R`;
- give-back from MFE;
- realized exit `R`.

This allows policy comparison across BTC, ETH, SOL and different volatility regimes.

---

## 44A.25. Policy score / aggressiveness

Do not predict the exact stop directly in the first ML version.

First define a bounded trail aggressiveness score:

```text
0.0 = preserve broad original/structural stop
1.0 = use most defensive valid structural stop
```

Inputs may include:

- position MFE/MAE;
- current R;
- channel slope/quality/position;
- new swing confidence;
- volatility regime;
- OFI/CVD/absorption;
- derivatives fragility;
- DeFi liquidity asymmetry;
- turning-point probability;
- time in trade.

Then deterministic safety logic maps aggressiveness to one of already-valid structural anchors.

This is safer and more interpretable than allowing ML/GMDH to emit an arbitrary stop price.

---

## 44A.26. Optional ML/GMDH research targets

Only after deterministic baselines exist.

Possible targets:

### Target A — premature stop-out probability

```text
P(stop touched before original target, then target reached within H)
```

This directly measures “the stop was too tight”.

### Target B — give-back risk

```text
P(give_back > X% of MFE within H)
```

### Target C — thesis failure probability

```text
P(original invalidation/structural reversal within H)
```

### Target D — optimal policy class

Classification among:

```text
HOLD_STOP
TRAIL_TO_PREVIOUS_SWING
TRAIL_TO_LATEST_SWING
TRAIL_TO_CHANNEL
DEFENSIVE_TRAIL
EXIT
```

Labels must be designed carefully to avoid hindsight-optimized stop paths that cannot be implemented online.

GMDH can be evaluated for interaction discovery, for example:

```text
MFE_R × channel_position
turn_probability × OFI
volatility × swing_prominence
OI_change × funding_z
DEX_depth_asymmetry × CEX_OFI
```

Promotion requires OOS incremental value over deterministic policy.

---

## 44A.27. Backtest semantics

Stop management requires event-order fidelity.

Preferred evaluation order:

1. tick/trade replay when available;
2. lower-timeframe bars for a higher-timeframe strategy;
3. conservative bar-only ambiguity handling.

If one OHLC bar contains both:

```text
new stop trigger
and
profit target
```

and ordering cannot be known, mark ambiguous or choose conservative ordering according to predeclared policy.

Never choose whichever ordering gives better PnL.

Stop updates are effective only after modeled decision + computation + network/exchange latency.

Example:

```text
signal computed at 10:15:00.100
stop modification ack at 10:15:00.260

market touch at 10:15:00.180
```

The new stop was not yet active.

---

## 44A.28. Counterfactual stop-path evaluation

For each immutable entry signal, replay multiple stop policies over the same future event stream.

Store:

```python
class StopPolicyOutcome:
    signal_id: UUID
    policy_id: str
    policy_version: str
    initial_R: float
    realized_R: float
    mfe_R: float
    mae_R: float
    max_giveback_R: float
    stop_updates: int
    stopped_out: bool
    premature_stop_then_target: bool
    exit_reason: str
    holding_seconds: int
```

This enables apples-to-apples comparison without changing the entry model.

---

## 44A.29. Premature-stop metric

A key product metric:

```text
PrematureStopRate =
trades stopped by adaptive stop that later reach the original target within H
/
all trades stopped by adaptive stop
```

Also report distance/time after stop before original target.

This metric directly tests the user's concern that a trailing stop “gets taken out” by ordinary price noise.

Do not optimize this metric alone: an infinitely wide stop would make it look good while destroying risk control.

Always combine with realized expectancy and downside metrics.

---

## 44A.30. Stop-efficiency metrics

Report:

```text
RealizedCapture = realized_profit / MFE
```

when MFE > 0, plus:

- MFE give-back;
- realized R;
- downside R;
- stop distance distribution;
- stop count/modification count;
- premature-stop rate;
- target-after-stop rate;
- tail slippage;
- time-to-risk-free / time-to-reduced-risk;
- percentage of positions where stop never moved;
- percentage exiting by stop vs signal invalidation vs target.

A good policy is not simply the one with the tightest average stop.

---

## 44A.31. Example LONG decision

```text
Entry:                 100.00
Initial structural SL:  97.80
Initial risk:            1.0R

Price rises to:        103.20
MFE:                    +1.45R

Latest pullback low:    101.40
BUT not yet confirmed
=> NO STOP CHANGE

Later:
confirmed higher low:   101.35
ATR/noise buffer:         0.55
raw structural stop:    100.80

OFI:                    recovering positive
bid replenishment:      present
channel:                healthy UP
P(MAX <= 6 bars):       0.21

current stop:            97.80
proposed stop:          100.80
min market distance:      0.65
actual market:          103.00
=> ACCEPT
```

Later:

```text
price:                  106.50
new confirmed HL:       104.20
noise buffer:             0.70
P(MAX <= 6 bars):        0.72
OFI flips negative
funding extreme

phase:
TREND_RIDE -> DEFENSIVE_TRAIL

candidate structural stop:
103.50

not:
106.20  # forbidden blind tick-following stop
```

---

## 44A.32. Example SHORT decision

Symmetric logic:

```text
confirmed lower high
+
upper-side noise buffer
+
negative/recovering sell OFI
+
healthy DOWN channel
=> tighten stop above lower high
```

Never derive SHORT stop from a future-confirmed high before `known_at`.

---

## 44A.33. UI requirements

Position page/chart must display:

- entry;
- initial stop;
- hard catastrophic stop;
- current adaptive stop;
- historical stop path;
- each stop proposal marker;
- anchor used for each proposal;
- rejected proposals;
- current position phase;
- open risk `R`;
- locked profit `R`;
- MFE/MAE;
- trail aggressiveness;
- reasons/vetoes;
- data-health status.

Clicking a stop update shows:

```text
Why moved:
+ confirmed higher low
+ channel remains UP
+ OFI recovered
+ MFE > activation threshold

Why not tighter:
- volatility floor
- nearby HVN rotation zone
- P(MAX) only moderate
```

`AS-SEEN-THEN` mode must show the stop path exactly as generated live/replay, not recompute a prettier historical trail.

---

## 44A.34. Alerting

Optional Telegram event:

```text
🛡 BTCUSDT LONG — STOP UPDATED

Entry:          112,400
Old stop:       111,180
New stop:       112,060
Price:          113,740

Position phase: STRUCTURE_TRAIL
Open risk:      1.00R -> 0.28R

Anchor:
confirmed higher low

Reasons:
+ channel UP / quality 0.84
+ OFI recovery
+ volatility buffer satisfied

[ OPEN POSITION CHART ]
```

Do not notify for rejected micro-updates unless debug mode is enabled.

---

## 44A.35. Configuration

Example:

```yaml
stop_management:
  enabled: false
  mode: shadow  # shadow | paper | live
  decision_on_bar_close: true
  microstructure_events: false

  initial_stop:
    structure_first: true
    atr_multiplier: 1.2
    spread_multiplier: 4.0
    min_stop_bps: 18

  activation:
    min_mfe_R: 0.8
    require_new_structure: true

  trailing:
    prefer_confirmed_swing: true
    allow_channel_anchor: true
    allow_midline_in_defensive_mode: true
    monotonic_tightening: true

  anti_churn:
    min_improvement_bps: 8
    min_improvement_R: 0.05
    min_seconds_between_updates: 30
    max_updates_per_hour: 12

  volatility:
    fast_window: 20
    slow_window: 100
    post_spike_cooldown_seconds: 60

  turning_point:
    defensive_max_probability: 0.70
    defensive_min_probability: 0.70

  health:
    freeze_on_l2_gap: true
    freeze_on_stale_market_data: true

  execution:
    trigger_price: mark
    reduce_only: true
```

Values are placeholders for research, not recommended universal trading parameters.

---

## 44A.36. Storage

HOT/Pinot candidate datasets:

```text
hot_positions
hot_stop_proposals
hot_stop_updates
hot_position_risk_state
```

Iceberg canonical history:

```text
positions
position_events
stop_proposals
stop_execution_events
stop_policy_outcomes
```

Postgres may hold operational current state for MVP.

---

## 44A.37. API

```text
POST /api/v1/positions/manual
GET  /api/v1/positions/open
GET  /api/v1/positions/{position_id}
GET  /api/v1/positions/{position_id}/stop-history
GET  /api/v1/positions/{position_id}/risk
POST /api/v1/positions/{position_id}/stop/shadow-evaluate
```

Live execution routes must be separated and authenticated more strongly; do not expose live stop modification in the initial analytics MVP.

---

## 44A.38. Testing

Required unit/integration tests:

1. LONG stop never loosens under default policy.
2. SHORT stop never loosens under default policy.
3. no use of swing before `known_at`.
4. no update inside minimum noise distance.
5. no update below minimum improvement threshold.
6. cooldown prevents churn.
7. stale L2 freezes OFI-dependent changes.
8. hard stop remains untouched during strategy-engine failure.
9. volatility spike does not cause blind stop chase.
10. channel repaint test cannot mutate historical stop proposals.
11. liquidation event cooldown works.
12. exchange tick-size rounding does not accidentally loosen risk.
13. partial position reduction recomputes stop order quantity correctly.
14. reconnect/reconciliation is idempotent.
15. delayed exchange acknowledgement is modeled in replay.
16. ambiguous target/stop bar handled conservatively.
17. stop policy replay uses identical immutable entry signals.
18. shadow/live decision logic parity test.

---

## 44A.39. Acceptance criteria

The module is acceptable for paper/shadow mode when:

- stop movement is causal and deterministic;
- every movement has a structural anchor and reason codes;
- no blind price-following path exists in default policy;
- current risk never exceeds accepted initial risk through a stop update;
- stale-data freeze works;
- historical stop path is immutable;
- naive trailing stop baseline is included in comparison;
- OOS report includes premature-stop rate and realized `R`;
- policy may conclude that leaving the original stop unchanged is optimal for a position;
- no ML component is required for correctness.

Live mode requires a separate execution-security/reconciliation acceptance process.

---

# 45. Phase Plan

## Phase 0 — Repository + correctness skeleton

Deliverables:

- repo layout;
- domain models;
- config loader;
- Docker Compose;
- Postgres/ClickHouse connectivity;
- virtual clock;
- event bus abstraction;
- CI;
- golden test framework.

Acceptance:

- `make test` green;
- services boot locally;
- canonical event serialization roundtrip.

## Phase 1 — CEX channel MVP

Deliverables:

- Binance perp + spot connector;
- trades;
- bars;
- basic market metadata;
- rolling OLS residual-quantile channel;
- immutable channel snapshots;
- boundary/middle state machine;
- Telegram;
- React chart;
- deep-link;
- bar-replay backtest.

Acceptance:

- live BTC/ETH/SOL channels update;
- historical snapshots never mutate;
- signal opens exact chart state;
- future-leak test passes;
- at least one backtest report generated.


### Phase 1A — Extremum baseline

Deliverables:

- directional-change confirmed highs/lows;
- causal local-polynomial slope/curvature;
- extremum candidate lifecycle;
- immutable `extremum_time` vs `known_at` semantics;
- chart markers for candidate vs confirmed extrema;
- replay/non-repaint tests;
- no ML required.

Acceptance:

- no confirmed extremum can appear earlier than `known_at` in `AS-SEEN-THEN` mode;
- appending future bars does not mutate finalized candidates/confirmed extrema;
- confirmation lag and prominence are reported.

## Phase 2 — CEX microstructure

Deliverables:

- L2 order book reconstruction;
- book health;
- queue imbalance;
- multi-depth imbalance;
- OFI;
- CVD;
- wall persistence/cancellation;
- absorption feature;
- volume profile;
- UI panes.

Acceptance:

- forced sequence gap disables book features;
- replay parity on captured stream;
- OFI features available in signal snapshot.

## Phase 3 — Derivatives

Deliverables:

- funding;
- OI;
- basis;
- liquidation feed;
- optional long/short stats;
- derivatives feature panel;
- score integration.

Acceptance:

- all derivative features point-in-time safe;
- stale REST polling cannot silently reuse old value.

## Phase 4 — DeFi ingestion + AMM market structure

Deliverables:

- multi-provider EVM RPC abstraction;
- live head follower + historical backfill;
- raw block/log/receipt canonical persistence;
- reorg/finality manager;
- pool/protocol discovery registry;
- ABI/decoder registry;
- Uniswap v3 pool reducer;
- concentrated-liquidity tick map and depth ±bps;
- Aerodrome Slipstream adapter using shared CL kernel;
- Aerodrome v2 stable/volatile adapter;
- Curve Stableswap-NG/Cryptoswap quote/depth adapter;
- Uniswap v4 PoolManager/PoolId adapter;
- v4 hook/custom-accounting safety classification;
- HyperCore native CLOB adapter (`l2Book`, trades, mids, asset contexts);
- HyperEVM EVM-ingestion profile;
- normalized swaps/liquidity/depth model;
- asset identity registry;
- CEX↔DEX executable-price normalization;
- DEX swap imbalance;
- LP liquidity delta/migration;
- executable DEX-CEX basis after estimated fees/gas/impact;
- Pinot HOT DeFi datasets;
- Iceberg canonical DeFi tables;
- UI liquidity/depth overlay.

Acceptance:

- reproduce known Uniswap v3 pool price from sqrtPrice/tick;
- deterministic checkpoint + replay reconstruction fixture;
- tick crossing updates active liquidity correctly;
- forced log gap disables stateful features until repaired;
- reorg fixture rolls state back and emits correction/invalidation;
- compute ETH/USDC DEX depth around market price for ±10/25/50/100 bps;
- Curve quote curve agrees with a trusted point-in-time contract quote within configured tolerance;
- Uniswap v4 PoolId resolves to the correct PoolKey and hook classification;
- unsupported v4 custom-accounting pool fails closed instead of emitting fake CL depth;
- Aerodrome v2 and Slipstream are decoded as distinct AMM models;
- HyperCore reconnect restores current book snapshot without treating it as AMM liquidity;
- CEX top-of-book is never compared directly with DEX infinitesimal spot for arbitrage scoring;
- backtest uses `available_at` and selected finality policy, not only block timestamp.

## Phase 5 — Cross-venue

Deliverables:

- Bybit;
- OKX;
- normalized symbol mapping;
- consensus mid;
- cross-venue basis;
- depth comparison;
- funding dispersion.

## Phase 6 — Research-grade validation

Deliverables:

- point-in-time dataset builder;
- event replay;
- walk-forward runner;
- ablation reports;
- experiment registry;
- dataset hashes;
- reproducible reports.

## Phase 7 — ML/GMDH

Deliverables:

- candidate labeler;
- logistic baseline;
- boosted tree baseline;
- GMDH implementation/wrapper;
- calibration;
- probability ranker;
- explainability;
- model registry;
- turning-point direct classifier/regressor;
- GMDH bounded forward-path option;
- derivative root extractor;
- derivative-root stability report;
- P(max)/P(min)/P(no-turn) calibration by horizon.

Acceptance:

- GMDH cannot be promoted unless it beats baseline OOS on predeclared metrics;
- no feature leakage tests failing;
- calibration report included.



## Phase 7A — Adaptive position / stop management (shadow → paper)

Deliverables:

- `PositionState` and immutable position-event model;
- hard-stop vs adaptive-strategy-stop semantics;
- structural stop-anchor service;
- volatility/noise buffer;
- phase state machine (`INITIAL_RISK`, `PROTECTING`, `STRUCTURE_TRAIL`, `TREND_RIDE`, `DEFENSIVE_TRAIL`);
- monotonic risk-tightening rule;
- cooldown/hysteresis/anti-churn;
- order-flow confirmation/veto;
- channel and turning-point integration;
- derivatives/DeFi context hooks;
- shadow stop proposals;
- counterfactual stop-policy replay;
- stop-path chart;
- Telegram stop-update notification;
- premature-stop and stop-efficiency report.

Acceptance:

- default policy cannot widen accepted initial risk;
- confirmed swing cannot be used before `known_at`;
- appending future market data does not mutate historical stop proposals;
- naive trailing baseline vs adaptive policy report exists;
- stale-data freeze test passes;
- paper/shadow replay models stop-update activation latency;
- policy can return `NO_CHANGE` indefinitely when no better causal invalidation anchor exists.

Live exchange stop modification is **not** required for this phase.


## Phase 8 — Production hardening

Deliverables:

- Redpanda/Kafka optional;
- S3 cold retention;
- monitoring dashboards;
- alerting on data outages;
- backup/restore;
- deployment docs;
- load tests.

---

# 46. Detailed Codex Work Packages

## WP-001 Project bootstrap

Tasks:

- create pyproject;
- setup `uv`;
- ruff;
- mypy/pyright optional;
- pytest;
- frontend scaffold;
- docker compose;
- Makefile.

Done when:

- one command starts dev stack.

## WP-002 Domain model

Implement all canonical events as immutable/frozen Pydantic models where practical.

Done when:

- serialization fixtures stable.

## WP-003 Binance connector

Requirements:

- reconnect before/at 24h lifecycle;
- ping/pong compliance;
- combined streams configurable;
- trades;
- book deltas;
- mark/funding;
- OI polling;
- liquidations when available;
- error metrics.

## WP-004 Order book service

- buffer + snapshot bootstrap;
- exact sequence validation;
- rebuild on gap;
- top-N access;
- depth-at-bps query;
- health state.

## WP-005 Bar aggregation

- event-time windows;
- late-event policy;
- finalized bar callback;
- trade-side aggregates.

## WP-006 Channel baseline

- rolling OLS log price;
- residual quantile bands;
- normalized slope;
- quality score;
- append-only storage.

## WP-007 Signal state machine

Implement long/short boundary + middle setups with deterministic transitions and tests.

## WP-008 Telegram

- format alert;
- inline deep-link button;
- dedupe;
- retry;
- delivery audit.

## WP-009 Chart

- candles;
- channel;
- zones;
- marker;
- historical snapshot mode;
- realtime WS.

## WP-010 Backtest v1

- virtual clock;
- bar replay;
- strategy reuse;
- reports.

## WP-011 OFI/LOB features

- QI;
- depth imbalance;
- microprice;
- OFI;
- CVD;
- persistence.

## WP-012 Volume profile

- trade-level bins;
- POC/VAH/VAL;
- HVN/LVN;
- chart plugin.

## WP-013 Derivatives

- funding/OI/basis/liquidations;
- z-scores;
- state joins.

## WP-014 EVM connector

- logs;
- finality;
- reorg;
- ABI decoder;
- RPC health.

## WP-015 Uniswap v3 adapter

- pool math;
- swap decode;
- mint/burn;
- tick state;
- depth simulation.

## WP-016 Cross-venue

- canonical instrument mapping;
- consensus price;
- basis.

## WP-017 PIT dataset

- as-of joins;
- leakage asserts;
- labels;
- purged chronological folds.

## WP-018 GMDH

- model abstraction;
- polynomial node search;
- complexity constraints;
- validation criterion;
- feature interaction export;
- comparison report.


## WP-019 Price extrema / turning points

Implement in this order:

1. research-only symmetric `k`-neighborhood labels;
2. directional-change live baseline;
3. adaptive threshold interface;
4. causal local-polynomial slope/curvature;
5. optional Kalman filtered slope;
6. `ExtremumCandidate`, `TurningPointForecast`, `ConfirmedExtremum`, outcome models;
7. Kafka topics and storage adapters;
8. chart overlays and `AS-SEEN-THEN` semantics;
9. structural turning-point score;
10. point-in-time dataset targets for max/min/no-turn;
11. direct logistic/boosted baseline;
12. GMDH forward-path derivative experiment;
13. root-stability analysis;
14. Telegram alert integration behind a feature flag.

Done when:

- future-bar invariance test passes;
- confirmation legality test passes;
- replay parity passes;
- direct baseline metrics exist;
- derivative experiment can return `NO_EDGE` without blocking product completion.


## WP-020 Adaptive stop management

Implement in this order:

1. `PositionState`, `StopAnchor`, `StopProposal`, `StopPolicyOutcome` models;
2. manual/shadow position ingestion;
3. initial structural stop + causal volatility/noise buffer;
4. deterministic position-phase state machine;
5. confirmed-swing trailing baseline;
6. monotonic tightening guard;
7. minimum-distance guard;
8. hysteresis/cooldown/anti-churn;
9. channel-aware anchors;
10. order-flow confirmation/veto;
11. turning-point transition into defensive mode;
12. derivatives/DeFi context adapters;
13. data-quality freeze;
14. counterfactual stop-policy replay;
15. naive fixed-percent and ATR trailing baselines;
16. UI stop path + reason inspector;
17. Telegram stop-update event;
18. optional exchange reconciliation interface behind disabled feature flag.

Done when:

- no-future-swing legality test passes;
- LONG/SHORT monotonic tightening tests pass;
- stop-path replay is deterministic;
- adaptive vs naive OOS report exists;
- premature-stop metric exists;
- stop update latency is represented in replay;
- module is usable in shadow/paper mode without any exchange trading key;
- ML is not required for baseline completion.


---

# 47. Definition of Done — whole product MVP+

The project is not “done” merely because a chart and bot exist.

Minimum serious milestone requires:

1. Non-repainting channel proven by automated tests.
2. Signals stored with exact point-in-time feature snapshots.
3. Telegram deep-link works.
4. Backtest uses same signal engine.
5. CEX L2 reconstruction has gap protection.
6. Volume/OFI/derivatives can be toggled in score.
7. DeFi ingestion reconstructs protocol-native state and produces validated executable-depth features across at least one CL AMM and one invariant AMM.
8. Walk-forward report exists.
9. Channel-only vs enriched-feature ablation exists.
10. At least one probability model is calibrated and compared against logistic baseline.
11. GMDH is treated as candidate, not assumed winner.
12. Research report explicitly states when there is **no detectable edge**.
13. Confirmed extrema preserve separate `extremum_time` and `known_at`.
14. Turning-point forecasts expose explicit horizon and calibrated `P(max)/P(min)/P(no-turn)`.
15. GMDH derivative roots cannot be promoted without root-stability and OOS incremental-value tests.
16. Adaptive stop proposals are immutable and point-in-time causal.
17. Default stop policy never widens accepted position risk.
18. Stop-policy reports include premature-stop rate, MFE give-back and realized R versus naive trailing baselines.
19. Adaptive stop management can run entirely in shadow/paper mode without trading credentials.

---

# 48. Key Research Questions to Answer Before Any Auto-Trading

1. Does channel rejection have positive expectancy after fees at all?
2. Which channel estimator is most stable OOS?
3. Does upper/lower boundary outperform middle continuation?
4. Is the edge concentrated in specific volatility regimes?
5. Does OFI add incremental information after channel position?
6. Do persistent walls matter more than snapshot walls?
7. Does CVD divergence add value after OFI?
8. Does POC/VAH/VAL confluence improve expectancy?
9. How does rising OI change rejection/breakout probability?
10. Does extreme funding improve contrarian setups or merely identify strong trends?
11. Do liquidation bursts improve entry timing?
12. Does DEX liquidity asymmetry predict whether a CEX boundary holds?
13. Does DEX-CEX divergence lead or merely react?
14. Are results stable across BTC, ETH, SOL and other liquid coins?
15. Does GMDH produce stable interactions across walk-forward folds?
16. Does any apparent improvement survive realistic costs and latency?
17. Is probability calibrated enough to rank signals meaningfully?
18. Does structural trailing improve realized R versus fixed and naive trailing stops OOS?
19. How often does each policy stop a trade that later reaches the original target?
20. Which minimum-noise-distance estimator best reduces premature stop-outs without materially increasing tail loss?
21. Does order-flow confirmation improve stop timing after controlling for price structure and volatility?
22. Does turning-point probability improve defensive trailing or merely over-tighten profitable trends?
23. Does DeFi liquidity asymmetry add incremental value to stop management after CEX microstructure is known?
24. In which volatility/trend regimes should the optimal action remain `NO_CHANGE`?
18. Which non-repainting structural swing definition produces the most stable meaningful highs/lows?
19. How much confirmation lag is unavoidable for a useful extremum definition?
20. Does causal slope/curvature add value beyond channel position and recent returns?
21. Can GMDH derivative roots predict turning-point timing OOS, or are they polynomial artifacts?
22. Are derivative roots stable across bootstrap/ensemble perturbations?
23. Is direct `P(max/min within H)` forecasting better calibrated than path-derivative forecasting?
24. Does order-flow exhaustion add predictive value before extrema rather than only explain them contemporaneously?
25. Do OI/funding/liquidation conditions distinguish true exhaustion from trend continuation?
26. Does DEX liquidity migration or executable CEX↔DEX basis improve ETH turning-point forecasts?
27. Are extrema features useful independently at 5m/15m/1h and in nested multi-timeframe form?

---

# 49. Research Interpretation Rules

For every experiment output one of:

- `SUPPORTED` — stable OOS evidence;
- `WEAK` — directionally interesting but unstable;
- `NO_EDGE` — no reliable incremental value;
- `INVALID` — leakage/data issue;
- `NEEDS_MORE_DATA`.

Do not force every feature into production.

A good result may be: “Volume profile adds no incremental predictive value and is retained only for visual context.”

---

# 50. Sources / Research Basis

The architecture and experimental priorities in this PRD are informed by the following public documentation and research.

## Repainting / backtesting

- TradingView — Script or strategy gives different results after refreshing the page (repainting):
  https://www.tradingview.com/support/solutions/43000478429-script-or-strategy-gives-different-results-after-refreshing-the-page-repainting/
- TradingView Pine Script — Repainting / future leak concepts:
  https://www.tradingview.com/pine-script-docs/v5/concepts/repainting/
- TradingView Pine Script — Strategies / lookahead bias:
  https://uk.tradingview.com/pine-script-docs/concepts/strategies/

## Order flow / market microstructure

- Cont, Kukanov, Stoikov — The Price Impact of Order Book Events:
  https://arxiv.org/abs/1011.6402
- Gould, Bonart — Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book:
  https://arxiv.org/abs/1512.03492
- Xu, Gould, Howison — Multi-Level Order-Flow Imbalance in a Limit Order Book:
  https://arxiv.org/abs/1907.06230
- Kolm, Turiel, Westray — Deep Order Flow Imbalance:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3900141
- Sitaru, Calinescu, Cucuringu — Order Flow Decomposition for Price Impact Analysis:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4572510

## Spoofing / phantom liquidity

- Do, Putniņš — Detecting Layering and Spoofing in Markets:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4525036
- John, Li, Liu, Yang — The Impact of Spoofing on Bitcoin Market Microstructure:
  https://papers.ssrn.com/sol3/Delivery.cfm/5771502.pdf?abstractid=5771502

## Volume profile

- TradingView — Volume profile indicators: basic concepts:
  https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/

## DeFi / AMM

- Uniswap Developers — How Uniswap Works:
  https://developers.uniswap.org/docs/get-started/concepts/how-uniswap-works
- Uniswap Developers — Understanding Swaps / price impact:
  https://developers.uniswap.org/docs/get-started/concepts/traders/swaps
- Uniswap Developers — v4 PoolManager singleton architecture:
  https://developers.uniswap.org/docs/protocols/v4/concepts/poolmanager
- Uniswap Developers — v4 Architecture / hooks / dynamic fees / custom accounting:
  https://developers.uniswap.org/docs/protocols/v4/concepts/architecture
- Uniswap v4 core — IPoolManager events (`Initialize`, `ModifyLiquidity`, `Swap`):
  https://github.com/Uniswap/v4-core/blob/main/src/interfaces/IPoolManager.sol
- Curve Knowledge Hub — Cryptoswap in depth (`A`, `gamma`, price scale/oracle, rebalancing):
  https://docs.curve.finance/developer/amm/cryptoswap-in-depth
- Curve Knowledge Hub — Stableswap-NG integration, dynamic fees, rates and oracle views:
  https://docs.curve.finance/developer/integration/stableswap-ng
- Aerodrome official protocol docs — classic AMM + Slipstream concentrated liquidity:
  https://aerodrome.finance/docs
- Hyperliquid Docs — WebSocket subscriptions (`l2Book`, trades, BBO, mids, asset contexts):
  https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions
- Hyperliquid Docs — Perpetual asset contexts / funding / open interest:
  https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals
- Hyperliquid Docs — HyperEVM:
  https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/hyperevm
- Zhu et al. — What Drives Liquidity on Decentralized Exchanges? Evidence from Uniswap:
  https://arxiv.org/abs/2410.19107
- Mestel et al. — Price discovery on centralized and decentralized cryptocurrency exchanges:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5777295
- Wu et al. — Measuring CEX-DEX Extracted Value and Searcher Profitability:
  https://arxiv.org/abs/2507.13023
- Hansson — Price Discovery in Constant Product Markets:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4582649
- The Graph — Subgraphs:
  https://thegraph.com/subgraphs/


## Turning points / extrema / online change detection

- Aloud, Tsang, Olsen, Dupuis — A Directional-Change Event Approach for Studying Financial Time Series:
  https://doi.org/10.5018/economics-ejournal.ja.2012-36
- Tsang et al. / review — Algorithmic trading with directional changes:
  https://link.springer.com/article/10.1007/s10462-022-10307-0
- Preis et al. / directional-change literature — The scale of market quakes:
  https://www.tandfonline.com/doi/full/10.1080/14697688.2011.609180
- Li, Deng, Luo — Trading strategy design in financial investment through a turning points prediction scheme:
  https://doi.org/10.1016/j.eswa.2008.11.014
- Adams, MacKay — Bayesian Online Changepoint Detection:
  https://arxiv.org/abs/0710.3742
- Tsaknaki, Lillo, Mazzarisi — Bayesian Autoregressive Online Change-Point Detection with Time-Varying Parameters:
  https://arxiv.org/abs/2407.16376
- SciPy — `find_peaks` (offline/research peak properties such as prominence/width):
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html
- SciPy — `savgol_filter` derivative support; centered usage must not leak into live features:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html

## Time-series uncertainty / robust trend

- Xu, Xie — Conformal prediction for time series:
  https://arxiv.org/abs/2010.09107
- Zaffran et al. — Adaptive Conformal Predictions for Time Series:
  https://arxiv.org/abs/2202.07282
- Wen et al. — RobustTrend:
  https://arxiv.org/abs/1906.03751

## Exchange / chart / notification docs

- Binance Developer Docs — WebSocket Market Streams:
  https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/websocket-market-streams/Connect
- Binance — Correct local order-book management:
  https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/websocket-market-streams/How-to-manage-a-local-order-book-correctly
- Bybit V5 — Orderbook WebSocket:
  https://bybit-exchange.github.io/docs/v5/websocket/public/orderbook
- OKX API documentation:
  https://www.okx.com/docs-v5/
- Lightweight Charts:
  https://tradingview.github.io/lightweight-charts/docs
- Lightweight Charts plugin examples, including heatmap/volume-profile primitives:
  https://tradingview.github.io/lightweight-charts/plugin-examples/
- Telegram Bot API:
  https://core.telegram.org/bots/api

## Open-source architecture references

- Cryptofeed:
  https://github.com/bmoscon/cryptofeed
- NautilusTrader:
  https://nautilustrader.io/
- Hummingbot connectors:
  https://hummingbot.org/connectors/
- Freqtrade backtesting/reference:
  https://docs.freqtrade.io/en/stable/backtesting/

---

# 51. Final implementation principle

ChannelFlow should be designed to make it **hard to fool ourselves**.

The project is successful if it can reliably answer not only:

> “Ось красивий сетап.”

but also:

> “На історії це виглядало красиво через repainting — у real-time такого сигналу не існувало.”

or:

> “Модель намалювала ідеальний локальний максимум лише тому, що label використовував майбутні бари; у live цей максимум став відомим через 3 бари.”

or:

> “GMDH має нуль похідної через 4 бари, але root нестабільний між folds/ensemble, тому turning-point alert не промотується.”

or:

> “Channel rejection існує, але після fees edge зникає.”

or:

> “Сам канал слабкий, але при persistent ask absorption + rising OI + thin DEX liquidity above spot probability of downside continuation materially increases.”

Only after such evidence should automatic execution be considered.
