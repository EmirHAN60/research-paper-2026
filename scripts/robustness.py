"""Secondary, date-specific sensitivity checks on recorded paired observations.

The primary estimates and within-window intervals in summary.json are read, never
overwritten. Domain-cluster resampling is an alternative conditional sensitivity
analysis, not evidence of population coverage with only ten selected domains.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import numpy as np


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def window_id(value) -> int:
    return int(re.search(r"\d+", str(value)).group())


def datasets(root: Path) -> list[dict]:
    """Include only complete, separately analyzed datasets; never pool dates."""
    found = []
    candidates = [("original", root / "data", root / "results")]
    for data in sorted((root / "data").glob("replication-*")):
        if data.is_dir():
            candidates.append((data.name, data, root / "results" / data.name))
    for label, data, results in candidates:
        summary_path = results / "summary.json"
        if not summary_path.exists() or not (data / "dns_raw.jsonl").exists():
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
        if summary.get("warnings"):
            raise ValueError(f"Resolve authoritative analysis warnings before secondary analysis: {summary_path}")
        dns = read_jsonl(data / "dns_raw.jsonl")
        pages = read_jsonl(data / "pages.jsonl") if (data / "pages.jsonl").exists() else []
        stamps = [r["started_utc"] for r in dns if r.get("phase") == "measure" and r.get("started_utc")]
        date = min(stamps)[:10] if stamps else label
        found.append({"label": label, "date": date, "data": data, "results": results,
                      "summary": summary, "dns": dns, "pages": pages})
    return found


def paired_rows(dataset: dict, experiment: str, provider: str, comparison: str, origins=None) -> list[dict]:
    blocks = defaultdict(dict)
    rows = dataset["dns"] if experiment == "lookup" else dataset["pages"]
    for row in rows:
        if row.get("provider") != provider:
            continue
        if experiment == "lookup":
            if row.get("phase") != "measure":
                continue
            key = (window_id(row["window"]), row["domain"], row["rep"])
            mode = row["protocol"]
        else:
            if row.get("origins") != origins:
                continue
            key = (window_id(row["window"]), row["origins"], row["rep"])
            mode = row["mode"]
        if mode in blocks[key]:
            raise ValueError(f"Duplicate paired record {dataset['label']} {provider} {key} {mode}")
        blocks[key][mode] = row
    out = []
    for key, modes in sorted(blocks.items()):
        baseline, treatment = modes.get("udp"), modes.get(comparison)
        if baseline is None or treatment is None:
            continue
        if experiment == "lookup":
            valid = baseline.get("valid") is True and treatment.get("valid") is True
            field = "elapsed_ms"
        else:
            valid = baseline.get("status") == "ok" and treatment.get("status") == "ok"
            field = "plt_ms"
        if not valid:
            continue
        b, t = float(baseline[field]), float(treatment[field])
        if not np.isfinite(b) or not np.isfinite(t) or b <= 0 or t < 0:
            raise ValueError("Invalid latency in successful paired record")
        out.append({"window": key[0], "domain": baseline.get("domain", ""),
                    "rep": baseline["rep"], "baseline_ms": b, "comparison_ms": t,
                    "delta_ms": t - b, "delta_pct": 100 * (t - b) / b})
    return out


def seeded(seed: int, label: str):
    return np.random.default_rng(seed ^ int.from_bytes(hashlib.sha256(label.encode()).digest()[:8], "big"))


def cluster_interval(pairs: list[dict], field: str, resamples: int, seed: int, label: str) -> tuple:
    grouped = defaultdict(list)
    for pair in pairs:
        grouped[pair["domain"]].append(pair[field])
    domains = sorted(grouped)
    if len(domains) < 2:
        return None, None
    rng = seeded(seed, label)
    estimates = np.empty(resamples)
    for i in range(resamples):
        sampled = rng.integers(0, len(domains), size=len(domains))
        values = np.concatenate([grouped[domains[j]] for j in sampled])
        estimates[i] = np.median(values)
    return tuple(float(x) for x in np.quantile(estimates, [.025, .975]))


def median(values):
    values = list(values)
    return float(np.median(values)) if values else None


def calculate(dataset: dict, resamples: int) -> dict:
    summary = dataset["summary"]
    seed = int(summary.get("seed", 20261115))
    checks = []
    rows, windows, domains, leave_window, leave_domain = [], [], [], [], []
    for experiment in ("lookup", "page"):
        for primary in summary.get(experiment + "_paired", []):
            provider, comparison = primary["provider"], primary["comparison"]
            origins = int(primary["origins"]) if experiment == "page" else None
            pairs = paired_rows(dataset, experiment, provider, comparison, origins)
            if not pairs:
                continue
            label = f"{dataset['date']}:{experiment}:{provider}:{origins}:{comparison}"
            deltas = np.asarray([p["delta_ms"] for p in pairs])
            pct = np.asarray([p["delta_pct"] for p in pairs])
            med = float(np.median(deltas))
            if not np.isclose(med, primary["median_delta_ms"], atol=1e-7, rtol=0):
                raise ValueError(f"Raw paired median disagrees with primary summary: {label}")
            if not np.isclose(float(np.median(pct)), primary["median_paired_pct_delta"], atol=1e-7, rtol=0):
                raise ValueError(f"Raw paired percentage disagrees with primary summary: {label}")
            if len(pairs) != primary["complete_pairs"]:
                raise ValueError(f"Raw pair count disagrees with primary summary: {label}")
            checks.append(label)
            row = {"dataset": dataset["label"], "date": dataset["date"], "experiment": experiment,
                   "provider": provider, "origins": origins if origins else "", "comparison": comparison,
                   "complete_pairs": len(pairs), "median_delta_ms": med,
                   "median_paired_pct_delta": float(np.median(pct)),
                   "primary_ci95_low_ms": primary["ci95_low_ms"],
                   "primary_ci95_high_ms": primary["ci95_high_ms"],
                   "positive_count": int(np.count_nonzero(deltas > 0)),
                   "negative_count": int(np.count_nonzero(deltas < 0)),
                   "zero_count": int(np.count_nonzero(deltas == 0)),
                   "positive_fraction": float(np.mean(deltas > 0)),
                   "negative_fraction": float(np.mean(deltas < 0)),
                   "domain_cluster_count": len(set(p["domain"] for p in pairs)) if experiment == "lookup" else None,
                   "domain_cluster_ci95_low_ms": None, "domain_cluster_ci95_high_ms": None,
                   "domain_cluster_ci95_low_pct": None, "domain_cluster_ci95_high_pct": None}
            if experiment == "lookup":
                low, high = cluster_interval(pairs, "delta_ms", resamples, seed, label + ":ms")
                low_pct, high_pct = cluster_interval(pairs, "delta_pct", resamples, seed, label + ":pct")
                row.update(domain_cluster_ci95_low_ms=low, domain_cluster_ci95_high_ms=high,
                           domain_cluster_ci95_low_pct=low_pct, domain_cluster_ci95_high_pct=high_pct)
            meta = {k: row[k] for k in ("dataset", "date", "experiment", "provider", "origins", "comparison")}
            for window in sorted(set(p["window"] for p in pairs)):
                selected = [p for p in pairs if p["window"] == window]
                windows.append({**meta, "window": window, "pairs": len(selected),
                                "median_delta_ms": median(p["delta_ms"] for p in selected),
                                "median_paired_pct_delta": median(p["delta_pct"] for p in selected),
                                "positive_fraction": float(np.mean([p["delta_ms"] > 0 for p in selected]))})
                remaining = [p for p in pairs if p["window"] != window]
                leave_window.append({**meta, "omitted_window": window, "pairs": len(remaining),
                                     "median_delta_ms": median(p["delta_ms"] for p in remaining)})
            if experiment == "lookup":
                for domain in sorted(set(p["domain"] for p in pairs)):
                    selected = [p for p in pairs if p["domain"] == domain]
                    domains.append({**meta, "domain": domain, "pairs": len(selected),
                                    "median_delta_ms": median(p["delta_ms"] for p in selected),
                                    "median_paired_pct_delta": median(p["delta_pct"] for p in selected)})
                    remaining = [p for p in pairs if p["domain"] != domain]
                    leave_domain.append({**meta, "omitted_domain": domain, "pairs": len(remaining),
                                         "median_delta_ms": median(p["delta_ms"] for p in remaining)})
            ws = [w["median_delta_ms"] for w in windows if all(w[k] == meta[k] for k in meta)]
            row["window_median_min_ms"], row["window_median_max_ms"] = min(ws), max(ws)
            row["window_sign_reversal"] = min(ws) < 0 < max(ws)
            rows.append(row)
    return {"generated_utc": datetime.now(timezone.utc).isoformat(), "dataset": dataset["label"],
            "date": dataset["date"], "seed": seed, "resamples": resamples,
            "method": {
                "primary": "The original summary.json point estimates and within-window paired-block intervals are retained unchanged.",
                "domain_cluster": "For each lookup provider/contrast, sample ten observed domain labels with replacement. Each selected cluster retains all its measured repetitions and windows. Compute the pooled median paired difference. Report percentile 2.5/97.5 limits. Percentage intervals resample domain clusters separately with a distinct deterministic seed.",
                "scope": "Secondary conditional sensitivity only. Ten selected domains are few clusters and not a random domain population. Serial/time effects and unobserved cache differences remain. This alternative interval is not inherently more valid than the primary interval.",
                "pages": "No domain-cluster interval is computed for pages because the fixed hostname graph is a shared fixture, not independent domain-set replication.",
                "sign": "Fractions of complete successful matched blocks with positive, negative or exactly zero DoH-minus-UDP difference; descriptive only, not a sign test.",
                "outliers": "All valid observed values retained; no trimming, winsorization or imputation.",
                "dates": "Each date analyzed independently. No pooled-date effect estimate."},
            "alignment_checks": len(checks), "comparisons": rows, "windows": windows,
            "domains": domains, "leave_one_window_out": leave_window,
            "leave_one_domain_out": leave_domain}


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--resamples", type=int, default=4000)
    args = parser.parse_args()
    if args.resamples < 100:
        parser.error("Use at least 100 resamples")
    found = datasets(args.root.resolve())
    if not found:
        raise SystemExit("No analyzed datasets found")
    for dataset in found:
        result = calculate(dataset, args.resamples)
        out = dataset["results"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "robustness.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        write_csv(out / "robustness.csv", result["comparisons"])
        write_csv(out / "robustness_signs_by_window.csv", result["windows"])
        write_csv(out / "robustness_leave_domain_out.csv", result["leave_one_domain_out"])
        print(json.dumps({"dataset": dataset["label"], "date": dataset["date"],
                          "contrasts": len(result["comparisons"]), "output": str(out / "robustness.json")}))


if __name__ == "__main__":
    main()
