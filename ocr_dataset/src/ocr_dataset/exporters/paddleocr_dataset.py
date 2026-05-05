"""PaddleOCR 学習形式への dataset export 境界を定義する。

責務:
    - evaluation case と synthetic variants から PaddleOCR 向け dataset を作る入口を提供する。
    - export の入出力境界を wrapper や GUI から分離する。

責務外:
    - PaddleOCR 本体の学習実行、モデル管理、OCR 推論。
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from ocr_dataset.paths import resolve_dataset_path


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"roi_labels.json not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"invalid roi_labels.json root: {path}")
    return payload


def _normalize_rec_text(text: str) -> str:
    return " ".join(text.replace("\t", " ").splitlines()).strip()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_paddleocr_dataset(case_dir: Path, output_dir: Path) -> Path:
    """verified ROI labels を PaddleOCR recognition label file へ export する。"""
    case_dir = resolve_dataset_path(case_dir)
    output_dir = resolve_dataset_path(output_dir)
    labels_path = case_dir / "roi_labels.json"
    payload = _read_json(labels_path)
    labels = payload.get("labels")
    if not isinstance(labels, list):
        raise ValueError(f"invalid roi_labels.json labels: {labels_path}")

    images_dir = output_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    if images_dir.exists():
        shutil.rmtree(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    label_file = output_dir / "rec_gt_train.txt"
    manifest_records: list[dict[str, object]] = []
    lines: list[str] = []
    skipped = 0

    for label in labels:
        if not isinstance(label, dict):
            skipped += 1
            continue
        if label.get("status") != "verified":
            skipped += 1
            continue
        image_rel = str(label.get("image", "")).strip()
        text = _normalize_rec_text(str(label.get("text", "")))
        if not image_rel:
            raise ValueError(f"verified ROI has no image: {label.get('roi_id', '-')}")
        if not text:
            raise ValueError(f"verified ROI has empty text: {label.get('roi_id', '-')}")

        source_image = case_dir / image_rel
        if not source_image.exists():
            raise FileNotFoundError(f"verified ROI image not found: {source_image}")
        export_image = images_dir / source_image.name
        shutil.copy2(source_image, export_image)

        export_image_rel = export_image.relative_to(output_dir).as_posix()
        lines.append(f"{export_image_rel}\t{text}")
        manifest_records.append(
            {
                "roi_id": label.get("roi_id", source_image.stem),
                "source_image": image_rel,
                "export_image": export_image_rel,
                "text": text,
                "source_status": label.get("status"),
            }
        )

    label_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "source_case": str(case_dir),
        "source_roi_labels": str(labels_path),
        "format": "paddleocr_recognition",
        "label_file": label_file.name,
        "image_dir": images_dir.name,
        "exported": len(manifest_records),
        "skipped": skipped,
        "records": manifest_records,
    }
    _write_json(output_dir / "manifest.json", manifest)
    return label_file


def main() -> int:
    """CLI 引数を読み取り、PaddleOCR recognition dataset を export する。"""
    parser = argparse.ArgumentParser(description="Export verified ROI labels to a PaddleOCR recognition dataset.")
    parser.add_argument("case_dir", type=Path, help="Source case directory under ocr_dataset, e.g. source_cases/img_0685")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output directory under ocr_dataset, e.g. exports/img_0685",
    )
    args = parser.parse_args()

    label_file = export_paddleocr_dataset(args.case_dir, args.output)
    print(f"exported PaddleOCR label file: {label_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
