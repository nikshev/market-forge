// @trace: REQ-WP-075
//
// PRD §27.1's overview route. The list is the state: one row per market from
// §28.1's read, in §43's order, with no aggregate invented here and no
// client-side sort — the API ranked them and the view shows that ranking.
//
// Each row is an ordinary link to the chart's deep link, carrying the chosen
// timeframe. A link is what a reader can middle-click, copy or open in a new
// tab, and its `href` is exactly the string the browser will use.

import { useEffect, useState } from "react";

import { fetchMarkets, fetchTimeframes } from "./api";
import { LoadState } from "./LoadState";
import { marketHref, scoreLabel } from "./markets";
import { TimeframeControl } from "./TimeframeControl";
import { DEFAULT_TIMEFRAME, type TimeframeOption } from "./timeframes";
import type { MarketOut } from "./types";

export function Markets(): JSX.Element {
  const [markets, setMarkets] = useState<MarketOut[] | null>(null);
  const [marketsFailure, setMarketsFailure] = useState<string | null>(null);
  const [offered, setOffered] = useState<TimeframeOption[] | null>(null);
  const [offeredFailure, setOfferedFailure] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<string>(DEFAULT_TIMEFRAME);

  useEffect(() => {
    let live = true;
    void (async () => {
      const result = await fetchMarkets();
      if (!live) {
        return;
      }
      if (!result.ok) {
        setMarketsFailure(result.error);
        return;
      }
      setMarkets(result.value.markets);
    })();
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    let live = true;
    void (async () => {
      const result = await fetchTimeframes();
      if (!live) {
        return;
      }
      if (!result.ok) {
        setOfferedFailure(result.error);
        return;
      }
      setOffered(
        result.value.timeframes.map((entry) => ({
          token: entry.token,
          timeframeNs: entry.timeframe_ns,
        })),
      );
    })();
    return () => {
      live = false;
    };
  }, []);

  const failed = marketsFailure !== null;
  const empty = markets !== null && markets.length === 0;

  return (
    <main>
      <h1>ChannelFlow</h1>
      <h2>Markets</h2>
      {offeredFailure === null ? null : <LoadState state="failed" detail={offeredFailure} />}
      {offered === null ? null : (
        <TimeframeControl offered={offered} selected={timeframe} onSelect={setTimeframe} />
      )}
      {failed ? <LoadState state="failed" detail={marketsFailure} /> : null}
      {empty ? <p role="status">No markets are configured on this deployment.</p> : null}
      {markets === null || failed ? null : (
        <ul aria-label="Markets">
          {markets.map((market) => (
            <li key={`${market.venue}:${market.symbol}`}>
              <a href={marketHref(market.venue, market.symbol, timeframe)}>{market.symbol}</a>
              <span>
                {" "}
                {market.venue} · {market.market_type}
              </span>
              <span>
                {" "}
                rank {scoreLabel(market.rank_score)} · setup {scoreLabel(market.setup_score)} ·
                confidence {scoreLabel(market.confidence)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
