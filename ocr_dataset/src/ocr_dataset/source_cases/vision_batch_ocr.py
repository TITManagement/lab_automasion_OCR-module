"""ROI 短冊画像を vision API で一括 OCR する CLI。

責務:
    - `roi_strips/strip_XXXX.jpg` を vision OCR に渡し、同名 `.txt` に保存する。
    - source case 作成後の ROI ラベル候補作成を補助する。

責務外:
    - OCR 結果の人手検証、`roi_labels.json` への verified 反映、PaddleOCR 学習実行。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import platform
import time
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from ocr_dataset.paths import dataset_root, resolve_dataset_path


DEFAULT_MODEL = "claude-sonnet-4-6"
SUMMARY_FILE_NAME = "vision_ocr_summary.json"
LOG_FILE_NAME = "vision_ocr.log"
TRANSCRIPTION_PROMPT = (
    "この画像に写っている日本語テキストをすべて転記してください。"
    "改行や段落構造を保持してください。余分なコメントや説明は不要です。"
    "テキストのみを出力してください。"
)
PROMPT_VERSION = "roi-strip-transcription-v1"


def encode_image_to_base64(image_path: Path) -> str:
    """画像ファイルを Anthropic vision API 用の base64 文字列へ変換する。"""
    return base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")


def _media_type(image_path: Path) -> str:
    media_type, _ = mimetypes.guess_type(str(image_path))
    return media_type or "image/jpeg"


def _text_from_message_content(content: Any) -> str:
    if not content:
        return ""
    first = content[0]
    text = getattr(first, "text", None)
    if text is not None:
        return str(text)
    if isinstance(first, dict):
        return str(first.get("text", ""))
    return str(first)


def _is_model_not_found_error(exc: Exception, model: str) -> bool:
    message = str(exc)
    return "not_found_error" in message and f"model: {model}" in message


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_size(path: Path) -> dict[str, int] | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    with Image.open(path) as image:
        width, height = image.size
    return {"width": width, "height": height}


def _package_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def _portable_dataset_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(dataset_root().resolve()).as_posix()
    except ValueError:
        return str(path)


def _portable_summary(summary: dict[str, Any]) -> dict[str, Any]:
    portable = dict(summary)
    for key in ["source_dir", "summary_path", "log_path"]:
        if key in portable:
            portable[key] = _portable_dataset_path(Path(str(portable[key])))
    return portable


def _write_log(log_path: Path | None, message: str) -> None:
    if log_path is None:
        return
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{_utc_now()} {message}\n")


def _print_and_log(log_path: Path | None, message: str) -> None:
    print(message)
    _write_log(log_path, message)


def _run_metadata(source_path: Path, model: str, start_strip: int, end_strip: int, dry_run: bool) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "source_dir": _portable_dataset_path(source_path),
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(TRANSCRIPTION_PROMPT.encode("utf-8")).hexdigest(),
        "range": {"start": start_strip, "end": end_strip},
        "dry_run": dry_run,
        "python": platform.python_version(),
        "anthropic_package": _package_version("anthropic"),
    }


def transcribe_image(client: Any, image_path: Path, *, model: str = DEFAULT_MODEL) -> str:
    """1枚の ROI 短冊画像からテキスト候補を生成する。"""
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": _media_type(image_path),
                            "data": encode_image_to_base64(image_path),
                        },
                    },
                    {
                        "type": "text",
                        "text": TRANSCRIPTION_PROMPT,
                    },
                ],
            }
        ],
    )
    return _text_from_message_content(message.content).strip()


def process_roi_strips(
    source_dir: Path,
    *,
    start_strip: int = 1,
    end_strip: int | None = None,
    dry_run: bool = False,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> dict[str, Any]:
    """ROI 短冊画像を一括 OCR し、同名 `.txt` へ保存する。"""
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package is required. Install with `python -m pip install anthropic`.") from exc

    source_path = resolve_dataset_path(source_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"directory not found: {source_path}")
    if not source_path.is_dir():
        raise NotADirectoryError(f"not a directory: {source_path}")

    strip_numbers = _strip_numbers(source_path)
    if end_strip is None:
        end_strip = max(strip_numbers, default=start_strip)

    client = Anthropic(api_key=api_key) if api_key else Anthropic()
    processed = 0
    skipped = 0
    errors = 0
    started_at = _utc_now()
    run_start = time.perf_counter()
    records: list[dict[str, Any]] = []
    log_path = None if dry_run else source_path / LOG_FILE_NAME
    if log_path is not None:
        log_path.write_text("", encoding="utf-8")

    _print_and_log(log_path, f"Started vision OCR: model={model}, source_dir={source_path}")

    for strip_num in range(start_strip, end_strip + 1):
        jpg_file = source_path / f"strip_{strip_num:04d}.jpg"
        txt_file = source_path / f"strip_{strip_num:04d}.txt"
        strip_name = jpg_file.name
        record: dict[str, Any] = {
            "strip": strip_num,
            "image": strip_name,
            "output_txt": txt_file.name,
            "status": "pending",
        }

        if not jpg_file.exists():
            record["status"] = "skipped"
            record["reason"] = "image_not_found"
            records.append(record)
            _print_and_log(log_path, f"- {strip_name} not found, skipping...")
            skipped += 1
            continue

        record["image_bytes"] = jpg_file.stat().st_size
        record["image_sha256"] = _sha256_file(jpg_file)
        record["media_type"] = _media_type(jpg_file)
        image_size = _image_size(jpg_file)
        if image_size is not None:
            record["image_size"] = image_size

        print(f"Processing {strip_name}...", end=" ", flush=True)
        strip_start = time.perf_counter()
        try:
            text = transcribe_image(client, jpg_file, model=model)
            elapsed_ms = round((time.perf_counter() - strip_start) * 1000)
            record["elapsed_ms"] = elapsed_ms
            record["text_chars"] = len(text)
            record["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if dry_run:
                print(f"[DRY RUN] Would save {len(text)} characters")
                print(f"  Preview: {text[:100]}...")
                record["status"] = "dry_run"
            else:
                txt_file.write_text(text + "\n", encoding="utf-8")
                print(f"Saved to {txt_file.name} ({len(text)} chars)")
                _write_log(log_path, f"Saved {strip_name} to {txt_file.name} ({len(text)} chars, {elapsed_ms} ms)")
                record["status"] = "processed"
                processed += 1
        except Exception as exc:  # noqa: BLE001 - batch CLI reports each failed strip and continues.
            if _is_model_not_found_error(exc, model):
                raise RuntimeError(
                    f"Anthropic model '{model}' was not found. Select an available vision model and retry."
                ) from exc
            print(f"Error: {exc}")
            record["status"] = "error"
            record["elapsed_ms"] = round((time.perf_counter() - strip_start) * 1000)
            record["error"] = str(exc)
            _write_log(log_path, f"Error {strip_name}: {exc}")
            errors += 1
        finally:
            records.append(record)

    finished_at = _utc_now()
    summary: dict[str, Any] = {
        **_run_metadata(source_path, model, start_strip, end_strip, dry_run),
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_ms": round((time.perf_counter() - run_start) * 1000),
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "records": records,
    }
    if not dry_run:
        summary_path = source_path / SUMMARY_FILE_NAME
        summary["summary_path"] = str(summary_path)
        summary["log_path"] = str(log_path)
        summary_path.write_text(
            json.dumps(_portable_summary(summary), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    _print_and_log(log_path, f"Summary: {processed} processed, {skipped} skipped, {errors} errors")
    if dry_run:
        print("(Dry run mode - no files were modified)")
    return summary


def _strip_numbers(source_path: Path) -> list[int]:
    numbers: list[int] = []
    for path in source_path.glob("strip_*.jpg"):
        try:
            numbers.append(int(path.stem.removeprefix("strip_")))
        except ValueError:
            continue
    return sorted(numbers)


def main() -> int:
    """CLI 引数を読み取り、ROI 短冊画像の vision OCR を実行する。"""
    parser = argparse.ArgumentParser(description="Vision-based batch OCR for ROI strip images.")
    parser.add_argument("source_dir", type=Path, help="Path to roi_strips directory.")
    parser.add_argument("--start", type=int, default=1, help="Starting strip number. Defaults to 1.")
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="Ending strip number. Defaults to the largest strip_XXXX.jpg found.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Anthropic model name. Defaults to {DEFAULT_MODEL}.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without saving.")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        parser.error("ANTHROPIC_API_KEY environment variable is required.")

    process_roi_strips(
        args.source_dir,
        start_strip=args.start,
        end_strip=args.end,
        dry_run=args.dry_run,
        model=args.model,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
