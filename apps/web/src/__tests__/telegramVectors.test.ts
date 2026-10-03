// @trace: REQ-WP-080
//
// The TypeScript signer against the answers `openssl` gave. The Python verifier is checked against the
// same file in the fast gate (`tests/unit/api/test_telegram_auth.py`); neither wrote it. If this signer
// and that verifier disagreed about Telegram's algorithm, one of them would fail against these.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { buildInitData, signFields } from "../../scripts/telegram-sign.mjs";

interface Vector {
  name: string;
  init_data: string;
  verdict: "accept" | "refuse";
}

const FILE = resolve(__dirname, "../../../../tests/vectors/telegram_init_data.json");
const VECTORS = JSON.parse(readFileSync(FILE, "utf8")) as {
  bot_token: string;
  cases: Vector[];
};

function fieldsOf(initData: string): { fields: Record<string, string>; hash: string | null } {
  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  params.delete("hash");
  return { fields: Object.fromEntries(params.entries()), hash };
}

describe("the TypeScript signer reproduces openssl's signatures", () => {
  const signedByTelegramsToken = VECTORS.cases.filter((c) =>
    ["valid", "valid_no_user", "stale", "from_the_future", "auth_date_not_a_number", "no_auth_date"].includes(c.name),
  );

  it.each(signedByTelegramsToken.map((c) => [c.name, c] as const))("%s", (_name, vector) => {
    const { fields, hash } = fieldsOf(vector.init_data);

    expect(signFields(VECTORS.bot_token, fields)).toBe(hash);
  });

  it("a changed field no longer matches the hash it came with", () => {
    const changed = VECTORS.cases.find((c) => c.name === "field_changed");
    const { fields, hash } = fieldsOf((changed as Vector).init_data);

    expect(signFields(VECTORS.bot_token, fields)).not.toBe(hash);
  });

  it("another token does not reproduce the hash", () => {
    const valid = VECTORS.cases.find((c) => c.name === "valid") as Vector;
    const { fields, hash } = fieldsOf(valid.init_data);

    expect(signFields("654321:ANOTHER-TEST-TOKEN", fields)).not.toBe(hash);
  });

  it("a built launch carries its own hash and round-trips", () => {
    const built = buildInitData(VECTORS.bot_token, { auth_date: "1790000000", query_id: "AAx" });
    const { fields, hash } = fieldsOf(built);

    expect(signFields(VECTORS.bot_token, fields)).toBe(hash);
  });
});
