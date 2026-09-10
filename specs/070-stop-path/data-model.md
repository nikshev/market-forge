# Phase 1 — Data model

## Wire shapes (mirrored, as `types.ts` mirrors the rest of §28)

```ts
StopAnchorOut    { kind, price, known_at_ns, description }
StopProposalOut  { at_ns, price, phase, reasons: string[], anchor: StopAnchorOut | null, moved }
PositionOut      { position_id, side, entry_time_ns, average_entry_price,
                   initial_stop_price, hard_stop_price: string | null,
                   current_strategy_stop }
ExcursionOut     { mfe_r: number | null, mae_r: number | null }
```

`hard_stop_price` is nullable and means **no catastrophic stop was set**. It is
never the initial stop: those are two different promises, and a view that
collapsed them would draw one line where the position has one and where it has
two.

`anchor` is nullable and means **this decision rested on no structural level** —
which is what a hold with nothing knowable is. It is never the previous anchor.

## The answer

```ts
StopLevel     { label: "entry" | "initial" | "hard" | "current", price: string }
StopPathPoint { at_ns, price, kind: "moved" | "held" | "refused",
                reasons: string[], anchor: StopAnchorOut | null }
StopPathView  { state: "ok" | "empty" | "inconsistent",
                note: string,
                levels: StopLevel[],
                path: StopPathPoint[],
                openRiskR: number | null,
                lockedProfitR: number,
                mfeR: number | null, maeR: number | null }
```

`state` follows `panes.ts`. `empty` is a position with no proposals — a real
answer with levels and risk but no path. `inconsistent` is a path carrying an
anchor its proposal could not have known, and it carries no path at all.

`lockedProfitR` is a number, not nullable: a stop still below entry locks
nothing, and zero is the true reading. `mfeR` and `maeR` are nullable, because
an excursion over nothing observed is not zero.

## State transitions

None. The view is a function of a position, a proposal list, a mode and an
instant.
