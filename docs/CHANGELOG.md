# Revision on 19 November 2026

## Research and evidence

- Added a separately analyzed 19 November replication: 1,800 measured DNS lookups and 360 controlled browser navigations. Combined recorded sample: 3,600 lookups and 720 navigations.
- Preserved all five original input hashes and all original primary numerical estimates and intervals.
- Retained changes in the direction of Google's established-session contrast across windows on both dates. Dates are not silently pooled.
- Added whole-domain bootstrap sensitivity, paired sign fractions, and window/domain omission checks without trimming valid observations.
- Expanded the bibliography from eight to eighteen claim-linked sources, including later DoQ/HTTP3 and resolver resource studies, with a source audit and explicit validity boundaries.
- Added fifteen data-derived scientific charts, each exported as PNG, PDF and SVG.
- Added genuine browser screenshots of the fixed fixture and an offline report of captured verification output, with metadata and source logs.

## Structure changes

| Previous path | Current path |
|---|---|
| `analyze.py` | `scripts/analyze.py` |
| `build_paper.py` | `scripts/build_paper.py` |
| `page-load.mjs` | `scripts/page-load.mjs` |
| `experiment/dns_client.mjs` | `scripts/dns_client.mjs` |
| `experiment/measure_dns.mjs` | `scripts/measure_dns.mjs` |
| `experiment/test_dns.mjs` | `tests/test_dns.mjs` |
| `experiment/test_live.mjs` | `tests/test_live.mjs` |
| `paper_source.md` | `docs/paper_source.md` |
| `LIMITATIONS.md`, `PROTOCOL.md`, `REFERENCES.md` | Corresponding files under `docs/` |

The generated manuscript and submission PDF remain at the repository root. Original raw files remain in `data/`, while the repeat session is a separate subdirectory. The existing ignored personal submission guide is excluded from the public manifest and release archive.

## Reproduction and checks

`python scripts/reproduce.py` now runs the offline saved-data pipeline. Local tests cover paired aggregation, failed observations, missing comparisons, wire validation, treatment consistency, CLI paths and manifest tampering. The run recorded eighteen passing Python tests plus passing Node wire tests. It checks links, collection snapshots, protected inputs and generated figures, then writes the SHA-256 manifest after closing the log.

The README's redundant preparation footer was removed. The paper retains the course-required AI-use declaration. The repository was prepared locally; no commit or remote upload is performed by the research scripts.
