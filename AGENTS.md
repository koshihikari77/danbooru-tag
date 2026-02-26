# danbooru_tag

Danbooru のタグ階層・使用回数・Wiki データを収集・管理するツール。
SceneForge のタグDB・RAG検索機能として利用される。

## 共通ルール

Git 運用・コミット規約・PR手順・worktree操作は **`../.agents/AGENTS.md`** を参照。

## このリポ固有のルール

### 開発環境

- Python 3.12+、パッケージ管理は `uv`
- セットアップ: `uv venv && uv sync`

### 主要ドキュメント

- 実装計画・タスクメモ: `docs/plans/`

### データファイル

大容量データファイル（`.pkl`, `.faiss`）は Git 管理外。
