"""source case の標準ファイルをまとめて初期化・更新する CLI。

責務:
    - 元画像追加後に `expected.txt`、`rois.json`、`roi_labels.json` を整える。
    - ROI 再生成時に既存ラベルを可能な範囲で保持し、座標変更時は確認待ちへ戻す。

責務外:
    - 正解文字列の自動推定、PaddleOCR 学習形式 export、PaddleOCR 本体の学習実行。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ocr_dataset.paths import resolve_dataset_path
from ocr_dataset.source_cases.generate_roi_strips import generate_roi_strips
from ocr_dataset.source_cases.schema import EvaluationCase


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _roi_geometry(roi: dict[str, Any]) -> tuple[int, int, int, int]:
    return (int(roi["x"]), int(roi["y"]), int(roi["width"]), int(roi["height"]))


def _build_roi_labels(
    case: EvaluationCase,
    rois_payload: dict[str, Any],
    *,
    previous_rois: dict[str, Any],
) -> dict[str, Any]:
    previous_labels = _read_json(case.roi_labels)

    previous_rois_by_id = {roi["id"]: roi for roi in previous_rois.get("rois", [])}
    previous_labels_by_id = {label["roi_id"]: label for label in previous_labels.get("labels", [])}

    labels: list[dict[str, str]] = []
    for roi in rois_payload.get("rois", []):
        roi_id = roi["id"]
        previous_label = previous_labels_by_id.get(roi_id, {})
        text = str(previous_label.get("text", ""))
        previous_status = str(previous_label.get("status", "needs_labeling"))
        previous_roi = previous_rois_by_id.get(roi_id)

        if not text:
            status = "needs_labeling"
        elif previous_roi and _roi_geometry(previous_roi) == _roi_geometry(roi):
            status = previous_status
        else:
            status = "needs_review"

        labels.append(
            {
                "roi_id": roi_id,
                "text": text,
                "status": status,
                "note": "Fill with the exact text visible in this ROI.",
            }
        )

    if labels and all(label["status"] == "verified" for label in labels):
        label_status = "verified"
    else:
        label_status = "needs_human_labeling"

    return {
        "schema_version": 1,
        "source_image": rois_payload["source_image"],
        "source_rois": case.rois.name,
        "label_status": label_status,
        "labels": labels,
    }


def prepare_source_case(
    case_dir: Path,
    *,
    image_name: str | None = None,
    overwrite_expected: bool = False,
) -> dict[str, Any]:
    """source case の標準ファイルを作成・更新し、処理結果 summary を返す。"""
    case = EvaluationCase(case_dir=resolve_dataset_path(case_dir))
    source_image = case.case_dir / image_name if image_name else case.source_image
    if not source_image.exists():
        raise FileNotFoundError(f"source image not found: {source_image}")

    expected_created = False
    if overwrite_expected or not case.expected_text.exists():
        case.expected_text.write_text("", encoding="utf-8")
        expected_created = True

    previous_rois_payload = _read_json(case.rois)
    rois_payload = generate_roi_strips(case.case_dir, image_name=source_image.name)
    labels_payload = _build_roi_labels(case, rois_payload, previous_rois=previous_rois_payload)
    _write_json(case.roi_labels, labels_payload)

    return {
        "case_dir": str(case.case_dir),
        "source_image": source_image.name,
        "expected_created": expected_created,
        "roi_count": rois_payload["roi_count"],
        "roi_labels": str(case.roi_labels),
        "label_status": labels_payload["label_status"],
    }


def main() -> int:
    """CLI 引数を読み取り、source case 標準ファイルを初期化・更新する。"""
    parser = argparse.ArgumentParser(description="Prepare OCR source case assets from a source image.")
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--image-name", default=None, help="Image file name inside case_dir. Defaults to source case image.")
    parser.add_argument(
        "--overwrite-expected",
        action="store_true",
        help="Overwrite expected.txt with an empty template. Use carefully.",
    )
    args = parser.parse_args()

    summary = prepare_source_case(args.case_dir, image_name=args.image_name, overwrite_expected=args.overwrite_expected)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
