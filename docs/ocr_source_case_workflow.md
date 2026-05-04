# OCR Source Case Workflow

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-SOURCE-CASE-WORKFLOW` |
| 作成日 | `2026-05-04` |
| 作成者 | `Codex` |
| 最終更新日 | `2026-05-04` |
| 最終更新者 | `Codex` |
| 版数 | `v1.0` |
| 状態 | `運用中` |

## 1. 概要

本書は、`lab-ocr-source-case-gui` と関連 CLI が作成する OCR 学習用 source case の流れを定義する。

source case は、PaddleOCR の fine-tuning に直接渡す最終データではなく、学習データを作るための元資産である。元画像、全文正解テキスト、ROI 短冊、OCR 候補、レビュー状態を分けて保持し、最終的には人が確認した ROI ラベルだけを PaddleOCR 形式へ export する。

## 2. 対象者

- OCR 学習用データを作成する使用者
- ROI 短冊と OCR 候補を確認するレビュー担当者
- PaddleOCR 学習形式 export を実装・保守する開発者

## 3. 責務境界

| 工程 | 主なツール | 責務 | PaddleOCR へ直接渡すか |
| --- | --- | --- | --- |
| source case 作成 | `lab-ocr-source-case-gui` | 元画像コピー、全文正解テキスト保存、ROI 短冊生成、OCR 候補生成 | いいえ |
| ROI 候補生成 | `lab-ocr-vision-batch` | `roi_strips/strip_XXXX.jpg` から同名 `.txt` 候補を作る | いいえ |
| ROI ラベル確認 | 今後の reviewer / 手動編集 | `roi_labels.json` の `text` と `status` を確定する | 確認済みだけ間接的に使う |
| PaddleOCR export | `ocr_dataset.exporters.paddleocr_dataset` | verified な ROI ラベルを PaddleOCR の label file に変換する | はい |
| PaddleOCR 学習 | `vendor/PaddleOCR` | export 済み dataset を使って fine-tuning する | はい |

## 4. GUI の位置づけ

`lab-ocr-source-case-gui` は、1つのページ画像から source case assets を作るための GUI である。

作成するもの:

- 元画像の case フォルダへのコピー
- `expected.txt`
- `expected_fields.json`
- `rois.json`
- `roi_strips/strip_XXXX.jpg`
- `roi_labels.json`
- `variants/`
- 任意で `roi_strips/strip_XXXX.txt`
- 任意で `roi_strips/vision_ocr_summary.json`
- 任意で `roi_strips/vision_ocr.log`

GUI が扱わないもの:

- ROI ごとの正解ラベル確定
- `roi_labels.json` の verified 化
- PaddleOCR 学習形式 export
- PaddleOCR 本体の学習実行

## 5. 使用者操作が必要な項目

GUI 内で使用者の判断が必要な項目は以下である。

- OCR 学習用元画像の選択
- 元画像に対応する全文正解テキストの読込または貼り付け
- `Case ID` の決定
- 既存 case を上書きするかの判断
- 合成バリエーション画像を生成するかの判断
- ROI 短冊から OCR 候補 `.txt` を生成するかの判断
- `Vision model` の指定
- OCR 候補生成時の Anthropic API key 入力
- 作成後の生成ファイル確認

Anthropic API key は、以下の条件を満たす場合だけ実行時モーダルで入力する。

- `ROI 短冊から OCR 候補 .txt を生成` が有効
- 環境変数 `ANTHROPIC_API_KEY` が未設定

入力された API key は保存しない。環境変数が設定済みの場合は、GUI モーダルを出さず環境変数を利用する。

## 6. OCR 候補と正解ラベル

`roi_strips/strip_XXXX.txt` は、Vision model が作成した OCR 候補である。これは正解ラベルではない。

PaddleOCR に誤ったラベルを学習させないため、候補は以下の扱いにする。

```text
ROI 短冊画像
  -> Vision OCR 候補 .txt
  -> 人が画像と照合
  -> roi_labels.json の text を確定
  -> status を verified にする
  -> PaddleOCR 形式へ export
```

`roi_labels.json` の基本形:

```json
{
  "roi_id": "strip_0010",
  "image": "roi_strips/strip_0010.jpg",
  "text": "人が確認した正解",
  "candidate_text": "Vision OCR 候補",
  "status": "verified",
  "note": "Review the ROI strip image and fill text."
}
```

未確認の `candidate_text` をそのまま PaddleOCR 学習に使ってはいけない。

## 7. PaddleOCR へ渡す最終形式

PaddleOCR の recognition dataset へ渡す最小情報は、画像パスと正解テキストである。

```text
roi_strips/strip_0010.jpg	お問い合わせ
roi_strips/strip_0011.jpg	ギャラリー
```

この label file は、`roi_labels.json` の `status == "verified"` の行から生成する。`needs_labeling`、`needs_review`、`trusted_auto` など未確定または弱い状態のデータは、通常の本番学習には混ぜない。

今後 `trusted_auto` を導入する場合も、`verified` とは別ファイルに export し、学習時に明示的に混ぜる設計にする。

## 8. OCR 実行 JSON / ログの用途

`vision_ocr_summary.json` と `vision_ocr.log` は PaddleOCR に直接渡す入力ではない。用途は、OCR 候補生成の再現性、監査、再実行判断、品質確認である。

記録する代表的な情報:

- model 名
- prompt version
- prompt sha256
- 実行開始・終了時刻
- processed / skipped / errors
- strip ごとの画像サイズ
- strip ごとの画像 sha256
- strip ごとの OCR 文字数
- strip ごとの OCR テキスト sha256
- strip ごとの処理時間
- skip 理由
- error 内容

記録しない情報:

- API key
- 画像 base64
- OCR 本文そのもの

OCR 本文は `strip_XXXX.txt` に保存し、JSON には追跡用の sha256 と件数情報だけを残す。

## 9. GUI 結果欄

GUI の `3. 学習前レビュー` には、作成後に確認すべきファイルを表示する。

表示対象:

- Case フォルダ
- `expected.txt`
- `rois.json`
- `roi_strips/`
- `roi_labels.json`
- `vision_ocr_summary.json`
- `vision_ocr.log`

結果欄のリンクはクリック可能であり、macOS では `open` により Finder または既定アプリで対象を開く。長いフルパスを常時表示せず、ファイル名またはフォルダ名をリンクとして表示する。

## 10. 今後の実装候補

優先度が高い次工程:

- `strip_XXXX.txt` を `roi_labels.json` の `candidate_text` に同期する処理
- ROI 短冊画像、候補テキスト、正解テキストを並べて確認する reviewer GUI
- `status == "verified"` の ROI だけを PaddleOCR label file へ export する処理
- `verified` と `trusted_auto` を分離した export
- export 結果の train / validation 分割

