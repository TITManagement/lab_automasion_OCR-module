"""source case 作成用の CustomTkinter GUI。

責務:
    - 仕様者が選択した元画像と全文正解テキストから source case を作成する。
    - ROI / ROI label / synthetic variants / ROI OCR 候補生成を GUI 操作で実行する。

責務外:
    - ROI ごとのラベル確認、PaddleOCR 学習形式 export、学習実行。
"""

from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

from aist_guiparts import BaseApp
from ocr_dataset.paths import dataset_root
from ocr_dataset.source_cases.source_case_creator import create_source_case
from ocr_dataset.source_cases.vision_batch_ocr import DEFAULT_MODEL, process_roi_strips


def _friendly_prepare_error(message: str) -> str:
    if "source image already exists:" in message:
        path = message.split("source image already exists:", 1)[1].strip()
        return (
            "この case には同じファイル名のページ画像がすでに存在します。\n\n"
            "既存画像を使う場合は case フォルダ内の画像を選択してください。別 case として作る場合は Case ID "
            "を変更してください。置き換える場合は「既存 case を上書き」を有効にします。\n\n"
            f"既存ファイル:\n{path}"
        )
    if "expected.txt already exists:" in message:
        path = message.split("expected.txt already exists:", 1)[1].strip()
        return (
            "この case には expected.txt がすでに存在します。\n\n"
            "既存テキストを保持する場合は「既存 case を上書き」を無効のままにしてください。画面内のテキストで "
            "expected.txt を置き換える場合は上書きを有効にします。\n\n"
            f"既存ファイル:\n{path}"
        )
    if "ANTHROPIC_API_KEY" in message:
        return "ROI 短冊から OCR 候補テキストを生成するには ANTHROPIC_API_KEY が必要です。"
    if "was not found" in message and "Anthropic model" in message:
        return (
            "指定した Anthropic model が見つかりませんでした。\n\n"
            "Vision model を利用可能なモデル名に変更して、もう一度実行してください。"
            f"\n\n詳細:\n{message}"
        )
    return message


