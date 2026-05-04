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

本書は、`lab_automation_OCR-module` の開発時に参照する docstring / comment 規約を定義する。

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
