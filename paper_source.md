# Performance Overhead of Secure DNS

## Evaluating Lookup Latency and Page Load Impact of DNS over HTTPS Versus Standard UDP DNS

{{IDENTITY}}

### Abstract

DNS over HTTPS (DoH) encrypts communication between a client and a recursive resolver, but the additional transport layers can change resolution time. This study asks how much of the observed latency difference remains when the resolver provider is held constant and an HTTPS connection is already established. A focused replication compares IPv4 A queries sent directly to Cloudflare and Google using UDP DNS, a fresh HTTP/2 connection, and an established HTTP/2 connection. The experiment records {{DNS_N}} lookup attempts across ten domain names in three short measurement windows. Direct wire queries bypass the operating system cache, while the recursive resolver cache remains observable only indirectly. Prewarming encourages cache reuse without establishing that a particular response is a cache hit. A separate controlled browser experiment records {{PAGE_N}} navigations to fixed pages containing seven image resources across either one or eight hostnames. Each response waits for a live DNS result before fixed local content is delivered. This fixture isolates a DNS dependency in page loading, while bypassing Chromium's native resolver and remote content transfer. {{ABSTRACT_RESULTS}} These observations support treating connection establishment and established-session queries as different performance conditions. They also show why a lookup difference cannot simply be multiplied by the number of page resources to estimate page load time. The findings are specific to one host, one network and a brief sampling period. They do not establish general website performance or processor overhead. Raw responses, measurement scripts and analysis procedures accompany the manuscript.

Keywords: DNS over HTTPS; DNS latency; connection reuse; page load time; reproducibility

## Introduction and related work

DNS resolution can delay a network request before a browser contacts a content server. Conventional DNS commonly carries messages over UDP port 53 (Mockapetris, 1987). DNS over HTTPS (DoH) carries a DNS exchange within HTTPS and protects the channel between the client and resolver (Hoffman & McManus, 2018). This adds connection management and cryptographic processing to the path. From a computer architecture perspective, the relevant distinction is between application latency and the work performed by the protocol stack. Elapsed time can include network waits as well as local processing, so it cannot by itself quantify processor cost.

The expected performance difference depends on the baseline. Chhabra et al. (2021) compared public DoH services with clients' default resolvers across a large international deployment. Their results establish the importance of network conditions and connection reuse, but that comparison also changes resolver infrastructure. Their controlled cache-miss workload used unique names under an authoritative zone they operated. Clearing a student's local cache cannot reproduce that condition. The present study adopts their separation of setup and established-session costs, while asking a narrower question about two services operated by the same provider.

Earlier research also cautions against equating resolution latency with browsing performance. Böttger et al. (2019) examined connection reuse and the cost of encrypted DNS. Hounsel et al. (2020) measured DNS queries and browser loads separately and found that higher query latency did not consistently translate into slower pages. Hounsel et al. (2021) further separated connection setup from query time and reported substantial variation across home networks. These studies motivate the controls here rather than supply expected numerical results.

The research question is: on the measured network, how do fresh and established HTTP/2 DoH sessions differ from UDP DNS within each provider, and how do those differences propagate through a fixed browser resource graph? The contribution is a small, reproducible comparison that keeps provider choice fixed, records connection state, and distinguishes direct lookup measurements from a controlled browser fixture. It is a focused replication and sensitivity test, rather than a claim of global coverage or a new DNS protocol.

## Methodology

### System and measurement conditions

Measurements were collected on 15 November 2026 using {{PLATFORM}} and Node.js {{NODE_VERSION}}. The host reported {{CPU_MODEL}}, {{LOGICAL_CPUS}} logical processors and {{MEMORY_GIB}} GiB of memory. The browser experiment used Google Chrome {{CHROME_VERSION}} through Playwright {{PLAYWRIGHT_VERSION}}. No CPU performance counters or energy measurements were collected. The network's access technology, ISP, physical location and background traffic were not characterized.

Cloudflare UDP queries targeted 1.1.1.1 and DoH queries used cloudflare-dns.com/dns-query pinned to that address. Google used 8.8.8.8 and dns.google/dns-query pinned to 8.8.8.8. Pinning removes endpoint hostname bootstrap from the comparison. TLS hostname verification remained enabled. Provider choice and destination IP were held constant within each comparison, although internal service routing and backend caches could still differ.

Queries requested an IPv4 A record with recursion desired, no EDNS extension and no DNSSEC request bit. UDP and DoH used equivalent DNS message semantics with independently generated transaction identifiers. DoH used binary POST with the application/dns-message media type, following RFC 8484. Negotiated HTTP/2 and TLS details were saved. HTTP/2 permits concurrent streams on a shared connection (Thomson & Benfield, 2022).

