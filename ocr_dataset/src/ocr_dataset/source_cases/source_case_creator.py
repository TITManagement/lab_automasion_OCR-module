"""source case 作成処理を GUI / CLI から共通利用する。

責務:
    - 元画像と全文正解テキストから source case の標準ファイルを作成する。
    - `prepare_source_case` と synthetic variants 生成を一連の処理として呼び出す。

責務外:
    - ROI ごとの正解文字列の確定、PaddleOCR 学習形式 export、学習実行。
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from ocr_dataset.paths import resolve_dataset_path, source_cases_root
from ocr_dataset.source_cases.prepare_source_case import prepare_source_case
from ocr_synthetic_data.generate_variants import generate_variants

CASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def default_source_cases_root() -> Path:
    """リポジトリ内の source case 保存先を返す。"""
    return source_cases_root()


def validate_case_id(case_id: str) -> str:
    """source case ID を検証し、前後空白を取り除いた値を返す。"""
    normalized = case_id.strip()
    if not normalized:
        raise ValueError("case ID is required.")
    if not CASE_ID_PATTERN.match(normalized):
        raise ValueError("case ID may contain only letters, numbers, underscore, dot, and hyphen.")
    return normalized


def _is_same_file(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return False
    return left.resolve() == right.resolve()


def create_source_case(
    *,
    image_path: Path,
    case_id: str,
    expected_text: str,
    source_cases_root: Path | None = None,
    overwrite: bool = False,
    generate_synthetic_variants: bool = True,
) -> dict[str, Any]:
    """元画像と全文正解から source case を作成し、summary を返す。"""
    source_image = image_path.expanduser().resolve()
    if not source_image.exists():
        raise FileNotFoundError(f"source image not found: {source_image}")
    if not source_image.is_file():
        raise ValueError(f"source image is not a file: {source_image}")

    normalized_case_id = validate_case_id(case_id)
    root = resolve_dataset_path(source_cases_root) if source_cases_root else default_source_cases_root()
    case_dir = root / normalized_case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    destination_image = case_dir / source_image.name
    image_reused = False
    if _is_same_file(source_image, destination_image):
        image_reused = True
    elif destination_image.exists() and not overwrite:
        raise FileExistsError(f"source image already exists: {destination_image}")
    else:
        shutil.copy2(source_image, destination_image)

    expected_path = case_dir / "expected.txt"
    normalized_expected = expected_text.rstrip() + "\n"
    expected_reused = False
    if expected_path.exists() and not overwrite:
        expected_reused = True
    else:
        expected_path.write_text(normalized_expected, encoding="utf-8")

    fields_path = case_dir / "expected_fields.json"
    if not fields_path.exists():
        fields_path.write_text("{}\n", encoding="utf-8")

    prepare_summary = prepare_source_case(case_dir, image_name=destination_image.name)

    variant_paths: list[Path] = []
    if generate_synthetic_variants:
        variant_paths = generate_variants(case_dir)

    return {
        "case_id": normalized_case_id,
        "case_dir": str(case_dir),
        "source_image": str(destination_image),
        "source_image_reused": image_reused,
        "expected_text": str(expected_path),
        "expected_text_reused": expected_reused,
        "expected_fields": str(fields_path),
        "rois": str(case_dir / "rois.json"),
        "roi_strips_dir": str(case_dir / "roi_strips"),
        "roi_labels": str(case_dir / "roi_labels.json"),
        "roi_count": prepare_summary["roi_count"],
        "variant_count": len(variant_paths),
        "variants_dir": str(case_dir / "variants"),
    }
