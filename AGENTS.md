# AGENTS.md (Project Template)

このリポジトリのエージェント運用正本は、この `AGENTS.md` と `README_STANDARD.md` とする。

<!-- AGENTS_BASE_SOURCE: (set by sync script) -->
<!-- AGENTS_BASE_SHA256: (set by sync script) -->

## 共通ルール（正本）

- コマンド提案前に `pwd` を実行して現在地を示す。
- 読み取り専用コマンド（`pwd`, `ls`, `rg`, `cat`, `git status`, `git diff` など）は許可なし実行可。
- 変更系コマンド（`rm`, `mv`, `cp`, `git add/commit/push` など）は明示許可後に実行する。
- 破壊的操作（`reset --hard`, `checkout --` 等）は使用しない。
- 重要結果は短く要約し、実行コマンドは場所・期待影響を明記して提示する。

## Repo固有ルール

- このテンプレートは各独立リポジトリへ複製して利用する前提とする。
- 複製先では `AGENTS_BASE_URL` を設定し、`agents-governance` の同期検証を有効化する。
- README 更新時は `README_STANDARD.md` に基づき、`scripts/docs/normalize_readme.py` で整形/検証する。
