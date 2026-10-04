// @trace: REQ-WP-083
// @trace: REQ-WP-075
//
// PRD §27.1's overview route. The list is the state: one row per market from
// §28.1's read, in §43's order, with no aggregate invented here and no
// client-side sort — the API ranked them and the view shows that ranking.
//
// Each row is an ordinary link to the chart's deep link, carrying the chosen
// timeframe. A link is what a reader can middle-click, copy or open in a new
// tab, and its `href` is exactly the string the browser will use.

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import { useEffect, useState } from "react";

import { AppShell } from "./AppShell";
import { MarketTypeChip } from "./MarketTypeChip";

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
    <AppShell>
      <Typography variant="h5" component="h2" sx={{ mb: 2 }}>
        Markets
      </Typography>
      {offeredFailure === null ? null : <LoadState state="failed" detail={offeredFailure} />}
      {offered === null ? null : (
        <Box sx={{ mb: 2 }}>
          <TimeframeControl offered={offered} selected={timeframe} onSelect={setTimeframe} />
        </Box>
      )}
      {failed ? <LoadState state="failed" detail={marketsFailure} /> : null}
      {empty ? (
        <Alert severity="info" role="status">
          No markets are configured on this deployment.
        </Alert>
      ) : null}
      {markets === null || failed ? null : (
        <Box
          component="ul"
          aria-label="Markets"
          sx={{
            listStyle: "none",
            p: 0,
            m: 0,
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
          }}
        >
          {markets.map((market) => (
            <Box component="li" key={`${market.venue}:${market.symbol}`}>
              <Card
                sx={{
                  height: "100%",
                  position: "relative",
                  transition: "box-shadow 120ms, border-color 120ms",
                  "&:hover": { borderColor: "primary.main", boxShadow: 3 },
                  "&:focus-within": { borderColor: "primary.main", boxShadow: 3 },
                }}
              >
                <CardContent>
                  {/* A stretched link: the link is the symbol alone, so its name (and its text) is exactly
                      the symbol; its box is stretched over the whole card so the card is the target. A name
                      that said everything on the card would make a screen reader read the card as a link. */}
                  <Typography variant="h6" component="div" sx={{ overflowWrap: "anywhere" }}>
                    <Link
                      href={marketHref(market.venue, market.symbol, timeframe)}
                      color="inherit"
                      underline="none"
                      sx={{ "&::after": { content: '""', position: "absolute", inset: 0 } }}
                    >
                      {market.symbol}
                    </Link>
                  </Typography>
                  <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 1 }}>
                    <Chip size="small" variant="outlined" label={market.venue} />
                    <MarketTypeChip type={market.market_type} />
                  </Box>
                  <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
                    {(
                      [
                        ["rank", market.rank_score],
                        ["setup", market.setup_score],
                        ["confidence", market.confidence],
                      ] as const
                    ).map(([name, value]) => (
                      <Chip
                        key={name}
                        size="small"
                        variant="outlined"
                        label={`${name} ${scoreLabel(value)}`}
                        sx={{
                          color: "text.secondary",
                          borderStyle: "dashed",
                          height: 22,
                          "& .MuiChip-label": { px: 0.75, fontSize: "0.7rem" },
                        }}
                      />
                    ))}
                  </Box>
                </CardContent>
              </Card>
            </Box>
          ))}
        </Box>
      )}
    </AppShell>
  );
}
