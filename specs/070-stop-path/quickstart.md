# Quickstart — validating the stop path

    make web-install
    cd apps/web && npx vitest run src/__tests__/stopPath.test.ts

Expected: passes.

To see the central rule is load-bearing, add the input it exists without:

```ts
export function stopPath({ position, proposals, bars, ... }) {
  // ...and derive the trail from `bars` instead of `proposals`
}
```

The two-futures test fails: the same position drawn against two different
subsequent price series stops producing the same path. That test is the only one
in the file that no recomputing implementation can pass, and it is why it is
written as a comparison rather than against a fixed expected path.

To see holds are not gaps, filter the path to `moved` proposals only; the
run-of-holds test fails, naming the reasons that vanished.
