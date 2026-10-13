// @trace: REQ-WP-001
// @trace: REQ-WP-009
// @trace: REQ-WP-074
// @trace: REQ-US-002
// @trace: REQ-WP-084
// @trace: REQ-WP-085
// @trace: REQ-WP-092
// @trace: REQ-WP-086
// @trace: REQ-WP-083
// @trace: REQ-WP-089
// @trace: REQ-WP-090
// @trace: REQ-WP-091
// @trace: REQ-WP-102
// @trace: REQ-WP-103
//
// The page an alert's deep link opens. PRD section 27.1's route, and section
// 27.5's default: AS-SEEN-THEN, always, unless the link says otherwise in so
// many words.
//
// REQ-WP-074: the link's `tf` is the timeframe the chart **opens** at; the
// control changes it afterwards. The offered set comes from the API, because a
// list written here would be the second list REQ-WP-073's FR-002 forbids.

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchBars,
  fetchChannel,
  fetchConsensus,
  fetchDexDepth,
  fetchExtrema,
  fetchFeatureSeries,
  fetchTimeframes,
  fetchVolumeProfile,
} from "./api";
import { AppShell } from "./AppShell";
import { CandidateSwitch } from "./CandidateSwitch";
import { Chart } from "./Chart";
import { GapNotice } from "./GapNotice";
import { Busy } from "./Busy";
import { LiveChip } from "./LiveChip";
import { LIVE_TIMEFRAME } from "./live";
import { useLiveBars } from "./useLiveBars";
import type { ChartHandle } from "./paneChart";
import { DexBands } from "./DexBands";
import { ChannelModeControl } from "./ChannelMode";
import { FlowPane } from "./FlowPane";
import { ProfileControls, type ProfileState } from "./ProfileControls";
import { DEFAULT_PROFILE_WINDOW, type ProfileWindow } from "./profileWindows";
import { LoadState, type LoadStateKind } from "./LoadState";
import { Markets } from "./Markets";
import { availablePanes, chooseSelection, ROW } from "./panes";
import { parseDeepLink, withMode, withTimeframe } from "./deepLink";
import { depthOverlay, type DepthOverlay } from "./dexDepth";
import { RESTORATION_NOTICE } from "./overlays";
import { TimeframeControl } from "./TimeframeControl";
import { DEFAULT_TIMEFRAME, matchTimeframe, type TimeframeOption } from "./timeframes";
import {
  AS_SEEN_THEN,
  type BarOut,
  type ChannelMode,
  type ChannelOut,
  type ConsensusOut,
  type ExtremaResponse,
  type FeaturePointOut,
  type VolumeProfileOut,
} from "./types";

// The instant the chart is showing: the link's, or the last bar's close when the
// link named none. Zero when there is neither, which ages every curve as
// `ahead` and says so rather than silently calling it fresh.
function atNsForDepth(linkAtNs: bigint | null, bars: readonly BarOut[]): bigint {
  return linkAtNs ?? bars.at(-1)?.close_time_ns ?? 0n;
}

// What a 404 from `/consensus` means (REQ-WP-091): the server has collected no quotes for this
// market yet, which is an answer rather than a failure -- the same distinction the volume profile
// makes. It is said in its own words and never as an error.
const NO_CONSENSUS_YET = "no consensus yet";

function asOptions(reported: readonly { token: string; timeframe_ns: number }[]): TimeframeOption[] {
  return reported.map((entry) => ({ token: entry.token, timeframeNs: entry.timeframe_ns }));
}

/**
 * Replace the address with `search`, leaving no history entry (REQ-WP-074).
 *
 * `replaceState`, not `pushState`: changing a timeframe or a mode is not
 * navigation, and a back button that steps through six timeframes is a worse
 * interface than one that leaves the page. The path is read live so unknown
 * segments survive.
 */
function writeAddress(search: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.history.replaceState(
    null,
    "",
    search === "" ? window.location.pathname : `${window.location.pathname}?${search}`,
  );
}

