#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

REQUIRED_MARKERS = [
    "AGENTS_BASE_SOURCE",
    "AGENTS_BASE_SHA256",
    "README_STANDARD.md",
]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    agents = root / "AGENTS.md"
    if not agents.exists():
        print("[NG] AGENTS.md がありません")
        return 1
    text = agents.read_text(encoding="utf-8")
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    if missing:
        print("[NG] AGENTS.md の必須記載が不足しています:")
        for item in missing:
            print(f"  - {item}")
        return 1
    print("[OK] AGENTS.md governance check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
