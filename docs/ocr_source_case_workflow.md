# OCR Source Case Workflow

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-SOURCE-CASE-WORKFLOW` |
| 作成日 | `2026-05-04` |
| 作成者 | `Codex` |
| 最終更新日 | `2026-05-04` |
| 最終更新者 | `Codex` |
| 版数 | `v1.3` |
| 状態 | `運用中` |

## 1. 概要

本書は、`lab-ocr-source-case-gui` と関連 CLI が作成する OCR 学習用 source case の流れを定義する。

source case は、PaddleOCR の fine-tuning に直接渡す最終データではなく、学習データを作るための元資産である。元画像、全文正解テキスト、ROI 短冊、OCR 候補、レビュー状態を分けて保持し、最終的には人が確認した ROI ラベルだけを PaddleOCR 形式へ export する。

`main.py` を入口にした OCR 実行系、PaddleOCR 学習、学習結果まで含む上位のデータフローは [ocr_accuracy_data_flow.md](ocr_accuracy_data_flow.md) を参照する。

## 2. 対象者

- OCR 学習用データを作成する使用者
- ROI 短冊と OCR 候補を確認するレビュー担当者
- PaddleOCR 学習形式 export を実装・保守する開発者

## 3. 責務境界

| 工程 | 主なツール | 責務 | PaddleOCR へ直接渡すか |
| --- | --- | --- | --- |
| source case 作成・ROI確認 | `lab-ocr-source-case-gui` | 元画像コピー、全文正解テキスト保存、ROI 短冊生成、OCR 候補生成、候補の `roi_labels.json` 反映、ROIごとの `text` / `status` 保存 | 確認済みだけ間接的に使う |
| ROI 候補生成 | `lab-ocr-vision-batch` | `roi_strips/strip_XXXX.jpg` から同名 `.txt` 候補を作る | いいえ |
| ROI 候補同期 | `lab-ocr-sync-roi-candidates` | `strip_XXXX.txt` を `roi_labels.json` の `candidate_text` に反映する | いいえ |
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
- 任意で `roi_labels.json` の `candidate_text`
- 任意で `roi_strips/vision_ocr_summary.json`
- 任意で `roi_strips/vision_ocr.log`

GUI が扱わないもの:

- PaddleOCR 学習形式 export
- PaddleOCR 本体の学習実行

## 5. 使用者操作が必要な項目

GUI 内で使用者の判断が必要な項目は以下である。

- OCR 学習用元画像の選択
- 元画像に対応する全文正解テキストの読込または貼り付け
- `Case ID` の決定
- 既存 case を上書きするかの判断
- 学習用の水増し画像を生成するかの判断
- ROI 短冊から OCR 候補 `.txt` を生成するかの判断
- `Vision provider` の指定
- `Vision model` の指定
- OCR 候補生成時の API key 入力
- `ROI確認` タブでの `candidate_text` 確認
- ROI ごとの `text` 入力
- ROI ごとの `status` 確定

既存 case を `ROI確認` タブで開く場合は、`ocr_dataset/source_cases/img_0678` のような `roi_labels.json` と `roi_strips/` を含む case フォルダを選択する。

`Vision provider` で `OpenAI` を選択した場合は、OpenAI の画像入力対応モデルをドロップダウンから選ぶ。初期値は ROI 短冊の一括処理で使いやすい `gpt-5.4-mini` とする。

API key は、以下の条件を満たす場合だけ実行時モーダルで入力する。

- `ROI 短冊から OCR 候補 .txt を生成` が有効
- 選択した provider に対応する環境変数が未設定

対応する環境変数:

- Anthropic: `ANTHROPIC_API_KEY`
- OpenAI: `OPENAI_API_KEY`

入力された API key は保存しない。環境変数が設定済みの場合は、GUI モーダルを出さず環境変数を利用する。

## 6. OCR 候補と正解ラベル

`roi_strips/strip_XXXX.txt` は、Vision model が作成した OCR 候補である。これは正解ラベルではない。

PaddleOCR に誤ったラベルを学習させないため、候補は以下の扱いにする。

```text
ROI 短冊画像
  -> Vision OCR 候補 .txt
  -> roi_labels.json の candidate_text に同期
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
  "candidate_source": "vision_ocr",
  "candidate_file": "roi_strips/strip_0010.txt",
  "status": "verified",
  "note": "Review the ROI strip image and fill text."
}
```

未確認の `candidate_text` をそのまま PaddleOCR 学習に使ってはいけない。

GUI では作業効率のため、`text` が空で `candidate_text` がある場合に `candidate_text` を `text` 欄へ仮入力する。ただしこれは verified ではない。人が短冊画像と照合し、必要な修正を行ってから `status` を `verified` にする。`status: verified` で `text` が空の場合、GUI は保存を拒否する。

`status` の意味:

- `needs_labeling`: 未確認。まだ学習に使わない。
- `needs_review`: 判断保留。分割や読順などを再確認する。
- `verified`: 画像と照合済み。PaddleOCR export の対象にできる。
- `skipped`: 学習に使わない。

`text` に書くのは、元ページの見た目レイアウトではなく、そのROI画像をOCRしたときに返ってほしい正解文字列である。画像内で読める順序を保ち、自然な行区切りの改行は残す。位置合わせ用の空白や余分な空行は入れすぎない。2段組みなら、左段を上から下、次に右段を上から下の順に書く。段組みや別文脈が混ざる場合は、文字列で吸収するよりROI分割の見直しを優先する。

## 7. PaddleOCR へ渡す最終形式

PaddleOCR の recognition dataset へ渡す最小情報は、画像パスと正解テキストである。

```text
roi_strips/strip_0010.jpg	お問い合わせ
roi_strips/strip_0011.jpg	ギャラリー
```

この label file は、`roi_labels.json` の `status == "verified"` の行から生成する。`needs_labeling`、`needs_review`、`trusted_auto` など未確定または弱い状態のデータは、通常の本番学習には混ぜない。

今後 `trusted_auto` を導入する場合も、`verified` とは別ファイルに export し、学習時に明示的に混ぜる設計にする。

export は次のコマンドで実行する。

```bash
python main.py export-paddleocr source_cases/img_0678 --output exports/img_0678
```

出力先には、PaddleOCR recognition 用の `rec_gt_train.txt`、短冊画像をコピーした `images/`、export 内容を記録する `manifest.json` を作成する。

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

## 9. Source Case Builder の完了条件

`lab-ocr-source-case-gui` の責務境界は、次の状態を作るところまでである。

- source case フォルダが作成されている
- 元画像が case フォルダに保存されている
- `expected.txt` が保存されている
- `rois.json` が生成されている
- `roi_strips/strip_XXXX.jpg` が生成されている
- `roi_labels.json` が生成されている
- OCR 候補生成を有効にした場合、`strip_XXXX.txt` が生成されている
- OCR 候補生成を有効にした場合、`roi_labels.json` の `candidate_text` に候補が同期されている
- OCR 候補生成を有効にした場合、`vision_ocr_summary.json` と `vision_ocr.log` が保存されている
- GUI の `ROI確認` タブで、短冊画像、`candidate_text`、編集可能な `text`、`status` を確認できる
- 人が確認した ROI は `text` と `status: verified` として `roi_labels.json` に保存されている

この完了状態では、まだ PaddleOCR 学習用形式への export は完了していない。次工程では、`status: verified` の ROI だけを PaddleOCR recognition dataset へ export する。

## 10. GUI 画面

GUI は `作成` と `ROI確認` のタブで構成する。

`作成` タブの結果欄には、作成後に確認すべきファイルを表示する。

- Case フォルダ
- `expected.txt`
- `rois.json`
- `roi_strips/`
- `roi_labels.json`
- `vision_ocr_summary.json`
- `vision_ocr.log`

結果欄のリンクはクリック可能であり、macOS では `open` により Finder または既定アプリで対象を開く。長いフルパスを常時表示せず、ファイル名またはフォルダ名をリンクとして表示する。

`ROI確認` タブには、以下を表示する。

- `strip_XXXX.jpg`
- `candidate_text`
- 編集可能な `text`
- `status`
- 前へ / 次へ
- 保存 / 保存して次へ
- 進捗と verified 件数
- status 説明
- ラベル入力の考え方

## 11. 今後の実装候補

優先度が高い次工程:

- `status == "verified"` の ROI だけを PaddleOCR label file へ export する処理
- `verified` と `trusted_auto` を分離した export
- export 結果の train / validation 分割
