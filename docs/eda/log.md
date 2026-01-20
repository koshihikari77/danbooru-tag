# EDA 発見メモ

このドキュメントは、探索的データ分析（EDA）の発見内容を時系列で記録するものです。

## 2024-06

### データセット構造分析

**スクリプト**: `workspace/analyze_arrow_datasets.py`

**発見**:
- danbooru-tags-2024は12個のArrowファイルに分割
- 総レコード数: 8,603,394件
- データサイズ: 5.27GB
- 31カラム（投稿メタデータ、タグ統計、ステータス等）

**詳細**:
- ID範囲: 1-740,639
- タグフィールドはカンマ区切りではなくスペース区切り
- parent_idが7.4%でNULL（親投稿のない投稿）
- 削除済み投稿が10%含まれる

### 正規化データ構造分析

**スクリプト**: `workspace/analyze_normalized_data_structure.py`

**発見**:
- scalable_scraping_result.jsonの階層構造
- 4-way分類システムの分布
- 正規化処理: 10,190件の大文字小文字変換、739件の重複除去

### RDB設計分析

**スクリプト**: `workspace/rdb_analysis.py`

**発見**:
- 正規化テーブル設計（Posts, Tags, Post_Tags, Wiki_Pages, Wiki_Other_Names）
- インデックス戦略（スコア、人気度、タグ検索用）
- 推定ストレージ: データベース約4.2GB、インデックス込み約6.3GB

### タグ分析

**スクリプト**: `workspace/quick_tag_analysis.py`, `workspace/llamaindex_tag_analyzer.py`

**発見**:
- llama-indexによるタグ検索・分析
- タグの意味理解、関連タグの発見

### LlamaIndex クエリ

**スクリプト**: `workspace/llama_index_query.py`, `workspace/llama_index_query_simple.py`

**発見**:
- llama-indexによるデータセットクエリ
- タグ階層の検索・分析

## 問題・課題

### Large areolae階層問題

**発見日**: 2024-06-29

**問題**: `areolae -> large areolae` の中間親が欠如

**原因**: 兄弟ul処理時の重複処理ロジック

**解決**: 兄弟ul内li要素の処理順序修正、マーキング戦略改善

### 統合処理のマッチング問題

**発見日**: 2024-06-29

**問題**: `tag group:breasts tags` → `breasts` のマッチング失敗

**原因**: "X tags" → "X" 変換ロジックの不備

**解決**: 複数マッチングオプション実装、柔軟なマッチング戦略

## 今後の分析予定

- タグ階層の完全性検証
- 特徴分類の精度評価
- タグの使用頻度・相関分析
- タグ階層の深さ分布分析
