# Market Forge — Crypto Market Structure & Signal Radar

> **AI tool disclosure.** This project was developed with AI assistance. Claude (Anthropic) was used throughout for code generation, refactoring and review; co-authorship is recorded in the commit trailers. All architectural decisions, algorithm design and final code review were done by the author.

Non-repainting crypto market-structure radar: finds channel-boundary setups,
confirms them with order flow, derivatives and DeFi liquidity, and sends
explainable alerts to Telegram.

## The problem

Most crypto "channel" and trendline indicators look great on history and fail
live. They repaint: they use unclosed bars, future pivot confirmations, or
recompute the whole history. Traders end up trusting backtests that were never
real, and the signal usually arrives as a bare arrow with no reasoning behind it.

## What Market Forge does

1. **A channel that never repaints.** Every finalized channel snapshot and signal
   decision is append-only and immutable. A feature at time `t` only uses data
   with `event_time <= t` that was actually available at `t`.
2. **Setups confirmed by independent data groups.** Boundary rejection and
   middle-line continuation setups are checked against order flow and book
   persistence (filtering out spoofed walls), volume profile, derivatives
   (OI, funding, liquidations) and DeFi liquidity (DEX↔CEX basis).
3. **Probabilities, not price targets.** Rejection, breakout and
   target-before-invalidation probabilities, with calibration metrics.
4. **Every alert is explained.** A factor-by-factor breakdown, and an explicit
   "NO ALERT" with a reason when the evidence does not support one.
5. **Telegram alerts with a deep link** that opens the interactive chart at the
   exact timestamp of the signal, with all overlays.

Live and replay share the same logic, so a backtest is reproducible from dataset
version, config and commit hash. Signal families can be compared by ablation
(channel only vs. + order flow vs. + derivatives vs. + DEX).

The MVP is analytics and alerts only. There is no automatic trading.

## Repository layout

| Path | What it holds |
|---|---|
| `channel_flow_prd_codex_ua_v5.md` | The PRD, the source of truth (read-only) |
| `src/channelflow/` | Python 3.12 backend: connectors, bars, channels, extrema, order book / OFI, derivatives, volume profile, DEX, cross-venue, scoring, signals, backtest, alerting, API |
| `apps/web/` | TypeScript chart application (Vite) |
| `specs/` | Spec Kit specification, plan and tasks per feature |
| `vault/` | Requirements, specs and outcome notes, with the traceability dashboard |
| `tools/trace/` | The traceability graph builder and validator |
| `tests/` | The pytest suite |
| `docs/deployment.md` | How the full stack is run |

## How it was built

Work is spec-driven and traceable. A PRD section becomes a requirement note, then
a spec, a plan, tasks, failing tests, and finally the implementation. Tests carry
`@pytest.mark.trace("REQ-...")` markers and source files carry `# @trace: REQ-...`
comments. `make validate` checks that every requirement has the spec, test,
outcome note and code it claims, and a pre-commit hook runs it on every commit.
Requirements that guard against look-ahead and repainting cannot advance without
a test.

## Quick start

Requirements: Python 3.12, Docker with Compose, Node (for the web app).

```sh
cp .env.example .env
make install                 # virtualenv and dependencies
sudo -E make data-dirs       # data directories owned by each service's user
make up                      # postgres and minio, waits until healthy
docker compose up -d --build # API, web app, ingest, resample, worker, Grafana
```

Nothing listens on an external interface by default; reach it through an SSH
tunnel or from the host itself. The web app is on `http://localhost:8080`
(for example `/chart/binance/BTCUSDT?tf=15m`) and Grafana on
`http://localhost:3000`. See [docs/deployment.md](docs/deployment.md) for the full
procedure and troubleshooting.

## Development

```sh
make test         # pytest
make lint         # ruff
make typecheck    # mypy --strict
make validate     # traceability rules
make web-install && make web-test && make web-build
```

## License

No license has been chosen yet.
