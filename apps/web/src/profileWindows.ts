// @trace: REQ-WP-089
//
// The windows the volume profile can be asked for. Not timeframes: a timeframe is the width of one bar and comes from
// what the deployment reports (REQ-WP-074); a profile window is how far back the price bins are summed, and the server
// serves exactly these (`ProfileWindow` in `api/volume_profile.py`).

export const PROFILE_WINDOWS = ["4h", "24h", "7d"] as const;
export type ProfileWindow = (typeof PROFILE_WINDOWS)[number];
export const DEFAULT_PROFILE_WINDOW: ProfileWindow = "24h";
