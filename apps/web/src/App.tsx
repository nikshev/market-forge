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
//
// The page an alert's deep link opens. PRD section 27.1's route, and section
// 27.5's default: AS-SEEN-THEN, always, unless the link says otherwise in so
// many words.
//
// REQ-WP-074: the link's `tf` is the timeframe the chart **opens** at; the
// control changes it afterwards. The offered set comes from the API, because a
// list written here would be the second list REQ-WP-073's FR-002 forbids.

import Alert from "@mui/material/Alert";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchBars,
  fetchChannel,
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

  const load = useCallback(async () => {
    if (link === null || option === null) {
      return;
    }
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
      setState("failed");
      setDetail(barsResult.error);
      return;
    }
    setBars(barsResult.value.bars);
    setBarsLoaded(true);
    setState(barsResult.value.bars.length === 0 ? "empty" : "ok");

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

  useEffect(() => {
    void load();
    // Releasing the id on every dep change or unmount supersedes an in-flight
    // load, so its remaining requests stop and its answers are ignored.
    return () => {
      loadId.current += 1;
    };
  }, [load]);

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
      </Typography>
      <Stack spacing={1.5} sx={{ mb: 1.5 }}>
        {offered === null ? null : (
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
        <Paper variant="outlined" sx={{ p: 1, overflow: "hidden" }}>
          <Chart
            bars={bars}
            channel={channel}
            signal={null}
            overlays={link.overlays.overlays}
            volumeProfile={profile}
            focusAtNs={link.atNs}
            extrema={extrema}
            showCandidates={showCandidates}
            mode={mode}
            scheme={theme.palette.mode}
            palette={chartPalette}
            onReady={setMainChart}
          />
        </Paper>
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
        barsLoaded={barsLoaded}
        chart={mainChart}
        scheme={theme.palette.mode}
        palette={chartPalette}
      />
    </AppShell>
  );
}
