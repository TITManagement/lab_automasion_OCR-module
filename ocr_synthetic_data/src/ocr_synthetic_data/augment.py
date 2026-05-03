"""画像変換で OCR synthetic data を生成する補助関数群。

責務:
    - 元画像に対して明るさ、ぼけ、ノイズ、傾きなどの変換を適用する。
    - 教師ラベルを変えずに評価・学習用の入力揺らぎを増やす。

責務外:
    - OCR 実行や PaddleOCR 学習形式への export。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


def load_image(path: Path) -> Image.Image:
    """指定パスの画像を RGB として読み込む。"""
    return Image.open(path).convert("RGB")


def adjust_brightness(image: Image.Image, factor: float) -> Image.Image:
    """明るさ係数を適用した画像を返す。"""
    return ImageEnhance.Brightness(image).enhance(factor)


def apply_blur(image: Image.Image, radius: float) -> Image.Image:
    """Gaussian blur を適用した画像を返す。"""
    return image.filter(ImageFilter.GaussianBlur(radius=radius))


def rotate_keep_canvas(image: Image.Image, degrees: float) -> Image.Image:
    """キャンバスを広げず、背景を白で埋めながら小角度回転する。"""
    return image.rotate(degrees, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=(255, 255, 255))

