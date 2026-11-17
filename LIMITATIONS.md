# Interpretation limits

1. One Windows host and one available network were sampled on a single date. Access medium, ISP, location, competing traffic and path changes were not characterized.
2. Three direct-DNS windows began five minutes apart. This is a short-term sample, not a morning/evening or multi-day study. Page timestamps describe their separate windows.
3. Public recursive cache state is unknown. Direct queries bypass the OS stub cache; prewarming encourages reuse without proving hits. TTL values are diagnostic only. The study does not claim verified recursive cache misses.
4. Holding provider and pinned destination IP constant reduces, but cannot eliminate, backend, anycast, routing and cache differences between UDP and HTTPS services.
5. The direct DNS workload uses ten fixed names, IPv4 transport and A questions without EDNS. No TCP fallback, HTTP/3, IPv6, induced packet loss or congestion treatment is included.
6. Application latency includes library, socket and validation work as well as network waiting. Fresh TCP/TLS setup is included in direct fresh-DoH queries, without resumed TLS. No CPU counters, energy or microarchitectural effects were measured.
7. The browser experiment is a fixed DNS-gated fixture. Returned A addresses are not contacted. Browser native resolver behavior, content-server TLS, real content transfer, CDN selection and website changes are not measured.
8. One fresh DoH session is shared within each fresh page, whereas direct fresh lookups open a connection per query. These are deliberately different units and cannot be compared as identical workloads.
9. Load-event timing is neither visual completeness nor user interactivity. The fixed document and seven images define the stopping condition.
10. Bootstrap intervals condition on the observed windows and successful pairs. Correlated repeated domains and only three windows prevent strong population claims. A pooled established-session result can hide changes of sign across windows. Thirty page loads per condition give an unstable tail percentile.
11. Failures remain in raw data and attempt counts. Successful-latency summaries are conditional on success. No failed attempt is imputed as a successful timeout-duration observation.