class SourceCaseCreatorGui(BaseApp):
    """元画像と全文正解テキストから source case を作成する GUI。"""

    def __init__(self) -> None:
        super().__init__(theme="light")
        self.title("OCR Source Case Builder")
        self.geometry("1040x820")
        self.minsize(920, 700)

        self.image_path = ctk.StringVar()
        self.case_id = ctk.StringVar()
        self.overwrite = ctk.BooleanVar(value=False)
        self.generate_variants = ctk.BooleanVar(value=True)
        self.generate_ocr_candidates = ctk.BooleanVar(value=False)
        self.vision_model = ctk.StringVar(value=DEFAULT_MODEL)
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._result_link_paths: dict[str, Path] = {}

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=3)
        self.grid_rowconfigure(9, weight=4)

        header = self.build_default_titlebar(
            title="OCR Source Case Builder",
            logo_height=36,
            font_size=18,
        )
        header.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")

        title = ctk.CTkLabel(self, text="OCR Source Case Builder", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=1, column=0, padx=18, pady=(8, 8), sticky="w")

        purpose = ctk.CTkLabel(
            self,
            text=(
                "OCR 学習用の元データとして使うページ画像から source case を作成します。画像コピー、全文正解テキスト保存、"
                "ROI 短冊生成を行い、必要に応じて人が確認するための OCR 候補テキストも作成します。"
            ),
            wraplength=980,
            justify="left",
        )
        purpose.grid(row=2, column=0, padx=18, pady=(0, 8), sticky="w")

        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=3, column=0, padx=18, pady=8, sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            input_frame,
            text="1. 入力: OCR 学習用元画像と全文正解テキスト",
            font=ctk.CTkFont(weight="bold"),
        ).grid(
            row=0, column=0, padx=12, pady=(12, 4), sticky="w"
        )
        ctk.CTkLabel(input_frame, text="OCR 学習用元画像").grid(row=1, column=0, padx=12, pady=12, sticky="w")
        ctk.CTkEntry(input_frame, textvariable=self.image_path).grid(row=1, column=1, padx=8, pady=12, sticky="ew")
        ctk.CTkButton(input_frame, text="画像選択", command=self._select_image, width=110).grid(
            row=1, column=2, padx=12, pady=12
        )

        expected_header = ctk.CTkFrame(self, fg_color="transparent")
        expected_header.grid(row=4, column=0, padx=18, pady=(12, 4), sticky="ew")
        expected_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(expected_header, text="元画像に対応する全文正解テキスト").grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(expected_header, text="テキスト読込", command=self._load_expected_text, width=130).grid(
            row=0, column=1, sticky="e"
        )
        self.expected_text = ctk.CTkTextbox(self, wrap="word", height=220)
        self.expected_text.grid(row=5, column=0, padx=18, pady=4, sticky="nsew")

        output_frame = ctk.CTkFrame(self)
        output_frame.grid(row=6, column=0, padx=18, pady=8, sticky="ew")
        output_frame.grid_columnconfigure(0, minsize=120)
        output_frame.grid_columnconfigure(2, weight=0)
        output_frame.grid_columnconfigure(3, weight=0)
        output_frame.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(
            output_frame,
            text="2. 生成内容: source case ファイル、ROI 短冊、OCR 候補テキスト",
            font=ctk.CTkFont(weight="bold"),
        ).grid(
            row=0, column=0, columnspan=5, padx=12, pady=(12, 4), sticky="w"
        )
        ctk.CTkLabel(output_frame, text="Case ID").grid(row=1, column=0, padx=12, pady=(10, 8), sticky="w")
        ctk.CTkEntry(output_frame, textvariable=self.case_id, placeholder_text="img_0678", width=430).grid(
            row=1, column=1, padx=8, pady=(10, 8), sticky="w"
        )
        ctk.CTkCheckBox(output_frame, text="既存 case を上書き", variable=self.overwrite).grid(
            row=1, column=2, padx=(12, 8), pady=(10, 8), sticky="w"
        )
        ctk.CTkCheckBox(output_frame, text="合成バリエーション画像を生成", variable=self.generate_variants).grid(
            row=2, column=1, padx=8, pady=(0, 8), sticky="w"
        )
        ctk.CTkCheckBox(
            output_frame,
            text="ROI 短冊から OCR 候補 .txt を生成",
            variable=self.generate_ocr_candidates,
        ).grid(row=2, column=2, columnspan=2, padx=(12, 8), pady=(0, 8), sticky="w")

        ctk.CTkLabel(output_frame, text="Vision model").grid(row=3, column=0, padx=12, pady=(0, 12), sticky="w")
        ctk.CTkEntry(output_frame, textvariable=self.vision_model, width=430).grid(
            row=3, column=1, padx=8, pady=(0, 12), sticky="w"
        )

        controls = ctk.CTkFrame(self)
        controls.grid(row=7, column=0, padx=18, pady=8, sticky="ew")
        controls.grid_columnconfigure(1, weight=1)
        self.run_button = ctk.CTkButton(controls, text="学習用データを作成", command=self._run_prepare, width=220)
        self.run_button.grid(row=0, column=0, padx=12, pady=12)
        self.status_label = ctk.CTkLabel(controls, text="待機中")
        self.status_label.grid(row=0, column=1, padx=12, pady=12, sticky="w")

        ctk.CTkLabel(self, text="3. 学習前レビュー: 人が確認すべき生成ファイル").grid(
            row=8, column=0, padx=18, pady=(12, 4), sticky="w"
        )
        self.result_text = ctk.CTkTextbox(self, wrap="word", height=240)
        self.result_text.grid(row=9, column=0, padx=18, pady=(4, 18), sticky="nsew")

    def _select_image(self) -> None:
        path = filedialog.askopenfilename(
            title="OCR 学習用元画像を選択",
            initialdir=str(dataset_root()),
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.image_path.set(path)
            if not self.case_id.get().strip():
                self.case_id.set(Path(path).stem.lower())

    def _load_expected_text(self) -> None:
        path = filedialog.askopenfilename(
            title="全文正解テキストを選択",
            initialdir=str(dataset_root()),
            filetypes=[
                ("Text files", "*.txt *.md"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            text = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            messagebox.showerror("読込失敗", "正解テキストは UTF-8 で保存されている必要があります。")
            return
        except OSError as exc:
            messagebox.showerror("読込失敗", str(exc))
            return

        self.expected_text.delete("1.0", "end")
        self.expected_text.insert("1.0", text)

    def _run_prepare(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        image_path = self.image_path.get().strip()
        case_id = self.case_id.get().strip()
        expected = self.expected_text.get("1.0", "end").strip()
        if not image_path or not case_id or not expected:
            messagebox.showerror("入力不足", "ページ画像、Case ID、全文正解テキストを入力してください。")
            return
        api_key = self._request_api_key_if_needed()
        if api_key == "":
            return

        self.run_button.configure(state="disabled")
        self.status_label.configure(text="準備中...")
        self._clear_result_links()
        self.result_text.delete("1.0", "end")

        self._worker = threading.Thread(
            target=self._worker_prepare,
            args=(
                Path(image_path),
                case_id,
                expected,
                self.overwrite.get(),
                self.generate_variants.get(),
                self.generate_ocr_candidates.get(),
                self.vision_model.get().strip() or DEFAULT_MODEL,
                api_key or None,
            ),
            daemon=True,
        )
        self._worker.start()

    def _request_api_key_if_needed(self) -> str | None:
        if not self.generate_ocr_candidates.get() or os.getenv("ANTHROPIC_API_KEY"):
            return None
        api_key = simpledialog.askstring(
            "Anthropic API key",
            "OCR 候補生成に使う Anthropic API key を入力してください。\n"
            "この key は保存せず、今回の実行中だけ使用します。",
            show="*",
            parent=self,
        )
        if api_key is None:
            return ""
        api_key = api_key.strip()
        if api_key:
            return api_key
        messagebox.showerror("API key 未設定", "OCR 候補生成には Anthropic API key が必要です。")
        return ""

    def _worker_prepare(
        self,
        image_path: Path,
        case_id: str,
        expected: str,
        overwrite: bool,
        generate_variants: bool,
        generate_ocr_candidates: bool,
        vision_model: str,
        api_key: str | None,
    ) -> None:
        try:
            self._queue.put(("status", "source case ファイルを作成中..."))
            summary = create_source_case(
                image_path=image_path,
                case_id=case_id,
                expected_text=expected,
                overwrite=overwrite,
                generate_synthetic_variants=generate_variants,
            )
            if generate_ocr_candidates:
                self._queue.put(("status", "ROI 短冊から OCR 候補テキストを生成中..."))
                summary["vision_ocr"] = process_roi_strips(
                    Path(str(summary["roi_strips_dir"])),
                    model=vision_model,
                    api_key=api_key,
                )
        except Exception as exc:  # noqa: BLE001 - GUI boundary reports any failure to user.
            self._queue.put(("error", str(exc)))
            return
        self._queue.put(("done", summary))

    def _poll_queue(self) -> None:
        try:
            event, payload = self._queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_queue)
            return

        if event == "status":
            self.status_label.configure(text=str(payload))
        elif event == "error":
            self.run_button.configure(state="normal")
            self.status_label.configure(text="失敗")
            messagebox.showerror("作成失敗", _friendly_prepare_error(str(payload)))
        else:
            self.run_button.configure(state="normal")
            self.status_label.configure(text="完了")
            self._render_result_summary(payload)

        self.after(100, self._poll_queue)

    def _clear_result_links(self) -> None:
        for tag in self._result_link_paths:
            self.result_text.tag_delete(tag)
        self._result_link_paths.clear()

    def _open_result_path(self, tag: str) -> None:
        path = self._result_link_paths[tag]
        if not path.exists():
            messagebox.showerror("ファイルを開けません", f"対象が見つかりません。\n\n{path}")
            return
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(path)], check=False)

    def _insert_result_link(self, label: str, path: object) -> None:
        link_path = Path(str(path))
        tag = f"result_link_{len(self._result_link_paths)}"
        start = self.result_text.index("insert")
        self.result_text.insert("insert", label)
        end = self.result_text.index("insert")
        self._result_link_paths[tag] = link_path
        self.result_text.tag_add(tag, start, end)
        self.result_text.tag_config(tag, foreground="#1f6aa5", underline=True)
        self.result_text.tag_bind(tag, "<Button-1>", lambda _event, link_tag=tag: self._open_result_path(link_tag))
        self.result_text.tag_bind(tag, "<Enter>", lambda _event: self.result_text.configure(cursor="hand2"))
        self.result_text.tag_bind(tag, "<Leave>", lambda _event: self.result_text.configure(cursor="xterm"))

    def _insert_result_file_line(self, label: str, path: object) -> None:
        path_obj = Path(str(path))
        self.result_text.insert("insert", f"- {label}: ")
        self._insert_result_link(path_obj.name, path_obj)
        self.result_text.insert("insert", "\n")

    def _render_result_summary(self, payload: object) -> None:
        self._clear_result_links()
        self.result_text.delete("1.0", "end")
        if not isinstance(payload, dict):
            self.result_text.insert("1.0", str(payload))
            return

        self.result_text.insert(
            "insert",
            "\n".join(
                [
                    "作成が完了しました。",
                    "",
                    f"Case ID: {payload.get('case_id', '-')}",
                    f"ROI 短冊数: {payload.get('roi_count', '-')}",
                    f"合成バリエーション画像数: {payload.get('variant_count', '-')}",
                ]
            ),
        )
        self.result_text.insert("insert", "\n")

        case_dir = payload.get("case_dir")
        if case_dir:
            self.result_text.insert("insert", "Caseフォルダ: ")
            self._insert_result_link(Path(str(case_dir)).name, case_dir)
            self.result_text.insert("insert", "\n")

        vision_ocr = payload.get("vision_ocr")
        if isinstance(vision_ocr, dict):
            self.result_text.insert(
                "insert",
                "OCR 候補 .txt: "
                f"{vision_ocr.get('processed', 0)} 件作成 / "
                f"{vision_ocr.get('skipped', 0)} 件スキップ / "
                f"{vision_ocr.get('errors', 0)} 件エラー\n",
            )
            if vision_ocr.get("summary_path"):
                self._insert_result_file_line("OCR 実行JSON", vision_ocr["summary_path"])
            if vision_ocr.get("log_path"):
                self._insert_result_file_line("OCR 実行ログ", vision_ocr["log_path"])

        self.result_text.insert("insert", "\n確認するファイル:\n")
        for label, key in [
            ("expected.txt", "expected_text"),
            ("rois.json", "rois"),
            ("roi_strips", "roi_strips_dir"),
            ("roi_labels.json", "roi_labels"),
        ]:
            path = payload.get(key)
            if path:
                self._insert_result_file_line(label, path)


def main() -> int:
    """source case creator GUI を起動する。"""
    parser = argparse.ArgumentParser(description="Create OCR source cases from an image and verified full text.")
    parser.parse_args()
    app = SourceCaseCreatorGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
