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

PaddleOCR を upstream/vendor として [vendor](vendor/) 配下に配置し、外側の wrapper から利用する Camera OCR モジュールです。

この README は、clone 後に配置する [vendor/PaddleOCR](vendor/PaddleOCR/) を含めた [lab_automasion_OCR-module](.) 全体を対象にします。ただし、[vendor/PaddleOCR](vendor/PaddleOCR/) 本体はこのリポジトリには直接コミットしません。OCR の起動、GUI、ROI、ログ整形、後処理、オフライン運用はこのリポジトリ側の wrapper で管理します。

注意: [vendor/PaddleOCR](vendor/PaddleOCR/) は GitHub upstream から取得する別リポジトリです。upstream 追従時は [vendor/PaddleOCR](vendor/PaddleOCR/) 側で `git fetch` / `git pull` などを実施し、このリポジトリ側では変更差分を直接保持しません。PaddleOCR 更新により CLI 引数、モデル名、出力形式、依存関係が変わる可能性があるため、更新後は [ocr_wrapper](ocr_wrapper/) の起動、ログ解析、後処理、オフラインモデル確認を回帰確認してください。

この README は、[vendor/PaddleOCR](vendor/PaddleOCR/) を含むモジュール全体の入口です。初回セットアップ、利用開始、PaddleOCR の配置、運用方針、関連ドキュメントへの導線を扱います。wrapper 実装の詳細な責務分割は [ocr_wrapper/README.md](ocr_wrapper/README.md) を参照してください。

## README の責務境界

| README | 扱う内容 | 扱わない内容 |
| --- | --- | --- |
| [README.md](README.md) | [vendor/PaddleOCR](vendor/PaddleOCR/) を含めたモジュール全体の概要、セットアップ、利用開始、PaddleOCR の配置と扱い、CI と運用方針 | wrapper 内部関数の詳細、補正アルゴリズムの詳細、テストデータ別の結果 |
| [ocr_wrapper/README.md](ocr_wrapper/README.md) | [ocr_wrapper](ocr_wrapper/) 配下に閉じた Python パッケージ構成、各 Python モジュールの責務、開発者向け直接実行、回帰テスト | モジュール全体の導入方針、PaddleOCR vendor clone 方針、文書全体の索引 |
| [ocr_dataset/README.md](ocr_dataset/README.md) | [ocr_dataset](ocr_dataset/) 配下に閉じた source case 資産、ROI 定義、PaddleOCR 学習形式 export 境界 | OCR 実行 GUI、synthetic variants 生成ロジック |
| [ocr_synthetic_data/README.md](ocr_synthetic_data/README.md) | [ocr_synthetic_data](ocr_synthetic_data/) 配下に閉じた synthetic variants 生成 | OCR 実行 GUI、source case 資産の保管、PaddleOCR 学習形式 export |
| [docs/ocr_support_algorithm_design.md](docs/ocr_support_algorithm_design.md) | PaddleOCR を補助する後処理・ROI・mojibake 補正の設計 | 日常操作手順、パッケージ構成一覧 |

## 対象者

- カメラOCRを利用する運用担当者
- OCR GUI、ROI、後処理ルールを保守する開発者
- PaddleOCR のオフライン運用やセキュリティ監査を確認する検証担当者

## 依存関係

- Python: 3.11 系
- 主要ライブラリ: [pyproject.toml](pyproject.toml) を参照
- PaddleOCR: [vendor/PaddleOCR](vendor/PaddleOCR/) に別途 clone して配置
- モデルキャッシュ: PaddleOCR / PDX の標準キャッシュを利用
- カメラOCR GUI: macOS のカメラアクセス権限が必要

## 最短セットアップ

以下は、このリポジトリ直下で実行する例です。社内 pip 設定を使う環境では `PIP_CONFIG_FILE` を指定してください。不要な環境では未指定で構いません。

```bash
# 必要な環境のみ:
# export PIP_CONFIG_FILE="../config/pip/pip.conf.local"

python -m venv .venv_OCR
source .venv_OCR/bin/activate
python -m pip install -e .
```

PaddleOCR はこのリポジトリには含めないため、別途取得します。

```bash
git clone https://github.com/PaddlePaddle/PaddleOCR.git vendor/PaddleOCR
```

既存運用では [main.py](main.py) がプロジェクト直下の `.venv_OCR/bin/python` を使って Camera OCR を起動します。PaddleOCR は [vendor/PaddleOCR](vendor/PaddleOCR/) に配置し、依存関係は `.venv_OCR` に統合します。

## 主な機能

- Camera OCR GUI
- アスペクト比を維持した Camera / ROI 左右プレビュー
- マウスドラッグによる ROI 指定と ROI プレビュー
- PaddleOCR CLI の offline-first 実行
- OCR結果の Corrected / Raw 並列表示
- Auto / Off / Basic / Context の OCR 後処理モード
- 郵便番号、TEL/FAX、URL、英数字記号、mojibake の安全寄り後処理
- OCR 評価・学習向け source case 管理と synthetic variants 生成
- セキュリティ監査・オフライン運用補助

## 使い方

Camera OCR GUI:

```bash
python main.py camera-ocr-gui
```

主な操作:

