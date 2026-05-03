# OCR Synthetic Data

<!-- README_LEVEL: L2 -->

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-SYNTHETIC-DATA-README` |
| 作成日 | `2026-05-03` |
| 作成者 | `Tinoue` |
| 最終更新日 | `2026-05-03` |
| 最終更新者 | `Codex` |
| 版数 | `v1.0` |
| 状態 | `運用中` |

<div align="center">

OCR 評価・学習向けの synthetic data 生成と dataset export を扱う補助パッケージです。

</div>

## 概要

この README は、[ocr_synthetic_data](.) 配下だけを対象にした開発者向け説明です。

モジュール全体の初回セットアップ、PaddleOCR の配置、OCR 実行アプリの使い方は [../README.md](../README.md) を正本とします。この README では、synthetic data 生成、教師データ拡張、PaddleOCR 学習形式への export に関する責務だけを扱います。

## README の責務境界

| README | 扱う内容 | 扱わない内容 |
| --- | --- | --- |
| [../README.md](../README.md) | [../PaddleOCR](../PaddleOCR/) を含めたモジュール全体の概要、セットアップ、利用開始、CI と運用方針 | synthetic data 生成ロジックの詳細 |
| [../ocr_wrapper/README.md](../ocr_wrapper/README.md) | OCR 実行、GUI、ROI、後処理、回帰テスト | synthetic data 生成、学習形式 export |
| [README.md](README.md) | [ocr_synthetic_data](.) 配下に閉じた synthetic data 生成、教師データ拡張、PaddleOCR 学習形式 export | OCR 実行 GUI、PaddleOCR 本体の学習実行 |

## 対象者

- OCR 評価用の疑似画像を作成する開発者
- 教師データを拡張する検証担当者
- PaddleOCR fine-tuning 用 dataset export を準備する担当者

## 依存関係

- Python 3.11 系
- [../pyproject.toml](../pyproject.toml) に定義された画像処理ライブラリ
- 元画像、正解テキスト、ROI 定義を含む evaluation case

## 最短セットアップ

通常の初回セットアップは [../README.md](../README.md) を参照してください。

editable install 後、Python から package import を確認します。

```bash
python -c "import ocr_synthetic_data; print(ocr_synthetic_data.__version__)"
```

## Python モジュール構成

| ファイル | 責務 |
| --- | --- |
| [src/ocr_synthetic_data/augment.py](src/ocr_synthetic_data/augment.py) | 明るさ、ぼけ、ノイズ、傾きなどの画像変換 |
| [src/ocr_synthetic_data/case_schema.py](src/ocr_synthetic_data/case_schema.py) | evaluation case のパスと metadata 表現 |
| [src/ocr_synthetic_data/generate_variants.py](src/ocr_synthetic_data/generate_variants.py) | case から synthetic variants を生成 |
| [src/ocr_synthetic_data/export_paddleocr_dataset.py](src/ocr_synthetic_data/export_paddleocr_dataset.py) | PaddleOCR 学習形式への export |

## Source Case

synthetic data の種となる元画像、正解テキスト、ROI 定義は [datasets/source_cases](datasets/source_cases/) に保存します。

[datasets/source_cases](datasets/source_cases/) は、別母艦でも再利用する OCR データセット資産です。人が確認した正解データを保持し、synthetic variants や PaddleOCR 学習形式 export の入力にします。

例:

```text
datasets/source_cases/img_0678/
├── source.jpg
├── expected.txt
├── expected_fields.json
└── rois.json
```

`variants/` は生成物のため git 管理対象外です。

## 開発者向け情報

このパッケージは synthetic data 生成までを責務とし、PaddleOCR 本体の学習実行は扱いません。

docstring / comment の記載規約は [../docs/dev/notes/DEVELOPER_GUIDE.md](../docs/dev/notes/DEVELOPER_GUIDE.md) を正本とします。

README の記載形式は [../../../README_STANDARD.md](../../../README_STANDARD.md) に従います。