### Lookup procedure and cache control

The lookup workload comprised example.com, wikipedia.org, mozilla.org, github.com, cloudflare.com, google.com, microsoft.com, apple.com, bbc.com and amazon.com. Each name was measured ten times per provider in each of three windows. The windows began five minutes apart and sampled short-term variation within one session, rather than different times of day. Each provider-domain-repetition block contained UDP, fresh DoH and established DoH in a seeded randomized order. Domains and providers were also shuffled within repetitions. There were no retries and a three-second timeout applied to each connection or query stage.

The UDP timer began before socket creation and stopped after a complete response was validated. The DoH timer began after query encoding, before connection establishment when necessary, and stopped after response validation. Fresh DoH created a new client and TCP/TLS session for every lookup. Established DoH reused the session primed for that provider and window. Fresh-session TLS resumption was checked in the recorded socket metadata. These application measurements include library and socket handling overhead and do not isolate encryption alone.

Direct DNS messages avoid operating system stub-resolver cache APIs, so flushing the system cache was unnecessary. Before measured blocks, each domain was queried through UDP and the persistent DoH client. This encouraged resolver reuse but did not clear or prove a hit in the remote recursive cache. Returned time-to-live values were retained as diagnostics, not cache-hit labels. This distinction follows the separate DNS and HTTP cache behavior described by Hoffman and McManus (2018).

Responses were checked for matching transaction identifier and question, response flag, opcode, truncation, response code and a valid A answer. DoH additionally required HTTP 200 and the DNS media type. Raw query and response bytes were saved. Truncation was treated as failure without TCP fallback. Tests covered valid responses, malformed packets, mismatches and compression loops.

### Controlled browser loads

Each page contained one HTML document and seven fixed SVG images. The one-hostname fixture resolved the main hostname once. The eight-hostname fixture resolved the main hostname before parsing and seven other hostnames as image requests became available. An in-flight promise was memoized per hostname to prevent duplicate queries. The returned addresses were validated and recorded but deliberately not contacted. Playwright fulfilled requests with fixed local bytes after live DNS succeeded. Consequently, this measures a DNS-gated browser fixture, not Chromium's native secure DNS or remote website transfers.

Every navigation used a new browser context with service workers blocked. The browser process remained open. UDP used direct queries. Fresh DoH opened one session inside the main-document gate and shared it across the page's names. Established DoH opened and primed a session before navigation, using an unrelated hostname. Thus fresh page loads pay setup once per page, unlike fresh lookup trials, which pay it once per query. The fixture hostname set was prewarmed through UDP for each provider before the window. Remote cache status remained unknown.

Ten matched navigation triplets were measured for each provider and hostname layout in each window, with randomized block and protocol order. Page load time was loadEventEnd minus startTime from Navigation Timing, read after loadEventEnd became nonzero (Weiss & Rosenthal, 2026). A successful page also required all seven images and the expected number of distinct lookups. DNS failures invalidated the page independently of the load event.

### Analysis

Successful latency distributions are summarized by medians and nearest-rank 95th percentiles. Failures remain in attempt counts and are excluded from successful-latency summaries. The primary contrast is the median of paired DoH-minus-UDP differences within matched blocks. It is distinct from subtracting marginal medians. Descriptive 95% percentile intervals use 4,000 paired bootstrap resamples stratified by window with a fixed seed. They are conditional on the sampled windows and workload, not population confidence guarantees. Per-window effects and leave-one-window-out sensitivity accompany the pooled estimates. Repeated domains and the small number of windows limit independence.

## Results

### Data completeness and connection checks

{{COMPLETENESS}}

### Lookup latency

{{LOOKUP_RESULTS}}

{{LOOKUP_TABLE}}

{{LOOKUP_FIGURE}}

{{LOOKUP_PAIRED}}

### Controlled page load time

{{PAGE_RESULTS}}

{{PAGE_TABLE}}

{{PAGE_PAIRED}}

## Discussion and limitations

{{DISCUSSION_RESULTS}}

The page results should be interpreted through the fixture's dependency graph. The document's DNS lookup precedes the image requests. In the eight-hostname layout, subsequent lookups can overlap, and HTTP/2 shares a connection. The number of resources therefore does not determine a serial DNS cost. Conversely, the one-hostname fixture performs a single DNS lookup despite loading seven images. This directly explains why summing per-query delays would describe a different workload.

