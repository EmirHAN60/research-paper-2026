# November 19 collection source snapshot

These three JavaScript files are byte-for-byte copies of the task-local files actually executed for the November 19 replication. They preserve the collection version independently of the maintained files in `scripts/`. `capture.json` records their hashes, timing, runtime versions and output dataset. The snapshot contains no screenshot feature.

The DNS collector ran three windows with ten repetitions, the original ten domains, two resolver providers and three transports. After each DNS window it launched the page collector for the same window. Each page window contains ten repetitions of two providers, two fixture layouts and three transports. DNS and page collection therefore did not overlap. Window targets were five minutes apart. The raw files preserve all attempts and their timestamps.

The actual authoring command used the task-local copies with Node.js 24.22.3 and the bundled Playwright 1.62.1. The same source snapshot can be run from the repository root after installing the pinned Node dependency and Google Chrome:

```text
node docs/evidence/collection-source-2026-11-19/measure_dns.mjs --windows 3 --interval-seconds 300 --reps 10 --seed 20261119 --out data/new-run --page-script docs/evidence/collection-source-2026-11-19/page-load.mjs
```

This command makes new network observations and refuses to overwrite an existing DNS dataset. It cannot recreate historical network conditions. The offline reproduction command in the main README uses the recorded data instead.

The maintained collectors have repository-relative default output paths and an optional evidence screenshot flag. Those maintenance changes were absent from this snapshot. The browser fixture content, queried names, resolver addresses and measurement logic were unchanged.
