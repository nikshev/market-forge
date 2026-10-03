// @trace: REQ-WP-080
//
// Telegram's launch-data signature, in JavaScript (Node's crypto).
//
//   secret = HMAC_SHA256(key = "WebAppData", message = bot_token)
//   hash   = HMAC_SHA256(key = secret, message = data_check_string), hex
//
// where data_check_string is every field except `hash`, as `key=value` with the *decoded* value,
// sorted by key and joined with "\n".
//
// This is the second implementation of the algorithm in this repository (the first is the Python
// verifier in the API). Neither is trusted by the other: both are checked against
// tests/vectors/telegram_init_data.json, whose signatures were computed by `openssl`.

import { createHmac } from "node:crypto";

export function dataCheckString(fields) {
  return Object.keys(fields)
    .sort()
    .map((key) => `${key}=${fields[key]}`)
    .join("\n");
}

export function signFields(botToken, fields) {
  const secret = createHmac("sha256", "WebAppData").update(botToken).digest();
  return createHmac("sha256", secret).update(dataCheckString(fields)).digest("hex");
}

// A complete, signed `initData` string: the fields, URL-encoded, with their hash.
export function buildInitData(botToken, fields) {
  const params = new URLSearchParams(fields);
  params.set("hash", signFields(botToken, fields));
  return params.toString();
}
