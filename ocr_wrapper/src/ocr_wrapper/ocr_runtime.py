"""Runtime helpers for invoking PaddleOCR through the offline wrapper.

責務:
    - GUI/CLI から使う PaddleOCR コマンドラインを一貫して組み立てる。
    - PaddleOCR の冗長なログを利用者向けに圧縮する。
    - 終了コードを GUI 表示しやすい文字列へ変換する。

責務外:
    - subprocess のライフサイクル管理や OCR 結果の文字列補正は扱わない。
"""

from __future__ import annotations

import re
import signal
from pathlib import Path


def build_ocr_cmd(wrapper: Path, image_path: Path, lang: str, ocr_version: str) -> list[str]:
    """macOS CPU で安定しやすい PaddleOCR CLI 引数を組み立てる。

    Args:
        wrapper: offline-first 実行を担う shell wrapper。
        image_path: OCR 対象画像。
        lang: PaddleOCR の言語指定。
        ocr_version: `PP-OCRv3` などのモデル世代指定。

    Returns:
        `subprocess` へ渡せるコマンド配列。
    """
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
    """PaddleOCR の実行ログから GUI 判断を妨げる既知ノイズを取り除く。

    Args:
        text: stdout と stderr を結合したログ文字列。

    Returns:
        ANSI 制御文字、ccache 警告、長いモデルキャッシュパスなどを整形した表示用ログ。
    """
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
    """負の終了コードを signal 名付きで表示できる文字列へ変換する。"""
    if returncode >= 0:
        return str(returncode)
    signal_number = -returncode
    try:
        signal_name = signal.Signals(signal_number).name
    except ValueError:
        signal_name = f"signal {signal_number}"
    return f"{returncode} ({signal_name})"
