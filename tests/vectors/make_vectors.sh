#!/usr/bin/env bash
# Regenerates telegram_init_data.json (REQ-WP-080).
#
# The signatures are computed by `openssl`, a THIRD implementation: the Python verifier in the API and
# the TypeScript dev signer are each checked against this file, and neither wrote it. A verifier tested
# only against its own signer proves nothing.
#
# Telegram's algorithm: secret = HMAC_SHA256(key="WebAppData", msg=bot_token);
#                       hash   = HMAC_SHA256(key=secret, msg=data_check_string) as hex,
# where data_check_string is every field except `hash`, as `key=value` (decoded), sorted by key,
# joined with "\n".
#
# Usage:  tests/vectors/make_vectors.sh > tests/vectors/telegram_init_data.json
set -euo pipefail

TOKEN='123456:TEST-TOKEN-NOT-A-SECRET'
OTHER='654321:ANOTHER-TEST-TOKEN'
NOW=1790000000
MAX_AGE=86400

USER='{"id":7,"first_name":"Test","username":"tester"}'
QID='AAHdF6IQAAAAAN0XohDhrOrc'

python3 - "$TOKEN" "$OTHER" "$NOW" "$MAX_AGE" "$USER" "$QID" <<'PY'
import json, subprocess, sys
from urllib.parse import urlencode

token, other, now, max_age, user, qid = sys.argv[1:7]
now, max_age = int(now), int(max_age)

def hmac_hex(key_hex, msg):
    out = subprocess.run(["openssl", "dgst", "-sha256", "-mac", "HMAC", "-macopt", f"hexkey:{key_hex}"],
                         input=msg.encode(), capture_output=True, check=True).stdout.decode()
    return out.split("= ")[-1].strip()

def secret_hex(tok):
    out = subprocess.run(["openssl", "dgst", "-sha256", "-hmac", "WebAppData"],
                         input=tok.encode(), capture_output=True, check=True).stdout.decode()
    return out.split("= ")[-1].strip()

def signed(tok, fields):
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    return hmac_hex(secret_hex(tok), dcs)

def launch(tok, fields, *, hash_=True, tamper=None):
    h = signed(tok, fields)
    body = dict(fields)
    if tamper:
        body.update(tamper)
    if hash_:
        body["hash"] = h
    return urlencode(body)

base = {"query_id": qid, "user": user, "auth_date": str(now - 100)}
no_user = {"query_id": qid, "auth_date": str(now - 100)}
no_date = {"query_id": qid, "user": user}
stale = dict(base, auth_date=str(now - max_age - 1))
future = dict(base, auth_date=str(now + 61))
malformed = dict(base, auth_date="not-a-number")

cases = [
    {"name": "valid", "init_data": launch(token, base), "verdict": "accept"},
    {"name": "valid_no_user", "init_data": launch(token, no_user), "verdict": "accept"},
    {"name": "field_changed", "init_data": launch(token, base, tamper={"query_id": qid + "X"}),
     "verdict": "refuse", "reason": "bad_signature"},
    {"name": "wrong_token", "init_data": launch(other, base), "verdict": "refuse", "reason": "bad_signature"},
    {"name": "no_hash", "init_data": launch(token, base, hash_=False), "verdict": "refuse", "reason": "missing_hash"},
    {"name": "no_auth_date", "init_data": launch(token, no_date), "verdict": "refuse", "reason": "missing_auth_date"},
    {"name": "stale", "init_data": launch(token, stale), "verdict": "refuse", "reason": "too_old"},
    {"name": "from_the_future", "init_data": launch(token, future), "verdict": "refuse", "reason": "from_the_future"},
    {"name": "auth_date_not_a_number", "init_data": launch(token, malformed), "verdict": "refuse", "reason": "malformed"},
]
print(json.dumps({
    "about": "REQ-WP-080. Signatures computed by openssl (tests/vectors/make_vectors.sh); never by the code under test.",
    "bot_token": token, "max_age_seconds": max_age, "now": now, "cases": cases,
}, indent=2))
PY
