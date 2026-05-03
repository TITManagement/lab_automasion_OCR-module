"""CustomTkinter Camera OCR GUI for PaddleOCR wrapper operation.

責務:
    - カメラ取得画像と ROI 抽出画像を同時にプレビューする。
    - マウスドラッグで ROI を指定し、OCR 対象フレームを決める。
    - PaddleOCR の実行を worker thread へ逃がし、GUI を固着させない。
    - Raw OCR と Corrected OCR、整形済み実行ログを表示する。

責務外:
    - OCR 文字列補正、画像前処理、PaddleOCR CLI 引数の詳細は専用モジュールへ委譲する。
"""

from __future__ import annotations

import argparse
import queue
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path

import cv2
from PIL import Image, ImageTk

try:
    from ocr_wrapper.image_processing import crop_frame_by_relative_roi, enhance_serial_roi
    from ocr_wrapper.ocr_runtime import build_ocr_cmd, clean_log_text, describe_returncode
    from ocr_wrapper.text_processing import build_result_sections, parse_rec_texts
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ocr_wrapper.image_processing import crop_frame_by_relative_roi, enhance_serial_roi
    from ocr_wrapper.ocr_runtime import build_ocr_cmd, clean_log_text, describe_returncode
    from ocr_wrapper.text_processing import build_result_sections, parse_rec_texts

try:
    import customtkinter as ctk
except ModuleNotFoundError as exc:
    raise SystemExit(
        "[ERROR] customtkinter is not installed. "
        "Install with: .venv_OCR/bin/pip install customtkinter"
    ) from exc


