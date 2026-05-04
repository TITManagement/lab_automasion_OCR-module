---
title: "lab_automasion_OCR-module Documentation Book"
date: "2026-05-04 23:12:58"
toc: true
numbersections: true
---

# Book Build Metadata

Generated at: 2026-05-04 23:12:58\n


---

<!-- source: README.md -->

<a id="chapter-readme-md"></a>

# lab_automasion_OCR-module
<!-- README_LEVEL: L2 -->

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-MODULE-README` |
| 作成日 | `2026-05-03` |
| 作成者 | `Tinoue` |
| 最終更新日 | `2026-05-04` |
| 最終更新者 | `Codex` |
| 版数 | `v1.1` |
| 状態 | `運用中` |

<div align="center">

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## 概要

PaddleOCR を upstream/vendor として [vendor](vendor/) 配下に配置し、外側の wrapper から利用する Camera OCR モジュールです。

この README は、clone 後に配置する [vendor/PaddleOCR](vendor/PaddleOCR/) を含めた [lab_automasion_OCR-module](.) 全体を対象にします。ただし、[vendor/PaddleOCR](vendor/PaddleOCR/) 本体はこのリポジトリには直接コミットしません。OCR の起動、GUI、ROI、ログ整形、後処理、オフライン運用はこのリポジトリ側の wrapper で管理します。

注意: [vendor/PaddleOCR](vendor/PaddleOCR/) は GitHub upstream から取得する別リポジトリです。upstream 追従時は [vendor/PaddleOCR](vendor/PaddleOCR/) 側で `git fetch` / `git pull` などを実施し、このリポジトリ側では変更差分を直接保持しません。PaddleOCR 更新により CLI 引数、モデル名、出力形式、依存関係が変わる可能性があるため、更新後は [ocr_wrapper](ocr_wrapper/) の起動、ログ解析、後処理、オフラインモデル確認を回帰確認してください。

この README は、[vendor/PaddleOCR](vendor/PaddleOCR/) を含むモジュール全体の入口です。初回セットアップ、利用開始、PaddleOCR の配置、運用方針、関連ドキュメントへの導線を扱います。wrapper 実装の詳細な責務分割は ocr_wrapper/README.md（未収録: ocr_wrapper/README.md） を参照してください。

## README の責務境界

| README | 扱う内容 | 扱わない内容 |
| --- | --- | --- |
| [README.md](#chapter-readme-md) | [vendor/PaddleOCR](vendor/PaddleOCR/) を含めたモジュール全体の概要、セットアップ、利用開始、PaddleOCR の配置と扱い、CI と運用方針 | wrapper 内部関数の詳細、補正アルゴリズムの詳細、テストデータ別の結果 |
| ocr_wrapper/README.md（未収録: ocr_wrapper/README.md） | [ocr_wrapper](ocr_wrapper/) 配下に閉じた Python パッケージ構成、各 Python モジュールの責務、開発者向け直接実行、回帰テスト | モジュール全体の導入方針、PaddleOCR vendor clone 方針、文書全体の索引 |
| ocr_dataset/README.md（未収録: ocr_dataset/README.md） | [ocr_dataset](ocr_dataset/) 配下に閉じた source case 資産、ROI 定義、PaddleOCR 学習形式 export 境界 | Camera OCR GUI、synthetic variants 生成ロジック |
| ocr_synthetic_data/README.md（未収録: ocr_synthetic_data/README.md） | [ocr_synthetic_data](ocr_synthetic_data/) 配下に閉じた synthetic variants 生成 | OCR 実行 GUI、source case 資産の保管、PaddleOCR 学習形式 export |
| [docs/ocr_support_algorithm_design.md](#chapter-docs-ocr-support-algorithm-design-md) | PaddleOCR を補助する後処理・ROI・mojibake 補正の設計 | 日常操作手順、パッケージ構成一覧 |
| [docs/ocr_source_case_workflow.md](#chapter-docs-ocr-source-case-workflow-md) | OCR Source Case Builder、ROI 短冊 OCR 候補、PaddleOCR export 前の確認工程 | Camera OCR の実行詳細、PaddleOCR 本体の学習手順 |

## 対象者

- カメラOCRを利用する運用担当者
- OCR GUI、ROI、後処理ルールを保守する開発者
- PaddleOCR のオフライン運用やセキュリティ監査を確認する検証担当者

## 依存関係

- Python: 3.11 系
- 主要ライブラリ: [pyproject.toml](pyproject.toml) を参照
- PaddleOCR: [vendor/PaddleOCR](vendor/PaddleOCR/) に別途 clone して配置
- AIST/AiLab GUI header: `aist-guiparts`
- ROI 短冊 OCR 候補生成: `anthropic`
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
- OCR 評価・学習向け source case 管理と学習用の水増し画像生成
- OCR Source Case Builder GUI
- ROI 短冊からの OCR 候補 `.txt` 生成
- ROI OCR 実行結果の JSON / log 記録
- source case 作成結果のクリック可能リンク表示
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
lab-ocr-vision-batch source_cases/img_0678/roi_strips
lab-ocr-sync-roi-candidates source_cases/img_0678
lab-ocr-prepare-source-case source_cases/img_0678
lab-ocr-source-case-gui
lab-ocr-generate-variants source_cases/img_0678
```

