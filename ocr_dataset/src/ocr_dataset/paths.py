"""ocr_dataset 配下の標準入出力パスを解決する。

責務:
    - source case などのデータセット資産を `ocr_dataset/` 起点で解決する。
    - CLI / GUI / Python API のパス解釈を統一する。

責務外:
    - 個別 source case の schema 解釈、ファイル生成、画像処理。
"""

from __future__ import annotations

from pathlib import Path


def dataset_root() -> Path:
    """このパッケージに対応する `ocr_dataset/` ディレクトリを返す。"""
    return Path(__file__).resolve().parents[2]


def source_cases_root() -> Path:
    """source case の標準保存先 `ocr_dataset/source_cases/` を返す。"""
    return dataset_root() / "source_cases"


def resolve_dataset_path(path: Path | str) -> Path:
    """相対パスを `ocr_dataset/` 起点で解決して返す。

    絶対パスはそのまま返す。相対パスは `ocr_dataset/` からの相対として扱う。
    これにより、別母艦へ clone した場合もリポジトリ絶対パスに依存しない。
    """
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    if candidate.parts and candidate.parts[0] == dataset_root().name:
        return dataset_root().parent / candidate
    return dataset_root() / candidate
