# Contract: the timeframe seam

1. **A higher-timeframe bar exists only for a closed window whose every source minute is present
   exactly once and final.** Anything else is a refusal, never a bar computed from the rest.
2. **A refusal names the window and what was wrong** — missing, duplicated, not final — with the open
   times, and is returned to the caller.
3. **A window still open yields neither a bar nor a refusal.**
4. **A read of a series as of `t` returns no bar with `close_time_ns > t`**, for every timeframe.
   The bar of a window is therefore absent for every instant inside it and present from its close.
5. **Nothing downstream is trusted to guarantee 1–3.** The table's refusal of unfinalized rows and the
   absence of duplicates are facts today; the resampler does not rely on them.