The fixture intentionally removes remote server response time, content transfer and content-server TLS setup. It also bypasses browser DNS prefetching, native caching, address racing, connection coalescing and secure-DNS fallback. Its load-event metric captures completion of the fixed document and images, rather than visual completeness or user interactivity. A real-site follow-up should configure and verify native browser resolution, retain network traces, and compare multiple websites without changing the resolver provider. The present measurements support a controlled mechanism study only.

Cache state remains a major uncertainty. The prewarming procedure may produce different effects across provider front ends, and entries can expire between trials. Positive answers and time-to-live values cannot prove that UDP and DoH reached the same cache. Randomization reduces systematic order bias but does not remove this uncertainty. Similarly, using the same provider and IP reduces infrastructure variation without establishing identical anycast routing or resolver processes. Any residual difference is an observed service-and-client contrast, rather than a pure causal estimate of cryptographic overhead.

The study covers one host and network, IPv4 A records, HTTP/2, and three nearby windows. It does not cover IPv6 transport, HTTP/3, loss injection, congested access links or another day. Quantiles and bootstrap intervals describe the collected sample. The page tail estimate has only thirty observations per condition and is especially unstable. Repeated observations from the same domains and window may share network conditions. These limitations prevent generalizing the provider ordering or the magnitude of the difference to all users.

For an implementation decision, connection lifetime deserves explicit attention. A workload that opens an HTTPS connection for every query is different from a browser or service that amortizes setup. Reporting only one condition would conceal that distinction. The latency findings also leave the privacy decision separate: DoH protects the client-to-resolver channel but does not hide queries from the selected resolver (Hoffman & McManus, 2018). This experiment evaluates timing rather than the full security or energy tradeoff.

## Conclusion

{{CONCLUSION_RESULTS}} The reproducible contribution is the separation of provider choice, connection state, cache uncertainty and page dependency structure. The strongest next step is longer sampling on additional networks and native-browser website measurements. Processor overhead would require separate utilization or hardware-counter measurements.

## Declaration of Generative AI and AI-Assisted Technologies

OpenAI Codex assisted with experimental design, source discovery, programming, execution of measurements, statistical analysis and drafting/editing the manuscript. Automated checks included response validation, parser tests and recalculation from retained raw measurements. These checks do not substitute for the student's independent verification. The submitting author remains responsible for understanding, checking and defending the sources, code, calculations and conclusions.

## Data and code availability

{{EVIDENCE_LINK}}

The accompanying reproducibility package contains the raw DNS responses and browser navigation records, environment metadata, fixed fixture generator, scripts, dependency versions, analysis tables and limitations. All findings reported here were calculated from recorded attempts. Preparation smoke tests are excluded from the analyzed dataset.

## References

Böttger, T., Cuadrado, F., Antichi, G., Fernandes, E. L., Tyson, G., Castro, I., & Uhlig, S. (2019). An empirical study of the cost of DNS-over-HTTPS. In *Proceedings of the Internet Measurement Conference*. ACM. https://doi.org/10.1145/3355369.3355575

Chhabra, R., Murley, P., Kumar, D., Bailey, M., & Wang, G. (2021). Measuring DNS-over-HTTPS performance around the world. In *Proceedings of the 21st ACM Internet Measurement Conference* (pp. 351–365). ACM. https://doi.org/10.1145/3487552.3487849

Hoffman, P., & McManus, P. (2018). *DNS queries over HTTPS (DoH)* (RFC 8484). RFC Editor. https://doi.org/10.17487/RFC8484

Hounsel, A., Borgolte, K., Schmitt, P., Holland, J., & Feamster, N. (2020). Comparing the effects of DNS, DoT, and DoH on web performance. In *Proceedings of The Web Conference 2020*. ACM. https://doi.org/10.1145/3366423.3380139

Hounsel, A., Schmitt, P., Borgolte, K., & Feamster, N. (2021). Can encrypted DNS be fast? In *Passive and Active Measurement* (pp. 444–459). Springer. https://doi.org/10.1007/978-3-030-72582-2_26

Mockapetris, P. (1987). *Domain names implementation and specification* (RFC 1035). RFC Editor. https://doi.org/10.17487/RFC1035

Thomson, M., & Benfield, C. (Eds.). (2022). *HTTP/2* (RFC 9113). RFC Editor. https://doi.org/10.17487/RFC9113

Weiss, Y., & Rosenthal, N. (Eds.). (2026, November 2). *Navigation Timing Level 2* [Working draft]. World Wide Web Consortium. https://www.w3.org/TR/2026/WD-navigation-timing-2-20261102/
