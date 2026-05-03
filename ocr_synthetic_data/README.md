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

OCR 評価・学習向けの synthetic data 生成だけを扱う補助パッケージです。

</div>

## 概要

この README は、[ocr_synthetic_data](.) 配下だけを対象にした開発者向け説明です。

モジュール全体の初回セットアップ、PaddleOCR の配置、OCR 実行アプリの使い方は [../README.md](../README.md) を正本とします。この README では、source case から synthetic variants を作る処理だけを扱います。

## README の責務境界

| README | 扱う内容 | 扱わない内容 |
| --- | --- | --- |
| [../README.md](../README.md) | [../vendor/PaddleOCR](../vendor/PaddleOCR/) を含めたモジュール全体の概要、セットアップ、利用開始、CI と運用方針 | synthetic data 生成ロジックの詳細 |
| [../ocr_wrapper/README.md](../ocr_wrapper/README.md) | OCR 実行、GUI、ROI、後処理、回帰テスト | synthetic data 生成、学習形式 export |
| [../ocr_dataset/README.md](../ocr_dataset/README.md) | source case 資産、ROI 定義、PaddleOCR 学習形式 export 境界 | synthetic variants 生成ロジック |
| [README.md](README.md) | [ocr_synthetic_data](.) 配下に閉じた synthetic variants 生成 | OCR 実行 GUI、source case 資産の保管、PaddleOCR 学習形式 export |

## 対象者

- OCR 評価用の疑似画像を作成する開発者
- 教師データを拡張する検証担当者

## 依存関係

- Python 3.11 系
- [../pyproject.toml](../pyproject.toml) に定義された画像処理ライブラリ
- [../ocr_dataset/source_cases](../ocr_dataset/source_cases/) に保存された source case

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
| [src/ocr_synthetic_data/generate_variants.py](src/ocr_synthetic_data/generate_variants.py) | source case から synthetic variants を生成 |

## Source Case

synthetic variants の入力となる元画像、正解テキスト、ROI 定義は [../ocr_dataset/source_cases](../ocr_dataset/source_cases/) に保存します。

synthetic variants を生成する例:

```bash
lab-ocr-generate-variants source_cases/img_0678
```

生成先は source case 配下の `variants/` です。`variants/` は生成物のため git 管理対象外です。

## 開発者向け情報

このパッケージは synthetic variants 生成だけを責務とし、source case 資産の保管、PaddleOCR 学習形式 export、PaddleOCR 本体の学習実行は扱いません。

docstring / comment の記載規約は [../docs/dev/notes/DEVELOPER_GUIDE.md](../docs/dev/notes/DEVELOPER_GUIDE.md) を正本とします。

README の記載形式は [../../../README_STANDARD.md](../../../README_STANDARD.md) に従います。
