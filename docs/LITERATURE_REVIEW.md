# Secure DNS performance and experimental interpretation

Secure DNS performance depends on the connection, resolver infrastructure and application workload around a query. A comparison can measure the cost of changing transport, changing resolver operator, establishing a connection or loading a page. Those choices produce different estimates. The literature therefore provides a framework for interpreting a controlled replication, rather than one expected overhead value. This review connects the project's lookup and browser measurements to prior empirical work, identifies residual confounding and explains the limits of an HTTP/2 comparison. It does not treat published findings as observations from this project.

## Lookup outcomes and connection state

The conventional DNS specification defines a compact message format, UDP transport and record caching (Mockapetris, 1987). DoH carries DNS messages through HTTPS and introduces HTTP connection and cache behavior (Hoffman & McManus, 2018). The protocol label alone consequently leaves an important experimental condition unspecified: whether connection establishment occurs inside the timed operation.

Böttger et al. (2019) compared persistent and nonpersistent DoH and examined the relationship between DNS costs and browser loading. Their work motivates separating setup from repeated exchanges. Hounsel et al. (2021) made that distinction explicit in home-network measurements, reporting connection establishment separately from query response time. They also found variation across resolver and client conditions. A useful comparison must identify which stages its timer includes and which connection behavior the implementation actually exhibits.

Chhabra et al. (2021) extend this perspective to a worldwide comparison. Their conventional-DNS baseline follows each client's default resolver, whereas their encrypted queries use public DoH services. Their design answers a deployment question involving both transport and resolver choice. Its authoritative-zone method also creates query-level cache misses. A same-provider experiment with publicly hosted names addresses a narrower question and cannot claim either that global coverage or that cache control.

These studies already establish the importance of reuse. The present replication's value lies in making its treatment boundaries inspectable: new connections and established connections must be supported by recorded transport state. A high-level client object being reused is insufficient evidence by itself. Query timing must also be distinguished from TLS session resumption, which can alter a newly opened connection without making it an already established one.

## Recursive caches and anycast infrastructure

Local and recursive caches occupy different places in DNS resolution. Direct wire-format queries bypass the operating system's resolver interface, but the selected public service can still answer from its own cache. RFC 8484 additionally describes interactions between HTTP caching and DNS TTLs (Hoffman & McManus, 2018). Local cache flushing therefore does not establish a cold recursive lookup.

Moura et al. (2019) examine how effective cache lifetimes depend on TTL settings and resolver behavior across the distributed DNS infrastructure. Their findings support treating recorded TTLs as contextual evidence. Prewarming encourages cached responses, but does not verify the state encountered by every subsequent query. A claimed cache-miss treatment needs stronger evidence, such as an authoritative zone controlled by the experimenter.

Provider matching is useful for reducing differences between operators, but a service address does not identify one physical server. De Oliveira Schmidt et al. (2017) describe how anycast addresses represent multiple sites and how routing policies affect client-to-site mapping and latency. This supports a residual-infrastructure caveat even when the provider IP is pinned. It does not establish that a route or site changed during this project. Without cache-hit indicators, site identifiers or path observations, changes between collection windows should remain observations whose cause is unresolved.

## Browser loading and dependency structure

Lookup response time and page-load time are separate outcomes. Hounsel et al. (2020) measured both and found that their rankings need not coincide under different network conditions. Böttger et al. (2019) likewise distinguish cumulative DNS work from page loading, where queries can overlap. Adding individual lookup delays as though every query runs sequentially can misrepresent an application's critical path.

A controlled browser fixture can make that dependency structure explicit. Fixed resource bodies reduce variation in content generation and transfer, while hostname placement changes where DNS waiting enters the resource graph. However, request interception also removes important behavior from the experiment. If returned addresses are never contacted, the fixture cannot estimate origin TLS, CDN selection or remote content-transport effects. It demonstrates how live DNS gates affect the chosen graph, rather than native browser secure-DNS performance on arbitrary websites.

The browser metric also needs a precise endpoint. Navigation Timing Level 2 defines the navigation entry and its completed load-event timing (Weiss & Rosenthal, 2026). This provides a reproducible event-based measure. It does not represent visual completeness, responsiveness or the completion of all content that a page may request later. Calling the outcome a load-event time preserves that distinction.

## Architecture and newer encrypted transports

Elapsed lookup time combines waiting with software work. It does not identify how many processor cycles encryption consumed. Le Louët et al. (2024) investigate resolver connection behavior and conduct controlled resource benchmarks that distinguish establishment, upkeep and message processing. Their measurements provide an architectural explanation for possible costs while showing why CPU and memory outcomes require their own instrumentation. Client-side latency cannot substitute for those measurements or establish energy consumption.

HTTP/2 provides concurrent streams and connection management over TCP (Thomson & Benfield, 2022). QUIC-based protocols change that transport structure. Dedicated DoQ maps DNS directly onto QUIC, while HTTP/3 maps HTTP onto QUIC (Huitema et al., 2022; Bishop, 2022). DoH over HTTP/3 and dedicated DoQ therefore remain distinct cases, even though both use QUIC.

Kosek et al. (2022) separate handshake and resolution time when comparing DoQ with other DNS transports, explicitly examining resumption behavior. Sengupta et al. (2024) study how DNS and HTTP/3 content delivery interact through connection coalescing. Bielefeld et al. (2026) add a current comparison of DoQ/DoH3 resolver features and browser loading. Together, these studies show why protocol version and connection policy must accompany a performance claim. They do not provide a numerical adjustment that converts this project's HTTP/2 results into predictions for newer transports.

| Study emphasis | Relevant condition | Interpretation for this project |
| --- | --- | --- |
| Chhabra et al. (2021) | Default-resolver baseline and controlled authoritative names | Resolver choice and cache treatment differ from a fixed-provider workload |
| Hounsel et al. (2020, 2021) | Browser outcomes and separately identified setup costs | Keep lookup, connection and application outcomes distinct |
| Le Louët et al. (2024) | Resolver processing and connection-resource costs | Architectural resource costs require measurements beyond elapsed latency |
| Sengupta et al. (2024); Bielefeld et al. (2026) | QUIC, content transport and implementation features | HTTP/2-only conclusions have explicit transport boundaries |

## Dependence, temporal scope and reproducibility

Repeated queries to the same names and observations collected close together can share conditions. Field and Welsh (2007) explain that clustered-bootstrap validity depends on the dependence structure and sampling model. This motivates preserving matched observations and examining aggregation sensitivity. It does not certify a particular median-difference estimator or turn a few collection windows into a representative sample of Internet users and networks.

Bajpai et al. (2019) recommend documenting operational measurement conditions, retaining raw data, validating tools and recording the timing and location of observations. Their guide is an expert editorial, explicitly identified as not peer reviewed. Its practical relevance is the ability to inspect the chain from stored attempts to reported statistics. Executable analysis can reproduce calculations from a saved dataset, while a later live collection may legitimately observe different network and service conditions.

The project is consequently best positioned as an introductory replication with transparent controls. Its contribution is the inspectability of treatment state, paired comparisons, temporal sensitivity and a deliberately limited browser demonstration. Existing research supplies the methods and broader context. The resulting evidence can support conditional conclusions about the observed workload, while leaving universal provider rankings, pure encryption cost and general website performance outside its scope.

Full bibliographic entries appear in [References](REFERENCES.md). Claim locations and source-specific limitations appear in [Source audit](SOURCE_AUDIT.md).
