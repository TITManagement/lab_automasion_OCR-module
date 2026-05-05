"""source case 作成用の CustomTkinter GUI。

責務:
    - 使用者が選択した元画像と全文正解テキストから source case を作成する。
    - ROI / ROI label / synthetic variants / ROI OCR 候補生成を GUI 操作で実行する。
    - ROI 短冊画像と候補テキストを確認し、ROI ごとの正解ラベルを保存する。

責務外:
    - PaddleOCR 学習形式 export、学習実行。
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk
from PIL import Image

from aist_guiparts import BaseApp
from ocr_dataset.paths import dataset_root
from ocr_dataset.source_cases.source_case_creator import create_source_case
from ocr_dataset.source_cases.sync_roi_candidates import sync_roi_ocr_candidates
from ocr_dataset.source_cases.vision_batch_ocr import (
    ANTHROPIC_MODELS,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    OPENAI_MODELS,
    PROVIDER_OPENAI,
    process_roi_strips,
)

STATUS_TO_LABEL = {
    "needs_labeling": "未確認",
    "needs_review": "保留",
    "verified": "学習に使う",
    "skipped": "使わない",
}
LABEL_TO_STATUS = {label: status for status, label in STATUS_TO_LABEL.items()}
STATUS_LABELS = list(STATUS_TO_LABEL.values())
STATUS_HELP = {
    "needs_labeling": "未確認のままです。見終えたら判定を選んで保存します。",
    "needs_review": "保存すると保留として残ります。あとで再確認します。",
    "verified": "保存すると学習対象になります。text が正しいことを確認してください。",
    "skipped": "保存すると学習対象から外します。",
}


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
    if "OPENAI_API_KEY" in message:
        return "ROI 短冊から OCR 候補テキストを生成するには OPENAI_API_KEY が必要です。"
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
        self.geometry("1180x820")
        self.minsize(1080, 700)

        self.image_path = ctk.StringVar()
        self.case_id = ctk.StringVar()
        self.overwrite = ctk.BooleanVar(value=False)
        self.generate_variants = ctk.BooleanVar(value=True)
        self.generate_ocr_candidates = ctk.BooleanVar(value=False)
        self.vision_provider = ctk.StringVar(value=DEFAULT_PROVIDER)
        self.vision_model = ctk.StringVar(value=DEFAULT_MODEL)
        self.review_case_dir = ctk.StringVar()
        self.review_progress = ctk.StringVar(value="未読込")
        self.review_status = ctk.StringVar(value=STATUS_TO_LABEL["needs_labeling"])
        self.review_status_help = ctk.StringVar(value=STATUS_HELP["needs_labeling"])
        self.review_guide_visible = ctk.BooleanVar(value=False)
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._result_link_paths: dict[str, Path] = {}
        self._review_doc: dict[str, object] | None = None
        self._review_labels: list[dict[str, object]] = []
        self._review_index = 0
        self._review_image: ctk.CTkImage | None = None

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

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

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=3, column=0, padx=18, pady=(8, 18), sticky="nsew")
        tabs.add("作成")
        tabs.add("ROI確認")
        self.tabs = tabs

        create_tab = tabs.tab("作成")
        create_tab.grid_columnconfigure(0, weight=3)
        create_tab.grid_columnconfigure(1, weight=2)
        create_tab.grid_rowconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(create_tab, fg_color="transparent")
        left_frame.grid(row=0, column=0, padx=(0, 10), pady=(8, 10), sticky="nsew")
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(2, weight=1)

        review_frame = ctk.CTkFrame(create_tab)
        review_frame.grid(row=0, column=1, padx=(10, 0), pady=(8, 10), sticky="nsew")
        review_frame.grid_columnconfigure(0, weight=1)
        review_frame.grid_rowconfigure(2, weight=1)

        input_frame = ctk.CTkFrame(left_frame)
        input_frame.grid(row=0, column=0, pady=(0, 8), sticky="ew")
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

        expected_header = ctk.CTkFrame(left_frame, fg_color="transparent")
        expected_header.grid(row=1, column=0, pady=(6, 4), sticky="ew")
        expected_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(expected_header, text="元画像に対応する全文正解テキスト").grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(expected_header, text="テキスト読込", command=self._load_expected_text, width=130).grid(
            row=0, column=1, sticky="e"
        )
        self.expected_text = ctk.CTkTextbox(left_frame, wrap="word", height=180)
        self.expected_text.grid(row=2, column=0, pady=(0, 8), sticky="nsew")

        output_frame = ctk.CTkFrame(left_frame)
        output_frame.grid(row=3, column=0, pady=8, sticky="ew")
        output_frame.grid_columnconfigure(0, minsize=120)
        output_frame.grid_columnconfigure(1, weight=1)
        output_frame.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(
            output_frame,
            text="2. 生成内容: source case ファイル、ROI 短冊、OCR 候補テキスト",
            font=ctk.CTkFont(weight="bold"),
        ).grid(
            row=0, column=0, columnspan=3, padx=12, pady=(12, 4), sticky="w"
        )
        ctk.CTkLabel(output_frame, text="Case ID").grid(row=1, column=0, padx=12, pady=(10, 8), sticky="w")
        ctk.CTkEntry(output_frame, textvariable=self.case_id, placeholder_text="img_0678").grid(
            row=1, column=1, padx=8, pady=(10, 8), sticky="ew"
        )
        ctk.CTkCheckBox(output_frame, text="既存 case を上書き", variable=self.overwrite).grid(
            row=1, column=2, padx=(12, 8), pady=(10, 8), sticky="w"
        )
        ctk.CTkCheckBox(output_frame, text="学習用の水増し画像を生成", variable=self.generate_variants).grid(
            row=2, column=1, padx=8, pady=(0, 8), sticky="w"
        )
        ctk.CTkCheckBox(
            output_frame,
            text="ROI 短冊から OCR 候補 .txt を生成",
            variable=self.generate_ocr_candidates,
        ).grid(row=2, column=2, padx=(12, 8), pady=(0, 8), sticky="w")

        ctk.CTkLabel(output_frame, text="Vision provider").grid(row=3, column=0, padx=12, pady=(0, 8), sticky="w")
        ctk.CTkOptionMenu(
            output_frame,
            variable=self.vision_provider,
            values=["Anthropic", "OpenAI"],
            command=self._change_vision_provider,
        ).grid(row=3, column=1, padx=8, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(output_frame, text="Vision model").grid(row=4, column=0, padx=12, pady=(0, 12), sticky="w")
        self.vision_model_menu = ctk.CTkOptionMenu(
            output_frame,
            variable=self.vision_model,
            values=ANTHROPIC_MODELS,
        )
        self.vision_model_menu.grid(
            row=4, column=1, padx=8, pady=(0, 12), sticky="ew"
        )

        controls = ctk.CTkFrame(left_frame)
        controls.grid(row=4, column=0, pady=(8, 0), sticky="ew")
        controls.grid_columnconfigure(1, weight=1)
        self.run_button = ctk.CTkButton(controls, text="学習用データを作成", command=self._run_prepare, width=220)
        self.run_button.grid(row=0, column=0, padx=12, pady=12)
        self.status_label = ctk.CTkLabel(controls, text="待機中")
        self.status_label.grid(row=0, column=1, padx=12, pady=12, sticky="w")

        ctk.CTkLabel(
            review_frame,
            text="3. 作成結果",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        ctk.CTkLabel(
            review_frame,
            text=(
                "作成後は ROI確認 タブで短冊画像と candidate_text を確認し、"
                "正しい文字列を text に保存します。"
            ),
            wraplength=430,
            justify="left",
        ).grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.result_text = ctk.CTkTextbox(review_frame, wrap="word", height=420)
        self.result_text.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.result_text.insert(
            "1.0",
            "作成後、ここに確認対象ファイルへのリンクが表示されます。",
        )
        self._build_review_tab(tabs.tab("ROI確認"))

    def _build_review_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(2, weight=1)

        loader = ctk.CTkFrame(tab)
        loader.grid(row=0, column=0, columnspan=2, padx=8, pady=(8, 10), sticky="ew")
        loader.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(loader, text="caseフォルダ（roi_labels.json / roi_strips）").grid(
            row=0, column=0, padx=12, pady=10, sticky="w"
        )
        ctk.CTkEntry(loader, textvariable=self.review_case_dir).grid(row=0, column=1, padx=8, pady=10, sticky="ew")
        ctk.CTkButton(loader, text="caseフォルダ選択", command=self._select_review_case, width=130).grid(
            row=0, column=2, padx=(8, 4), pady=10
        )
        ctk.CTkButton(loader, text="読込", command=self._load_review_case, width=90).grid(
            row=0, column=3, padx=(4, 12), pady=10
        )

        guide = ctk.CTkFrame(tab)
        guide.grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 8), sticky="ew")
        guide.grid_columnconfigure(0, weight=1)
        guide_header = ctk.CTkFrame(guide, fg_color="transparent")
        guide_header.grid(row=0, column=0, padx=12, pady=8, sticky="w")
        ctk.CTkLabel(
            guide_header,
            text="ラベル入力の考え方",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        self.review_guide_button = ctk.CTkButton(
            guide_header,
            text="表示",
            width=72,
            command=self._toggle_review_guide,
        )
        self.review_guide_button.grid(row=0, column=1, padx=(10, 0), sticky="w")

        self.review_guide_detail = ctk.CTkLabel(
            guide,
            text=(
                "text には、この短冊画像をOCRしたときに返ってほしい正解文字列を入れます。"
                "元ページの見た目レイアウトを無理に再現せず、画像内で読める順序を保ちます。"
                "自然な行区切りの改行は残し、位置合わせ用の空白や余分な空行は入れすぎないでください。"
                "2段組みなら左段を上から下、次に右段を上から下の順に書きます。"
                "text が空の場合は candidate_text を仮入力しますが、verified にする前に必ず画像と照合してください。"
                "段組みや別文脈が混ざる場合は、文字列を工夫するよりROI分割を見直す方が有効です。"
            ),
            wraplength=1040,
            justify="left",
        )

        image_panel = ctk.CTkFrame(tab)
        image_panel.grid(row=2, column=0, padx=(8, 6), pady=(0, 8), sticky="nsew")
        image_panel.grid_columnconfigure(0, weight=1)
        image_panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            image_panel,
            text="ROI 短冊画像",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")
        self.roi_image_label = ctk.CTkLabel(image_panel, text="case を読み込んでください")
        self.roi_image_label.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

        edit_panel = ctk.CTkFrame(tab)
        edit_panel.grid(row=2, column=1, padx=(6, 8), pady=(0, 8), sticky="nsew")
        edit_panel.grid_columnconfigure(0, weight=1)
        edit_panel.grid_rowconfigure(6, weight=1)

        top_line = ctk.CTkFrame(edit_panel, fg_color="transparent")
        top_line.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        top_line.grid_columnconfigure(0, weight=1)
        self.roi_id_label = ctk.CTkLabel(top_line, text="ROI未選択", font=ctk.CTkFont(weight="bold"))
        self.roi_id_label.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top_line, textvariable=self.review_progress).grid(row=0, column=1, sticky="e")

        nav = ctk.CTkFrame(edit_panel, fg_color="transparent")
        nav.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")
        nav.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(nav, text="前へ", command=self._previous_review_label, width=90).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(nav, text="次へ", command=self._next_review_label, width=90).grid(row=0, column=2, sticky="e")

        ctk.CTkLabel(edit_panel, text="candidate_text").grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        self.candidate_text = ctk.CTkTextbox(edit_panel, wrap="word", height=105)
        self.candidate_text.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.candidate_text.configure(state="disabled")

        ctk.CTkButton(
            edit_panel,
            text="candidate_text を text にコピー",
            command=self._copy_candidate_to_text,
        ).grid(row=4, column=0, padx=12, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(edit_panel, text="text（学習に使う確定文字列）").grid(
            row=5, column=0, padx=12, pady=(0, 4), sticky="w"
        )
        self.label_text = ctk.CTkTextbox(edit_panel, wrap="word", height=145)
        self.label_text.grid(row=6, column=0, padx=12, pady=(0, 8), sticky="nsew")

        status_row = ctk.CTkFrame(edit_panel, fg_color="transparent")
        status_row.grid(row=7, column=0, padx=12, pady=(0, 8), sticky="ew")
        status_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(status_row, text="ROI判定").grid(row=0, column=0, sticky="w")
        ctk.CTkOptionMenu(
            status_row,
            variable=self.review_status,
            values=STATUS_LABELS,
            command=lambda _choice: self._update_review_status_help(),
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")
        ctk.CTkLabel(
            edit_panel,
            textvariable=self.review_status_help,
            text_color="#555555",
            wraplength=430,
            justify="left",
        ).grid(row=8, column=0, padx=12, pady=(0, 8), sticky="ew")

        actions = ctk.CTkFrame(edit_panel, fg_color="transparent")
        actions.grid(row=9, column=0, padx=12, pady=(0, 12), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(actions, text="保存", command=self._save_current_review_label).grid(
            row=0, column=0, padx=(0, 4), sticky="ew"
        )
        self.save_next_button = ctk.CTkButton(
            actions,
            text="保存して次へ",
            command=self._save_and_next_review_label,
        )
        self.save_next_button.grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def _toggle_review_guide(self) -> None:
        visible = not self.review_guide_visible.get()
        self.review_guide_visible.set(visible)
        if visible:
            self.review_guide_detail.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")
            self.review_guide_button.configure(text="非表示")
        else:
            self.review_guide_detail.grid_remove()
            self.review_guide_button.configure(text="表示")

    def _change_vision_provider(self, provider: str) -> None:
        values = OPENAI_MODELS if provider == PROVIDER_OPENAI else ANTHROPIC_MODELS
        self.vision_model_menu.configure(values=values)
        self.vision_model.set(values[0])

    def _select_review_case(self) -> None:
        path = filedialog.askdirectory(
            title="source case フォルダを選択",
            initialdir=str(dataset_root() / "source_cases"),
        )
        if path:
            self.review_case_dir.set(path)

    def _load_review_case(self) -> None:
        case_dir_text = self.review_case_dir.get().strip()
        if not case_dir_text:
            messagebox.showerror("読込失敗", "source case フォルダを指定してください。")
            return
        case_dir = Path(case_dir_text).expanduser()
        if not case_dir.exists() or not case_dir.is_dir():
            messagebox.showerror("読込失敗", f"source case フォルダが見つかりません。\n\n{case_dir}")
            return

        labels_path = case_dir / "roi_labels.json"
        if not labels_path.exists():
            messagebox.showerror("読込失敗", f"roi_labels.json が見つかりません。\n\n{labels_path}")
            return

        try:
            doc = json.loads(labels_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("読込失敗", str(exc))
            return

        labels = doc.get("labels")
        if not isinstance(labels, list):
            messagebox.showerror("読込失敗", "roi_labels.json の labels が配列ではありません。")
            return

        self._review_doc = doc
        self._review_labels = [label for label in labels if isinstance(label, dict)]
        self._review_index = 0
        self._render_current_review_label()

    def _render_current_review_label(self) -> None:
        if not self._review_labels:
            self.review_progress.set("0/0")
            self.roi_id_label.configure(text="ROIなし")
            self.roi_image_label.configure(image=None, text="ROI label がありません")
            self._set_textbox_text(self.candidate_text, "", disabled=True)
            self._set_textbox_text(self.label_text, "")
            self.review_status.set(STATUS_TO_LABEL["needs_labeling"])
            self._update_review_status_help()
            self.save_next_button.configure(text="保存して次へ")
            return

        label = self._review_labels[self._review_index]
        roi_id = str(label.get("roi_id", "-"))
        image_rel = str(label.get("image", ""))
        candidate = str(label.get("candidate_text", ""))
        text = str(label.get("text", ""))
        if not text and candidate:
            text = candidate
        status = str(label.get("status", "needs_labeling"))
        if status not in {"needs_labeling", "needs_review", "verified", "skipped"}:
            status = "needs_labeling"

        self.roi_id_label.configure(text=roi_id)
        self.review_progress.set(self._review_progress_text())
        self.review_status.set(STATUS_TO_LABEL[status])
        self._update_review_status_help()
        self._set_textbox_text(self.candidate_text, candidate, disabled=True)
        self._set_textbox_text(self.label_text, text)
        self._render_roi_image(Path(self.review_case_dir.get()) / image_rel)
        self.save_next_button.configure(text="保存して完了" if self._is_last_review_label() else "保存して次へ")

    def _render_roi_image(self, image_path: Path) -> None:
        if not image_path.exists():
            self._review_image = None
            self.roi_image_label.configure(image=None, text=f"画像が見つかりません\n{image_path.name}")
            return
        try:
            image = Image.open(image_path)
        except OSError as exc:
            self._review_image = None
            self.roi_image_label.configure(image=None, text=f"画像を開けません\n{exc}")
            return

        image.thumbnail((640, 420))
        self._review_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        self.roi_image_label.configure(image=self._review_image, text="")

    def _set_textbox_text(self, textbox: ctk.CTkTextbox, text: str, *, disabled: bool = False) -> None:
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        if text:
            textbox.insert("1.0", text)
        textbox.configure(state="disabled" if disabled else "normal")

    def _review_progress_text(self) -> str:
        total = len(self._review_labels)
        counts = {
            "needs_labeling": 0,
            "needs_review": 0,
            "verified": 0,
            "skipped": 0,
        }
        for label in self._review_labels:
            status = str(label.get("status", "needs_labeling"))
            counts[status if status in counts else "needs_labeling"] += 1
        decided = counts["verified"] + counts["skipped"]
        return (
            f"{self._review_index + 1}/{total}  判定済 {decided}/{total}"
            f"（採用{counts['verified']}・除外{counts['skipped']}・"
            f"未{counts['needs_labeling']}・保{counts['needs_review']}）"
        )

    def _is_last_review_label(self) -> bool:
        return bool(self._review_labels) and self._review_index >= len(self._review_labels) - 1

    def _selected_review_status(self) -> str:
        selected = self.review_status.get()
        if selected in LABEL_TO_STATUS:
            return LABEL_TO_STATUS[selected]
        if selected in STATUS_TO_LABEL:
            return selected
        return "needs_labeling"

    def _update_review_status_help(self) -> None:
        self.review_status_help.set(STATUS_HELP[self._selected_review_status()])

    def _copy_candidate_to_text(self) -> None:
        if not self._review_labels:
            return
        candidate = self.candidate_text.get("1.0", "end").strip()
        self._set_textbox_text(self.label_text, candidate)

    def _previous_review_label(self) -> None:
        if not self._review_labels:
            return
        self._store_current_review_label()
        self._review_index = max(0, self._review_index - 1)
        self._render_current_review_label()

    def _next_review_label(self) -> None:
        if not self._review_labels:
            return
        self._store_current_review_label()
        self._review_index = min(len(self._review_labels) - 1, self._review_index + 1)
        self._render_current_review_label()

    def _store_current_review_label(self) -> None:
        if not self._review_labels:
            return
        label = self._review_labels[self._review_index]
        label["text"] = self.label_text.get("1.0", "end").strip()
        label["status"] = self._selected_review_status()

    def _save_current_review_label(self) -> bool:
        if not self._review_labels or self._review_doc is None:
            messagebox.showerror("保存失敗", "保存する ROI label が読み込まれていません。")
            return False
        if self._selected_review_status() == "verified" and not self.label_text.get("1.0", "end").strip():
            messagebox.showerror(
                "保存失敗",
                "ROI判定を「学習に使う」にする場合は、text（学習に使う確定文字列）を入力してください。",
            )
            return False
        self._store_current_review_label()
        labels_path = Path(self.review_case_dir.get()) / "roi_labels.json"
        try:
            labels_path.write_text(
                json.dumps(self._review_doc, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            messagebox.showerror("保存失敗", str(exc))
            return False
        self.review_progress.set(self._review_progress_text())
        return True

    def _save_and_next_review_label(self) -> None:
        if not self._save_current_review_label():
            return
        if self._is_last_review_label():
            self._show_review_complete_message()
            return
        self._next_review_label()

    def _show_review_complete_message(self) -> None:
        messagebox.showinfo(
            "ROI確認完了",
            (
                "ROI確認を最後まで保存しました。\n\n"
                "次に確認してください:\n"
                "- verified 件数\n"
                "- needs_labeling / needs_review の残り\n"
                "- roi_labels.json の text\n\n"
                "verified のROIだけが学習対象です。"
            ),
        )

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
                self.vision_provider.get(),
                self.vision_model.get().strip() or DEFAULT_MODEL,
                api_key or None,
            ),
            daemon=True,
        )
        self._worker.start()

    def _request_api_key_if_needed(self) -> str | None:
        provider = self.vision_provider.get()
        env_name = "OPENAI_API_KEY" if provider == PROVIDER_OPENAI else "ANTHROPIC_API_KEY"
        if not self.generate_ocr_candidates.get() or os.getenv(env_name):
            return None
        api_key = simpledialog.askstring(
            f"{provider} API key",
            f"OCR 候補生成に使う {provider} API key を入力してください。\n"
            "この key は保存せず、今回の実行中だけ使用します。",
            show="*",
            parent=self,
        )
        if api_key is None:
            return ""
        api_key = api_key.strip()
        if api_key:
            return api_key
        messagebox.showerror("API key 未設定", f"OCR 候補生成には {provider} API key が必要です。")
        return ""

    def _worker_prepare(
        self,
        image_path: Path,
        case_id: str,
        expected: str,
        overwrite: bool,
        generate_variants: bool,
        generate_ocr_candidates: bool,
        vision_provider: str,
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
                    provider=vision_provider,
                    model=vision_model,
                    api_key=api_key,
                    progress_callback=lambda current, total: self._queue.put(
                        ("status", f"OCR 候補生成中... {current}/{total}")
                    ),
                )
                self._queue.put(("status", "OCR 候補を roi_labels.json に同期中..."))
                summary["roi_candidate_sync"] = sync_roi_ocr_candidates(Path(str(summary["case_dir"])))
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
                    f"学習用の水増し画像数: {payload.get('variant_count', '-')}",
                ]
            ),
        )
        self.result_text.insert("insert", "\n")

        case_dir = payload.get("case_dir")
        if case_dir:
            self.review_case_dir.set(str(case_dir))
            self._load_review_case()
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

        candidate_sync = payload.get("roi_candidate_sync")
        if isinstance(candidate_sync, dict):
            self.result_text.insert(
                "insert",
                "roi_labels.json 候補同期: "
                f"{candidate_sync.get('updated', 0)} 件更新 / "
                f"{candidate_sync.get('unchanged', 0)} 件変更なし / "
                f"{candidate_sync.get('missing', 0)} 件候補なし\n",
            )

        self.result_text.insert("insert", "\n次に確認するもの:\n")
        for label, key, description in [
            ("ROI確認タブ", "roi_labels", "短冊画像と candidate_text を見比べ、text/status を保存する"),
            ("roi_strips", "roi_strips_dir", "候補 .txt と短冊画像の実ファイル。必要時のみ確認"),
            ("expected.txt", "expected_text", "ページ全体の全文正解を確認する"),
            ("rois.json", "rois", "ROI分割定義。必要時のみ確認"),
        ]:
            path = payload.get(key)
            if path:
                self.result_text.insert("insert", f"- {label}: ")
                self._insert_result_link(Path(str(path)).name, path)
                self.result_text.insert("insert", f" - {description}\n")


def main() -> int:
    """source case creator GUI を起動する。"""
    parser = argparse.ArgumentParser(description="Create OCR source cases from an image and verified full text.")
    parser.parse_args()
    app = SourceCaseCreatorGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
