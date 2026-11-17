# Verified primary sources

Each reference below was checked against an original paper, RFC or standards document on 15 November 2026. The manuscript uses APA author-date citations. No references are derived solely from a generated bibliography.

- Böttger et al. (2019), *An empirical study of the cost of DNS-over-HTTPS*. DOI: https://doi.org/10.1145/3355369.3355575 . Author manuscript: https://arxiv.org/pdf/1909.06192 . Connection reuse and browser lookup/load distinction.
- Chhabra et al. (2021), *Measuring DNS-over-HTTPS performance around the world*. IMC, 351–365. DOI: https://doi.org/10.1145/3487552.3487849 . Author full text: https://kumarde.com/papers/imc_doh.pdf . Teacher's recommended paper; sections 3 and 5 distinguish cache-miss generation and connection state. Its default-resolver baseline differs from this same-provider design.
- Hoffman & McManus (2018), *DNS queries over HTTPS (DoH)*. RFC 8484. https://doi.org/10.17487/RFC8484 . Full text: https://www.rfc-editor.org/rfc/rfc8484.html . Wire-format POST, HTTP/2, cache interaction and privacy scope.
- Hounsel et al. (2020), *Comparing the effects of DNS, DoT, and DoH on web performance*. DOI: https://doi.org/10.1145/3366423.3380139 . Author manuscript: https://arxiv.org/pdf/1907.08089 . Separate DNS and browser-load methodology; historical findings are not this dataset.
- Hounsel et al. (2021), *Can encrypted DNS be fast?* PAM, 444–459. DOI: https://doi.org/10.1007/978-3-030-72582-2_26 . Author manuscript: https://kevin.borgolte.me/files/pdf/pam2021-can-encrypted-dns-be-fast.pdf . Connection setup and variation across networks; this paper does not measure page loads.
- Mockapetris (1987), *Domain names - implementation and specification*. RFC 1035. https://doi.org/10.17487/RFC1035 . Full text: https://www.rfc-editor.org/rfc/rfc1035.html . DNS messages, TTL and UDP.
- Thomson & Benfield (Eds.) (2022), *HTTP/2*. RFC 9113. https://doi.org/10.17487/RFC9113 . Full text: https://www.rfc-editor.org/rfc/rfc9113.html . Concurrent streams and shared connections.
- Weiss & Rosenthal (Eds.) (2026, November 2), *Navigation Timing Level 2* [W3C Working Draft]. https://www.w3.org/TR/2026/WD-navigation-timing-2-20261102/ . Navigation load-event metric. This is a working draft, not a W3C Recommendation.

Implementation documentation checked:

- Cloudflare binary DoH: https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/dns-wireformat/
- Google RFC 8484 endpoint: https://developers.google.com/speed/public-dns/docs/doh
- Playwright routed fulfillment: https://playwright.dev/docs/api/class-route#route-fulfill

Supplied course files were used for deliverable requirements rather than as scientific sources. The 5 November 2026 handbook, pages 10–14 and 16, controls structure, citation flexibility, AI disclosure, reproducibility and submission. Generic template section quotas were not treated as mandatory because handbook page 11 expressly permits flexible structure and no section word quotas.
