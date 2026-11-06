#!/usr/bin/env python3
"""
Triple Workspace Synchronizer & SHA-256 Drift Verifier
Keeps code, scripts, skills, subagent definitions, and templates 100% identical across:
  - Source (Canonical): C:\\ganar dinero
  - Mirror 1:           C:\\VideoStudio\\cli
  - Mirror 2:           C:\\Users\\Juan\\Desktop\\CanalesYoutube
Safely skips runtime directories (.git, __pycache__, videos, pipeline_runs, storage, config/sessions,
config/history, config/channels.json, config/stock_credentials.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SOURCE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_MIRRORS = [
    r"C:\VideoStudio\cli",
    r"C:\Users\Juan\Desktop\CanalesYoutube",
]

SYNC_REL_PATHS = [
    "AGENTS.md",
    "AGENT.md",
    "KNOWLEDGE_GRAPH.md",
    "README.md",
    "SETUP_ONBOARDING.md",
    "requirements.txt",
    ".gitignore",
    "config/channels.example.json",
    "config/hardware.json",
    "scripts",
    ".agents",
]

IGNORE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".git"}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_canonical_files(root: str) -> list[str]:
    rel_files: list[str] = []
    for item in SYNC_REL_PATHS:
        abs_item = os.path.join(root, item)
        if not os.path.exists(abs_item):
            continue
        if os.path.isfile(abs_item):
            rel_files.append(item.replace("\\", "/"))
        elif os.path.isdir(abs_item):
            for dirpath, dirnames, filenames in os.walk(abs_item):
                dirnames[:] = [d for d in dirnames if d not in IGNORE_DIR_NAMES]
                for fn in filenames:
                    if fn.endswith((".pyc", ".pyo")):
                        continue
                    full_p = os.path.join(dirpath, fn)
                    rel_p = os.path.relpath(full_p, root).replace("\\", "/")
                    rel_files.append(rel_p)
    return sorted(set(rel_files))


def sync_and_verify(mirrors: list[str], verify_only: bool = False) -> dict:
    canonical_files = collect_canonical_files(SOURCE_ROOT)
    report = {
        "source": SOURCE_ROOT,
        "tracked_files_count": len(canonical_files),
        "verify_only": verify_only,
        "mirrors": {}
    }

    for mirror in mirrors:
        if not os.path.exists(mirror):
            report["mirrors"][mirror] = {"exists": False, "copied": 0, "diffs": []}
            continue

        copied = 0
        diffs = []
        for rel_p in canonical_files:
            src_f = os.path.join(SOURCE_ROOT, rel_p)
            dst_f = os.path.join(mirror, rel_p)

            needs_sync = (not os.path.exists(dst_f)) or (_sha256(src_f) != _sha256(dst_f))
            if needs_sync:
                if verify_only:
                    diffs.append(rel_p)
                else:
                    os.makedirs(os.path.dirname(dst_f), exist_ok=True)
                    shutil.copy2(src_f, dst_f)
                    copied += 1
                    if _sha256(src_f) != _sha256(dst_f):
                        diffs.append(rel_p)

        report["mirrors"][mirror] = {
            "exists": True,
            "copied": copied,
            "diffs_count": len(diffs),
            "diffs": diffs
        }

    report["all_in_sync"] = all(
        (not m["exists"]) or m["diffs_count"] == 0
        for m in report["mirrors"].values()
    )
    return report


def main():
    parser = argparse.ArgumentParser(description="Sync and hash-verify canonical files across local mirrors.")
    parser.add_argument("--verify", action="store_true", help="Only verify SHA-256 parity without copying")
    args = parser.parse_args()

    res = sync_and_verify(DEFAULT_MIRRORS, verify_only=args.verify)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if not res["all_in_sync"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
