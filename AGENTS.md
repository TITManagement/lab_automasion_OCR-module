# AGENTS.md (lab_automation_OCR-module)

共通ルールは [../../AGENTS.md](../../AGENTS.md) を正本とする。
このファイルには、`lab_automation_OCR-module` 固有の差分だけを書く。

## モジュール固有ルール

- [vendor/PaddleOCR](vendor/PaddleOCR/) は upstream/vendor 本体として扱い、原則として直接修正しない。
- OCRの起動、GUI、カメラ入力、ログ整形、前処理、後処理、モデル選択、オフライン運用の調整は、原則として以下の外側レイヤーに閉じる。
  - [main.py](main.py)
  - [ocr_wrapper](ocr_wrapper/)
  - [_post_clone_assets/security_ops](_post_clone_assets/security_ops/)
- [vendor/PaddleOCR](vendor/PaddleOCR/) 配下を変更する必要が出た場合は、先に理由、代替不能性、upstream更新時の影響、復旧手順を明文化し、ユーザー確認を得てから実施する。
- `.venv_OCR`、`vendor/PaddleOCR/.venv_*`、モデルキャッシュ、`__pycache__`、一時画像、OCR出力の一時ファイルは生成物として扱い、コミット対象に含めない。

## 実行エントリ

- 通常の起動入口は [main.py](main.py) とする。
- `python main.py camera-ocr-gui` は [ocr_wrapper/src/ocr_wrapper/camera_ocr_gui.py](ocr_wrapper/src/ocr_wrapper/camera_ocr_gui.py) を、プロジェクト直下の [.venv_OCR](.venv_OCR/) で起動する。
- PaddleOCR CLIの直接実行は、原則 [_post_clone_assets/security_ops/scripts/run_paddleocr_offline.sh](_post_clone_assets/security_ops/scripts/run_paddleocr_offline.sh) 経由とする。

## OCR GUI運用

- `camera-ocr-gui` は実機カメラを使う REAL 操作として扱う。
- GUI、カメラ、OCR精度調整を行う場合は、作業前に実機操作の有無を明記する。
- プレビュー表示は、映像全体を切り取らず、アスペクト比を維持する。黒帯は許容する。
- OCR認識精度の調整は、PaddleOCR本体改変ではなく、入力画像の前処理、ROI切り出し、結果後処理、モデル選択で行う。

## オフライン・モデル運用

- OCR実行は offline-first とし、モデルキャッシュの存在確認を優先する。
- 一時的にモデル取得が必要な場合は、`PADDLEOCR_STRICT_OFFLINE=0` の必要性、取得対象モデル、保存先を明記してから実行する。
- デフォルトのカメラOCRでは、macOS CPUでの安定性を優先し、軽量モデルを選ぶ。高精度モデルへ切り替える場合は、クラッシュや処理時間増加のリスクを明記する。

## ログ・結果表示

- 実行ログは、利用者が判断しやすい形に整形する。ANSI制御文字、既知のノイズ、長いキャッシュパスは必要に応じて簡略化する。
- OCR結果の後処理では、表示改善と認識値の置換を分けて扱う。
- 認識値を辞書補正やルール補正で置換する場合は、補正ルール、対象フィールド、誤補正リスクを明記する。

## Docstring / Comment

- Python ソースの docstring / comment は [docs/dev/notes/DEVELOPER_GUIDE.md](docs/dev/notes/DEVELOPER_GUIDE.md) を正本とする。
- `__init__.py` を除く `.py` ファイルには module docstring を置く。
- public class / public function は役割を先に書き、必要に応じて返り値、副作用、前提を補う。
- private helper は、外部 I/O、例外吸収、状態変換、payload 整形、並行処理境界など、責務境界上重要なものを優先して書く。
- getter / setter 相当の自明な関数には、名前の焼き直しになる docstring を書かない。
