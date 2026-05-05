# OCR Dataset

<!-- README_LEVEL: L2 -->

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-DATASET-README` |
| 作成日 | `2026-05-03` |
| 作成者 | `Tinoue` |
| 最終更新日 | `2026-05-03` |
| 最終更新者 | `Codex` |
| 版数 | `v1.0` |
| 状態 | `運用中` |

<div align="center">

OCR 評価・学習に再利用する source case 資産と dataset 整備ツールを扱います。

</div>

## 概要

この README は、[ocr_dataset](.) 配下だけを対象にした開発者向け説明です。

[ocr_dataset](.) は、人が確認した元画像、正解テキスト、ROI 定義、PaddleOCR 学習形式への export 境界を扱います。画像の水増し生成ロジックは [../ocr_synthetic_data/README.md](../ocr_synthetic_data/README.md) を参照してください。

## README の責務境界

| README | 扱う内容 | 扱わない内容 |
| --- | --- | --- |
| [../README.md](../README.md) | [../vendor/PaddleOCR](../vendor/PaddleOCR/) を含めたモジュール全体の概要、セットアップ、利用開始、CI と運用方針 | dataset 個別仕様 |
| [README.md](README.md) | source case 資産、ROI 定義、PaddleOCR 学習形式 export 境界 | OCR 実行 GUI、synthetic variants 生成ロジック |
| [../ocr_synthetic_data/README.md](../ocr_synthetic_data/README.md) | source case から synthetic variants を生成する処理 | source case 資産の保管、PaddleOCR 学習形式 export |

## 対象者

- OCR 評価・学習用の source case を整備する開発者
- ROI 定義や正解データを保守する検証担当者
- PaddleOCR fine-tuning 用 dataset export を準備する担当者

## 依存関係

- Python 3.11 系
- [../pyproject.toml](../pyproject.toml) に定義された画像処理ライブラリ
- 元画像、正解テキスト、ROI 定義を含む source case

## 最短セットアップ

通常の初回セットアップは [../README.md](../README.md) を参照してください。

editable install 後、Python から package import を確認します。

```bash
python -c "import ocr_dataset; print(ocr_dataset.__version__)"
```

## Python モジュール構成

| ディレクトリ | 責務 |
| --- | --- |
| [src/ocr_dataset/source_cases](src/ocr_dataset/source_cases/) | source case の schema と ROI 整備 |
| [src/ocr_dataset/exporters](src/ocr_dataset/exporters/) | PaddleOCR など外部学習形式への export |

## Source Case

元画像、正解テキスト、ROI 定義は [source_cases](source_cases/) に保存します。

[source_cases](source_cases/) は、別母艦でも再利用する OCR データセット資産です。人が確認した正解データを保持し、synthetic variants や PaddleOCR 学習形式 export の入力にします。

dataset 系 CLI / GUI のファイル入出力は、この [ocr_dataset](.) を起点にします。相対パスは `source_cases/img_0678` のように指定します。過去のコマンド例との互換のため `ocr_dataset/source_cases/img_0678` も受け付けますが、標準表記は `source_cases/img_0678` です。

例:

```text
source_cases/img_0678/
├── IMG_0678.jpg
├── expected.txt
├── expected_fields.json
├── roi_labels.json
└── rois.json
```

`variants/` は生成物のため git 管理対象外です。

短冊状 ROI を自動生成する例:

```bash
lab-ocr-generate-roi-strips source_cases/img_0678
```

`--image-name` を指定すると、同じ source case 配下の任意の画像ファイルから ROI を生成できます。データセットとして再利用する場合は、原本ファイル名を維持した画像を正本にします。

画像追加・更新後に標準ファイルをまとめて整える例:

```bash
lab-ocr-prepare-source-case source_cases/img_0678
```

このコマンドは、`expected.txt` がなければ空ファイルを作成し、`rois.json` を再生成し、`roi_labels.json` を ROI ID に合わせて同期します。既存の `expected.txt` は `--overwrite-expected` を指定しない限り上書きしません。既存の ROI ラベルは可能な範囲で保持し、ROI 座標が変わったラベルは `needs_review` に戻します。

GUI で source case を作成する例:

```bash
lab-ocr-source-case-gui
```

GUI では、事前に確認済みの元画像と画像全体の正解文字列を入力し、case ID を指定して source case assets を作成します。実行すると、元画像のコピー、`expected.txt` 保存、`rois.json` 生成、`roi_labels.json` 初期生成、`variants/` 生成をまとめて行います。必要に応じて `ROI 短冊から OCR 候補 .txt を生成` を有効にすると、生成した ROI 短冊から `.txt` 候補も続けて作成し、`roi_labels.json` の `candidate_text` に同期します。作成後は `ROI確認` タブで短冊画像と `candidate_text` を見比べ、確定文字列を `text` に保存し、確認済みの `status` を `verified` にします。

`ROI確認` タブで手動読込する場合は、`source_cases/img_0678` のような case フォルダを選択します。選択するフォルダには `roi_labels.json` と `roi_strips/` が必要です。`text` が空で `candidate_text` がある場合、GUI は作業効率のため `candidate_text` を `text` 欄へ仮入力します。ただし候補は正解ではないため、画像と照合するまで `verified` にしないでください。`verified` のまま `text` が空の保存は拒否します。

## 学習準備プロセス

[source_cases/img_0678/IMG_0678.jpg](source_cases/img_0678/IMG_0678.jpg) と [source_cases/img_0678/expected.txt](source_cases/img_0678/expected.txt) は、PaddleOCR の fine-tuning に向けた source case です。

現時点でこのリポジトリに実装済みの範囲は、学習そのものではなく、学習に使う source case の整備と学習用の水増し画像生成までです。PaddleOCR 学習形式への export 境界は [src/ocr_dataset/exporters/paddleocr_dataset.py](src/ocr_dataset/exporters/paddleocr_dataset.py) にありますが、実処理は未実装です。

処理の流れ:

```text
IMG_0678.jpg
  -> expected.txt を人が確認して整備
  -> rois.json を生成または調整
  -> roi_strips/ から OCR 候補テキストを生成
  -> roi_labels.json に ROI ごとの正解文字列を入力
  -> variants/ を生成
  -> PaddleOCR 学習形式へ export
  -> vendor/PaddleOCR 側で fine-tuning
