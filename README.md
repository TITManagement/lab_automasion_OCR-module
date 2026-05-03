# project_template
<!-- README_LEVEL: L2 -->

<div align="center">

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## 概要

AiLab 配下の独立リポジトリを標準運用で開始するためのテンプレートです。

## 対象者
- 運用担当者: 日常運用・手順実行を行う担当者
- 開発者: 機能追加・保守を行う担当者
- 検証担当者: 実機/テスト環境で動作確認を行う担当者

## 依存関係
- Python: `pyproject.toml` の `requires-python` に従う
- 主要ライブラリ: `pyproject.toml` の `dependencies` を参照
- pip index設定: `$AILAB_ROOT/lab_automation_module/config/pip/pip.conf.local` を正本とする

## 最短セットアップ
`bash` / `zsh` で以下を実行。
```bash
export AILAB_ROOT=/path/to/AiLab
export PIP_CONFIG_FILE="$AILAB_ROOT/lab_automation_module/config/pip/pip.conf.local"
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python main.py
```

## README標準
- README の編集基準は `README_STANDARD.md` を正本とする。
- このテンプレートを複製した先でも、同等ルールの `README_STANDARD.md` を配置して運用する。

## 主な機能
- `main.py` 入口 + `project-template` console script
- `PR Gate` / `QA Gate` / `Docs Automation` / `OSS License` workflow 同梱
- README 標準章（対象者/依存関係/最短セットアップ）を初期実装

## 使い方
```bash
python main.py
```

## 構成
```
project_template/
├── .github/workflows/
├── src/
├── main.py
├── pyproject.toml
└── README.md
```

## ライセンス
MIT
