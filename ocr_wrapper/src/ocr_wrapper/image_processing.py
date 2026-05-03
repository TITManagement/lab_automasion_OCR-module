from __future__ import annotations

import cv2


def enhance_serial_roi(frame):
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
    height, width = frame.shape[:2]
    left, top, right, bottom = roi
    x1 = max(0, min(width - 1, int(width * left)))
    y1 = max(0, min(height - 1, int(height * top)))
    x2 = max(x1 + 1, min(width, int(width * right)))
    y2 = max(y1 + 1, min(height, int(height * bottom)))
    return frame[y1:y2, x1:x2]
