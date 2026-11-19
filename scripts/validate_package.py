"""Offline checks for research inputs, analysis, public links and SHA-256 coverage."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

IGNORED_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}
FIGURES = ("lookup_ecdf", "lookup_paired_distributions", "window_effects", "domain_effects", "page_effects", "setup_breakdown", "timing_series")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def public_files(root):
    files = []
    for folder, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not (Path(folder) == root / "data" and d == "new-run")]
        for name in names:
            p = Path(folder) / name
            rel = p.relative_to(root).as_posix()
            if rel in {"SHA256SUMS.txt", "SON_ADIMLAR_TR.md"} or name.endswith((".pyc", ".pyo")) or name.startswith("npm-debug.log") or name == ".DS_Store":
                continue
            if p.is_symlink():
                raise ValueError(f"Public package contains an unsupported symlink: {rel}")
            files.append(p)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def original_data_checks(root):
    ledger_path = root / "docs/evidence/original-data-sha256.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
    entries = ledger["files"]
    for rel, expected in entries.items():
        target = (root / rel).resolve()
        if not target.is_relative_to(root) or not rel.startswith("data/"):
            raise ValueError("Unsafe protected-data path")
        if not target.is_file() or digest(target) != expected:
            raise ValueError(f"Original November 15 input changed or is absent: {rel}")
    return len(entries)


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def check_dataset(root, data, result):
    raw = rows(data / "dns_raw.jsonl")
    pages = rows(data / "pages.jsonl")
    gates = rows(data / "page-dns.jsonl")
    env = json.loads((data / "environment.json").read_text(encoding="utf-8-sig"))
    if env.get("status") != "complete":
        raise ValueError(f"Collection is incomplete: {data.relative_to(root)}")
    summary = json.loads((result / "summary.json").read_text(encoding="utf-8-sig"))
    measured = [r for r in raw if r.get("phase") == "measure"]
    expected = env["windows"] * env["reps"] * len(env["domains"]) * len(env["providers"]) * 3
    if len(measured) != expected:
        raise ValueError(f"Unexpected measured lookup count in {data.relative_to(root)}")
    design = collections.Counter((r["window"], r["provider"], r["protocol"]) for r in measured)
    if len(design) != env["windows"] * len(env["providers"]) * 3 or set(design.values()) != {env["reps"] * len(env["domains"])}:
        raise ValueError("Lookup groups do not match the recorded design")
    expected_pages = env["windows"] * env["reps"] * len(env["providers"]) * 2 * 3
    if len(pages) != expected_pages:
        raise ValueError("Page attempts do not match the recorded design")
    wanted = {"lookup_all_rows": len(raw), "lookup_measurements": len(measured), "pages": len(pages), "page_dns_rows": len(gates)}
    for name, value in wanted.items():
        if summary["counts"][name] != value:
            raise ValueError(f"Summary count does not match raw inputs: {name}")
    for audit in summary["validation"].values():
        if audit.get("validation_errors") or audit.get("transport_mismatches"):
            raise ValueError(f"Analysis audit failed: {audit['dataset']}")
    if summary.get("warnings"):
        raise ValueError("Analysis reported warnings")
    return {"data": data.relative_to(root).as_posix(), **wanted}


def check_links(root):
    checked = 0
    sources = [root / "README.md", *sorted((root / "docs").rglob("*.md"))]
    for source in sources:
        if not source.exists():
            continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", source.read_text(encoding="utf-8-sig")):
            target = target.strip("<>")
            if urlsplit(target).scheme or target.startswith("#"):
                continue
            local = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not local:
                continue
            destination = (source.parent / local).resolve()
            if not destination.is_relative_to(root) or not destination.exists():
                raise ValueError(f"Broken local link in {source.relative_to(root)}: {target}")
            if destination.name == "SON_ADIMLAR_TR.md":
                raise ValueError("Public document links to the user's ignored private guide")
            checked += 1
    return checked


def check_figures(root, dates):
    stems = [root / "figures" / stem for stem in FIGURES]
    if len(dates) > 1:
        stems += [root / "figures/replication-2026-11-19" / stem for stem in FIGURES]
        stems.append(root / "figures/cross_date_comparison")
    for stem in stems:
        for extension, signature in ((".png", b"\x89PNG\r\n\x1a\n"), (".pdf", b"%PDF"), (".svg", b"<svg")):
            file = stem.with_suffix(extension)
            data = file.read_bytes()
            if (signature not in data[:1000]) or len(data) < 100:
                raise ValueError(f"Invalid figure artifact: {file.relative_to(root)}")
    return len(stems)


def check_collection_snapshot(root):
    folder = root / "docs/evidence/collection-source-2026-11-19"
    capture = json.loads((folder / "capture.json").read_text(encoding="utf-8-sig"))
    for name, expected in capture["script_sha256"].items():
        file = (folder / name).resolve()
        if not file.is_relative_to(folder) or digest(file) != expected:
            raise ValueError(f"Collection source snapshot hash differs: {name}")
    for line in (folder / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        expected, name = line.split("  ", 1)
        file = (folder / name).resolve()
        if not file.is_relative_to(folder) or digest(file) != expected:
            raise ValueError(f"Collection snapshot manifest differs: {name}")
    return len(capture["script_sha256"])


def manifest(root, write=False):
    file = root / "SHA256SUMS.txt"
    public = public_files(root)
    if write:
        file.write_text("".join(f"{digest(p)}  {p.relative_to(root).as_posix()}\n" for p in public), encoding="utf-8")
    listed = {}
    for line in file.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match or match[2] in listed:
            raise ValueError("Malformed or duplicate SHA256SUMS entry")
        listed[match[2]] = match[1]
    expected_names = {p.relative_to(root).as_posix() for p in public}
    if set(listed) != expected_names:
        raise ValueError(f"Manifest coverage differs: missing={sorted(expected_names-set(listed))}; extra={sorted(set(listed)-expected_names)}")
    for rel, expected in listed.items():
        target = (root / rel).resolve()
        if not target.is_relative_to(root) or digest(target) != expected:
            raise ValueError(f"SHA-256 mismatch: {rel}")
    return len(listed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--raw-only", action="store_true", help="Verify the frozen original inputs before a rebuild")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ignore-manifest", action="store_true")
    group.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    protected = original_data_checks(root)
    if args.raw_only:
        print(json.dumps({"status": "PASS", "protected_original_inputs": protected}, indent=2))
        return
    required = ["README.md", "package.json", "package-lock.json", "requirements.txt", "profile.json", "manuscript.md", "docs/paper_source.md", "docs/references.json", "scripts/analyze.py", "scripts/build_paper.py", "scripts/plot_results.py", "scripts/robustness.py", "scripts/reproduce.py", "scripts/dns_client.mjs", "scripts/measure_dns.mjs", "scripts/page-load.mjs", "tests/test_analysis.py", "tests/test_dns.mjs", "tests/test_live.mjs"]
    for rel in required:
        if not (root / rel).is_file():
            raise ValueError(f"Required public file absent: {rel}")
    package = json.loads((root / "package.json").read_text(encoding="utf-8-sig"))
    lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8-sig"))
    if package["dependencies"] != lock["packages"][""]["dependencies"] or package["version"] != lock["version"]:
        raise ValueError("package.json and package-lock.json disagree")
    profile = json.loads((root / "profile.json").read_text(encoding="utf-8-sig"))
    if any(not str(profile.get(k, "")).strip() for k in ("author_name", "student_id", "institution", "repository_url")):
        raise ValueError("Author profile incomplete")
    json.loads((root / "docs/references.json").read_text(encoding="utf-8-sig"))
    pdf = root / "Secure_DNS_Research_Paper.pdf"
    if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF"):
        raise ValueError("Final paper PDF absent or invalid")
    datasets = [check_dataset(root, root / "data", root / "results")]
    replica = root / "data/replication-2026-11-19"
    snapshot_files = 0
    if replica.exists():
        datasets.append(check_dataset(root, replica, root / "results/replication-2026-11-19"))
        snapshot_files = check_collection_snapshot(root)
    figure_count = check_figures(root, datasets)
    links = check_links(root)
    coverage = None if args.ignore_manifest else manifest(root, args.write_manifest)
    print(json.dumps({"status": "PASS", "protected_original_inputs": protected, "collection_snapshot_files": snapshot_files, "datasets": datasets, "figure_stems": figure_count, "local_links_checked": links, "manifest_files": coverage, "network_access": "none"}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
