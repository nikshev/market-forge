// @trace: REQ-WP-009
//
// jsdom has no layout engine, so `lightweight-charts` cannot measure a
// container and refuses to draw. The chart's own rendering is the library's
// concern and is tested by the library; what these tests check is the data
// handed to it and what a reader is told -- see `Chart.test.tsx`.
import "@testing-library/jest-dom/vitest";


// REQ-WP-102: a page that mounts the live feed opens a WebSocket, and no test but the ones about the feed wants one -- a
// real attempt at `ws://localhost` would only fail and be retried on a timer. This one never connects; the feed's own
// tests stub the global with a socket they can drive.
import { vi } from "vitest";

class InertSocket {
  readyState = 0;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  send(): void {}
  close(): void {}
}
vi.stubGlobal("WebSocket", InertSocket);
