// @vitest-environment node
// @trace: REQ-WP-080
//
// A production build must not contain a signed launch (FR-014, SC-004).
//
// The risk is real, not hypothetical. Vite reads some `.env.*` files in a production build, and
// `docker build` copies whatever sits in the directory, so a developer's `npm run dev:init` output could
// become part of a deployed bundle. The application reads the variable only under `import.meta.env.DEV`;
// this builds with a sentinel in it and searches every output file for the sentinel.
//
// **Built in a child process with `NODE_ENV=production`, as `npm run build` does.** The first version
// called Vite's `build()` from inside the test, and failed -- correctly, as it turned out, for the wrong
// reason: vitest sets `NODE_ENV=test`, so `import.meta.env.DEV` was true inside that build and the
// sentinel was bundled. A check that runs under different conditions from the thing it checks says
// nothing about it. The development build below is the control: it *does* contain the sentinel, so the
// search is capable of finding one.

import { execFileSync } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { describe, expect, it } from "vitest";

const SENTINEL = "SENTINEL-SIGNED-LAUNCH-auth_date=1790000000-hash=deadbeefdeadbeef";
const WEB = resolve(__dirname, "../..");
const VITE_BIN = join(WEB, "node_modules", "vite", "bin", "vite.js");

function filesUnder(dir: string): string[] {
  return readdirSync(dir).flatMap((name: string) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? filesUnder(path) : [path];
  });
}

function buildWith(mode: "production" | "development"): string[] {
  const out = mkdtempSync(join(tmpdir(), `mf-build-${mode}-`));
  execFileSync(
    process.execPath,
    [VITE_BIN, "build", "--mode", mode, "--outDir", out, "--emptyOutDir", "--logLevel", "silent"],
    {
      cwd: WEB,
      env: { ...process.env, NODE_ENV: mode, VITE_DEV_INITDATA: SENTINEL },
      stdio: "pipe",
    },
  );
  const files = filesUnder(out);
  expect(files.length).toBeGreaterThan(0);
  return files.filter((file) => readFileSync(file, "utf8").includes(SENTINEL));
}

describe("the build", () => {
  it("for production contains no signed launch, even with one in the environment", () => {
    expect(buildWith("production")).toEqual([]);
  }, 180_000);

  it("the control: a development build does contain it, so the search can find one", () => {
    expect(buildWith("development").length).toBeGreaterThan(0);
  }, 180_000);
});
