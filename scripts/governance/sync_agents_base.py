#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync AGENTS.md base metadata from remote source")
    parser.add_argument("--source-url", required=True, help="Raw AGENTS.md URL")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    agents_path = repo_root / "AGENTS.md"
    content = urllib.request.urlopen(args.source_url, timeout=20).read()
    digest = hashlib.sha256(content).hexdigest()

    text = agents_path.read_text(encoding="utf-8")
    text = re.sub(
        r"(AGENTS_BASE_SOURCE:\s*).+", rf"\1{args.source_url}", text
    )
    text = re.sub(
        r"(AGENTS_BASE_SHA256:\s*).+", rf"\1{digest}", text
    )
    agents_path.write_text(text, encoding="utf-8")
    print(f"[OK] synced: {agents_path}")
    print(f"[OK] sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