OCR Source Case Builder:

```bash
source .venv_OCR/bin/activate
lab-ocr-source-case-gui
```

この GUI は、OCR 学習用元画像と画像全体の全文正解テキストから、1つの source case を作成します。作成対象は、元画像コピー、`expected.txt`、`rois.json`、`roi_strips/`、`roi_labels.json`、必要に応じた `variants/` と ROI OCR 候補 `.txt` です。作成後は同じGUI内の `ROI確認` タブで短冊画像、`candidate_text`、確定用 `text`、`status` を確認・保存できます。

`ROI 短冊から OCR 候補 .txt を生成` を有効にした場合だけ、Vision provider / model による候補生成を実行します。Provider は `Anthropic` または `OpenAI` から選択できます。OpenAI を選ぶと `gpt-5.4-mini`、`gpt-5.5`、`gpt-5.4`、`gpt-5.4-nano`、`gpt-4.1`、`gpt-4.1-mini` を選択できます。環境変数 `ANTHROPIC_API_KEY` または `OPENAI_API_KEY` が設定済みならそれを使い、未設定なら実行時モーダルで入力します。入力された API key は保存しません。

ROI OCR 候補生成の結果は、`roi_strips/vision_ocr_summary.json` と `roi_strips/vision_ocr.log` に保存します。候補 `.txt` は `roi_labels.json` の `candidate_text` にも同期します。これらは PaddleOCR へ直接渡す学習入力ではなく、候補生成の再現性、監査、再実行判断、品質確認に使う情報です。

