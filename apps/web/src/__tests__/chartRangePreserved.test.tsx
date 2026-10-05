// @trace: REQ-WP-090
//
// Chart receives isInitialLoad=false on refresh, does not call fitContent/setVisibleLogicalRange

import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Chart } from "../Chart";

// Use vi.hoisted to define mocks that are accessible in the vi.mock factory
const { mockFitContent, mockSetVisibleLogicalRange, mockCreateChart } = vi.hoisted(() => {
  const fitContent = vi.fn();
  const setVisibleLogicalRange = vi.fn();
  const timeScale = vi.fn(() => ({
    fitContent,
    setVisibleLogicalRange,
  }));
  const chartInstance = {
    timeScale,
    remove: vi.fn(),
    addCandlestickSeries: vi.fn(() => ({
      setData: vi.fn(),
      setMarkers: vi.fn(),
      createPriceLine: vi.fn(),
      attachPrimitive: vi.fn(),
      detachPrimitive: vi.fn(),
    })),
    addLineSeries: vi.fn(() => ({
      setData: vi.fn(),
    })),
    removeSeries: vi.fn(),
  };
  const createChart = vi.fn(() => chartInstance);
  return { mockFitContent: fitContent, mockSetVisibleLogicalRange: setVisibleLogicalRange, mockCreateChart: createChart };
});

vi.mock("lightweight-charts", () => ({
  createChart: mockCreateChart,
  IChartApi: {},
  ISeriesApi: {},
}));

const MINUTE_NS = 60_000_000_000n;

function bars(count = 10, base = 1_789_344_000_000_000_000n): any[] {
  const result = [];
  for (let i = 0; i < count; i++) {
    const openNs = base + BigInt(i) * MINUTE_NS;
    result.push({
      open_time_ns: openNs,
      close_time_ns: openNs + MINUTE_NS,
      open: "100",
      high: "101",
      low: "99",
      close: "100",
      volume_base: "1",
      is_final: true,
    });
  }
  return result;
}

function channel(lookback = 100): any {
  return {
    centre: [{ time: 1, value: 100 }, { time: 2, value: 101 }],
    upper: [{ time: 1, value: 102 }, { time: 2, value: 103 }],
    lower: [{ time: 1, value: 98 }, { time: 2, value: 97 }],
    lookback,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("US2: isInitialLoad=false on refresh does not reset range", () => {
  it("calls setVisibleLogicalRange for channel window on initial load (isInitialLoad=true, no focusAtNs)", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<Chart bars={bars()} channel={channel()} isInitialLoad={true} />);

    // createChart is called synchronously on mount
    await waitFor(() => expect(mockCreateChart).toHaveBeenCalled(), { timeout: 2000 });
    // Give time for the second effect to run
    await waitFor(() => {}, { timeout: 100 });
    // With channel and no focusAtNs, setVisibleLogicalRange is called for channel window
    await waitFor(() => expect(mockSetVisibleLogicalRange).toHaveBeenCalled(), { timeout: 2000 });
    expect(mockFitContent).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });

  it("does NOT call fitContent or setVisibleLogicalRange on refresh (isInitialLoad=false)", async () => {
    render(<Chart bars={bars()} channel={channel()} isInitialLoad={false} />);

    await waitFor(() => expect(mockCreateChart).toHaveBeenCalled(), { timeout: 2000 });
    await waitFor(() => expect(mockFitContent).not.toHaveBeenCalled(), { timeout: 2000 });
    expect(mockSetVisibleLogicalRange).not.toHaveBeenCalled();
  });

  it("calls setVisibleLogicalRange for deep link instant (focusAtNs) on initial load", async () => {
    const focusAtNs = 1_789_344_000_000_000_000n + 5n * MINUTE_NS;
    render(<Chart bars={bars()} channel={channel()} focusAtNs={focusAtNs} isInitialLoad={true} />);

    await waitFor(() => expect(mockCreateChart).toHaveBeenCalled(), { timeout: 2000 });
    await waitFor(() => expect(mockSetVisibleLogicalRange).toHaveBeenCalled(), { timeout: 2000 });
  });

  it("does NOT call setVisibleLogicalRange for deep link instant on refresh", async () => {
    const focusAtNs = 1_789_344_000_000_000_000n + 5n * MINUTE_NS;
    render(<Chart bars={bars()} channel={channel()} focusAtNs={focusAtNs} isInitialLoad={false} />);

    await waitFor(() => expect(mockCreateChart).toHaveBeenCalled(), { timeout: 2000 });
    await waitFor(() => expect(mockSetVisibleLogicalRange).not.toHaveBeenCalled(), { timeout: 2000 });
  });
});