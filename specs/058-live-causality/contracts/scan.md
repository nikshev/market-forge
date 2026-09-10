# Contract — the scan

```
forbidden_in(source: str) -> tuple[str, ...]
```

Every forbidden helper named anywhere in `source`, in the order `FORBIDDEN_IMPORTS`
lists them. Empty when there are none.

A substring match, deliberately, for [[ADR-022]]'s reason: the check is a
tripwire and not a parser, and an import-only check would miss every other way
of reaching the same function.

```
EXEMPT: Mapping[str, str]
```

Module path → reason. The scan skips exactly these modules and no others.

## What the suite does with them

Walks every `*.py` under `src/channelflow/`, calls `forbidden_in` on each, and
fails naming the module and the helper. It fails rather than passes when the
walk finds no modules, and fails when `EXEMPT` names a module that is not there.

## Does not

- Parse imports, resolve names, or follow call graphs.
- Say anything about a transform that lies about being causal. That is Test A's,
  and `causality.py` already records it.
