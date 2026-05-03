# golden data

<!-- README_LEVEL: L3 -->

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-WRAPPER-GOLDEN-README` |
| 作成日 | `2026-05-03` |
| 作成者 | `Tinoue` |
| 最終更新日 | `2026-05-03` |
| 最終更新者 | `Codex` |
| 版数 | `v1.0` |
| 状態 | `運用中` |

## 概要

このディレクトリは、OCR wrapper の回帰テストで使う golden data を置く場所です。

## 使い方

初回作成手順:

1. `sample.png` を配置
2. [../../src/ocr_wrapper/run_ocr.py](../../src/ocr_wrapper/run_ocr.py) を実行し `sample_result.golden.json` を作成
3. 目視確認後に固定

## 依存

- OCR wrapper の実行環境
- Golden 比較に使う固定入力画像

## 配置

- `sample.png`: 比較対象の固定入力画像
- `sample_result.golden.json`: 期待する OCR 実行結果