export function App(): JSX.Element {
  const theme = useTheme();
  // The chart's and the pane's colours, from the theme, so both sit on the surface they are drawn on.
  const chartPalette = {
    background: theme.palette.background.paper,
    text: theme.palette.text.secondary,
    grid: theme.palette.divider,
  };
  // Parsed once, at mount. The address is an input on the way in and an output
  // afterwards: re-parsing it every render re-created this object, re-created
  // `load` with it, and refired the effect -- measured 2026-09-23 as 316 bars
  // requests in 300ms. The control's state, not the URL, is what changes while
  // the page is open; the address is written to match it.
  const [link] = useState(() =>
    typeof window === "undefined"
      ? null
      : parseDeepLink(window.location.pathname, window.location.search),
  );

  // Which view this page is. Read once, like the link and for the same reason:
  // an identity that changed per render would let a fetch completion flip the
  // view, and a route is not something that changes while a page is open --
  // every navigation here is a full load (REQ-WP-075).
  const [path] = useState(() => (typeof window === "undefined" ? "" : window.location.pathname));

  const [timeframe, setTimeframe] = useState<string>(() => link?.timeframe ?? DEFAULT_TIMEFRAME);
  const [offered, setOffered] = useState<TimeframeOption[] | null>(null);
  const [offeredFailure, setOfferedFailure] = useState<string | null>(null);
  const [mode, setMode] = useState<ChannelMode>(link?.mode ?? AS_SEEN_THEN);
  const [bars, setBars] = useState<BarOut[]>([]);
  const [channel, setChannel] = useState<ChannelOut | null>(null);
  const [state, setState] = useState<LoadStateKind>("ok");
  const [detail, setDetail] = useState<string | undefined>(undefined);
  // `null` when no pane has data for the view (REQ-WP-084). Starts on the first pane and moves once it is
  // known which panes have data.
  const [pane, setPane] = useState<string | null>(ROW[0]!.feature);
  const [points, setPoints] = useState<FeaturePointOut[]>([]);
  // False from the start of a load until the feature series has answered, ok or failed. Before then `points`
  // is empty, which is not the same as "no pane has data".
  const [pointsLoaded, setPointsLoaded] = useState(false);
  // True once the bars have answered, including with none. `state` cannot say it: it starts at "ok".
  const [barsLoaded, setBarsLoaded] = useState(false);
  // The main chart's handle, for the pane under it to line up with (REQ-WP-092); null until it exists.
  const [mainChart, setMainChart] = useState<ChartHandle | null>(null);
  // Candidate extrema are the detector's unconfirmed turns; off on every load, and not part of the link.
  const [showCandidates, setShowCandidates] = useState(false);
  // A pane's own failure, kept apart from the page's: the chart can load while
  // the features do not, and one message for both would blame the wrong thing.
  const [paneFailure, setPaneFailure] = useState<string | null>(null);
  const [extrema, setExtrema] = useState<ExtremaResponse>({ confirmed: [], candidates: [] });
  const [depth, setDepth] = useState<DepthOverlay | null>(null);
  // The volume profile by price level (REQ-WP-089): its own window, and its own state, because it is collected apart
  // from the bars and a market can have bars and no price bins.
  const [profileWindow, setProfileWindow] = useState<ProfileWindow>(DEFAULT_PROFILE_WINDOW);
  const [profile, setProfile] = useState<VolumeProfileOut | null>(null);
  const [profileState, setProfileState] = useState<ProfileState>("loading");
  const [profileFailure, setProfileFailure] = useState("");
  // The cross-venue consensus, in the window the chart is showing (REQ-WP-091). Its own state,
  // like the profile's: the chart is drawn whether or not the consensus answered, and an absent
  // consensus is a gap in the line rather than an empty page.
  const [consensus, setConsensus] = useState<ConsensusOut | null>(null);
  // Why there is no consensus when one was asked for: null while there is one, or when nothing was
  // asked. The per-bar refusals are `Chart`'s to say; this is the whole request's answer.
  const [consensusFailure, setConsensusFailure] = useState<string | null>(null);
  // True from the request until it has answered, ok, nothing or failed (REQ-WP-103).
  const [consensusLoading, setConsensusLoading] = useState(false);

  // Live refresh (REQ-WP-090): timer, in-flight guard, visibility, failure state
  const refreshIntervalMs = (() => {
    const raw = import.meta.env.VITE_CHART_REFRESH_MS;
    const parsed = raw === undefined ? 60_000 : Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
  })();
  // `window.setInterval` returns a number; `ReturnType<typeof setTimeout>` is Node's Timeout under @types/node.
  const timerId = useRef<number | null>(null);
  const isLoading = useRef(false);
  const [, setLastRefreshFailed] = useState(false);
  const [, setLastRefreshError] = useState<string | null>(null);
  // isInitialLoad: true for mount and timeframe/mode change, false for timer refresh
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  // The offered set, read once. Until it arrives no series request goes out:
  // the duration each request needs is one of these options.
  useEffect(() => {
    if (link === null) {
      return;
    }
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
      setOffered(asOptions(result.value.timeframes));
    })();
    return () => {
      live = false;
    };
  }, [link]);

  // Responses carry the id of the load that asked for them; a response whose
  // load has been superseded is discarded rather than drawn. Two fast clicks on
  // the timeframe control must end on the second, not on whichever fetch
  // happened to answer last.
  const loadId = useRef(0);

  const option = offered === null ? null : matchTimeframe(offered, timeframe);
  const refused = offered !== null && option === null;

  // Waiting, said out loud (REQ-WP-103). The first load is the chart with nothing to draw yet: `bars` empty and the answer
  // outstanding. A reload is the same wait with a chart already on screen, so it is a small mark by the title instead.
  const firstLoad = !refused && !barsLoaded && bars.length === 0 && state !== "failed";
  const refreshing = !refused && (!barsLoaded || !pointsLoaded) && bars.length > 0;

  // The chart's real-time feed (REQ-WP-102): only for the live 1m chart -- not a view pinned to an instant, which is
  // history and must not grow -- and for no timeframe the ingest does not build bars at.
  const live = useLiveBars({
    venue: link?.venue ?? "",
    symbol: link?.symbol ?? "",
    enabled: link !== null && link.atNs === null && option !== null && option.token === LIVE_TIMEFRAME,
  });

  const load = useCallback(async (initial = false) => {
    if (link === null || option === null) {
      return;
    }
    setIsInitialLoad(initial);
    const mine = ++loadId.current;
    const superseded = () => mine !== loadId.current;
    setPointsLoaded(false);
    setBarsLoaded(false);

    const timeframeNs = option.timeframeNs;
    const barsResult = await fetchBars({
      venue: link.venue,
      symbol: link.symbol,
      timeframeNs,
      limit: 500,
    });
    if (superseded()) {
      return;
    }
    if (!barsResult.ok) {
      // FR-016: a failed load is stated, never rendered as an empty chart that
      // could be mistaken for a quiet market.
      const detail = initial ? barsResult.error : `Refresh failed: ${barsResult.error}`;
      setState("failed");
      setDetail(detail);
      if (!initial) {
        setLastRefreshFailed(true);
        setLastRefreshError(barsResult.error);
      }
      return;
    }
    setBars(barsResult.value.bars);
    setBarsLoaded(true);
    setState(barsResult.value.bars.length === 0 ? "empty" : "ok");
    if (!initial) {
      setLastRefreshFailed(false);
      setLastRefreshError(null);
    }

    const atNs = link.atNs ?? barsResult.value.bars.at(-1)?.close_time_ns ?? null;
    if (atNs === null) {
      return;
    }
    const channelResult = await fetchChannel({
      venue: link.venue,
      symbol: link.symbol,
      timeframeNs,
      atNs,
      mode,
    });
    if (superseded()) {
      return;
    }
    // An absent channel is not a failure of the page: the chart draws candles
    // and no channel, which is the honest picture (US4 scenario 5).
    setChannel(channelResult.ok ? channelResult.value : null);

    const loaded = barsResult.value.bars;
    const seriesResult = await fetchFeatureSeries({
      venue: link.venue,
      symbol: link.symbol,
      timeframeNs,
      startNs: loaded[0]?.open_time_ns ?? atNs,
      endNs: loaded.at(-1)?.close_time_ns ?? atNs,
    });
    if (superseded()) {
      return;
    }
    setPaneFailure(seriesResult.ok ? null : seriesResult.error);
    setPoints(seriesResult.ok ? seriesResult.value.points : []);
    setPointsLoaded(true);

    const extremaResult = await fetchExtrema({
      instrumentId: `${link.venue}:${link.symbol}`,
      timeframeNs,
      // AS-SEEN-THEN asks as of the instant; CURRENT REFIT asks for everything
      // on record, which is where PRD section 27.5 wants the difference to show.
      asOfNs: mode === AS_SEEN_THEN ? atNs : null,
    });
    if (superseded()) {
      return;
    }
    // An absent list is not a failure of the page, the way an absent channel is
    // not: the chart draws what it has.
    setExtrema(extremaResult.ok ? extremaResult.value : { confirmed: [], candidates: [] });

    // Only when the link named a pool. Without one there is nothing to ask for,
    // and a failed request would produce "depth could not be loaded" on every
    // chart of every CEX symbol -- a notice about a layer nobody could have.
    if (link.chainId !== null && link.pool !== null) {
      const depthResult = await fetchDexDepth({
        chainId: link.chainId,
        pool: link.pool,
        atNs,
      });
      if (superseded()) {
        return;
      }
      // The failure is kept, not discarded: `depthOverlay` turns it into the
      // FAILED state, which the layer states rather than drawing as an empty
      // curve (FR-016).
      setDepth(depthOverlay(depthResult));
    }
  }, [link, mode, option]);

  // Which panes have data: known only once the series has answered and did not fail. `null` is "not known",
  // and says nothing of any pane -- a load in flight, or a failed one, is not an absence.
  const available = useMemo(
    () => (pointsLoaded && paneFailure === null ? availablePanes(points, bars) : null),
    [pointsLoaded, paneFailure, points, bars],
  );
  useEffect(() => {
    setPane((current) => chooseSelection(current, available));
  }, [available]);

  const wantsProfile = link !== null && link.overlays.overlays.includes("volume_profile");
  useEffect(() => {
    if (link === null || !wantsProfile) {
      return;
    }
    let live = true;
    setProfileState("loading");
    void (async () => {
      // Whatever goes wrong here is the profile's alone: the chart and its panes do not wait for it, and a failed
      // profile is stated as a failure, never drawn as an empty one (FR-016).
      try {
        const result = await fetchVolumeProfile({
          venue: link.venue,
          symbol: link.symbol,
          window: profileWindow,
          atNs: link.atNs,
        });
        if (!live) {
          return;
        }
        if (result.ok && Array.isArray(result.value?.bins)) {
          setProfile(result.value);
          setProfileState("ok");
        } else if (result.ok) {
          // An answer that is not a profile is not drawn as one.
          setProfile(null);
          setProfileState("failed");
          setProfileFailure("the response was not a volume profile");
        } else {
          setProfile(null);
          // 404 is the server saying nothing has been collected for this market yet, which is not a failure.
          setProfileState(result.error === "HTTP 404" ? "none" : "failed");
          setProfileFailure(result.error);
        }
      } catch (cause) {
        if (live) {
          setProfile(null);
          setProfileState("failed");
          setProfileFailure(cause instanceof Error ? cause.message : String(cause));
        }
      }
    })();
    return () => {
      live = false;
    };
  }, [link, wantsProfile, profileWindow]);

  // The cross-venue consensus (REQ-WP-091, PRD §17.1): asked for only when the link turned the
  // layer on, for the market in the link, as of the link's instant, in the timeframe in force.
  // The same shape as the profile's effect above: it never holds up the chart, and a request that
  // fails is stated rather than drawn as an absent line that could read as a quiet market.
  const wantsConsensus = link !== null && link.overlays.overlays.includes("consensus");
  useEffect(() => {
    if (link === null || !wantsConsensus) {
      setConsensus(null);
      setConsensusFailure(null);
      setConsensusLoading(false);
      return;
    }
    if (option === null) {
      // The offered set has not answered yet, so there is no timeframe to ask with. Nothing has
      // been asked, so there is nothing to clear either.
      return;
    }
    let live = true;
    setConsensus(null);
    setConsensusFailure(null);
    setConsensusLoading(true);
    void (async () => {
      try {
        const result = await fetchConsensus({
          venue: link.venue,
          symbol: link.symbol,
          timeframeNs: option.timeframeNs,
          // The profile's window, for the same reason: how far back to read, chosen once here
          // rather than carried in the link.
          window: "24h",
          atNs: link.atNs,
        });
        if (!live) {
          return;
        }
        if (result.ok) {
          setConsensus(result.value);
        } else {
          setConsensus(null);
          // 404 is the server saying no quotes have been collected for this market yet -- an
          // answer, not a failure (FR-016 states the difference in the words it uses).
          setConsensusFailure(result.error === "HTTP 404" ? NO_CONSENSUS_YET : result.error);
        }
      } catch (cause) {
        if (live) {
          setConsensus(null);
          setConsensusFailure(cause instanceof Error ? cause.message : String(cause));
        }
      } finally {
        if (live) {
          setConsensusLoading(false);
        }
      }
    })();
    return () => {
      live = false;
    };
  }, [link, wantsConsensus, option]);

  useEffect(() => {
    void load(true); // initial load is "initial"
    // Releasing the id on every dep change or unmount supersedes an in-flight
    // load, so its remaining requests stop and its answers are ignored.
    return () => {
      loadId.current += 1;
    };
  }, [load]);

  // The timers below must call the CURRENT `load`. `load` is rebuilt when the offered timeframes arrive
  // (it closes over `option`, which is null on the first render), and an effect whose dependencies are
  // `[refreshIntervalMs, link]` keeps the `load` it first saw -- one that returns at once because there is
  // no option yet. A refresh timer calling that one fires on schedule and refreshes nothing, which is
  // exactly what the interval test caught: the second bars request never came.
  const loadRef = useRef(load);
  useEffect(() => {
    loadRef.current = load;
  }, [load]);

  // Live refresh timer (REQ-WP-090): runs on interval while page is visible, unpinned, enabled, and not loading
  useEffect(() => {
    if (refreshIntervalMs <= 0 || link === null || link.atNs !== null) {
      return; // disabled, no link, or pinned chart
    }
    const tick = () => {
      if (isLoading.current) {
        return; // skip if previous load still in flight
      }
      isLoading.current = true;
      void loadRef.current(false).finally(() => {
        isLoading.current = false;
      });
    };
    timerId.current = window.setInterval(tick, refreshIntervalMs);
    return () => {
      if (timerId.current !== null) {
        window.clearInterval(timerId.current);
        timerId.current = null;
      }
    };
  }, [refreshIntervalMs, link]);

  // Visibility change: pause on hidden, one immediate refresh on visible (REQ-WP-090)
  useEffect(() => {
    if (refreshIntervalMs <= 0 || link === null || link.atNs !== null) {
      return;
    }
    const onVisibilityChange = () => {
      if (document.hidden) {
        if (timerId.current !== null) {
          window.clearInterval(timerId.current);
          timerId.current = null;
        }
      } else if (!isLoading.current) {
        // One immediate refresh when becoming visible
        isLoading.current = true;
        void loadRef.current(false).finally(() => {
          isLoading.current = false;
        });
        // Restart interval
        timerId.current = window.setInterval(() => {
          if (isLoading.current) {
            return;
          }
          isLoading.current = true;
          void loadRef.current(false).finally(() => {
            isLoading.current = false;
          });
        }, refreshIntervalMs);
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [refreshIntervalMs, link]);

  if (path === "/" || path === "/markets") {
    // The overview route (PRD §27.1). The PRD names no `/` route; serving the
    // same view there is this deployment's decision, recorded in
    // [[REQ-WP-075]] rather than left as an undocumented redirect.
    return <Markets />;
  }

  if (link === null) {
    return (
      <AppShell>
        <Typography>Open a chart at /chart/&lt;venue&gt;/&lt;symbol&gt;.</Typography>
      </AppShell>
    );
  }

  if (offeredFailure !== null) {
    // FR-010: the set could not be read, so no control and no chart -- an
    // empty control would look like a shape with no data rather than a
    // failure.
    return (
      <AppShell back="/">
        <Typography variant="h5" component="h2" sx={{ mb: 1 }}>
          {link.symbol} · {link.venue} · {timeframe}
        </Typography>
        <LoadState state="failed" detail={offeredFailure} />
      </AppShell>
    );
  }

  // Said out loud, never inferred from an empty chart: a page that quietly
  // showed its defaults would claim to have restored a state nobody recorded.
  const notice = RESTORATION_NOTICE[link.overlays.state];

  const selectTimeframe = (token: string): void => {
    setTimeframe(token);
    writeAddress(withTimeframe(window.location.search, token));
  };

  const selectMode = (next: ChannelMode): void => {
    setMode(next);
    writeAddress(withMode(window.location.search, next));
  };

  return (
    <AppShell back="/">
      <Typography variant="h5" component="h2" sx={{ mb: 1.5, overflowWrap: "anywhere" }}>
        {link.symbol} · {link.venue} · {timeframe}
        <LiveChip status={live.status} />
        {refreshing ? <Busy label="Updating the chart" inline /> : null}
      </Typography>
      <Stack spacing={1.5} sx={{ mb: 1.5 }}>
        {offered === null ? (
          <Busy label="Loading timeframes" />
        ) : (
          <TimeframeControl offered={offered} selected={timeframe} onSelect={selectTimeframe} />
        )}
        <ChannelModeControl mode={mode} onChange={selectMode} />
      </Stack>
      {refused ? (
        // FR-006: refused visibly, naming the token, instead of silently
        // substituting a timeframe nobody asked for. No chart: an empty one
        // would read as "no data at the right timeframe", which is a different
        // and false claim.
        <Alert severity="warning" role="alert" sx={{ my: 1 }}>
          Cannot show {timeframe}: this deployment offers{" "}
          {offered.map((entry) => entry.token).join(", ")}.
        </Alert>
      ) : null}
      <LoadState state={state} detail={detail} />
      {notice === null ? null : (
        // Named, because the page now carries more than one status and a
        // reader -- or a test -- asking for "the status" would get whichever
        // came first.
        <Alert severity="info" variant="outlined" role="status" aria-label="Overlay restoration" sx={{ my: 1 }}>
          {notice}
        </Alert>
      )}
      {refused ? null : <CandidateSwitch pressed={showCandidates} onChange={setShowCandidates} />}
      {refused ? null : (
        // The chart sits on the theme's surface and draws in its palette (REQ-WP-083).
        <Paper variant="outlined" sx={{ p: 1, overflow: "hidden", position: "relative" }}>
          {firstLoad ? (
            // Over the chart, which is mounted underneath so it can draw the moment the bars arrive: an empty chart is what
            // a quiet market and a slow load both look like (REQ-WP-103).
            <Box
              sx={{
                position: "absolute",
                inset: 0,
                zIndex: 2,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                bgcolor: "background.paper",
                opacity: 0.85,
              }}
            >
              <Busy label="Loading the chart" />
            </Box>
          ) : null}
          <Chart
            bars={bars}
            channel={channel}
            signal={null}
            overlays={link.overlays.overlays}
            volumeProfile={profile}
            // The `consensus` array of the envelope, not the envelope: `Chart`'s prop is one point
            // per bar (T017's test pins the shape), and the envelope's window and instant are the
            // request's own, not something the chart draws.
            consensus={consensus?.consensus ?? null}
            focusAtNs={link.atNs}
            extrema={extrema}
            showCandidates={showCandidates}
            mode={mode}
            scheme={theme.palette.mode}
            palette={chartPalette}
            onReady={setMainChart}
            isInitialLoad={isInitialLoad}
            liveBars={live.bars}
          />
        </Paper>
      )}
      {refused || !wantsConsensus || !consensusLoading ? null : <Busy label="Loading the consensus" />}
      {refused || !wantsConsensus || consensusFailure === null ? null : (
        // Said above the panes, never left as a gap: with no consensus at all the chart would look
        // exactly like a layer nobody switched on (FR-016).
        <Alert
          severity={consensusFailure === NO_CONSENSUS_YET ? "info" : "warning"}
          role="status"
          aria-label="Consensus"
          sx={{ my: 1 }}
        >
          {consensusFailure === NO_CONSENSUS_YET
            ? "No consensus collected for this market yet."
            : `Could not load the consensus: ${consensusFailure}`}
        </Alert>
      )}
      {refused || !wantsProfile ? null : (
        <ProfileControls
          window={profileWindow}
          onWindow={setProfileWindow}
          profile={profile}
          state={profileState}
          failure={profileFailure}
        />
      )}
      {refused ? null : <GapNotice bars={bars} />}
      {depth === null || refused ? null : (
        <DexBands
          overlay={depth}
          // The cursor's instant is a `number` and is therefore already
          // quantised to the nearest 256ns -- REQ-WP-054's open question,
          // untouched here. The curve's own time is exact, so the comparison is
          // accurate to 256ns against a threshold of a minute.
          atNs={BigInt(atNsForDepth(link.atNs, bars))}
          visible={link.overlays.overlays.includes("dex_liquidity_bands")}
        />
      )}
      <FlowPane
        points={points}
        feature={pane}
        onSelect={setPane}
        failure={paneFailure}
        available={available}
        bars={bars}
        liveBars={live.bars}
        barsLoaded={barsLoaded}
        pointsLoaded={pointsLoaded}
        chart={mainChart}
        scheme={theme.palette.mode}
        palette={chartPalette}
      />
    </AppShell>
  );
}
