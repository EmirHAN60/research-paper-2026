# Secure DNS performance research

**Author:** Emirhan TEKBAŞ (75831), Computer Engineering, Vistula University.

This package accompanies *Performance Overhead of Secure DNS: Evaluating Lookup Latency and Page Load Impact of DNS over HTTPS Versus Standard UDP DNS* for Architecture of Computers, 2026/2027.

The paper reports genuine measurements collected on 15 November 2026. It contains 1,800 measured direct lookups and 360 controlled browser navigations. Priming records are retained separately. Preparation smoke tests are excluded. This is a single-host, single-network study with three nearby windows, not a global or long-term benchmark.

## Before submission

The PDF contains the author's supplied identity and repository URL, https://github.com/EmirHAN60/research-paper-2026 . Upload the package contents to that repository and confirm reviewer access before submitting the PDF. The local package does not by itself establish that the remote repository contains the evidence. Inspect the final PDF before uploading it to Platon.

Read `SON_ADIMLAR_TR.md`, verify the sources and calculations independently, and retain an accurate AI-use declaration. The handbook permits AI assistance but makes the student responsible for understanding and defending the work.

## Files

- `Secure_DNS_Research_Paper.pdf`: formatted English paper with the author's identity and supplied evidence URL.
- `manuscript.md`: readable, editable manuscript with calculated results and tables.
- `paper_source.md`: manuscript template used by the builder. Numeric results are inserted from the recorded-data analysis.
- `profile.json`: author information and repository URL for the builder.
- `data/dns_raw.jsonl`: all direct-DNS attempts, including priming, query/response wire bytes, timings and transport metadata.
- `data/pages.jsonl`: navigation timings and validation for all controlled page attempts.
- `data/page-dns.jsonl`: nested DNS gates, prewarming and connection primers for the page fixture.
- `data/environment.json` and `data/page-environment.jsonl`: software, hardware and collection parameters, without local interface identifiers.
- `results/summary.json`: authoritative analysis, including validation, counts, bootstrap method and warnings.
- `results/*.csv`: marginal, paired, per-window, per-domain and leave-one-window-out results. The primary effect is the median paired difference.
- `experiment/dns_client.mjs`, `experiment/measure_dns.mjs`, `experiment/test_dns.mjs`: direct clients, collector and packet checks.
- `page-load.mjs`: complete HTML/image fixture generator and controlled browser collector.
- `analyze.py`: the sole authoritative statistical analysis used by the paper.
- `build_paper.py`: PDF and Markdown builder from `results/summary.json`.
- `PROTOCOL.md`, `REFERENCES.md`, `LIMITATIONS.md`: procedure, verified primary links and interpretation boundaries.
- `SHA256SUMS.txt`: integrity manifest for the distributed files.

## Dependencies

Collection used Node.js 24.22.1, OpenSSL 3.5.9, Playwright 1.62.1 and installed Google Chrome 157.0.8103.51 on Windows x64. Analysis/build used Python 3.12.14, NumPy 2.3.5 and ReportLab 4.4.9. Exact recorded machine details are in `data/environment.json`. The direct DNS client has no third-party dependencies.

For an ordinary local terminal, install a compatible recent Node.js and Python, then run:

```powershell
npm install
python -m pip install -r requirements.txt
node experiment/test_dns.mjs
```

Playwright uses the installed Google Chrome (`channel: 'chrome'`). This code never changes the operating system's DNS servers and does not require administrator rights. Internet collection requires outbound UDP port 53 and TCP port 443 to 1.1.1.1 and 8.8.8.8. An enterprise firewall or restricted sandbox may prevent collection. TLS certificate checks remain enabled.

## Recalculate the published results without network access

Run these commands from this package's directory:

```powershell
python analyze.py --dns data/dns_raw.jsonl --pages data/pages.jsonl --page-dns data/page-dns.jsonl --out results
python build_paper.py
```

The analysis checks saved DNS packets independently, verifies treatment/connection conditions, reports failure counts, and runs in-memory arithmetic checks. It uses 4,000 seeded, window-stratified paired bootstrap resamples. The saved point estimates and intervals should reproduce from the retained data. Output timestamps may differ. The PDF builder requires the complete 1,800/360 dataset and rejects audit warnings. Times New Roman is embedded from Windows fonts when available, with standard PDF Times as a fallback.

To personalize the final PDF, fill `repository_url` in `profile.json` with the actual evidence URL, then run `python build_paper.py`. The builder writes `Secure_DNS_Research_Paper.pdf` when author name, student ID and URL are all present. It does not upload or verify repository permissions. Independently test the link and inspect the PDF. The source file remains available if editorial changes are needed.

## Collect an independent replication

Use fresh output directories. Do not overwrite the distributed measurements. Start with the packet checks above. A full direct-lookup run takes approximately eleven minutes on a responsive network:

```powershell
node experiment/measure_dns.mjs --out replication/dns --windows 3 --reps 10 --interval-seconds 300 --seed 20261115
```

This produces three direct-DNS windows five minutes apart. All attempts and priming are retained; there are no retries. For a separate controlled browser replication, run:

```powershell
node page-load.mjs --window w1 --reps 10 --out replication/pages
node page-load.mjs --window w2 --reps 10 --out replication/pages
node page-load.mjs --window w3 --reps 10 --out replication/pages
```

Allow several minutes between page windows and avoid simultaneous lookup/page collection or heavy network traffic. In the distributed study, each page window ran after a direct-DNS window, with no overlap. The direct-DNS window spacing is fixed; page window spacing is documented by actual timestamps rather than assumed to be exactly five minutes. Reusing a page window ID in the same directory is rejected.

Analyze the new data in its own results directory:

```powershell
python analyze.py --dns replication/dns/dns_raw.jsonl --pages replication/pages/pages.jsonl --page-dns replication/pages/page-dns.jsonl --out replication/results
```

Network timings will differ. Do not replace only a few cells in the old manuscript with new results. Recalculate all tables, reassess claims and keep the datasets distinguishable.

## What the browser fixture measures

The fixture waits for a live DNS result before fulfilling each distinct hostname's browser requests with fixed local HTML/SVG bytes. One page has one hostname; the other has eight. There are seven images in both cases. Concurrent requests share an in-flight DNS promise per hostname. UDP is direct. DoH fresh opens one new session per page, while DoH established primes one session before navigation. All names in a page share that DoH session.

The DNS answer IP is recorded and validated but not used for content delivery. Chrome's native DNS, remote site TLS, Internet content transfer and site changes are bypassed. `plt_ms` is observed Navigation Timing load-event time for this fixture. It is neither a prediction of real-site load time nor a native-browser DoH benchmark. For fresh page loads, `gate_ms` includes explicit connection setup while the nested client's `elapsed_ms` begins after that explicit setup; do not confuse these fields. For fresh direct lookups, `elapsed_ms` includes lazy connection setup.

## Research integrity and privacy

Only recorded real attempts contribute to the reported results. Artificial arrays in the analysis self-check are used in memory solely to verify arithmetic and are never exported as research observations. Data includes public test domain names, public provider addresses and DNS answers, but not local interface addresses, usernames, credentials or browsing history. `profile.json` and the paper intentionally contain the student's supplied name and ID, which may be omitted from a public repository if a private reviewer-accessible copy supplies the course identity instead. Retain a correct link and identity in the assessed PDF.

This package was prepared with OpenAI Codex assistance. Automated verification does not constitute the student's independent verification. The declaration in the manuscript must remain accurate after the student's final review.
