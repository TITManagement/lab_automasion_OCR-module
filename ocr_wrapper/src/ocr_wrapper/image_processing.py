"""Image preprocessing helpers for the camera OCR wrapper.

責務:
    - GUI で選択された ROI を元フレーム座標へ安全に写像する。
    - 英数字や記号列を拾う補助 OCR パス向けに画像を強調する。

責務外:
    - OCR 実行、文字列補正、GUI 状態管理は扱わない。
"""

from __future__ import annotations

import cv2


def enhance_serial_roi(frame):
    """英数字記号列の補助 OCR パス向けに、ROI 内部を拡大・強調する。

    Args:
        frame: OpenCV の BGR 画像。通常はユーザー指定 ROI 後のフレーム。

    Returns:
        コントラスト強調とシャープ化を施した画像。切り出し不能な場合は元画像。
    """
    height, width = frame.shape[:2]
    x1, x2 = int(width * 0.22), int(width * 0.88)
    y1, y2 = int(height * 0.22), int(height * 0.58)
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return frame
    scale = 3
    roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
    sharpened = cv2.addWeighted(enhanced, 1.6, blurred, -0.6, 0)
    return sharpened


def crop_frame_by_relative_roi(frame, roi: tuple[float, float, float, float]):
    """相対座標 ROI をフレーム内へクランプし、OCR 対象画像を切り出す。

    Args:
        frame: OpenCV の BGR 画像。
        roi: `(left, top, right, bottom)` 形式の相対座標。各値は 0.0 から 1.0 を想定する。

    Returns:
        フレーム境界内へ収めた ROI 切り出し画像。
    """
    height, width = frame.shape[:2]
    left, top, right, bottom = roi
    x1 = max(0, min(width - 1, int(width * left)))
    y1 = max(0, min(height - 1, int(height * top)))
    x2 = max(x1 + 1, min(width, int(width * right)))
    y2 = max(y1 + 1, min(height, int(height * bottom)))
    return frame[y1:y2, x1:x2]
