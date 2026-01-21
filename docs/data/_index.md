# データ一覧・依存関係

## データ一覧表

### 生データ (0_raw)

| データ | 件数 | サイズ | フォーマット | 更新日 | 説明 |
|--------|------|--------|-------------|--------|------|
| danbooru-tags-2024 | 8,603,394件 | 5.27GB | Arrow | - | HuggingFace投稿メタデータ |
| danbooru-wiki-2024_df.pkl | 180,839件 | 72.38MB | Pickle | - | HuggingFace Wikiデータ |
| scalable_scraping_result.json | 15,951件 | 15.76MB | JSON | - | タグ階層構造スクレイピング結果 |

### 中間データ (1_intermediate)

| データ | 件数 | サイズ | フォーマット | 更新日 | 説明 |
|--------|------|--------|-------------|--------|------|
| tag_groups.pkl | 15,183件 | 3.61MB | Pickle (polars) | - | タググループ階層データ |
| tag_classification_result.pkl | 15,183件 | 3.92MB | Pickle (polars) | - | 分類済みタグデータ |
| danbooru_tags_top20k.pkl | 20,000件 | 15.92MB | Pickle (polars) | - | 上位投稿データ |

## データフロー図

```
外部データソース
├── HuggingFace isek-ai/danbooru-tags-2024
│   └── danbooru-tags-2024/ (Arrow, 12ファイル)
│       └── [src/incremental_pickle.py]
│           └── danbooru_tags_top20k.pkl
│
├── HuggingFace isek-ai/danbooru-wiki-2024
│   └── danbooru-wiki-2024_df.pkl
│
└── Danbooru tag_groupsページ
    └── [src/scalable_hierarchy_scraper.py]
        └── scalable_scraping_result.json
            └── [src/convert_tag_groups_to_pickle.py]
                └── tag_groups.pkl
                    └── [分類処理]
                        └── tag_classification_result.pkl
```

## 依存関係

### 0_raw データ間の依存関係
- なし（独立したデータソース）

### 1_intermediate データの依存関係

```
danbooru-tags-2024 (0_raw)
    ↓ incremental_pickle.py
danbooru_tags_top20k.pkl (1_intermediate)

scalable_scraping_result.json (0_raw)
    ↓ convert_tag_groups_to_pickle.py
tag_groups.pkl (1_intermediate)
    ↓ 分類処理
tag_classification_result.pkl (1_intermediate)
```

## データ使用目的

| データ | 主な用途 |
|--------|----------|
| danbooru-tags-2024 | 投稿データの分析、人気タグの抽出 |
| danbooru-wiki-2024_df.pkl | タグの詳細説明、別名参照 |
| scalable_scraping_result.json | タグ階層構造の取得・分析 |
| tag_groups.pkl | タグ階層の検索・クエリ |
| tag_classification_result.pkl | キャラクター特徴の分類・識別 |
| danbooru_tags_top20k.pkl | 人気投稿の分析・機械学習用データ |

## 更新状況

- 最終スクレイピング: 2024年6月
- 外部データセットバージョン: 2024
