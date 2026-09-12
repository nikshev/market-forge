"""Shared machinery for the chain capture tools.

# @trace: REQ-WP-046

Three capture tools now read contract state from public endpoints, and each one
learned the same lessons in turn. This is where they live:

* **Two endpoints answer every call, and a disagreement is a finding.** PRD
  section 18.17 asks for a multi-RPC strategy; the reason shows up the first
  time you use one, in that a value both agree on is a value.
* **The pool of candidates is larger than two.** Free endpoints rate-limit a
  sustained capture, and the Slipstream capture died two thirds of the way
  through on a 403 with two. An endpoint that starts refusing should cost the
  run an endpoint, not the run -- while two healthy ones stay required, so the
  pool degrades and the guarantee does not.
* **A refusal and a revert are different things**, and a caller must be able to
  tell them apart. A contract-level revert is a fact about the call that every
  endpoint would repeat, so treating it as a refusal burns the whole pool on one
  reverting call; a method an endpoint declines to serve, or a block it has
  pruned, is about the endpoint. They are separate exception types here because
  a capability probe -- "does this pool answer `gamma()`?" -- reads a revert as
  an answer and a quorum failure as a broken run, and conflating them turns the
  second into a silent wrong answer.
* **A pool that is momentarily short waits rather than failing.** A quorum of
  two out of a handful is easy to lose to one rate limit late in a long run, and
  aborting there throws away everything captured so far. The cooldowns are
  known, so the pool waits for the soonest one and tries again.
* **The pause between calls applies to reverts too.** A probe that expects most
  of its calls to revert otherwise hammers an endpoint at full speed and is rate
  limited into a cooldown, which is how a working probe returns nothing at all.
* **Selectors are computed, never copied.** A selector is the Keccak-256 of a
  signature, so computing it from a signature read out of the published source
  turns a typo into a failed call instead of a wrong one. Note that
  `hashlib.sha3_256` is *not* this -- SHA-3 and Keccak differ in their padding,
  and the wrong one produces plausible hashes rather than an error.

Nothing here runs in CI. These tools are run deliberately, and what they write
is committed.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from eth_hash.auto import keccak

HEADERS = {"Content-Type": "application/json", "User-Agent": "channelflow-capture/1.0"}

#: How long an endpoint that refuses stays out of the rotation.
COOLDOWN_SECONDS = 90.0

#: A breath between calls. These are public nodes nobody pays for, and a tool
#: that ignored that would be taking from a commons to save itself a minute.
PAUSE_SECONDS = 0.35

#: How many endpoints must answer every call. Two, always.
QUORUM = 2

#: How long to keep waiting for a quorum to come back before giving up. Longer
#: than one cooldown, so a single rate-limited endpoint costs a pause and not
#: the run; short enough that a genuinely dead pool is reported, not hung on.
QUORUM_WAIT_SECONDS = COOLDOWN_SECONDS * 2.5

#: The JSON-RPC error code every endpoint tested uses for a contract revert
#: (EIP-1474). Matched alongside the message, because one of the three omits
#: the `data` field the other two send and a payload shape is not a contract.
REVERT_CODE = 3


def selector(signature: str) -> str:
    return "0x" + keccak(signature.encode())[:4].hex()


class Refused(RuntimeError):
    """An endpoint declined this request. Another may not."""


class Reverted(RuntimeError):
    """The contract refused the call. Every endpoint would say the same.

    Distinct from `Refused` on purpose: for a capability probe this is the
    answer, not a failure.
    """


class EndpointPool:
    """A set of candidate endpoints, of which two must agree on every answer."""

    def __init__(self, urls: tuple[str, ...]) -> None:
        if len(urls) < QUORUM:
            raise ValueError(f"need at least {QUORUM} endpoints, got {len(urls)}")
        self.urls = urls
        self._available_at: dict[str, float] = dict.fromkeys(urls, 0.0)

    def healthy(self) -> list[str]:
        now = time.monotonic()
        return [url for url in self.urls if self._available_at[url] <= now]

    def _cool_off(self, url: str) -> None:
        self._available_at[url] = time.monotonic() + COOLDOWN_SECONDS

    def rpc(self, url: str, method: str, params: list[Any]) -> Any:
        """One JSON-RPC call to one endpoint."""
        request = urllib.request.Request(  # noqa: S310
            url,
            data=json.dumps(
                {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            ).encode(),
            headers=HEADERS,
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                body = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError) as exc:
            self._cool_off(url)
            raise Refused(f"{url}: {exc}") from exc
        finally:
            # Every call, not only the ones that return a value: a probe whose
            # calls mostly revert would otherwise run flat out and be rate
            # limited into a cooldown on every endpoint at once.
            time.sleep(PAUSE_SECONDS)
        if "error" in body:
            error = body["error"]
            if (
                error.get("code") == REVERT_CODE
                or "revert" in str(error.get("message", "")).lower()
            ):
                raise Reverted(f"{method}: {error}")
            self._cool_off(url)
            raise Refused(f"{url}: {error}")
        return body["result"]

    def any_rpc(self, method: str, params: list[Any]) -> Any:
        """One JSON-RPC call, from whichever endpoint answers first.

        For questions where a second opinion adds nothing -- the head block
        number, which every endpoint reports differently by design.
        """
        for url in self.healthy():
            try:
                return self.rpc(url, method, params)
            except Refused:  # noqa: PERF203
                continue
        raise RuntimeError(f"no endpoint answered {method}; healthy: {self.healthy()}")

    def _next_available_in(self) -> float:
        now = time.monotonic()
        waits = sorted(max(0.0, at - now) for at in self._available_at.values())
        return waits[QUORUM - 1] if len(waits) >= QUORUM else float("inf")

    def call(self, to: str, data: str, block: str) -> str:
        """One `eth_call`, asked of two healthy endpoints and refused if they differ."""
        params = [{"to": to, "data": data}, block]
        deadline = time.monotonic() + QUORUM_WAIT_SECONDS
        while True:
            answers: dict[str, str] = {}
            for url in self.healthy():
                if len(answers) == QUORUM:
                    break
                try:
                    answers[url] = self.rpc(url, "eth_call", params)
                except Refused:  # noqa: PERF203
                    continue
            if len(answers) >= QUORUM:
                break
            wait = self._next_available_in()
            if time.monotonic() + wait > deadline:
                raise RuntimeError(
                    f"fewer than {QUORUM} endpoints answered {to} {data[:10]} at {block}; "
                    f"healthy: {self.healthy()}"
                )
            time.sleep(wait + 1.0)
        distinct = set(answers.values())
        if len(distinct) != 1:
            raise RuntimeError(f"endpoints disagree on {to} {data[:10]} at {block}: {answers}")
        return distinct.pop()


def word(result: str, index: int = 0) -> int:
    raw = result[2:]
    return int(raw[index * 64 : (index + 1) * 64], 16)


def signed(result: str, index: int = 0) -> int:
    value = word(result, index)
    return value - (1 << 256) if value >= (1 << 255) else value


def address(result: str, index: int = 0) -> str:
    return "0x" + result[2:][index * 64 : (index + 1) * 64][-40:]


def dyn_array(result: str) -> list[int]:
    """A `uint256[]` return value, at the offset its head points to."""
    head = word(result, 0) // 32
    return [word(result, head + 1 + i) for i in range(word(result, head))]


def encode_uint(value: int) -> str:
    return f"{value & ((1 << 256) - 1):064x}"


def encode_address(value: str) -> str:
    return f"{int(value, 16):064x}"


def answers(pool: EndpointPool, to: str, data: str, block: str) -> bool:
    """Whether a contract answers this call at all -- a capability probe.

    A revert is the answer "no", not a failure. Anything else propagates: a
    probe that read a broken endpoint as "this pool has no `gamma()`" would
    classify a Cryptoswap pool as a Stableswap and price it with the wrong
    invariant, which is the whole failure this classification exists to stop.

    Empty return data is also "no", and separately so. A contract with a
    payable fallback -- WETH, for one -- accepts *any* selector and returns
    nothing rather than reverting, so a probe that only caught reverts would
    report that WETH answers every function Curve has.
    """
    try:
        result = pool.call(to, data, block)
    except Reverted:
        return False
    return bool(result) and result != "0x"
