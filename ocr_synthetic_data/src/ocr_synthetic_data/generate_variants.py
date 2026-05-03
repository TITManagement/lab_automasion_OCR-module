"""evaluation case から OCR synthetic variants を生成する CLI。

責務:
    - source image を読み込み、教師テキストを維持したまま入力画像の揺らぎを生成する。
    - 生成物を case directory 配下の variants に保存する。

責務外:
    - OCR 実行、評価指標計算、PaddleOCR 学習形式への export。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ocr_dataset.paths import resolve_dataset_path
from ocr_dataset.source_cases.schema import EvaluationCase
from ocr_synthetic_data.augment import adjust_brightness, apply_blur, load_image, rotate_keep_canvas


def generate_variants(case_dir: Path) -> list[Path]:
    """指定 case の source image から最小セットの synthetic variants を生成する。"""
    case = EvaluationCase(case_dir=resolve_dataset_path(case_dir))
    case.require_source_assets()
    case.variants_dir.mkdir(parents=True, exist_ok=True)

    image = load_image(case.source_image)
    variants = {
        "brightness_dark.jpg": adjust_brightness(image, 0.82),
        "brightness_light.jpg": adjust_brightness(image, 1.15),
        "blur_soft.jpg": apply_blur(image, 0.8),
        "rotate_left.jpg": rotate_keep_canvas(image, -1.5),
        "rotate_right.jpg": rotate_keep_canvas(image, 1.5),
    }

    written: list[Path] = []
    for name, variant in variants.items():
        out = case.variants_dir / name
        variant.save(out, quality=92)
        written.append(out)
    return written


def main() -> int:
    """CLI 引数を読み取り、evaluation case の synthetic variants を生成する。"""
    parser = argparse.ArgumentParser(description="Generate OCR synthetic data variants from an evaluation case.")
    parser.add_argument("case_dir", type=Path)
    args = parser.parse_args()

    for path in generate_variants(args.case_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
