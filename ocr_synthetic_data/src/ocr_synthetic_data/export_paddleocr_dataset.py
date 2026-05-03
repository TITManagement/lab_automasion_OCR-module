"""PaddleOCR 学習形式への dataset export 境界を定義する。

責務:
    - evaluation case と synthetic variants から PaddleOCR 向け dataset を作る入口を提供する。
    - export の入出力境界を wrapper や GUI から分離する。

責務外:
    - PaddleOCR 本体の学習実行、モデル管理、OCR 推論。
"""

from __future__ import annotations

from pathlib import Path


def export_paddleocr_dataset(case_dir: Path, output_dir: Path) -> Path:
    """PaddleOCR dataset export の出力先を作成し、将来実装の境界を固定する。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    raise NotImplementedError("PaddleOCR dataset export is not implemented yet.")
