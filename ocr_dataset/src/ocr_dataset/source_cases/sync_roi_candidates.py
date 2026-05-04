"""ROI OCR 候補テキストを roi_labels.json に同期する。

責務:
    - `roi_strips/strip_XXXX.txt` を `roi_labels.json` の `candidate_text` に反映する。
    - 候補は正解ではなく、人手確認前の下書きとして保持する。

責務外:
    - `text` の確定、`verified` 化、PaddleOCR 学習形式 export。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ocr_dataset.paths import resolve_dataset_path
from ocr_dataset.source_cases.schema import EvaluationCase


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _candidate_path(case: EvaluationCase, label: dict[str, Any]) -> Path:
    image = Path(str(label.get("image", "")))
    if image.suffix:
        return case.case_dir / image.with_suffix(".txt")
    roi_id = str(label.get("roi_id", ""))
    return case.roi_strips_dir / f"{roi_id}.txt"


def sync_roi_ocr_candidates(case_dir: Path) -> dict[str, Any]:
    """ROI 短冊 OCR 候補 `.txt` を `roi_labels.json` の candidate_text へ反映する。"""
    case = EvaluationCase(case_dir=resolve_dataset_path(case_dir))
    labels_payload = _read_json(case.roi_labels)
    labels = labels_payload.get("labels", [])
    if not isinstance(labels, list):
        raise ValueError(f"invalid roi_labels.json labels: {case.roi_labels}")

    updated = 0
    missing = 0
    unchanged = 0
    for label in labels:
        if not isinstance(label, dict):
            continue
        candidate_path = _candidate_path(case, label)
        if not candidate_path.exists():
            missing += 1
            continue

        candidate_text = candidate_path.read_text(encoding="utf-8").strip()
        if str(label.get("candidate_text", "")) == candidate_text:
            unchanged += 1
            continue

        label["candidate_text"] = candidate_text
        label["candidate_source"] = "vision_ocr"
        label["candidate_file"] = str(candidate_path.relative_to(case.case_dir))
        if not str(label.get("text", "")):
            label["status"] = "needs_labeling"
        updated += 1

    labels_payload["candidate_status"] = "has_candidates" if updated or unchanged else "no_candidates"
    _write_json(case.roi_labels, labels_payload)
    return {
        "case_dir": str(case.case_dir),
        "roi_labels": str(case.roi_labels),
        "updated": updated,
        "unchanged": unchanged,
        "missing": missing,
    }


def main() -> int:
    """CLI 引数を読み取り、ROI OCR 候補を roi_labels.json に同期する。"""
    parser = argparse.ArgumentParser(description="Sync ROI OCR candidate .txt files into roi_labels.json.")
    parser.add_argument("case_dir", type=Path)
    args = parser.parse_args()

    summary = sync_roi_ocr_candidates(args.case_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