```

### 1. 正解テキストを整備する

[source_cases/img_0678/expected.txt](source_cases/img_0678/expected.txt) は、[source_cases/img_0678/IMG_0678.jpg](source_cases/img_0678/IMG_0678.jpg) に写っている文字の正解データです。

このファイルは OCR 出力ではなく、人が確認した教師データとして扱います。OCR の誤認識をそのまま貼らず、画像と照合して正しい文字列に直します。

新規 source case は GUI から作成できます。

```bash
lab-ocr-source-case-gui
```

GUI 内で `ROI 短冊から OCR 候補 .txt を生成` を有効にすると、source case 作成後に ROI 短冊 OCR 候補生成と `roi_labels.json` への候補同期まで続けて実行できます。Vision provider は `Anthropic` または `OpenAI` から選択できます。OpenAI provider では `gpt-5.4-mini`、`gpt-5.5`、`gpt-5.4`、`gpt-5.4-nano`、`gpt-4.1`、`gpt-4.1-mini` を選択できます。この機能には `ANTHROPIC_API_KEY` または `OPENAI_API_KEY` が必要です。

### 2. ROI 短冊を生成する

ROI 定義は [source_cases/img_0678/rois.json](source_cases/img_0678/rois.json) に保存します。人が分割単位を確認できるよう、同時に `source_cases/img_0678/roi_strips/strip_XXXX.jpg` も生成します。

```bash
lab-ocr-generate-roi-strips source_cases/img_0678
```

`rois.json` には `source_image`、画像サイズ、短冊ごとの座標、短冊画像への相対パスを保存します。`IMG_0678.jpg` から生成した場合、`source_image` は `IMG_0678.jpg` になります。

### 3. ROI 短冊の OCR 候補を生成する

`roi_strips/strip_XXXX.jpg` から同名の `.txt` を生成し、ROI ごとのラベル入力候補として使えます。

```bash
export ANTHROPIC_API_KEY="..."
lab-ocr-vision-batch source_cases/img_0678/roi_strips --provider Anthropic
lab-ocr-vision-batch source_cases/img_0678/roi_strips --provider OpenAI --model gpt-5.4-mini
```

この出力は候補です。候補 `.txt` を `roi_labels.json` の `candidate_text` に同期するには次を実行します。

```bash
lab-ocr-sync-roi-candidates source_cases/img_0678
```

GUI から候補生成した場合、この同期は自動で行われます。`candidate_text` は正解ではないため、`ROI確認` タブで画像と照合してから `text` に反映します。

### 4. ROI ごとの正解ラベルを整備する

ROI ごとの正解ラベルは [source_cases/img_0678/roi_labels.json](source_cases/img_0678/roi_labels.json) に保存します。

`expected.txt` は画像全体の全文正解です。PaddleOCR の学習では、切り出した ROI 画像ごとに、その ROI に写っている文字列だけを教師ラベルにします。

例:

```json
{
  "roi_id": "strip_0001",
  "image": "roi_strips/strip_0001.jpg",
  "text": "ギャラリー",
  "candidate_text": "ギャラリー",
  "candidate_source": "vision_ocr",
  "candidate_file": "roi_strips/strip_0001.txt",
  "status": "verified"
}
```

自動生成直後の `roi_labels.json` は `status: needs_labeling` とし、`text` は空にします。`image` が指す短冊画像を人が確認してから `text` を入力し、確認済みのものは `status: verified` に変更します。この確認・保存は `lab-ocr-source-case-gui` の `ROI確認` タブで行えます。未確認のラベルを学習に使ってはいけません。

`status` の意味:

- `needs_labeling`: 未確認。まだ学習に使わない。
- `needs_review`: 判断保留。分割や読順などを再確認する。
- `verified`: 画像と照合済み。PaddleOCR export の対象にできる。
- `skipped`: 学習に使わない。

`text` に書くのは、元ページの見た目レイアウトではなく、そのROI画像をOCRしたときに返ってほしい正解文字列です。画像内で読める順序を保ち、自然な行区切りの改行は残します。位置合わせ用の空白や余分な空行は入れすぎません。2段組みなら、左段を上から下、次に右段を上から下の順に書きます。段組みや別文脈が混ざる場合は、文字列で吸収するよりROI分割の見直しを優先します。

画像を差し替えた場合は、次のコマンドで `rois.json` と `roi_labels.json` を同期します。

```bash
lab-ocr-prepare-source-case source_cases/img_0678
```

### 5. 学習用の水増し画像を生成する

明るさ、ぼけ、回転などの揺らぎ画像は [../ocr_synthetic_data](../ocr_synthetic_data/) 側で生成します。

```bash
lab-ocr-generate-variants source_cases/img_0678
```

生成物は `source_cases/img_0678/variants/` に保存されます。`variants/` は再生成可能な派生データなので git 管理対象外です。

### 6. PaddleOCR 学習形式へ export する

PaddleOCR の認識モデルを学習するには、最終的に PaddleOCR が要求する label file と画像ディレクトリへ変換する必要があります。

この export は [src/ocr_dataset/exporters/paddleocr_dataset.py](src/ocr_dataset/exporters/paddleocr_dataset.py) が担当します。`status: verified` の ROI だけを対象にし、`needs_labeling`、`needs_review`、`skipped` は学習用 label file に含めません。

```bash
lab-ocr-export-paddleocr-dataset source_cases/img_0678 --output exports/img_0678
```

[../main.py](../main.py) から実行する場合:

```bash
python main.py export-paddleocr source_cases/img_0678 --output exports/img_0678
```

出力先には、PaddleOCR recognition 用の `rec_gt_train.txt`、コピー済み短冊画像を含む `images/`、export 内容を確認する `manifest.json` を作成します。`rec_gt_train.txt` は画像相対パスと正解文字列をタブ区切りで保存します。

### 7. PaddleOCR 側で fine-tuning する

学習実行は [../vendor/PaddleOCR](../vendor/PaddleOCR/) 側の責務です。このリポジトリでは PaddleOCR 本体を直接改変せず、source case、ROI、variants、export までを管理します。

## 開発者向け情報

docstring / comment の記載規約は [../docs/dev/notes/DEVELOPER_GUIDE.md](../docs/dev/notes/DEVELOPER_GUIDE.md) を正本とします。

README の記載形式は [../../../README_STANDARD.md](../../../README_STANDARD.md) に従います。
