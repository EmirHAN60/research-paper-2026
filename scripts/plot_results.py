"""Create scientific figures from the retained observations and frozen analysis.

Run after analyze.py and robustness.py. PNG (220 dpi), vector PDF and SVG files
are written for each date separately; no cross-date pooling is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from robustness import datasets, paired_rows


MODE_COLORS = {"udp": "#286D8B", "doh_fresh": "#BD602B", "doh_warm": "#36846B", "doh_reused": "#36846B"}
PROVIDER_COLORS = {"cloudflare": "#286D8B", "google": "#A34E81"}
MODE_NAMES = {"udp": "UDP", "doh_fresh": "DoH fresh", "doh_warm": "DoH established", "doh_reused": "DoH established"}
PROVIDER_NAMES = {"cloudflare": "Cloudflare", "google": "Google"}
PROVIDERS = ("cloudflare", "google")
CONTRASTS = ("doh_fresh", "doh_warm")


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10.2, "axes.titlesize": 11,
        "axes.labelsize": 10.2, "xtick.labelsize": 10, "ytick.labelsize": 10,
        "legend.fontsize": 10, "figure.titlesize": 12, "axes.spines.top": False,
        "axes.spines.right": False, "axes.edgecolor": "#6A737C", "axes.linewidth": .65,
        "grid.color": "#DFE4E8", "grid.linewidth": .6, "pdf.fonttype": 42,
        "ps.fonttype": 42, "svg.fonttype": "none", "savefig.facecolor": "white",
        "axes.unicode_minus": True,
    })


def tidy(ax, axis="y"):
    ax.grid(True, axis=axis, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=3, width=.6)


def save(fig, directory: Path, stem: str, caption: str, dataset: dict, manifest: list[dict]):
    directory.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf", "svg"):
        fig.savefig(directory / f"{stem}.{extension}", dpi=220,
                    metadata={"Creator": "Measured-data figure generator"} if extension == "pdf" else None)
    manifest.append({"stem": stem, "date": dataset["date"], "dataset": dataset["label"],
                     "files": [f"{stem}.{e}" for e in ("png", "pdf", "svg")],
                     "caption": caption, "source": "Retained JSONL observations and authoritative summary.json; no generated observations.",
                     "width_inches": float(fig.get_figwidth()), "height_inches": float(fig.get_figheight()),
                     "png_dpi": 220})
    plt.close(fig)


def lookup_ecdf(ds, out, manifest):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.5), layout="constrained")
    for ax, provider in zip(axes, PROVIDERS):
        for mode in ("udp", "doh_fresh", "doh_warm"):
            values = sorted(float(r["elapsed_ms"]) for r in ds["dns"]
                            if r.get("phase") == "measure" and r.get("provider") == provider
                            and r.get("protocol") == mode and r.get("valid") is True)
            if values:
                ax.step(values, np.arange(1, len(values) + 1) / len(values), where="post",
                        color=MODE_COLORS[mode], linewidth=1.55,
                        linestyle={"udp":"-", "doh_fresh":"--", "doh_warm":"-."}[mode],
                        label=MODE_NAMES[mode])
        ax.set(title=PROVIDER_NAMES[provider], xlabel="Lookup latency (ms)", ylim=(0, 1.02), xlim=(0, None))
        ax.set_yticks([0, .25, .5, .75, 1])
        tidy(ax)
    axes[0].set_ylabel("Fraction of successful queries")
    axes[1].legend(loc="lower right", frameon=False, handlelength=1.6, labelspacing=.5)
    fig.suptitle(f"Direct lookup latency · {ds['date']}")
    save(fig, out, "lookup_ecdf",
         f"Empirical cumulative distributions of successful direct lookup latency on {ds['date']}. Each provider/mode has 300 observations in the distributed complete dataset. Fresh DoH creates a new connection per query; established DoH reuses one connection per provider/window. Every successful observation is shown; tails are not trimmed.", ds, manifest)


def paired_distributions(ds, out, manifest):
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 4.8), layout="constrained")
    for row, provider in enumerate(PROVIDERS):
        for col, mode in enumerate(CONTRASTS):
            ax = axes[row, col]
            values = np.asarray([p["delta_ms"] for p in paired_rows(ds, "lookup", provider, mode)])
            jitter = np.random.default_rng(771 + row * 10 + col).uniform(-.105, .105, len(values))
            ax.scatter(values, jitter, s=8, color=MODE_COLORS[mode], alpha=.32, edgecolors="none", zorder=2)
            box = ax.boxplot([values], vert=False, positions=[0], widths=.24, whis=(0, 100),
                            showfliers=False, patch_artist=True,
                            boxprops={"facecolor": "white", "edgecolor": "#333333", "alpha": .65},
                            medianprops={"color": "black", "linewidth": 1.5},
                            whiskerprops={"color": "#555555"}, capprops={"color": "#555555"})
            ax.axvline(0, color="#555555", linewidth=.8, linestyle="--", zorder=1)
            ax.set(yticks=[], ylim=(-.25, .25), xlabel="Paired difference (ms)",
                   title=f"{PROVIDER_NAMES[provider]} · {'fresh' if mode == 'doh_fresh' else 'established'}")
            ax.text(.98, .91, f"Median {np.median(values):+.1f} ms", transform=ax.transAxes,
                    ha="right", va="top", fontsize=10, bbox={"facecolor":"white", "edgecolor":"none", "alpha":.85})
            tidy(ax, "x")
    fig.suptitle(f"Matched DoH minus UDP lookup differences · {ds['date']}")
    save(fig, out, "lookup_paired_distributions",
         "Each dot is a successful matched DoH-minus-UDP difference. Vertical jitter only separates overlapping dots. Boxes span the interquartile range, central lines show medians, and whiskers span the complete observed range. Axes vary between panels to expose established-session variation. No outlier is excluded.", ds, manifest)


def window_effects(ds, robustness, out, manifest):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.5), layout="constrained")
    for ax, mode in zip(axes, CONTRASTS):
        for provider in PROVIDERS:
            rows = [r for r in robustness["windows"] if r["experiment"] == "lookup"
                    and r["provider"] == provider and r["comparison"] == mode]
            rows.sort(key=lambda r:r["window"])
            ax.plot([r["window"] for r in rows], [r["median_delta_ms"] for r in rows],
                    marker="o", markersize=5, color=PROVIDER_COLORS[provider],
                    linewidth=1.4, label=PROVIDER_NAMES[provider])
        ax.axhline(0, color="#555555", linestyle="--", linewidth=.8)
        ax.set(title="Fresh connection" if mode == "doh_fresh" else "Established connection",
               xticks=[1,2,3], xlabel="Measurement window")
        tidy(ax)
    axes[0].set_ylabel("Median paired difference (ms)")
    axes[1].legend(frameon=False, loc="best", handlelength=1.5)
    fig.suptitle(f"Window-specific DoH minus UDP effects · {ds['date']}")
    save(fig, out, "window_effects",
         "Median matched lookup differences calculated separately for each of the three nearby windows. Lines join observed medians as a visual guide, not a temporal model. Panels have separate vertical scales. A sign reversal in established-session differences is evidence of sensitivity within the sampled session, even when the pooled conditional interval excludes zero.", ds, manifest)


def domain_effects(ds, robustness, out, manifest):
    names = sorted(set(r["domain"] for r in robustness["domains"]))
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 5.1), sharey=True, layout="constrained")
    for ax, mode in zip(axes, CONTRASTS):
        for provider, offset in zip(PROVIDERS, [-.12, .12]):
            table = {r["domain"]:r["median_delta_ms"] for r in robustness["domains"]
                     if r["provider"] == provider and r["comparison"] == mode}
            ax.scatter([table[n] for n in names], np.arange(len(names)) + offset,
                       s=30, marker="o" if provider == "cloudflare" else "s",
                       color=PROVIDER_COLORS[provider], label=PROVIDER_NAMES[provider], zorder=3)
        ax.axvline(0, color="#555555", linewidth=.8, linestyle="--")
        ax.set(xlabel="Median paired difference (ms)",
               title="Fresh connection" if mode == "doh_fresh" else "Established connection")
        tidy(ax, "y")
    axes[0].set_yticks(np.arange(len(names)), names)
    axes[0].invert_yaxis()
    fig.legend(handles=[Line2D([], [], color=PROVIDER_COLORS[p], marker="o" if p == "cloudflare" else "s",
                               linestyle="none", label=PROVIDER_NAMES[p]) for p in PROVIDERS],
               loc="outside lower center", ncol=2, frameon=False, handletextpad=.3)
    fig.suptitle(f"Domain-specific DoH minus UDP effects · {ds['date']}")
    save(fig, out, "domain_effects",
         "Each point is a domain-specific median paired lookup difference across its repetitions and three windows. Provider markers are vertically offset for legibility. Panels have separate horizontal scales. The ten chosen names are a fixed workload, not a random sample of all Internet domains.", ds, manifest)


def page_effects(ds, out, manifest):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 4.0), sharey=True, layout="constrained")
    conditions = [(1,"doh_fresh"), (1,"doh_reused"), (8,"doh_fresh"), (8,"doh_reused")]
    labels = ["1 name: fresh", "1 name: established", "8 names: fresh", "8 names: established"]
    for ax, provider in zip(axes, PROVIDERS):
        for y, (origins, mode) in enumerate(conditions):
            matches = [r for r in ds["summary"]["page_paired"]
                       if r["provider"] == provider and int(r["origins"]) == origins and r["comparison"] == mode]
            if not matches:
                continue
            r = matches[0]
            med, low, high = [float(r[k]) for k in ("median_delta_ms", "ci95_low_ms", "ci95_high_ms")]
            ax.errorbar(med, y, xerr=[[med-low],[high-med]], fmt="o", markersize=5,
                        capsize=3, linewidth=1.5, color=MODE_COLORS[mode], zorder=3)
        ax.axvline(0, color="#555555", linestyle="--", linewidth=.8)
        ax.set(title=PROVIDER_NAMES[provider], xlabel="Median paired difference (ms)")
        tidy(ax, "x")
    axes[0].set_yticks(range(len(labels)), labels)
    axes[0].invert_yaxis()
    fig.suptitle(f"DNS-gated page load effects · {ds['date']}")
    save(fig, out, "page_effects",
         "Median paired fixture load-event differences relative to UDP, with the original descriptive 95% within-window paired-bootstrap intervals. Each condition contains thirty matched navigations. Fresh DoH opens one shared connection per page; established setup occurs before navigation. These are fixed local-content DNS-gated browser loads, not native-browser DoH or general website performance.", ds, manifest)


def setup_breakdown(ds, out, manifest):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.7), sharey=True, layout="constrained")
    for ax, provider in zip(axes, PROVIDERS):
        rows = [r for r in ds["dns"] if r.get("phase") == "measure" and r.get("valid") is True
                and r.get("provider") == provider and r.get("protocol") == "doh_fresh"]
        values = [[r["connect_ms"] for r in rows],
                  [r["elapsed_ms"] - r["connect_ms"] for r in rows],
                  [r["elapsed_ms"] for r in rows]]
        for y, v in enumerate(values):
            lo, med, hi = np.quantile(v, [.25,.5,.75])
            ax.errorbar(med, y, xerr=[[med-lo],[hi-med]], fmt="o", color="#BD602B",
                        capsize=3, markersize=5, linewidth=1.6, zorder=3)
        ax.set(title=PROVIDER_NAMES[provider], xlabel="Recorded time (ms)", xlim=(0,None))
        tidy(ax, "x")
    axes[0].set_yticks(range(3), ["Connection stage", "Remaining exchange", "Total lookup"])
    axes[0].invert_yaxis()
    fig.suptitle(f"Fresh DoH timing components · {ds['date']}")
    save(fig, out, "setup_breakdown",
         "Medians and interquartile ranges of the recorded connection stage, remaining time (individual elapsed minus connection time), and total fresh lookup time. Marginal medians are shown separately and must not be added. The connection stage includes networking and client handling of TCP/TLS/HTTP2 setup; neither component isolates cryptographic CPU cost.", ds, manifest)


def timing_series(ds, out, manifest):
    fig, axes = plt.subplots(2, 1, figsize=(6.5, 4.7), sharex=True, layout="constrained")
    rows = [r for r in ds["dns"] if r.get("phase") == "measure" and r.get("valid") is True]
    stamp = lambda s:datetime.fromisoformat(s.replace("Z", "+00:00"))
    start = min(stamp(r["started_utc"]) for r in rows)
    for ax, provider in zip(axes, PROVIDERS):
        for mode in ("udp", "doh_fresh", "doh_warm"):
            selected = [r for r in rows if r["provider"] == provider and r["protocol"] == mode]
            times = [(stamp(r["started_utc"]) - start).total_seconds()/60 for r in selected]
            ax.scatter(times, [r["elapsed_ms"] for r in selected], s=7, alpha=.5,
                       edgecolors="none", color=MODE_COLORS[mode], label=MODE_NAMES[mode])
        ax.set_title(PROVIDER_NAMES[provider], loc="left")
        ax.set_ylabel("Lookup time (ms)")
        tidy(ax)
    fig.legend(handles=[Line2D([], [], color=MODE_COLORS[m], marker="o", linestyle="none",
                               label=MODE_NAMES[m]) for m in ("udp", "doh_fresh", "doh_warm")],
               loc="outside lower center", frameon=False, ncol=3,
               handletextpad=.2, columnspacing=.7)
    axes[1].set_xlabel("Minutes since first measured lookup")
    fig.suptitle(f"Recorded lookup sequence · {ds['date']}")
    save(fig, out, "timing_series",
         "Every successful measured lookup plotted against its actual start time relative to the first measured lookup. Gaps separate the three measurement windows. No smoothing, time interpolation or outlier removal is applied. Chronological changes can be shared by neighboring trials and limit independence.", ds, manifest)


def cross_date(found, out, manifest):
    if len(found) < 2:
        return
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.1), layout="constrained")
    ordered = sorted(found, key=lambda ds:ds["date"])
    positions = np.arange(len(ordered))
    for row, provider in enumerate(PROVIDERS):
        for col, mode in enumerate(CONTRASTS):
            ax = axes[row,col]
            for x, ds in zip(positions, ordered):
                r = next(r for r in ds["summary"]["lookup_paired"] if r["provider"] == provider and r["comparison"] == mode)
                med, low, high = [float(r[k]) for k in ("median_delta_ms", "ci95_low_ms", "ci95_high_ms")]
                ax.errorbar(x, med, yerr=[[med-low],[high-med]], fmt="o", color=MODE_COLORS[mode],
                            capsize=4, linewidth=1.5, markersize=5)
            ax.axhline(0, color="#555555", linestyle="--", linewidth=.8)
            ax.set(title=f"{PROVIDER_NAMES[provider]} · {'fresh' if mode == 'doh_fresh' else 'established'}",
                   xticks=positions, xticklabels=[ds["date"][5:] for ds in ordered],
                   xlim=(-.4,len(ordered)-.6))
            if col == 0:
                ax.set_ylabel("Paired difference (ms)")
            if row == 1:
                ax.set_xlabel("Collection date (2026)")
            tidy(ax)
    fig.suptitle("Independent date-specific lookup contrasts")
    save(fig, out, "cross_date_comparison",
         "Independent date-specific median paired lookup differences and their original conditional within-window bootstrap intervals. Each date is analyzed separately and no pooled-date estimate is calculated. Axes vary between panels. Differences between sessions can reflect network, resolver, cache and background conditions; two dates do not identify a causal time trend or long-term population distribution.",
         {"date": ", ".join(ds["date"] for ds in ordered), "label":"separate-date-comparison"}, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    found = datasets(root)
    if not found:
        raise SystemExit("No analyzed datasets found")
    style()
    all_manifest = []
    for ds in found:
        robustness_path = ds["results"] / "robustness.json"
        if not robustness_path.exists():
            raise SystemExit(f"Run robustness.py first: {robustness_path} absent")
        robustness = json.loads(robustness_path.read_text(encoding="utf-8"))
        out = root / "figures" if ds["label"] == "original" else root / "figures" / ds["label"]
        manifest = []
        lookup_ecdf(ds, out, manifest)
        paired_distributions(ds, out, manifest)
        window_effects(ds, robustness, out, manifest)
        domain_effects(ds, robustness, out, manifest)
        page_effects(ds, out, manifest)
        setup_breakdown(ds, out, manifest)
        timing_series(ds, out, manifest)
        (out / "figure_manifest.json").write_text(json.dumps({"matplotlib_version":matplotlib.__version__,
                "figures":manifest}, indent=2) + "\n", encoding="utf-8")
        all_manifest.extend(manifest)
        print(json.dumps({"dataset": ds["label"], "figures": len(manifest), "directory":str(out)}))
    cross_date(found, root / "figures", all_manifest)
    (root / "figures" / "all_figures.json").write_text(json.dumps({"matplotlib_version":matplotlib.__version__,
            "figures":all_manifest}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
