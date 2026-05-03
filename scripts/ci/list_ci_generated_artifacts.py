#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import date


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    workflows = sorted((root / ".github" / "workflows").glob("*.yml"))
    out = root / "docs" / "devops" / "CI_GENERATED_ARTIFACTS.md"

    lines = [
        "# CI Generated Artifacts",
        "",
        f"更新日: {date.today().isoformat()}",
        "",
        "## 目的",
        "CIで生成・更新される成果物を一覧化し、参照先を明確化する。",
        "",
        "## 成果物一覧",
        "| Workflow | 生成物/更新物 | 備考 |",
        "| --- | --- | --- |",
    ]

    for wf in workflows:
        name = wf.name
        text = wf.read_text(encoding="utf-8")
        if "IMPORT_MODULE_ORIGIN_AUDIT.md" in text:
            lines.append(f"| `{name}` | `docs/operations/IMPORT_MODULE_ORIGIN_AUDIT.md` | import由来一覧を更新 |")
        if "docs/_book" in text:
            lines.append(f"| `{name}` | `docs/_book/` | 統合ドキュメントを生成 |")

    lines += [
        "",
        "## ローカル一時生成先",
        "- `ops/ci/artifacts/`: CIと同じ構造でローカル検証時の生成物を保存する。",
    ]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
