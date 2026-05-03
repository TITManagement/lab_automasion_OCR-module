# OCR Wrapper (Non-invasive)

<!-- README_LEVEL: L2 -->

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-WRAPPER-README` |
| 作成日 | `2026-05-03` |
| 作成者 | `Tinoue` |
| 最終更新日 | `2026-05-03` |
| 最終更新者 | `Codex` |
| 版数 | `v1.0` |
| 状態 | `運用中` |

<div align="center">

PaddleOCR 本体を改変せず、CLI 実行・セキュリティゲート・回帰テストを外側で扱う OCR ラッパーです。

</div>

## 概要

このディレクトリは [../PaddleOCR](../PaddleOCR/) 本体を改変せずに利用するための外部ラッパーです。

## 対象者

- カメラOCRや単発OCRの動作確認を行う検証担当
- PaddleOCR 本体を変更せずに運用レイヤーを調整する開発者
- オフライン実行や脆弱性ゲートを確認する運用担当

## 方針

- [../PaddleOCR](../PaddleOCR/) は編集しない
- このラッパーから `paddleocr` CLI を呼び出す
- 回帰テストは golden JSON 比較で行う

## 構成

- [src/ocr_wrapper/camera_ocr_gui.py](src/ocr_wrapper/camera_ocr_gui.py): Camera OCR GUI
- [src/ocr_wrapper/camera_ocr.py](src/ocr_wrapper/camera_ocr.py): OpenCVベースの簡易カメラOCR
- [src/ocr_wrapper/run_ocr.py](src/ocr_wrapper/run_ocr.py): 単発OCR実行とセキュリティゲート
- [src/ocr_wrapper/text_processing.py](src/ocr_wrapper/text_processing.py): OCR出力解析と補正
- [src/ocr_wrapper/image_processing.py](src/ocr_wrapper/image_processing.py): ROI切り出しと画像強調
- [src/ocr_wrapper/ocr_runtime.py](src/ocr_wrapper/ocr_runtime.py): PaddleOCR CLI実行補助とログ整形

## 依存関係

- Python 3.11 系
- [../PaddleOCR](../PaddleOCR/) に作成済みの PaddleOCR 実行用仮想環境
- `opencv-python`
- `Pillow`
- `customtkinter`
- `paddleocr`
- `paddlepaddle`
- カメラOCR GUI を使う場合は macOS のカメラアクセス権限

## 最短セットアップ

`AILAB_ROOT` は AiLab ルートを指す環境変数です。以下は AiLab ルートで実行する例です。社内 pip 設定を使う環境では `PIP_CONFIG_FILE` を指定してください。不要な環境では未指定で構いません。

```bash
export AILAB_ROOT="$(pwd)"
# 必要な環境のみ:
# export PIP_CONFIG_FILE="$AILAB_ROOT/pip.conf.local"
cd "$AILAB_ROOT/lab_automation_module/lab_automasion_OCR-module/PaddleOCR"
source .venv_paddleocr311/bin/activate
```

## 単発OCR実行

```bash
cd "$AILAB_ROOT/lab_automation_module/lab_automasion_OCR-module"
python ocr_wrapper/src/ocr_wrapper/run_ocr.py \
  --image ocr_wrapper/tests/golden/sample.png \
  --out ocr_wrapper/tests/output/sample_result.json \
  --lang japan \
  --security-gate \
  --max-vulns 0
```

## セキュリティポリシー

- 許可言語のみ実行 (`japan`, `en`, `ch`)
- 実行時はオフライン強制環境変数を注入
- `--security-gate` 指定時は `pip-audit` 実行結果で fail-fast

## 回帰テスト

```bash
python ocr_wrapper/tests/test_regression.py \
  --image ocr_wrapper/tests/golden/sample.png \
  --golden ocr_wrapper/tests/golden/sample_result.golden.json \
  --work ocr_wrapper/tests/output/sample_result.current.json \
  --lang japan
```
