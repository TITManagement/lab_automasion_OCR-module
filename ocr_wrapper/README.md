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

この README は、[ocr_wrapper](.) 配下だけを対象にした Python パッケージ保守用の開発者向け説明です。

モジュール全体の初回セットアップ、利用開始、PaddleOCR vendor clone 方針、CI の入口は [../README.md](../README.md) を正本とします。この README では、[ocr_wrapper](.) 配下の責務分割、直接実行、回帰テストだけを扱います。

## README の責務境界

| README | 扱う内容 | 扱わない内容 |
| --- | --- | --- |
| [../README.md](../README.md) | [../vendor/PaddleOCR](../vendor/PaddleOCR/) を含めたモジュール全体の概要、セットアップ、利用開始、PaddleOCR の配置と扱い、CI と運用方針 | wrapper 内部関数の詳細、補正アルゴリズムの詳細 |
| [README.md](README.md) | [ocr_wrapper](.) 配下に閉じた Python パッケージ構成、各 Python モジュールの責務、開発者向け直接実行、回帰テスト | モジュール全体の導入方針、PaddleOCR vendor clone 方針、文書全体の索引 |
| [../docs/ocr_support_algorithm_design.md](../docs/ocr_support_algorithm_design.md) | OCR 補助アルゴリズムの設計 | Python パッケージ構成や実行コマンド一覧 |

## 対象者

- カメラOCRや単発OCRの動作確認を行う検証担当
- PaddleOCR 本体を変更せずに運用レイヤーを調整する開発者
- オフライン実行や脆弱性ゲートを確認する運用担当

## 方針

- [../vendor/PaddleOCR](../vendor/PaddleOCR/) は編集しない
- このラッパーから `paddleocr` CLI を呼び出す
- 回帰テストは golden JSON 比較で行う
- GUI、画像処理、OCR 実行、テキスト補正の責務を分ける

## Python モジュール構成

| ファイル | 責務 | 主な利用元 |
| --- | --- | --- |
| [src/ocr_wrapper/camera_ocr_gui.py](src/ocr_wrapper/camera_ocr_gui.py) | GUI、カメラ制御、ROI 操作、非同期 OCR 実行 | [../main.py](../main.py) の `camera-ocr-gui` |
| [src/ocr_wrapper/camera_ocr.py](src/ocr_wrapper/camera_ocr.py) | OpenCV ベースの簡易カメラ OCR | [../main.py](../main.py) の `camera-ocr` |
| [src/ocr_wrapper/run_ocr.py](src/ocr_wrapper/run_ocr.py) | 単発 OCR 実行とセキュリティゲート | `lab-ocr` console script |
| [src/ocr_wrapper/ocr_runtime.py](src/ocr_wrapper/ocr_runtime.py) | PaddleOCR CLI 実行補助とログ整形 | GUI / runner |
| [src/ocr_wrapper/image_processing.py](src/ocr_wrapper/image_processing.py) | ROI 切り出しと画像強調 | GUI / OCR 前処理 |
| [src/ocr_wrapper/text_processing.py](src/ocr_wrapper/text_processing.py) | OCR 出力解析、Raw / Corrected 生成、補正ルール | GUI / camera OCR |

## 依存関係

- Python 3.11 系
- プロジェクト直下の [../.venv_OCR](../.venv_OCR/) に作成済みの OCR 実行用仮想環境
- `opencv-python`
- `Pillow`
- `customtkinter`
- `paddleocr`
- `paddlepaddle`
- カメラOCR GUI を使う場合は macOS のカメラアクセス権限

## 最短セットアップ

通常の初回セットアップは [../README.md](../README.md) を参照してください。

wrapper を直接確認する場合は、モジュールルートで作成済みの OCR 実行用仮想環境を有効化します。以下はモジュールルートから実行する例です。PaddleOCR の vendor 配置や仮想環境作成は [../README.md](../README.md) の責務です。

```bash
# 必要な環境のみ:
# export PIP_CONFIG_FILE="./pip.conf"
source .venv_OCR/bin/activate
```

## 単発OCR実行

```bash
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

## 開発者向け情報

docstring / comment の記載規約は [../docs/dev/notes/DEVELOPER_GUIDE.md](../docs/dev/notes/DEVELOPER_GUIDE.md) を正本とします。

README の記載形式は [../../../README_STANDARD.md](../../../README_STANDARD.md) に従います。
