"""source case 画像から短冊状 ROI 定義を自動生成する CLI。

責務:
    - source image 内の文字がありそうな横長領域を推定する。
    - 推定した ROI を source case の `rois.json` へ保存する。

責務外:
    - OCR 実行、正解テキストとの対応付け、PaddleOCR 学習形式への export。
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

from ocr_dataset.paths import resolve_dataset_path
from ocr_dataset.source_cases.schema import EvaluationCase


@dataclass(frozen=True)
class RoiStrip:
    """画像内の短冊 ROI を pixel 座標と相対座標で保持する。"""

    id: str
    kind: str
    x: int
    y: int
    width: int
    height: int
    rel_x: float
    rel_y: float
    rel_width: float
    rel_height: float
    image: str


def _source_image_path(case: EvaluationCase, image_name: str | None) -> Path:
    if image_name:
        return case.case_dir / image_name
    return case.source_image


def _merge_close_bands(bands: list[tuple[int, int]], gap: int) -> list[tuple[int, int]]:
    if not bands:
        return []
    merged = [bands[0]]
    for start, end in bands[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= gap:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _find_vertical_bands(binary: np.ndarray, *, min_height: int, gap: int) -> list[tuple[int, int]]:
    row_density = (binary > 0).mean(axis=1)
    window = max(5, min_height // 2)
    kernel = np.ones(window, dtype=np.float32) / float(window)
    smoothed = np.convolve(row_density, kernel, mode="same")
    threshold = max(0.0025, float(np.percentile(smoothed, 72)) * 0.45)

    bands: list[tuple[int, int]] = []
    in_band = False
    start = 0
    for row, value in enumerate(smoothed):
        if value >= threshold and not in_band:
            start = row
            in_band = True
        elif value < threshold and in_band:
            if row - start >= min_height:
                bands.append((start, row))
            in_band = False
    if in_band and len(smoothed) - start >= min_height:
        bands.append((start, len(smoothed)))
    return _merge_close_bands(bands, gap)


def _content_bounds(binary_slice: np.ndarray, *, pad_x: int) -> tuple[int, int] | None:
    cols = np.where((binary_slice > 0).mean(axis=0) > 0.001)[0]
    if cols.size == 0:
        return None
    left = max(0, int(cols.min()) - pad_x)
    right = min(binary_slice.shape[1], int(cols.max()) + pad_x)
    if right <= left:
        return None
    return left, right


def generate_roi_strips(
    case_dir: Path,
    *,
    image_name: str | None = None,
    output: Path | None = None,
    min_height_ratio: float = 0.006,
    max_height_ratio: float = 0.13,
    pad_ratio: float = 0.006,
) -> dict:
    """source case 画像から短冊 ROI を推定し、JSON serializable な payload を返す。"""
    case = EvaluationCase(case_dir=resolve_dataset_path(case_dir))
    source_image = _source_image_path(case, image_name)
    if not source_image.exists():
        raise FileNotFoundError(f"source image not found: {source_image}")

    image = cv2.imread(str(source_image))
    if image is None:
        raise ValueError(f"failed to read source image: {source_image}")

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        35,
        13,
    )

    # Connect nearby characters into line-like horizontal strips without binding whole columns.
    kernel_w = max(9, width // 180)
    kernel_h = max(2, height // 1400)
    morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((kernel_h, kernel_w), np.uint8))

    min_height = max(10, int(height * min_height_ratio))
    max_height = max(min_height + 1, int(height * max_height_ratio))
    gap = max(6, int(height * 0.004))
    pad_y = max(4, int(height * pad_ratio))
    pad_x = max(8, int(width * pad_ratio))

    case.roi_strips_dir.mkdir(parents=True, exist_ok=True)
    for stale_strip in case.roi_strips_dir.glob("strip_*.jpg"):
        stale_strip.unlink()

    strips: list[RoiStrip] = []
    for start, end in _find_vertical_bands(morph, min_height=min_height, gap=gap):
        strip_height = end - start
        if strip_height > max_height:
            continue
        y0 = max(0, start - pad_y)
        y1 = min(height, end + pad_y)
        bounds = _content_bounds(morph[y0:y1, :], pad_x=pad_x)
        if bounds is None:
            continue
        x0, x1 = bounds
        roi_width = x1 - x0
        roi_height = y1 - y0
        if roi_width < width * 0.08 or roi_height < min_height:
            continue
        strip_id = f"strip_{len(strips) + 1:04d}"
        strip_image_name = f"{strip_id}.jpg"
        strip_image_rel = f"{case.roi_strips_dir.name}/{strip_image_name}"
        strip_image_path = case.roi_strips_dir / strip_image_name
        cv2.imwrite(str(strip_image_path), image[y0:y1, x0:x1])

        strips.append(
            RoiStrip(
                id=strip_id,
                kind="auto_strip",
                x=int(x0),
                y=int(y0),
                width=int(roi_width),
                height=int(roi_height),
                rel_x=round(x0 / width, 6),
                rel_y=round(y0 / height, 6),
                rel_width=round(roi_width / width, 6),
                rel_height=round(roi_height / height, 6),
                image=strip_image_rel,
            )
        )

    payload = {
        "schema_version": 1,
        "generated_by": "ocr_dataset.source_cases.generate_roi_strips",
        "source_image": source_image.name,
        "image_size": {"width": width, "height": height},
        "roi_strips_dir": case.roi_strips_dir.name,
        "roi_count": len(strips),
        "rois": [asdict(strip) for strip in strips],
    }

    output_path = resolve_dataset_path(output) if output else case.rois
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    """CLI 引数を読み取り、source case の `rois.json` を生成する。"""
    parser = argparse.ArgumentParser(description="Generate horizontal ROI strips from an OCR source case image.")
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--image-name", default=None, help="Image file name inside case_dir. Defaults to source case image.")
    parser.add_argument("--output", type=Path, default=None, help="Output rois.json path. Defaults to case_dir/rois.json.")
    args = parser.parse_args()

    payload = generate_roi_strips(args.case_dir, image_name=args.image_name, output=args.output)
    print(f"wrote {payload['roi_count']} ROI strips")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
