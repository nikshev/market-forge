// @trace: REQ-WP-009
//
// jsdom has no layout engine, so `lightweight-charts` cannot measure a
// container and refuses to draw. The chart's own rendering is the library's
// concern and is tested by the library; what these tests check is the data
// handed to it and what a reader is told -- see `Chart.test.tsx`.
import "@testing-library/jest-dom/vitest";
