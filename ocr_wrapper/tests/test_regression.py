from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ocr_wrapper.run_ocr import run_ocr


def normalize(payload: dict) -> dict:
    return {
        "returncode": payload.get("returncode"),
        "stdout": payload.get("stdout", "").strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--golden", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--lang", default="japan")
    args = parser.parse_args()

    code = run_ocr(
        Path(args.image),
        Path(args.work),
        args.lang,
        security_gate=False,
        max_vulns=0,
    )
    if code != 0:
        print("NG: paddleocr returned non-zero")
        return 2

    golden_path = Path(args.golden)
    work_path = Path(args.work)
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    current = json.loads(work_path.read_text(encoding="utf-8"))

    if normalize(golden) != normalize(current):
        print("NG: regression detected")
        return 1

    print("OK: no regression")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
