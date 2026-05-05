"""Entry point for offline PaddleOCR execution in this module.

Usage:
    python main.py ocr -i ./sample.png --lang japan
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    module_root = Path(__file__).resolve().parent
    wrapper = module_root / "_post_clone_assets" / "security_ops" / "scripts" / "run_paddleocr_offline.sh"
    camera_app = module_root / "ocr_wrapper" / "src" / "ocr_wrapper" / "camera_ocr.py"
    camera_gui_app = module_root / "ocr_wrapper" / "src" / "ocr_wrapper" / "camera_ocr_gui.py"
    paddle_python = module_root / ".venv_OCR" / "bin" / "python"

    if len(sys.argv) > 1 and sys.argv[1] == "source-case-gui":
        if not paddle_python.exists():
            print(f"[ERROR] python runtime not found: {paddle_python}", file=sys.stderr)
            return 2
        cmd = [str(paddle_python), "-m", "ocr_dataset.source_cases.source_case_gui", *sys.argv[2:]]
        return subprocess.run(cmd).returncode

    if len(sys.argv) > 1 and sys.argv[1] == "export-paddleocr":
        if not paddle_python.exists():
            print(f"[ERROR] python runtime not found: {paddle_python}", file=sys.stderr)
            return 2
        cmd = [str(paddle_python), "-m", "ocr_dataset.exporters.paddleocr_dataset", *sys.argv[2:]]
        return subprocess.run(cmd).returncode

    if len(sys.argv) > 1 and sys.argv[1] == "camera-ocr":
        if not camera_app.exists():
            print(f"[ERROR] camera app not found: {camera_app}", file=sys.stderr)
            return 2
        if not paddle_python.exists():
            print(f"[ERROR] python runtime not found: {paddle_python}", file=sys.stderr)
            return 2
        cmd = [str(paddle_python), str(camera_app), *sys.argv[2:]]
        return subprocess.run(cmd).returncode

    if len(sys.argv) > 1 and sys.argv[1] == "camera-ocr-gui":
        if not camera_gui_app.exists():
            print(f"[ERROR] camera gui app not found: {camera_gui_app}", file=sys.stderr)
            return 2
        if not paddle_python.exists():
            print(f"[ERROR] python runtime not found: {paddle_python}", file=sys.stderr)
            return 2
        cmd = [str(paddle_python), str(camera_gui_app), *sys.argv[2:]]
        return subprocess.run(cmd).returncode

    if not wrapper.exists():
        print(f"[ERROR] wrapper not found: {wrapper}", file=sys.stderr)
        return 2

    cmd = ["bash", str(wrapper), *sys.argv[1:]]
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