PaddleOCR へ最終的に渡す recognition dataset は、`roi_labels.json` で人が確認し `verified` にした ROI ラベルから export します。Vision OCR の `.txt` 候補や `candidate_text` を未確認のまま学習に使ってはいけません。詳細は [docs/ocr_source_case_workflow.md](#chapter-docs-ocr-source-case-workflow-md) を参照してください。

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

- ocr_wrapper/README.md（未収録: ocr_wrapper/README.md）
- ocr_dataset/README.md（未収録: ocr_dataset/README.md）
- ocr_synthetic_data/README.md（未収録: ocr_synthetic_data/README.md）
- [docs/ocr_support_algorithm_design.md](#chapter-docs-ocr-support-algorithm-design-md)
- [docs/ocr_source_case_workflow.md](#chapter-docs-ocr-source-case-workflow-md)
- [docs/dev/notes/DEVELOPER_GUIDE.md](#chapter-docs-dev-notes-developer-guide-md)
- _post_clone_assets/README_POST_CLONE_ASSETS.md（未収録: _post_clone_assets/README_POST_CLONE_ASSETS.md）
- _post_clone_assets/security_ops/README_SECURITY_OFFLINE.md（未収録: _post_clone_assets/security_ops/README_SECURITY_OFFLINE.md）

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
- [source_cases/vision_batch_ocr.py](ocr_dataset/src/ocr_dataset/source_cases/vision_batch_ocr.py): ROI 短冊画像から vision OCR 候補テキストを生成
- [source_cases/sync_roi_candidates.py](ocr_dataset/src/ocr_dataset/source_cases/sync_roi_candidates.py): ROI OCR 候補を `roi_labels.json` に同期
- [source_cases/source_case_gui.py](ocr_dataset/src/ocr_dataset/source_cases/source_case_gui.py): OCR Source Case Builder GUI
- [exporters/paddleocr_dataset.py](ocr_dataset/src/ocr_dataset/exporters/paddleocr_dataset.py): PaddleOCR 学習形式 export の境界

synthetic data 側の主な責務分割:

- [augment.py](ocr_synthetic_data/src/ocr_synthetic_data/augment.py): 明るさ、ぼけ、傾きなどの画像変換
- [generate_variants.py](ocr_synthetic_data/src/ocr_synthetic_data/generate_variants.py): source image から synthetic variants を生成

docstring / comment の記載規約は [docs/dev/notes/DEVELOPER_GUIDE.md](#chapter-docs-dev-notes-developer-guide-md) を正本とします。

README の記載形式は ../../README_STANDARD.md（未収録: ../../README_STANDARD.md） に従います。

## CI

GitHub Actions では、PR に対して editable install と Python compile check を実行します。

- [qa_gate.yml](.github/workflows/qa_gate.yml): `python -m pip install -e .` と `python -m compileall -q .`
- [agents-governance.yml](.github/workflows/agents-governance.yml): AGENTS.md（未収録: AGENTS.md） のガバナンス記載確認
- [docs_automation.yml](.github/workflows/docs_automation.yml): README 正規化チェック

module docstring の存在検証は、現時点では CI の強制対象ではありません。運用規約は [docs/dev/notes/DEVELOPER_GUIDE.md](#chapter-docs-dev-notes-developer-guide-md) に定義しています。

## ライセンス

MIT


---

<!-- source: ocr_support_algorithm_design.md -->

<a id="chapter-docs-ocr-support-algorithm-design-md"></a>

# OCR Support Algorithm Design

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-OCR-SUPPORT-ALGORITHM-SPEC` |
| 作成日 | `2026-05-03` |
| 作成者 | `Tinoue` |
| 最終更新日 | `2026-05-03` |
| 最終更新者 | `Codex` |
| 版数 | `v1.0` |
| 状態 | `運用中` |

## 1. 概要

この設計書は、`lab_automasion_OCR-module` で PaddleOCR を支援するために外側レイヤーへ追加したアルゴリズムを整理する。

本モジュールでは、PaddleOCR 本体を直接変更せず、以下の支援処理でカメラOCRの実用性を上げる。

- 入力画像の ROI 切り出し
- 英数字・記号領域向けの追加 OCR パス
- OCR 出力の構造化、重複除去、表示整形
- 郵便番号、電話番号、FAX、URL、英数字記号列の安全寄り補正
- 文脈依存補正を Basic 補正から分離
- 実行ログの可読化

この支援処理は「医療専用」ではない。日本語文書、住所、電話番号、URL、英数字記号が混在するカメラOCR全般を対象にする。

## 2. 対象者

- カメラOCRの認識精度を調整する開発者
- PaddleOCR 本体を変更せずに運用レイヤーを保守する担当者
- OCR結果の補正ルールと誤補正リスクを確認する検証担当者

## 3. 前提条件

- [../vendor/PaddleOCR](../vendor/PaddleOCR/) は upstream/vendor として扱い、原則として直接変更しない。
- OCR精度改善は、ROI、前処理、後処理、モデル選択で行う。
- Corrected OCR と Raw OCR を分けて表示し、補正前後を比較できる状態を維持する。

## 4. 本文

### 4.1 対象ファイル

現行実装の主な対象は以下。

- [../main.py](../main.py)
  - `camera-ocr-gui` コマンドの起動入口
- [../ocr_wrapper/src/ocr_wrapper/camera_ocr_gui.py](../ocr_wrapper/src/ocr_wrapper/camera_ocr_gui.py)
  - カメラプレビュー、ROIドラッグ、GUI状態管理、非同期OCR実行
- [../ocr_wrapper/src/ocr_wrapper/text_processing.py](../ocr_wrapper/src/ocr_wrapper/text_processing.py)
  - OCR出力解析、Raw/Corrected表示構築、文字列補正
- [../ocr_wrapper/src/ocr_wrapper/image_processing.py](../ocr_wrapper/src/ocr_wrapper/image_processing.py)
  - ROI切り出し、英数字記号向け画像強調
- [../ocr_wrapper/src/ocr_wrapper/ocr_runtime.py](../ocr_wrapper/src/ocr_wrapper/ocr_runtime.py)
  - PaddleOCR CLIコマンド構築、ログ整形、終了コード表示
- [../_post_clone_assets/security_ops/scripts/run_paddleocr_offline.sh](../_post_clone_assets/security_ops/scripts/run_paddleocr_offline.sh)
  - PaddleOCR CLI 実行ラッパー

[../vendor/PaddleOCR](../vendor/PaddleOCR/) 配下は upstream/vendor として扱い、原則として直接変更しない。

### 4.2 全体フロー

カメラOCRの処理は以下の流れで実行する。

1. カメラからフレームを取得する。
2. GUI上でアスペクト比を維持して表示する。
3. ROI が有効な場合、ユーザーがドラッグ指定した範囲を相対座標で保持する。
4. OCR実行時に、現在フレームから ROI を切り出す。
5. 切り出し画像に対して PaddleOCR を実行する。
6. 英数字・記号列を拾いやすくするため、同じ ROI から追加の強調画像を作成し、2回目の OCR パスを実行する。
7. PaddleOCR の標準出力から `rec_texts` を抽出する。
8. 重複を除去し、英数字記号列を優先して並べる。
9. 補正モードに応じて Corrected OCR を作成する。
10. Corrected OCR と Raw OCR を横並びで表示する。
11. 実行ログは ANSI シーケンスや既知のノイズを除去して表示する。

### 4.3 GUI と ROI

#### プレビュー表示

カメラ映像はアスペクト比を維持して表示する。表示領域とフレームの比率が一致しない場合は黒帯を許容する。

これは OCR の対象画像を歪ませないための方針である。映像を UI 領域いっぱいに引き伸ばすと、文字の縦横比が変化し、PaddleOCR の認識精度に悪影響を与える可能性がある。

#### 左右プレビュー

プレビューは2ペイン構成にする。

- `Camera`
  - カメラ取得画像全体
  - ROI 選択枠を重ねて表示
- `ROI`
  - 実際に OCR へ渡す切り出し画像

この構成により、ユーザーは「カメラの全体構図」と「OCR対象として切り出される画像」を同時に確認できる。

#### ROI 指定

ROI は数値入力ではなく、`Camera` ペイン上のマウスドラッグで指定する。

内部では ROI をピクセル座標ではなく、フレーム幅・高さに対する相対座標で保持する。

```text
(left, top, right, bottom)
```

各値は `0.0` から `1.0` の範囲に正規化する。これにより、プレビューサイズやウィンドウサイズが変わっても、元フレームに対する選択範囲を安定して再現できる。

ROI が小さすぎる場合は、最低幅・最低高さを確保する。ドラッグ方向が逆でも、left/right と top/bottom を入れ替えて正規化する。

#### ROI プリセット

ドラッグ指定に加えて、以下のプリセットを保持する。

- `Center`
- `Full`
- `Top`
- `Bottom`

プリセットは初期位置や素早い切り替えのための補助機能であり、最終的な ROI はドラッグで調整できる。

### 4.4 OCR 実行

#### PaddleOCR 呼び出し

GUI は PaddleOCR を直接 import せず、ラッパースクリプト経由で CLI 実行する。

```text
_post_clone_assets/security_ops/scripts/run_paddleocr_offline.sh ocr ...
```

CLI オプションでは、macOS CPU 環境での安定性を優先する。

- `--device cpu`
- `--enable_mkldnn False`
- `--cpu_threads 1`
- `--text_recognition_batch_size 1`
- `--use_doc_orientation_classify False`
- `--use_doc_unwarping False`
- `--use_textline_orientation False`

デフォルトの OCR バージョンは `PP-OCRv3` とする。これはカメラOCR用途で、サーバーモデルよりクラッシュリスクと処理時間を抑えやすいためである。

#### 2パスOCR

OCRは2パスで実行する。

1. `full`
   - ROI 切り出し画像そのものを OCR する。
   - 日本語本文、住所、一般テキストを拾う主経路。
2. `serial-roi`
   - ROI 内の中央寄り領域をさらに切り出し、拡大、CLAHE、シャープ化を行って OCR する。
   - 英数字・記号列の候補を拾う補助経路。

2パスの出力は結合し、後段で重複除去する。

### 4.5 画像前処理

#### ROI 切り出し

ROI が有効な場合、OCR対象画像は現在フレームから相対座標で切り出す。

範囲外参照を避けるため、切り出し座標はフレーム内にクランプする。右端・下端は最低でも左端・上端より1ピクセル以上大きくする。

#### 英数字記号向け強調

`serial-roi` パスでは、ROI 画像から追加の局所領域を切り出し、以下の処理を行う。

- 3倍拡大
- グレースケール化
- CLAHE による局所コントラスト強調
- Gaussian Blur を使ったアンシャープマスク

この処理は、伝票番号、管理番号、郵便番号、URL 断片など、細く小さい英数字記号列の候補を拾いやすくするための補助である。

ただし、これは万能な認識改善ではない。強調によって日本語本文が崩れる場合もあるため、主経路の `full` パスとは分けて扱う。

### 4.6 OCR 出力解析

#### rec_texts 抽出

PaddleOCR の標準出力から `rec_texts` を正規表現で抽出する。

複数 OCR パスの出力を同じ解析関数で処理するため、標準出力中に複数の `rec_texts` が存在しても順番に処理する。

抽出には以下の方針を使う。

- まず `ast.literal_eval` で Python リスト相当として読む。
- 失敗した場合は、単純なクォート文字列抽出にフォールバックする。
- 文字列内のリテラル `\u3000` は全角スペースへ戻す。
- 同一文字列は順序を保って重複除去する。

#### Raw OCR

Raw OCR は PaddleOCR の認識結果をできるだけそのまま保持する表示欄である。

Raw OCR は誤補正の検証に使うため、補正済み表示と混ぜない。

#### Corrected OCR

Corrected OCR は、Raw OCR に対して選択された補正モードを適用した表示欄である。

現行の表示では、Corrected OCR と Raw OCR を横並びにして、補正の効果と副作用を比較できるようにしている。

### 4.7 補正モード

補正モードは以下を持つ。

- `Auto`
- `Off`
- `Basic`
- `Context`

#### Off

補正を行わない。Corrected OCR には Raw OCR と同じ内容を表示する。

#### Basic

Basic は文書種別に依存しにくい安全寄りの補正である。

対象は以下。

- 郵便番号
- TEL/FAX
- URL
- 英数字記号列
- 連続空白

Basic では、特定施設名や特定文書に閉じた置換は行わない。

#### Context

Context は Basic より踏み込んだ補正である。

以下のような、文脈上の誤認識が強く疑われる場合に限って適用する。

- 日本語専門語の典型的な誤認識
- 住所形式の典型的な崩れ
- URL から対象文書の文脈が強く推定できる場合の補正

Context は誤補正リスクが Basic より高い。そのため Raw OCR を残し、補正内容を比較できる UI にしている。

#### Auto

Auto は Raw OCR と Basic 補正後の文字列を見て、Context 補正が有効そうなマーカーがある場合だけ Context を選ぶ。

現在の Auto は簡易判定であり、機械学習モデルではない。したがって、ユーザーが必要に応じて Off、Basic、Context を手動選択できる余地を残している。

### 4.8 Basic 補正

#### 文字化け復元

以下のような文字列は、UTF-8 バイト列を Latin-1 として誤解釈した可能性がある。

```text
å½ç«ç ç©¶éçºæ³äºº...
```

これは通常のOCR誤認識というより、文字コード復元の問題である。

Basic / Context 補正では、全行へ無条件に適用せず、以下の安全判定を満たす場合だけ復元を採用する。

1. `å`、`ç`、`ã`、`æ`、`è`、`é`、`Â`、C1制御文字などの mojibake らしい文字が一定数以上ある。
2. 文字列長に対して mojibake らしい文字の割合が一定以上ある。
3. `latin1 -> utf-8` の復元に成功する。
4. 復元後に日本語文字数が増える。
5. 復元後に mojibake らしい文字数が減る。

上記を満たす場合だけ Corrected OCR 側に反映する。Raw OCR には原文を残す。

全角スペースなど Latin-1 に戻せない文字が混在する場合は、行全体を無理に復元しない。mojibake らしい連続区間だけを復元対象にし、復元後の行全体が改善した場合だけ採用する。

#### 郵便番号

郵便番号は以下の崩れを補正する。

- `302-0022`
- `〒302-0022`
- `で302-0022`
- `干3020022`
- `千3020022`

単独の郵便番号行は `〒NNN-NNNN` に整形する。

住所と同じ行に郵便番号が含まれる場合は、行全体を破壊しないように郵便番号部分だけを接頭辞として補正する。

例:

```text
千305-8567茨城県つくば市東1-1-1中央第7
```

補正後:

```text
〒305-8567 茨城県つくば市東1-1-1中央第7
```

この方針は、郵便番号らしさだけで行全体を電話番号や英数字列として処理してしまう副作用を避けるためである。

#### TEL/FAX

電話・FAX 行では、ラベル誤認識と区切り記号の崩れを補正する。

代表例:

- `IEL`、`1EL`、`IlEL` 相当を `TEL` へ補正
- `FAx`、`FA×`、`F4X` 相当を `FAX` へ補正
- `--` を `-` へ補正
- `(代)` 周辺で詰まった `FAX` を分離

電話・FAX 補正では、許可する文字を以下に絞る。

```text
TELFAX0123456789-() 代
```

これは whitelist 相当のフィルタである。ただし、住所行や郵便番号付き住所行に誤って適用すると日本語情報を欠落させるため、電話らしさの判定を通った行にだけ適用する。

#### URL

URL 行では、OCRで崩れやすい英数字・記号を補正する。

代表例:

- `URl`、`URI`、`UR1` を `URL` へ補正
- `http:I/www.`、`http.I/www.` を `http://www.` へ補正
- `medicaI` を `medical` へ補正
- `or,jp` を `or.jp` へ補正
- 空白を除去
- URL に使える文字だけに制限

URL 補正では、URL 本体に許可する文字を以下に絞る。

```text
ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:/._-
```

これも whitelist 相当のフィルタである。URLらしさを判定した行にだけ適用する。

#### 英数字記号列

`serial-roi` パスなどから得た候補に対して、英数字記号列らしさを判定する。

候補化の流れ:

1. 空白を除去する。
2. 全角英数字や記号を半角へ寄せる。
3. 大文字化する。
4. `A-Z`、`0-9`、`#`、`-` 以外を除去する。
5. 郵便番号、電話、URL らしい行は除外する。
6. 最低長、数字数、英字または `#` の有無で候補を絞る。

この処理は、OCRエンジンの辞書を編集する代わりに、後段で whitelist 相当の安全な抽出を行う設計である。

### 4.9 Context 補正

Context 補正は、Basic の後に文脈依存の置換を行う。

現在の代表的な補正例:

- `取毛市` → `取手市`
- `皮店` → `皮膚`
- `耳鼻侯科` → `耳鼻咽喉科`
- `耳皇因帳科` → `耳鼻咽喉科`
- `歯科口空外科` → `歯科口腔外科`
- `歯科口歴外科` → `歯科口腔外科`
- `リハビリテーション科放射線科` → `リハビリテーション科・放射線科`
- `本郷2一1一1` のような住所中の `一` を `-` へ補正

また、`toride-medical` を含む URL が検出された場合に限り、既知施設向けの限定補正を適用する。

この限定補正は、対象文書の文脈が URL から強く示される場合だけ実行する。文脈がない文書へ無条件に適用しない。

### 4.10 ログ整形

PaddleOCR の実行ログは、そのままだと GUI で読みづらい。

ログ表示では以下を行う。

- ANSI カラーシーケンス除去
- 制御文字除去
- `No ccache found` 警告の折りたたみ
- `sysctl:` 行の除外
- モデルキャッシュの長いパスをモデル名だけに短縮
- 連続空行の圧縮

ログ整形は表示だけを対象にする。PaddleOCR の標準出力そのものは、OCR結果解析に使えるよう別途保持する。

### 4.11 安全性と誤補正対策

#### Raw OCR の保持

補正は必ず Raw OCR と分けて表示する。

理由:

- 補正による情報欠落を検知できる。
- 補正ルールの妥当性をユーザーが確認できる。
- 誤補正が発生した場合でも、元の OCR 結果へ戻れる。

#### Basic と Context の分離

Basic は形式補正、Context は文脈補正として分ける。

Basic:

- 郵便番号
- TEL/FAX
- URL
- 英数字記号列

Context:

- 日本語語彙の置換
- 住所語の推定補正
- URL などの文脈に基づく既知対象補正

この分離により、用途を固定しない汎用OCR支援と、文脈を使った高リスク補正を切り分ける。

#### whitelist 相当処理の適用範囲

英数字・記号の whitelist 相当処理は、行全体へ無条件に適用しない。

適用対象は以下のように限定する。

- 電話らしい行
- URLらしい行
- serial-like と判定された候補

日本語住所や本文へ whitelist を誤適用すると、漢字かな情報が消えるためである。

### 4.12 既知の制約

- Auto 判定はルールベースであり、確率的な信頼度は持たない。
- Context 補正は便利だが、文脈の取り違えによる誤補正リスクがある。
- `serial-roi` の画像強調は英数字向けであり、日本語本文の認識改善を保証しない。
- ROI が小さすぎる、ピントが合っていない、露出が悪い場合は、後処理だけでは限界がある。
- OCR結果の並び順は PaddleOCR の検出順に依存する。

### 4.13 今後の拡張候補

#### 補正根拠の可視化

将来的には Corrected OCR に対して、どのルールが適用されたかを別ログまたはツールチップで表示できる。

例:

```text
IEL0297-74-5551 -> TEL 0297-74-5551  [phone_label]
http:I/www... -> http://www...       [url_scheme]
```

これにより、誤補正の調査とルール調整が容易になる。

## 5. 参照

- ../AGENTS.md（未収録: ../AGENTS.md）
- ../ocr_wrapper/README.md（未収録: ../ocr_wrapper/README.md）
- ../_post_clone_assets/security_ops/README_SECURITY_OFFLINE.md（未収録: ../_post_clone_assets/security_ops/README_SECURITY_OFFLINE.md）

### 5.1 運用方針

- PaddleOCR 本体は直接変更しない。
- OCR精度改善は、ROI、前処理、後処理、モデル選択で行う。
- 補正ルールを追加する場合は、適用条件を狭くし、Raw OCR と比較できる状態を維持する。
- 特定画像だけに過適合する補正は避ける。
- 特定文書や特定施設に閉じた補正は、文脈マーカーが明確な場合だけ Context として追加する。


---

<!-- source: ocr_source_case_workflow.md -->

<a id="chapter-docs-ocr-source-case-workflow-md"></a>

# OCR Source Case Workflow

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-SOURCE-CASE-WORKFLOW` |
| 作成日 | `2026-05-04` |
| 作成者 | `Codex` |
| 最終更新日 | `2026-05-04` |
| 最終更新者 | `Codex` |
| 版数 | `v1.2` |
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

## 11. 今後の実装候補

優先度が高い次工程:

- `status == "verified"` の ROI だけを PaddleOCR label file へ export する処理
- `verified` と `trusted_auto` を分離した export
- export 結果の train / validation 分割


---

<!-- source: dev/notes/DEVELOPER_GUIDE.md -->

<a id="chapter-docs-dev-notes-developer-guide-md"></a>

# Developer Guide

| 項目 | 内容 |
| --- | --- |
| 文書ID | `LABOCR-DEV-DEVELOPER-GUIDE` |
| 作成日 | `2026-05-03` |
| 作成者 | `Tinoue` |
| 最終更新日 | `2026-05-03` |
| 最終更新者 | `Codex` |
| 版数 | `v1.0` |
| 状態 | `運用中` |

## 1. 概要

本書は、`lab_automasion_OCR-module` の開発時に参照する docstring / comment 規約を定義する。

この規約は、AiLab の既存標準を本リポジトリ内で運用できるように引用・要約したものである。単独 clone された環境では、本書を正本として扱う。

## 2. 対象者

- OCR wrapper を保守する開発者
- Camera OCR GUI の責務境界を確認するレビュー担当者
- CI や静的検証で docstring の存在を確認する運用担当者

## 3. 前提条件

- docstring は、コードを読めば自明な説明を増やすためではなく、責務・境界・副作用・前提を補うために書く。
- 機械検証では、`__init__.py` を除く `.py` ファイルの module docstring 存在を最小要件とする。
- 本リポジトリでは、PaddleOCR 本体ではなく wrapper 側の責務境界を明確にすることを優先する。

## 4. Docstring / Comment Rule

### 4.1 Module Docstring

`__init__.py` を除く `.py` ファイルには、モジュール先頭 docstring を置く。

推奨構成:

```python
"""概要。

責務:
    - このモジュールが扱うこと。
    - 外部 I/O、状態変換、payload 整形などの境界。

責務外:
    - 他モジュールへ委譲すること。
"""
```

### 4.2 Public Class / Public Function

public class / public function では、`役割` を先に書く。必要に応じて `返り値`、`副作用`、`呼び出し側から見た前提` を補う。

例:

```python
def build_payload(state: dict) -> dict:
    """run 状態と metadata から公開用の平坦な payload を生成する。"""
```

### 4.3 Private Helper

private helper は、すべてに機械的には書かない。

優先して書く対象:

- 外部 I/O
- 例外吸収
- 状態変換
- payload 整形
- 永続化
- 並行処理
- thread / event loop 境界をまたぐ処理

### 4.4 Getter / Setter 相当

getter / setter 相当の自明な関数には、名前の焼き直しになる docstring は書かない。

悪い例:

```python
def get_value() -> str:
    """値を取得する。"""
```

### 4.5 Comment

comment は行単位の説明ではなく、連続した処理ブロックの意図が読み取りにくいときだけ短く書く。

## 5. 参照

本書は、以下の AiLab 既存規約を本リポジトリ内に取り込んだもの。

- `AiLab/project_template/docs/dev/notes/DEVELOPER_GUIDE.md`
- `AiLab/lab_automation_System/LabOrch/docs/governance/documentation_management_spec.md`

上記の要点:

- 読み手が責務と境界を短時間で判断できることを重視する。
- docstring と comment は、コードだけで読み取りにくい振る舞いに限定して書く。
- module docstring の存在を最小要件として扱う。
- docstring は API 契約や責務境界の補助情報として機能させ、単なる名前の言い換えにしない。
