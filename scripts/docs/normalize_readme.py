#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED_SECTIONS_L2 = [
    "## 対象者",
    "## 依存関係",
    "## 最短セットアップ",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate README.md against AiLab minimum standard")
    parser.add_argument("--check", action="store_true", help="check only")
    parser.add_argument("--file", default="README.md")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"[NG] {path} がありません")
        return 1

    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    if "<!-- README_LEVEL:" not in text:
        errors.append("README_LEVEL コメントがありません")

    if "README_STANDARD.md" not in text:
        errors.append("README_STANDARD.md への参照がありません")

    for sec in REQUIRED_SECTIONS_L2:
        if sec not in text:
            errors.append(f"必須章が不足: {sec}")

    if errors:
        print("[NG] README standard check failed")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[OK] README standard check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
