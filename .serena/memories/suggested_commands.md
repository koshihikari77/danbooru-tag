# 推奨コマンド

## 環境管理
```bash
# 環境セットアップ
uv sync

# 仮想環境アクティベート
source .venv/bin/activate

# パッケージ追加
uv add package_name
```

## メインスクリプト実行
```bash
# 階層スクレイピング（メイン機能）
uv run python scripts/scalable_hierarchy_scraper.py

# 特定tag group処理
uv run python scripts/scalable_hierarchy_scraper.py --target-groups "Tag group:Body parts"

# レート制限調整
uv run python scripts/scalable_hierarchy_scraper.py --rate-limit 1.0
```

## データ分析
```bash
# タグ分析（軽量版）
uv run python scripts/quick_tag_analysis.py

# LlamaIndex分析システム
uv run python scripts/llamaindex_tag_analyzer.py

# Body Parts関連タグ調査
uv run python scripts/query_body_parts.py
```

## データ変換
```bash
# JSONからpickle変換
uv run python scripts/convert_tag_groups_to_pickle.py

# 大容量データ分割処理
uv run python scripts/incremental_pickle.py process
uv run python scripts/incremental_pickle.py combine
```

## システムコマンド（Linux）
```bash
# ファイル検索
find . -name "*.py" -type f
rg "pattern" --type py

# プロセス管理
ps aux | grep python
kill -9 PID

# ディスク使用量
du -h data/
df -h
```