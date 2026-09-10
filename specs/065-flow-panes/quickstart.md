# Quickstart — validating the lower panes

    make web-install
    make web-test

Expected: passes. The two worth reading are in `panes.test.ts`:

- "leaves a gap where a point carries no value for it";
- "draws a real zero".

Either alone is satisfiable by an implementation that gets the other wrong,
which is why they are a pair.

    make web-typecheck && make web-build
