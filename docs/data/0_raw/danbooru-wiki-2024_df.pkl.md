# danbooru-wiki-2024_df.pkl

## 概要

DanbooruのWikiページデータ。タグ・概念の詳細説明（本文、別名等）を含むpandas DataFrame。

主な用途:
- タグの詳細説明取得
- タグの別名参照
- タグの意味理解

## Origin

| 項目 | 値 |
|------|-----|
| データソース | HuggingFace |
| データセット名 | isek-ai/danbooru-wiki-2024 |
| URL | https://huggingface.co/datasets/isek-ai/danbooru-wiki-2024 |
| 取得時バージョン | 2024 |
| ライセンス | Danbooruのコンテンツは各権利者に帰属 |

## Acquisition

### 取得方法

```python
# HuggingFace datasets ライブラリを使用
from datasets import load_dataset

dataset = load_dataset("isek-ai/danbooru-wiki-2024")
df = dataset['train'].to_pandas()
df.to_pickle("data/0_raw/danbooru-wiki-2024_df.pkl")
```

### 再現手順

1. HuggingFaceアカウント作成
2. `huggingface-cli login` で認証
3. 上記Pythonスクリプト実行

### レート制限/ポリシー

- Danbooru APIの利用規約に従う
- 商用利用には権利者の許諾が必要

### 失敗時のハンドリング

- ネットワークエラー: 自動リトライ（datasetsライブラリ標準機能）
- メモリ不足: データを分割して処理

## Schema

### フィールド定義

| フィールド | 型 | 説明 | 例 |
|-----------|-----|------|-----|
| id | int64 | WikiページID | 115416 |
| created_at | string | 作成日時 (ISO 8601) | "2018-11-01T00:00:00+09:00" |
| updated_at | string | 更新日時 (ISO 8601) | "2024-12-31T12:34:56+09:00" |
| title | string | ページタイトル | "veemusic" |
| other_names | array | 別名リスト | ["Vee", "VEE"] |
| body | string | 本文（Wikiマークアップ） | "[[Virtual YouTuber]] agency..." |
| is_locked | bool | ロック状態 | false |
| is_deleted | bool | 削除済み | false |
| category | string | カテゴリ (general/artist/character/copyright/meta) | "copyright" |
| tag | string | 対応タグ名 | "veemusic" |

### データ例

```json
{
  "id": 115416,
  "created_at": "2018-11-01T00:00:00+09:00",
  "updated_at": "2024-12-31T12:34:56+09:00",
  "title": "veemusic",
  "other_names": ["Vee", "VEE"],
  "body": "[[Virtual YouTuber]] agency and music label launched in November 2018.",
  "is_locked": false,
  "is_deleted": false,
  "category": "copyright",
  "tag": "veemusic"
}
```

## Stats

### 基本統計

| 項目 | 値 |
|------|-----|
| 総レコード数 | 180,839件 |
| データサイズ | 72.38 MB (75,896,666 bytes) |
| ID範囲 | 10 - 216,069 |

### ユニーク値分布

| フィールド | ユニーク値数 |
|-----------|-------------|
| id | 180,839 (100%) |
| created_at | 180,839 (100%) |
| updated_at | 180,838 (99.999%) |
| title | 180,839 (100%) |
| tag | 180,839 (100%) |
| body | 133,226 (73.7%) |
| category | 5 |

### カテゴリ分布

| カテゴリ | 説明 | 件数 (推定) |
|---------|------|------------|
| general | 一般タグ | - |
| artist | アーティスト | - |
| character | キャラクター | - |
| copyright | 著作権 | - |
| meta | メタタグ | - |

### 欠損値分布

| フィールド | NULL件数 | NULL率 |
|-----------|----------|--------|
| 全フィールド | 0 | 0% |

## Quality

### 既知の品質問題

- 特になし

### データの癖・特殊な値

- `body` はWikiマークアップ形式（[[リンク]]等の記法）
- `other_names` は配列形式
- `updated_at` が99.999%ユニーク（ほぼ毎ページ異なる）

### 注意点

- `body` フィールドはWikiマークアップの解析が必要
- データサイズが小さくメモリ効率的な処理は不要

## Lineage

### 変換先

```
danbooru-wiki-2024_df.pkl (0_raw)
    ↓ (現在のところ変換処理なし)
(直接使用)
```

### 変換処理の概要

- 現在のところ、このデータは中間データへの変換処理なしで直接使用

## Changelog

- 2024-06: データセット取得
- 変更なし
