# Analysis decisions recorded before full collection

15 November 2026. This is a task-local protocol record, not an external preregistration.

Compare providers separately. Direct UDP DNS is the baseline. Lookup DoH uses either a fresh TCP/TLS/HTTP2 session per query or a verified established session. Page fixtures use one new shared session per navigation or an established shared session. Never combine these different fresh-connection definitions.

Primary lookup metric: elapsed monotonic milliseconds until complete validated response. Primary browser metric: Navigation Timing loadEventEnd minus startTime. Failed attempts are retained and reported separately. Do not assign the timeout threshold as a successful latency.

Summarize successful observations using sample count, median, p95 and interquartile range. Estimate paired within-block differences from UDP for both DoH modes. Report medians of paired differences separately from differences of marginal medians. Bootstrap paired blocks with a fixed seed for a descriptive 95% interval. Few short windows do not support population inference; also report each window and domain sensitivity. Do not report hypothesis-test p-values as proof of a universal transport effect.

The browser fixture has one HTML document and seven fixed SVG resources. All responses are local bytes delivered by Playwright routing after live DNS succeeds. DNS A records are checked but returned IP addresses are intentionally not used. One or eight hostnames create different DNS dependency structures. This experiment measures DNS gating of controlled browser loads. It cannot establish native browser secure-DNS performance, CDN effects or real website load times.

Direct wire queries bypass the local OS stub cache. Public recursive cache entries cannot be cleared or proved hot. Prewarming is an attempt, TTL is diagnostic, and remote cache state stays unknown. Pin the same provider IP while retaining certificate validation and hostname SNI for DoH. Provider identity does not guarantee the same internal cache, anycast site or network path.

Hardware/platform information provides reproducibility context only. No CPU utilization, energy, cache-miss or hardware-counter measurements are available.

## Extension on 19 November 2026

The original 15 November inputs remain unchanged. A second collection date repeats ten lookup names, two providers, three connection treatments, ten repetitions and three windows with collection seed 20261119. One page window follows each direct-DNS window, avoiding simultaneous measurement traffic. DNS window scheduling targets five minutes between starts; actual execution times are retained. The dates are analyzed separately and never silently pooled.

The update adds domain-cluster resampling and sign fractions as secondary sensitivity checks. Primary paired point estimates and within-window bootstrap intervals for the original session remain unchanged. All valid values remain included. A different resampling unit is not claimed to solve unobserved time dependence or systematic cache/routing differences.

Recorded software versions differ across sessions. The second date therefore extends conditional replication rather than isolating the effect of calendar time. Collection snapshots, command logs and image capture metadata support an audit; none is an external preregistration or independent timestamp authority.
