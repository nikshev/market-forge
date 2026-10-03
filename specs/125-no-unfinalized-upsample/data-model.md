# Data Model: No unfinalized higher-timeframe close reaches a lower-timeframe consumer

No stored data changes.

## Window judgement (inside `resample`, per closed window)

Given the target window `[s, s + T)` and source timeframe `S`:

- **expected** = `{ s + k·S : k = 0 … T/S − 1 }` — the source open times that tile the window.
- **held** = a count, per open time, of the window's source bars.
- **missing** = expected − keys of held.
- **duplicated** = open times with a count above one.
- **not final** = open times of any held bar whose `is_final` is false.
- The window **folds** only if all three are empty. Otherwise a `Refusal`.

## `Refusal` (unchanged fields)

| field | meaning after this change |
|---|---|
| `open_time_ns` | the window's start |
| `expected` | `T / S` |
| `present` | the number of **distinct** expected minutes held |
| `reason` | `window <s> at <T> has <present> of <expected> source <S> bars` followed by `; missing [<open times>]`, `; duplicated [<open times>]`, `; not final [<open times>]` for whichever apply |
