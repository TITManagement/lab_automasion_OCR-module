# lab_automasion_OCR-module
<!-- README_LEVEL: L2 -->

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-MODULE-README` |
| 作成日 | `2026-05-03` |
| 作成者 | `Tinoue` |
| 最終更新日 | `2026-05-03` |
| 最終更新者 | `Codex` |
| 版数 | `v1.0` |
| 状態 | `運用中` |

<div align="center">

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## 概要

PaddleOCR を upstream/vendor として外側から利用する Camera OCR モジュールです。

このリポジトリは、[PaddleOCR](PaddleOCR/) 本体を直接コミットしません。PaddleOCR は clone 後に取得し、OCR の起動、GUI、ROI、ログ整形、後処理、オフライン運用はこのリポジトリ側の wrapper で管理します。

## 対象者

- カメラOCRを利用する運用担当者
- OCR GUI、ROI、後処理ルールを保守する開発者
- PaddleOCR のオフライン運用やセキュリティ監査を確認する検証担当者

## 依存関係

- Python: 3.11 系
- 主要ライブラリ: [pyproject.toml](pyproject.toml) を参照
- PaddleOCR: [PaddleOCR](PaddleOCR/) に別途 clone して配置
- モデルキャッシュ: PaddleOCR / PDX の標準キャッシュを利用
- カメラOCR GUI: macOS のカメラアクセス権限が必要

## 最短セットアップ

以下は、このリポジトリ直下で実行する例です。社内 pip 設定を使う環境では `PIP_CONFIG_FILE` を指定してください。不要な環境では未指定で構いません。

```bash
# 必要な環境のみ:
# export PIP_CONFIG_FILE="../config/pip/pip.conf.local"

python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

PaddleOCR はこのリポジトリには含めないため、別途取得します。

```bash
git clone https://github.com/PaddlePaddle/PaddleOCR.git PaddleOCR
```

既存運用では [main.py](main.py) が [PaddleOCR](PaddleOCR/) 配下の `.venv_paddleocr311/bin/python` を使って Camera OCR を起動します。PaddleOCR 側の仮想環境作成と依存導入は、PaddleOCR の公式手順または運用手順に従ってください。

## 主な機能

- Camera OCR GUI
- ROI ドラッグ指定と ROI プレビュー
- PaddleOCR CLI の offline-first 実行
- OCR結果の Raw / Corrected 並列表示
- 郵便番号、TEL/FAX、URL、英数字記号、mojibake の安全寄り後処理
- セキュリティ監査・オフライン運用補助

## 使い方

Camera OCR GUI:

```bash
python main.py camera-ocr-gui
```

OpenCV ベースの簡易 Camera OCR:

```bash
python main.py camera-ocr
```

単発 OCR:

```bash
python main.py ocr -i ./sample.png --lang japan
```

## 構成

```text
lab_automasion_OCR-module/
├── _post_clone_assets/
├── docs/
├── main.py
├── ocr_wrapper/
└── pyproject.toml
```

詳細:

- [ocr_wrapper/README.md](ocr_wrapper/README.md)
- [docs/ocr_support_algorithm_design.md](docs/ocr_support_algorithm_design.md)
- [_post_clone_assets/README_POST_CLONE_ASSETS.md](_post_clone_assets/README_POST_CLONE_ASSETS.md)
- [_post_clone_assets/security_ops/README_SECURITY_OFFLINE.md](_post_clone_assets/security_ops/README_SECURITY_OFFLINE.md)

## 開発者向け情報

`PaddleOCR/` は `.gitignore` で除外します。PaddleOCR 本体の修正が必要な場合は、まず upstream 側の変更として扱い、このリポジトリ側では wrapper、入力前処理、後処理、モデル選択、運用スクリプトで対応します。

## ライセンス

MIT
