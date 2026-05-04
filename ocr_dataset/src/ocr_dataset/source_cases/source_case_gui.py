"""source case 作成用の CustomTkinter GUI。

責務:
    - 仕様者が選択した元画像と全文正解テキストから source case を作成する。
    - ROI / ROI label / synthetic variants 生成を GUI 操作で実行する。

責務外:
    - ROI ごとのラベル確認、PaddleOCR 学習形式 export、学習実行。
"""

from __future__ import annotations

import argparse
import json
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ocr_dataset.paths import dataset_root
from ocr_dataset.source_cases.source_case_creator import create_source_case


class SourceCaseCreatorGui(ctk.CTk):
    """元画像と全文正解テキストから source case を作成する GUI。"""

    def __init__(self) -> None:
        super().__init__()
        self.title("Source Case Creator")
        self.geometry("1040x760")
        self.minsize(920, 640)

        self.image_path = ctk.StringVar()
        self.case_id = ctk.StringVar()
        self.overwrite = ctk.BooleanVar(value=False)
        self.generate_variants = ctk.BooleanVar(value=True)
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=3)
        self.grid_rowconfigure(6, weight=2)

        title = ctk.CTkLabel(self, text="Source Case Creator", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, padx=18, pady=(18, 8), sticky="w")

        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, padx=18, pady=8, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="Image").grid(row=0, column=0, padx=12, pady=12, sticky="w")
        ctk.CTkEntry(form, textvariable=self.image_path).grid(row=0, column=1, padx=8, pady=12, sticky="ew")
        ctk.CTkButton(form, text="Select", command=self._select_image, width=110).grid(row=0, column=2, padx=12, pady=12)

        ctk.CTkLabel(form, text="Case ID").grid(row=1, column=0, padx=12, pady=12, sticky="w")
        ctk.CTkEntry(form, textvariable=self.case_id, placeholder_text="img_0678").grid(
            row=1, column=1, padx=8, pady=12, sticky="ew"
        )
        ctk.CTkCheckBox(form, text="Overwrite existing case", variable=self.overwrite).grid(
            row=1, column=2, padx=12, pady=12, sticky="w"
        )

        ctk.CTkCheckBox(form, text="Generate synthetic variants", variable=self.generate_variants).grid(
            row=2, column=1, padx=8, pady=(0, 12), sticky="w"
        )

        expected_header = ctk.CTkFrame(self, fg_color="transparent")
        expected_header.grid(row=2, column=0, padx=18, pady=(12, 4), sticky="ew")
        expected_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(expected_header, text="Expected Text").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(expected_header, text="Load Text", command=self._load_expected_text, width=120).grid(
            row=0, column=1, sticky="e"
        )
        self.expected_text = ctk.CTkTextbox(self, wrap="word", height=220)
        self.expected_text.grid(row=3, column=0, padx=18, pady=4, sticky="nsew")

        controls = ctk.CTkFrame(self)
        controls.grid(row=4, column=0, padx=18, pady=8, sticky="ew")
        controls.grid_columnconfigure(1, weight=1)
        self.run_button = ctk.CTkButton(controls, text="Prepare Source Case", command=self._run_prepare, width=200)
        self.run_button.grid(row=0, column=0, padx=12, pady=12)
        self.status_label = ctk.CTkLabel(controls, text="Ready")
        self.status_label.grid(row=0, column=1, padx=12, pady=12, sticky="w")

        ctk.CTkLabel(self, text="Result").grid(row=5, column=0, padx=18, pady=(12, 4), sticky="w")
        self.result_text = ctk.CTkTextbox(self, wrap="none", height=160)
        self.result_text.grid(row=6, column=0, padx=18, pady=(4, 18), sticky="nsew")

    def _select_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select source image",
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
            title="Select expected text",
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
            messagebox.showerror("Load failed", "Expected text must be UTF-8 encoded.")
            return
        except OSError as exc:
            messagebox.showerror("Load failed", str(exc))
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
            messagebox.showerror("Missing input", "Image, Case ID, and Expected Text are required.")
            return

        self.run_button.configure(state="disabled")
        self.status_label.configure(text="Preparing...")
        self.result_text.delete("1.0", "end")

        self._worker = threading.Thread(
            target=self._worker_prepare,
            args=(Path(image_path), case_id, expected, self.overwrite.get(), self.generate_variants.get()),
            daemon=True,
        )
        self._worker.start()

    def _worker_prepare(
        self,
        image_path: Path,
        case_id: str,
        expected: str,
        overwrite: bool,
        generate_variants: bool,
    ) -> None:
        try:
            summary = create_source_case(
                image_path=image_path,
                case_id=case_id,
                expected_text=expected,
                overwrite=overwrite,
                generate_synthetic_variants=generate_variants,
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

        self.run_button.configure(state="normal")
        if event == "error":
            self.status_label.configure(text="Failed")
            messagebox.showerror("Prepare failed", str(payload))
        else:
            self.status_label.configure(text="Done")
            self.result_text.insert("1.0", json.dumps(payload, ensure_ascii=False, indent=2))

        self.after(100, self._poll_queue)


def main() -> int:
    """source case creator GUI を起動する。"""
    parser = argparse.ArgumentParser(description="Create OCR source cases from an image and verified full text.")
    parser.parse_args()
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = SourceCaseCreatorGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
