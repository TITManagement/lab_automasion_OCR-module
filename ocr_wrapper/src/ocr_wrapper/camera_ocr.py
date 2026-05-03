"""OpenCV preview loop for running PaddleOCR from a physical camera.

責務:
    - カメラフレームを取得し、簡易プレビューを表示する。
    - offline wrapper 経由で単発 OCR を実行する。
    - GUI 版と同じ OCR 出力パーサを利用して結果表示を揃える。

責務外:
    - OCR 結果の補正や GUI 用 ROI 操作は扱わない。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import cv2

try:
    from ocr_wrapper.text_processing import parse_rec_texts
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ocr_wrapper.text_processing import parse_rec_texts


def _run_ocr(wrapper: Path, image_path: Path, lang: str) -> tuple[int, str]:
    """offline wrapper を呼び出し、stdout/stderr を後段で解析できる形に結合する。"""
    cmd = ["bash", str(wrapper), "ocr", "-i", str(image_path), "--lang", lang]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    merged = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode, merged


def main() -> int:
    """カメラプレビューを起動し、周期実行またはキー操作で OCR を実行する。"""
    parser = argparse.ArgumentParser(description="Camera OCR app (webcam/UVC) via offline paddleocr wrapper.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--lang", default="japan")
    parser.add_argument("--interval-sec", type=float, default=2.0, help="Periodic OCR interval in seconds")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()

    module_root = Path(__file__).resolve().parents[3]
    wrapper = module_root / "_post_clone_assets" / "security_ops" / "scripts" / "run_paddleocr_offline.sh"
    if not wrapper.exists():
        print(f"[ERROR] wrapper not found: {wrapper}")
        return 2

    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        print(f"[ERROR] failed to open camera index={args.camera_index}")
        return 3

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    last_texts: list[str] = []
    last_status = "Press 'o' to OCR now, 'q' to quit"
    last_ocr_at = 0.0

    print("[INFO] Camera OCR started")
    print("[INFO] key: q=quit, o=run OCR now")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                last_status = "camera read failed"
            else:
                now = time.time()
                key = cv2.waitKey(1) & 0xFF
                should_ocr = (now - last_ocr_at) >= args.interval_sec or key == ord("o")

                if should_ocr:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                        image_path = Path(f.name)
                    cv2.imwrite(str(image_path), frame)
                    code, output = _run_ocr(wrapper, image_path, args.lang)
                    image_path.unlink(missing_ok=True)

                    if code == 0:
                        texts = parse_rec_texts(output)
                        last_texts = texts[:3]
                        last_status = f"OCR OK ({len(texts)} text blocks)"
                        if texts:
                            print(f"[OCR] {' | '.join(texts[:5])}")
                        else:
                            print("[OCR] no text parsed from output")
                    else:
                        last_status = f"OCR NG (code={code})"
                        print(output.strip())
                    last_ocr_at = now

                cv2.putText(frame, last_status, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                for i, txt in enumerate(last_texts):
                    cv2.putText(
                        frame,
                        txt[:70],
                        (20, 80 + i * 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                    )
                cv2.imshow("camera-ocr", frame)

                if key == ord("q"):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