class CameraOCRGui(ctk.CTk):
    """カメラプレビュー、ROI選択、非同期OCR実行を束ねる GUI アプリケーション。"""

    def __init__(self, camera_index: int, lang: str, ocr_version: str):
        super().__init__()
        self.title("Camera OCR")
        self.geometry("980x720")
        self.camera_index = camera_index
        self.lang = lang
        self.ocr_version = ocr_version
        self.cap: cv2.VideoCapture | None = None
        self.current_frame = None
        self.tk_image = None
        self.tk_roi_image = None
        self.last_preview_size: tuple[int, int] | None = None
        self.last_roi_preview_size: tuple[int, int] | None = None
        self.preview_image_rect: tuple[int, int, int, int] | None = None
        self.roi_drag_start: tuple[float, float] | None = None
        self.preview_after_id: str | None = None
        self.preview_paused_for_ocr = False
        self.ocr_after_id: str | None = None
        self.ocr_process: subprocess.Popen[str] | None = None
        self.ocr_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.ocr_started_at: float | None = None
        self.ocr_temp_images: list[Path] = []
        self.roi_enabled = ctk.BooleanVar(value=True)
        self.correction_mode = ctk.StringVar(value="Auto")
        self.roi_left = ctk.DoubleVar(value=0.15)
        self.roi_top = ctk.DoubleVar(value=0.12)
        self.roi_right = ctk.DoubleVar(value=0.85)
        self.roi_bottom = ctk.DoubleVar(value=0.82)
        self.is_closing = False
        self.wrapper = Path(__file__).resolve().parents[3] / "_post_clone_assets" / "security_ops" / "scripts" / "run_paddleocr_offline.sh"
        self.camera_indices = [0, 1]
        if self.camera_index not in self.camera_indices:
            self.camera_indices.insert(0, self.camera_index)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        preview_frame.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        preview_frame.grid_columnconfigure(0, weight=1, uniform="previews")
        preview_frame.grid_columnconfigure(1, weight=1, uniform="previews")
        preview_frame.grid_rowconfigure(1, weight=1)

        self.preview_title = ctk.CTkLabel(preview_frame, text="Camera")
        self.preview_title.grid(row=0, column=0, padx=(0, 6), pady=(0, 4), sticky="w")
        self.roi_preview_title = ctk.CTkLabel(preview_frame, text="ROI")
        self.roi_preview_title.grid(row=0, column=1, padx=(6, 0), pady=(0, 4), sticky="w")

        self.preview = tk.Label(preview_frame, text="No Camera", bg="black", fg="white")
        self.preview.grid(row=1, column=0, padx=(0, 6), sticky="nsew")
        self.preview.bind("<Configure>", self._on_preview_configure)
        self.preview.bind("<ButtonPress-1>", self._on_roi_drag_start)
        self.preview.bind("<B1-Motion>", self._on_roi_drag_move)
        self.preview.bind("<ButtonRelease-1>", self._on_roi_drag_end)
        self.roi_preview = tk.Label(preview_frame, text="No ROI", bg="black", fg="white")
        self.roi_preview.grid(row=1, column=1, padx=(6, 0), sticky="nsew")
        self.roi_preview.bind("<Configure>", self._on_preview_configure)

        controls = ctk.CTkFrame(self)
        controls.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        controls.grid_columnconfigure(8, weight=1)

        self.camera_var = ctk.StringVar(value=str(self.camera_index))
        self.camera_select = ctk.CTkOptionMenu(
            controls,
            values=[str(i) for i in self.camera_indices],
            variable=self.camera_var,
            command=self.on_camera_selected,
            width=130,
        )
        self.camera_select.grid(row=0, column=0, padx=8, pady=8)

        self.start_btn = ctk.CTkButton(controls, text="Start", command=self.start_camera, width=90)
        self.start_btn.grid(row=0, column=1, padx=8, pady=8)
        self.stop_btn = ctk.CTkButton(controls, text="Stop", command=self.stop_camera, width=90)
        self.stop_btn.grid(row=0, column=2, padx=8, pady=8)
        self.ocr_btn = ctk.CTkButton(controls, text="Run OCR", command=self.run_ocr, width=110)
        self.ocr_btn.grid(row=0, column=3, padx=8, pady=8)
        self.roi_checkbox = ctk.CTkCheckBox(controls, text="ROI", variable=self.roi_enabled, command=self._refresh_preview)
        self.roi_checkbox.grid(row=0, column=4, padx=8, pady=8)
        self.roi_preset_select = ctk.CTkOptionMenu(
            controls,
            values=["Center", "Full", "Top", "Bottom"],
            command=self.on_roi_preset_selected,
            width=100,
        )
        self.roi_preset_select.grid(row=0, column=5, padx=8, pady=8)

        self.correction_select = ctk.CTkOptionMenu(
            controls,
            values=["Auto", "Off", "Basic", "Context"],
            variable=self.correction_mode,
            width=110,
        )
        self.correction_select.grid(row=0, column=6, padx=8, pady=8)

        self.status = ctk.CTkLabel(controls, text="Ready")
        self.status.grid(row=0, column=7, padx=8, pady=8, sticky="w")

        self.result_label = ctk.CTkLabel(self, text="OCR Result")
        self.result_label.grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")

        result_frame = ctk.CTkFrame(self, fg_color="transparent")
        result_frame.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")
        result_frame.grid_columnconfigure(0, weight=1, uniform="ocr_results")
        result_frame.grid_columnconfigure(1, weight=1, uniform="ocr_results")

        self.corrected_result_label = ctk.CTkLabel(result_frame, text="Corrected OCR")
        self.corrected_result_label.grid(row=0, column=0, padx=(0, 6), pady=(0, 4), sticky="w")
        self.raw_result_label = ctk.CTkLabel(result_frame, text="Raw OCR")
        self.raw_result_label.grid(row=0, column=1, padx=(6, 0), pady=(0, 4), sticky="w")

        self.corrected_result_box = ctk.CTkTextbox(result_frame, height=120)
        self.corrected_result_box.grid(row=1, column=0, padx=(0, 6), sticky="ew")
        self.raw_result_box = ctk.CTkTextbox(result_frame, height=120)
        self.raw_result_box.grid(row=1, column=1, padx=(6, 0), sticky="ew")

        self.log_label = ctk.CTkLabel(self, text="Execution Log")
        self.log_label.grid(row=4, column=0, padx=12, pady=(0, 4), sticky="w")
        self.log_box = ctk.CTkTextbox(self, height=120)
        self.log_box.grid(row=5, column=0, padx=12, pady=(0, 12), sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_camera_selected(self, value: str) -> None:
        """選択されたカメラ index へ切り替え、稼働中ならプレビューを再開する。"""
        try:
            selected = int(value)
        except ValueError:
            self.status.configure(text=f"Invalid camera: {value}")
            return
        was_running = self.cap is not None and self.cap.isOpened()
        self.stop_camera()
        self.camera_index = selected
        self.status.configure(text=f"Camera selected: {selected}")
        if was_running:
            self.start_camera()

    def on_roi_preset_selected(self, value: str) -> None:
        """プリセット名から相対 ROI を設定し、現在フレームへ反映する。"""
        presets = {
            "Center": (0.15, 0.12, 0.85, 0.82),
            "Full": (0.0, 0.0, 1.0, 1.0),
            "Top": (0.10, 0.05, 0.90, 0.55),
            "Bottom": (0.10, 0.45, 0.90, 0.95),
        }
        left, top, right, bottom = presets.get(value, presets["Center"])
        self.roi_left.set(left)
        self.roi_top.set(top)
        self.roi_right.set(right)
        self.roi_bottom.set(bottom)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if self.current_frame is not None:
            self._render_preview_frame(self.current_frame)

    def _current_roi(self) -> tuple[float, float, float, float]:
        """GUI 変数上の ROI を正規化し、最小サイズを満たす相対座標として返す。"""
        left = max(0.0, min(1.0, self.roi_left.get()))
        top = max(0.0, min(1.0, self.roi_top.get()))
        right = max(0.0, min(1.0, self.roi_right.get()))
        bottom = max(0.0, min(1.0, self.roi_bottom.get()))
        if right < left:
            left, right = right, left
        if bottom < top:
            top, bottom = bottom, top
        if right - left < 0.02:
            right = min(1.0, left + 0.02)
        if bottom - top < 0.02:
            bottom = min(1.0, top + 0.02)
        self.roi_left.set(left)
        self.roi_top.set(top)
        self.roi_right.set(right)
        self.roi_bottom.set(bottom)
        return left, top, right, bottom

    def _on_roi_drag_start(self, event: tk.Event) -> None:
        point = self._preview_event_to_roi_point(event)
        if point is None:
            return
        self.roi_enabled.set(True)
        self.roi_drag_start = point
        self._set_roi_from_points(point, point)
        self.status.configure(text="ROI selecting...")
        self._refresh_preview()

    def _on_roi_drag_move(self, event: tk.Event) -> None:
        if self.roi_drag_start is None:
            return
        point = self._preview_event_to_roi_point(event)
        if point is None:
            return
        self._set_roi_from_points(self.roi_drag_start, point)
        self._refresh_preview()

    def _on_roi_drag_end(self, event: tk.Event) -> None:
        if self.roi_drag_start is None:
            return
        point = self._preview_event_to_roi_point(event)
        if point is not None:
            self._set_roi_from_points(self.roi_drag_start, point)
        self.roi_drag_start = None
        left, top, right, bottom = self._current_roi()
        self.status.configure(text=f"ROI selected: {int((right - left) * 100)}% x {int((bottom - top) * 100)}%")
        self._refresh_preview()

    def _preview_event_to_roi_point(self, event: tk.Event) -> tuple[float, float] | None:
        """黒帯を除いた実画像表示領域のマウス座標を ROI 相対座標へ変換する。"""
        if self.preview_image_rect is None:
            return None
        left, top, right, bottom = self.preview_image_rect
        if right <= left or bottom <= top:
            return None
        x = max(left, min(right, int(event.x)))
        y = max(top, min(bottom, int(event.y)))
        return (x - left) / (right - left), (y - top) / (bottom - top)

    def _set_roi_from_points(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        self.roi_left.set(min(start[0], end[0]))
        self.roi_top.set(min(start[1], end[1]))
        self.roi_right.set(max(start[0], end[0]))
        self.roi_bottom.set(max(start[1], end[1]))

    def start_camera(self) -> None:
        """実機カメラを開き、取得フレームのプレビュー更新ループを開始する。"""
        if self.is_closing:
            return
        if self.cap is not None and self.cap.isOpened():
            return
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_AVFOUNDATION)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.status.configure(text=f"Camera open failed: {self.camera_index}")
            self.cap = None
            return
        self.status.configure(text=f"Camera started: {self.camera_index}")
        self._update_preview()

    def stop_camera(self) -> None:
        """プレビュー更新を止め、カメラデバイスと表示画像の参照を解放する。"""
        if self.preview_after_id is not None:
            try:
                self.after_cancel(self.preview_after_id)
            except Exception:
                pass
            self.preview_after_id = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.tk_image = None
        self.tk_roi_image = None
        try:
            self.preview.configure(image="", text="No Camera")
            self.roi_preview.configure(image="", text="No ROI")
        except tk.TclError:
            return
        self.status.configure(text="Camera stopped")

    def _update_preview(self) -> None:
        if self.is_closing or self.cap is None or self.preview_paused_for_ocr:
            return
        ok, frame = self.cap.read()
        if ok:
            self.current_frame = frame
            self._render_preview_frame(frame)
        self.preview_after_id = self.after(30, self._update_preview)

    def _on_preview_configure(self, _event: tk.Event) -> None:
        if self.current_frame is None:
            return
        size = (
            self.preview.winfo_width(),
            self.preview.winfo_height(),
            self.roi_preview.winfo_width(),
            self.roi_preview.winfo_height(),
        )
        if size == (self.last_preview_size or ()) + (self.last_roi_preview_size or ()):
            return
        self._render_preview_frame(self.current_frame)

    def _render_preview_frame(self, frame) -> None:
        """アスペクト比を維持した Camera/ROI プレビュー画像を生成して表示する。"""
        frame_height, frame_width = frame.shape[:2]
        if frame_width <= 0 or frame_height <= 0:
            return

        canvas, image_size, paste_xy = self._frame_to_canvas(frame, self.preview)
        image_width, image_height = image_size
        paste_x, paste_y = paste_xy
        self.preview_image_rect = (paste_x, paste_y, paste_x + image_width, paste_y + image_height)
        if self.roi_enabled.get():
            left, top, right, bottom = self._current_roi()
            roi_box = (
                paste_x + int(image_width * left),
                paste_y + int(image_height * top),
                paste_x + int(image_width * right),
                paste_y + int(image_height * bottom),
            )
            self._draw_roi_box(canvas, roi_box)

        roi_frame = crop_frame_by_relative_roi(frame, self._current_roi()) if self.roi_enabled.get() else frame
        roi_canvas, _, _ = self._frame_to_canvas(roi_frame, self.roi_preview)

        self.tk_image = ImageTk.PhotoImage(image=canvas)
        self.tk_roi_image = ImageTk.PhotoImage(image=roi_canvas)
        self.last_preview_size = (self.preview.winfo_width(), self.preview.winfo_height())
        self.last_roi_preview_size = (self.roi_preview.winfo_width(), self.roi_preview.winfo_height())
        try:
            self.preview.configure(image=self.tk_image, text="")
            self.roi_preview.configure(image=self.tk_roi_image, text="")
        except tk.TclError:
            return

    def _frame_to_canvas(self, frame, widget: tk.Label) -> tuple[Image.Image, tuple[int, int], tuple[int, int]]:
        """フレームをウィジェットサイズの黒背景キャンバスへ letterbox 表示する。"""
        preview_width = widget.winfo_width()
        preview_height = widget.winfo_height()
        if preview_width <= 2 or preview_height <= 2:
            preview_width, preview_height = 470, 260

        frame_height, frame_width = frame.shape[:2]
        scale = min(preview_width / frame_width, preview_height / frame_height)
        image_width = max(1, int(frame_width * scale))
        image_height = max(1, int(frame_height * scale))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb).resize((image_width, image_height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (preview_width, preview_height), "black")
        paste_x = (preview_width - image_width) // 2
        paste_y = (preview_height - image_height) // 2
        canvas.paste(image, (paste_x, paste_y))
        return canvas, (image_width, image_height), (paste_x, paste_y)

    def _draw_roi_box(self, image: Image.Image, box: tuple[int, int, int, int]) -> None:
        pixels = image.load()
        left, top, right, bottom = box
        color = (0, 220, 255)
        for offset in range(3):
            for x in range(max(0, left), min(image.width, right)):
                if 0 <= top + offset < image.height:
                    pixels[x, top + offset] = color
                if 0 <= bottom - offset - 1 < image.height:
                    pixels[x, bottom - offset - 1] = color
            for y in range(max(0, top), min(image.height, bottom)):
                if 0 <= left + offset < image.width:
                    pixels[left + offset, y] = color
                if 0 <= right - offset - 1 < image.width:
                    pixels[right - offset - 1, y] = color

    def _pause_preview_for_ocr(self) -> None:
        """OCR 実行中に同じフレームを扱うため、プレビュー更新だけを一時停止する。"""
        self.preview_paused_for_ocr = True
        if self.preview_after_id is not None:
            try:
                self.after_cancel(self.preview_after_id)
            except Exception:
                pass
            self.preview_after_id = None

    def _resume_preview_after_ocr(self) -> None:
        """OCR 終了後、カメラが開いていればプレビュー更新を再開する。"""
        self.preview_paused_for_ocr = False
        if self.is_closing or self.cap is None or not self.cap.isOpened():
            return
        if self.preview_after_id is None:
            self._update_preview()

    def run_ocr(self) -> None:
        """現在フレームを一時画像化し、通常パスと英数字補助パスの OCR を開始する。"""
        if self.ocr_process is not None:
            self.status.configure(text="OCR already running")
            return
        if self.current_frame is None:
            self.status.configure(text="No frame")
            return
        if not self.wrapper.exists():
            self.status.configure(text="Wrapper not found")
            return
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            image_path = Path(f.name)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            serial_image_path = Path(f.name)
        self._pause_preview_for_ocr()
        ocr_frame = crop_frame_by_relative_roi(self.current_frame, self._current_roi()) if self.roi_enabled.get() else self.current_frame
        cv2.imwrite(str(image_path), ocr_frame)
        cv2.imwrite(str(serial_image_path), enhance_serial_roi(ocr_frame))
        commands = [
            ("full", build_ocr_cmd(self.wrapper, image_path, self.lang, self.ocr_version)),
            ("serial-roi", build_ocr_cmd(self.wrapper, serial_image_path, self.lang, self.ocr_version)),
        ]
        self.ocr_temp_images = [image_path, serial_image_path]
        self.ocr_started_at = time.monotonic()
        self.ocr_btn.configure(state="disabled")
        self.status.configure(text="OCR running: 0s")
        self.log_box.delete("1.0", "end")
        self.log_box.insert("1.0", "OCR started. Waiting for PaddleOCR output...")

        worker = threading.Thread(target=self._run_ocr_worker, args=(commands,), daemon=True)
        worker.start()
        self._poll_ocr()

    def _run_ocr_worker(self, commands: list[tuple[str, list[str]]]) -> None:
        """PaddleOCR subprocess を worker thread で順番に実行し、結果を queue へ渡す。"""
        try:
            combined_stdout: list[str] = []
            combined_stderr: list[str] = []
            primary_returncode = 1
            for index, (label, cmd) in enumerate(commands):
                combined_stdout.append(f"\n=== OCR pass: {label} ===\n")
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.ocr_queue.put(("process", proc))
                stdout, stderr = proc.communicate()
                if index == 0:
                    primary_returncode = proc.returncode
                combined_stdout.append(stdout or "")
                combined_stderr.append(f"\n=== OCR pass: {label} ===\n")
                combined_stderr.append(stderr or "")
                if index == 0 and proc.returncode != 0:
                    break
            self.ocr_queue.put(("done", (primary_returncode, "".join(combined_stdout), "".join(combined_stderr))))
        except Exception as exc:
            self.ocr_queue.put(("error", exc))

    def _poll_ocr(self) -> None:
        """worker thread からの OCR 進捗と完了通知を Tk event loop 上で処理する。"""
        while True:
            try:
                event, payload = self.ocr_queue.get_nowait()
            except queue.Empty:
                break
            if event == "process":
                self.ocr_process = payload  # type: ignore[assignment]
            elif event == "done":
                returncode, stdout, stderr = payload  # type: ignore[misc]
                self._finish_ocr(returncode, stdout or "", stderr or "")
                return
            elif event == "error":
                self._finish_ocr(1, "", str(payload))
                return

        if self.ocr_process is not None and self.ocr_started_at is not None:
            elapsed = int(time.monotonic() - self.ocr_started_at)
            if elapsed >= 300:
                self.status.configure(text=f"OCR running: {elapsed}s (over 5 min)")
            else:
                self.status.configure(text=f"OCR running: {elapsed}s")
        if not self.is_closing:
            self.ocr_after_id = self.after(1000, self._poll_ocr)

    def _finish_ocr(self, returncode: int, stdout: str, stderr: str) -> None:
        """一時ファイルを片付け、OCR結果・ログ・ステータスを GUI に反映する。"""
        if self.ocr_after_id is not None:
            try:
                self.after_cancel(self.ocr_after_id)
            except Exception:
                pass
            self.ocr_after_id = None
        for image_path in self.ocr_temp_images:
            image_path.unlink(missing_ok=True)
        self.ocr_temp_images = []
        self.ocr_process = None
        self.ocr_started_at = None
        self.ocr_btn.configure(state="normal")
        self._resume_preview_after_ocr()

        returncode_label = describe_returncode(returncode)
        merged = stdout + "\n" + stderr
        display_log = clean_log_text(merged)
        self.log_box.delete("1.0", "end")
        if display_log:
            self.log_box.insert("1.0", display_log[-6000:])
        else:
            self.log_box.insert("1.0", f"(no logs)\nprocess exit: {returncode_label}")
        if returncode == 0:
            texts = parse_rec_texts(merged)
            corrected_payload, raw_payload = build_result_sections(texts, self.correction_mode.get())
            self.status.configure(text=f"OCR done: {len(texts)}")
            self.corrected_result_box.delete("1.0", "end")
            self.corrected_result_box.insert("1.0", corrected_payload)
            self.raw_result_box.delete("1.0", "end")
            self.raw_result_box.insert("1.0", raw_payload)
        else:
            self.status.configure(text=f"OCR failed: {returncode_label}")
            self.corrected_result_box.delete("1.0", "end")
            self.corrected_result_box.insert("1.0", "(OCR failed)")
            self.raw_result_box.delete("1.0", "end")
            self.raw_result_box.insert("1.0", "(OCR failed)")

    def on_close(self) -> None:
        """ウィンドウ終了時に OCR process、after callback、カメラを順に解放する。"""
        self.is_closing = True
        if self.ocr_process is not None:
            self.ocr_process.terminate()
        if self.ocr_after_id is not None:
            try:
                self.after_cancel(self.ocr_after_id)
            except Exception:
                pass
            self.ocr_after_id = None
        for image_path in self.ocr_temp_images:
            image_path.unlink(missing_ok=True)
        self.ocr_temp_images = []
        self.stop_camera()
        self.destroy()


def main() -> int:
    """Camera OCR GUI の CLI 引数を読み取り、CustomTkinter アプリを起動する。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--lang", default="japan")
    parser.add_argument(
        "--ocr-version",
        default="PP-OCRv3",
        choices=["PP-OCRv3", "PP-OCRv4", "PP-OCRv5"],
        help="OCR model generation. PP-OCRv3 mobile is the safest default for camera OCR on macOS CPU.",
    )
    args = parser.parse_args()

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = CameraOCRGui(camera_index=args.camera_index, lang=args.lang, ocr_version=args.ocr_version)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
