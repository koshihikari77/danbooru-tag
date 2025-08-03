# プロジェクト構造

## ディレクトリ構成
```
danbooru_tag/
├── .claude/                         # Claude設定
├── .serena/                         # Serena設定
├── scripts/                         # メインスクリプト
│   ├── scalable_hierarchy_scraper.py    # メインスクレイパー
│   ├── convert_tag_groups_to_pickle.py  # JSON→pickle変換
│   ├── incremental_pickle.py            # 大容量データ処理
│   ├── quick_tag_analysis.py           # 軽量タグ分析
│   ├── llamaindex_tag_analyzer.py      # AI検索システム
│   └── query_body_parts.py             # 特定タグ調査
├── data/                            # データファイル
│   ├── 0_raw/                       # 生データ
│   ├── temp_chunks/                 # 分割データ
│   └── *.pkl                        # 処理済みデータ
├── docs/                            # ドキュメント
├── tmp/                             # 一時・検証データ
├── pyproject.toml                   # プロジェクト設定
├── CLAUDE.md                        # 開発指針
├── README.md                        # プロジェクト説明
└── .gitignore                       # Git除外設定
```

## 主要ファイル説明
- **scalable_hierarchy_scraper.py**: Danbooruスクレイピングのメイン処理
- **quick_tag_analysis.py**: 人物固有特徴の自動分類
- **incremental_pickle.py**: メモリ効率的な大容量データ処理
- **llamaindex_tag_analyzer.py**: 自然言語でのタグ検索システム