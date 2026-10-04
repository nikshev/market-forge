# Contract: the channel as drawn

1. `GET /api/v1/channels` adds `slope_log_per_bar` (float) and changes nothing else.
2. For a channel with lookback L, `as_of` T and slope s, the bars drawn are the last L with close <= T.
3. Point `i` of line `x` (counting 0..n-1, last = n-1) is `x_now * exp(s * (i - (n-1)))`.
4. A non-finite `s` draws nothing.
