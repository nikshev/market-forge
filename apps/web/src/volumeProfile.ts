// @trace: REQ-WP-012
//
// PRD section 27.2 lists "volume profile" and "POC/VAH/VAL" among the chart's
// overlays. As with `series.ts`, the decision about what to draw lives here
// and is tested; the drawing itself is the library's problem, and jsdom has no
// layout engine for a component test to see it through.

export interface ProfileBin {
  low: number;
  high: number;
  volume: number;
}

export interface Profile {
  bins: ProfileBin[];
  pocIndex: number;
  valueAreaIndices: number[];
}

export type BarRole = "poc" | "value-area" | "ordinary";

export interface ProfileBar {
  low: number;
  high: number;
  // 0..1, relative to the busiest bin. A chart scales this to whatever width
  // it has; sending pixels from here would tie the data to one layout.
  width: number;
  role: BarRole;
}

export function profileBars(profile: Profile | null): ProfileBar[] {
  if (profile === null || profile.bins.length === 0) {
    // An absent profile draws nothing. A zero-width bar per bin would put a
    // ghost of the overlay on the chart, and a reader would have no way to
    // tell it from a genuinely empty session.
    return [];
  }

  const busiest = Math.max(...profile.bins.map((bin) => bin.volume));
  const inValueArea = new Set(profile.valueAreaIndices);

  return profile.bins.map((bin, index) => ({
    low: bin.low,
    high: bin.high,
    width: busiest === 0 ? 0 : bin.volume / busiest,
    role:
      index === profile.pocIndex
        ? "poc"
        : inValueArea.has(index)
          ? "value-area"
          : "ordinary",
  }));
}
