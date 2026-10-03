// @trace: REQ-WP-080
//
// Dev helper: generate a freshly signed Telegram `initData` string and write it to
// `.env.development.local` as `VITE_DEV_INITDATA`, so the Mini App's authentication can be exercised
// in a plain browser (no Telegram, no tunnel, no BotFather).
//
// **Not `.env.local`.** Vite reads `.env.local` in a *production* build too, and `docker build` copies
// whatever is in the directory: a signed launch written there would be baked into a deployed bundle.
// `.env.development.local` is read only in development, `apps/web/.dockerignore` keeps it out of the
// image, and the application reads the variable only when `import.meta.env.DEV`.
//
// The signature must match the API's bot token. The token is, in order: `--token`, the
// `TELEGRAM_BOT_TOKEN` environment variable, then a dev default that matches nothing real.
//
// Usage (from apps/web):
//   npm run dev:init -- [--token 123:abc] [--id 7] [--name Mia] [--auth-date <unix seconds>] [--print]

import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { buildInitData } from "./telegram-sign.mjs";

const WEB_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const TARGET = resolve(WEB_DIR, ".env.development.local");
const DEV_DEFAULT_TOKEN = "123456:dev-token-matches-nothing-real";

function arg(name) {
  const at = process.argv.indexOf(`--${name}`);
  return at !== -1 ? process.argv[at + 1] : undefined;
}

const token = arg("token") ?? process.env.TELEGRAM_BOT_TOKEN ?? DEV_DEFAULT_TOKEN;
const id = Number(arg("id") ?? 1);
const name = arg("name") ?? "Dev";
const authDate = arg("auth-date") ?? String(Math.floor(Date.now() / 1000));

const initData = buildInitData(token, {
  auth_date: authDate,
  query_id: "AAdev",
  user: JSON.stringify({ id, first_name: name }),
});

if (process.argv.includes("--print")) {
  process.stdout.write(`${initData}\n`);
} else {
  writeFileSync(TARGET, `VITE_DEV_INITDATA=${initData}\n`);
  process.stdout.write(`wrote ${TARGET}\n`);
}