- `Start`: カメラプレビュー開始
- `Stop`: カメラプレビュー停止
- `Run OCR`: 現在フレームまたは ROI に対して OCR 実行
- `ROI`: ROI 利用の有効化
- Camera プレビュー上のドラッグ操作: OCR 対象 ROI を指定
- `Auto` / `Off` / `Basic` / `Context`: Corrected OCR に適用する後処理モード

OpenCV ベースの簡易 Camera OCR:

```bash
python main.py camera-ocr
```

単発 OCR:

```bash
python main.py ocr -i ./sample.png --lang japan
```

パッケージを editable install した環境では、console script からも起動できます。
dataset 系の console script は、相対パスを [ocr_dataset](ocr_dataset/) 起点として解決します。

```bash
lab-camera-ocr-gui
lab-camera-ocr
lab-ocr --image ./sample.png --out ./sample_result.json --lang japan
lab-ocr-generate-roi-strips source_cases/img_0678
lab-ocr-prepare-source-case source_cases/img_0678
lab-ocr-source-case-gui
lab-ocr-generate-variants source_cases/img_0678
```

## 構成

```text
lab_automasion_OCR-module/
├── _post_clone_assets/
├── docs/
├── main.py
├── ocr_dataset/
├── ocr_wrapper/
├── ocr_synthetic_data/
├── vendor/
│   └── PaddleOCR/    # clone 後に配置。git 管理対象外
└── pyproject.toml
```

詳細:

- [ocr_wrapper/README.md](ocr_wrapper/README.md)
- [ocr_dataset/README.md](ocr_dataset/README.md)
- [ocr_synthetic_data/README.md](ocr_synthetic_data/README.md)
- [docs/ocr_support_algorithm_design.md](docs/ocr_support_algorithm_design.md)
- [docs/dev/notes/DEVELOPER_GUIDE.md](docs/dev/notes/DEVELOPER_GUIDE.md)
- [_post_clone_assets/README_POST_CLONE_ASSETS.md](_post_clone_assets/README_POST_CLONE_ASSETS.md)
- [_post_clone_assets/security_ops/README_SECURITY_OFFLINE.md](_post_clone_assets/security_ops/README_SECURITY_OFFLINE.md)

## 開発者向け情報

`vendor/PaddleOCR/` は `.gitignore` で除外します。PaddleOCR 本体の修正が必要な場合は、まず upstream 側の変更として扱い、このリポジトリ側では wrapper、入力前処理、後処理、モデル選択、運用スクリプトで対応します。

wrapper 側の主な責務分割:

- [camera_ocr_gui.py](ocr_wrapper/src/ocr_wrapper/camera_ocr_gui.py): GUI、カメラ制御、ROI 操作、非同期 OCR 実行
- [camera_ocr.py](ocr_wrapper/src/ocr_wrapper/camera_ocr.py): OpenCV ベースの簡易カメラ OCR
- [run_ocr.py](ocr_wrapper/src/ocr_wrapper/run_ocr.py): 単発 OCR 実行とセキュリティゲート
- [ocr_runtime.py](ocr_wrapper/src/ocr_wrapper/ocr_runtime.py): PaddleOCR CLI 実行補助とログ整形
- [image_processing.py](ocr_wrapper/src/ocr_wrapper/image_processing.py): ROI 切り出しと画像強調
- [text_processing.py](ocr_wrapper/src/ocr_wrapper/text_processing.py): OCR 出力解析、Raw / Corrected 生成、補正ルール

dataset 側の主な責務分割:

- [source_cases/schema.py](ocr_dataset/src/ocr_dataset/source_cases/schema.py): source case の標準ファイル配置
- [source_cases/generate_roi_strips.py](ocr_dataset/src/ocr_dataset/source_cases/generate_roi_strips.py): source image から短冊状 ROI 定義を生成
- [exporters/paddleocr_dataset.py](ocr_dataset/src/ocr_dataset/exporters/paddleocr_dataset.py): PaddleOCR 学習形式 export の境界

synthetic data 側の主な責務分割:

- [augment.py](ocr_synthetic_data/src/ocr_synthetic_data/augment.py): 明るさ、ぼけ、傾きなどの画像変換
- [generate_variants.py](ocr_synthetic_data/src/ocr_synthetic_data/generate_variants.py): source image から synthetic variants を生成

docstring / comment の記載規約は [docs/dev/notes/DEVELOPER_GUIDE.md](docs/dev/notes/DEVELOPER_GUIDE.md) を正本とします。

README の記載形式は [../../README_STANDARD.md](../../README_STANDARD.md) に従います。

## CI

GitHub Actions では、PR に対して editable install と Python compile check を実行します。

- [qa_gate.yml](.github/workflows/qa_gate.yml): `python -m pip install -e .` と `python -m compileall -q .`
- [agents-governance.yml](.github/workflows/agents-governance.yml): [AGENTS.md](AGENTS.md) のガバナンス記載確認
- [docs_automation.yml](.github/workflows/docs_automation.yml): README 正規化チェック

module docstring の存在検証は、現時点では CI の強制対象ではありません。運用規約は [docs/dev/notes/DEVELOPER_GUIDE.md](docs/dev/notes/DEVELOPER_GUIDE.md) に定義しています。

## ライセンス

MIT
