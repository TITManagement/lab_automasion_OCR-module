from __future__ import annotations

import re
import signal
from pathlib import Path


def build_ocr_cmd(wrapper: Path, image_path: Path, lang: str, ocr_version: str) -> list[str]:
    return [
        "bash",
        str(wrapper),
        "ocr",
        "-i",
        str(image_path),
        "--lang",
        lang,
        "--ocr_version",
        ocr_version,
        "--device",
        "cpu",
        "--enable_mkldnn",
        "False",
        "--cpu_threads",
        "1",
        "--text_recognition_batch_size",
        "1",
        "--use_doc_orientation_classify",
        "False",
        "--use_doc_unwarping",
        "False",
        "--use_textline_orientation",
        "False",
    ]


def clean_log_text(text: str) -> str:
    ansi_escape = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    cleaned = ansi_escape.sub("", text)
    cleaned = cleaned.replace("\r", "\n")
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    lines = []
    skip_continuation = False
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            skip_continuation = False
            lines.append("")
            continue
        if skip_continuation:
            if "warnings.warn(warning_message)" in stripped:
                skip_continuation = False
            continue
        if "UserWarning: No ccache found" in stripped:
            skip_continuation = True
            continue
        if stripped.startswith("sysctl:"):
            continue
        if "Model files already exist. Using cached files." in stripped:
            model = re.search(r"`([^`]+)`", stripped)
            if model:
                lines.append(f"Using cached model: {Path(model.group(1)).name}")
            else:
                lines.append("Using cached model.")
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def describe_returncode(returncode: int) -> str:
    if returncode >= 0:
        return str(returncode)
    signal_number = -returncode
    try:
        signal_name = signal.Signals(signal_number).name
    except ValueError:
        signal_name = f"signal {signal_number}"
    return f"{returncode} ({signal_name})"
