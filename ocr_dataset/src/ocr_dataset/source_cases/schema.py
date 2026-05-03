"""OCR evaluation case のファイル配置と metadata を表現する。

責務:
    - source image、expected text、field expected、ROI 定義の標準パスをまとめる。
    - synthetic data 生成処理が case directory に依存しすぎないよう境界を作る。

責務外:
    - 画像変換、OCR 実行、PaddleOCR dataset export。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


@dataclass(frozen=True)
class EvaluationCase:
    """1つの OCR 評価ケースに含まれる標準ファイルのパスを保持する。"""

    case_dir: Path

    @property
    def source_image(self) -> Path:
        """元画像ファイルの標準パスを返す。

        原本ファイル名を source case の識別情報として残すため、`source.jpg`
        以外の画像が存在する場合はそちらを優先する。
        """
        images = sorted(
            path
            for path in self.case_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and path.name != "source.jpg"
        )
        if images:
            return images[0]
        return self.case_dir / "source.jpg"

    @property
    def expected_text(self) -> Path:
        """全文正解テキストの標準パスを返す。"""
        return self.case_dir / "expected.txt"

    @property
    def expected_fields(self) -> Path:
        """フィールド別正解 JSON の標準パスを返す。"""
        return self.case_dir / "expected_fields.json"

    @property
    def rois(self) -> Path:
        """ROI 定義 JSON の標準パスを返す。"""
        return self.case_dir / "rois.json"

    @property
    def roi_labels(self) -> Path:
        """ROI ごとの正解ラベル JSON の標準パスを返す。"""
        return self.case_dir / "roi_labels.json"

    @property
    def variants_dir(self) -> Path:
        """生成した synthetic variants の保存先ディレクトリを返す。"""
        return self.case_dir / "variants"

    def require_source_assets(self) -> None:
        """生成前に必要な source assets が存在することを検証する。"""
        missing = [path for path in [self.source_image, self.expected_text] if not path.exists()]
        if missing:
            joined = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(f"missing evaluation case assets: {joined}")
