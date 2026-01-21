# tag_groups.pkl

## 概要

scalable_scraping_result.jsonをpolars DataFrameに変換したタググループ階層データ。

主な用途:
- タグ階層の検索・クエリ
- タグの親子関係データベース
- 特徴分類の基礎データ

## Origin

| 項目 | 値 |
|------|-----|
| 生データ | scalable_scraping_result.json |
| 変換スクリプト | src/convert_tag_groups_to_pickle.py |
| 作成日 | 2024年6月 |

## Acquisition

### 取得方法

```bash
# JSON → pkl 変換
python src/convert_tag_groups_to_pickle.py
```

### 再現手順

1. `data/0_raw/scalable_scraping_result.json` が存在することを確認
2. `python src/convert_tag_groups_to_pickle.py` 実行

### レート制限/ポリシー

- ローカルファイル処理のため不要

### 失敗時のハンドリング

- JSONファイル存在確認
- スキーマ整合性チェック

## Schema

### フィールド定義

| カラム | 型 | 説明 | 例 |
|--------|-----|------|-----|
| name | String | タグ/タググループ名（小文字正規化済み） | "cat ears" |
| url | String | リンク先URL | "/wiki_pages/cat_ears" |
| path | String | パス（" → "区切り文字列） | "visual characteristics → body → tag group:body parts → ..." |
| parent | String | 親タググループ名 | "animal ears" |
| depth | Int64 | 階層深度（1から開始） | 5 |
| has_nested_list | Boolean | 下位リストを持つか | false |
| classification | String | 分類タイプ | "final_tag_only" |
| should_follow | Boolean | リンク追跡対象か | false |

### データ例

```json
{
  "name": "cat ears",
  "url": "/wiki_pages/cat_ears",
  "path": "visual characteristics → body → tag group:body parts → tag group:ears tags → animal ears → cat ears",
  "parent": "animal ears",
  "depth": 5,
  "has_nested_list": false,
  "classification": "final_tag_only",
  "should_follow": false
}
```

## Stats

### 基本統計

| 項目 | 値 |
|------|-----|
| 総レコード数 | 15,183件 |
| ファイル形式 | pickle (polars DataFrame) |
| ファイルサイズ | 3.61MB |

### 分類タイプ分布

| 分類 | 件数 | 割合 |
|------|------|------|
| final_tag_only | 9,648 | 60.5% |
| tag_and_tag_group | 4,677 | 29.3% |
| tag_group_only | 794 | 5.0% |
| traditional_tag_group | 64 | 0.4% |

## Quality

### 既知の品質問題

- なし

### データの癖・特殊な値

- pathカラムは" → "区切り文字列（配列ではない）
- 全て小文字に正規化済み
- 重複は除去済み

### 注意点

- pathカラムの区切り文字は" → "（矢印スペース矢印スペース）
- polars DataFrame形式なのでpolarsで読み込む必要あり

## Lineage

### 入力

```
scalable_scraping_result.json (0_raw)
```

### 出力

```
tag_groups.pkl (1_intermediate)
    ↓ 分類処理
tag_classification_result.pkl (1_intermediate)
```

### 変換処理の概要

1. **JSON読み込み**: normalized_data.items からデータ取得
2. **形式変換**: path配列を" → "区切り文字列に変換
3. **DataFrame変換**: polars DataFrameに変換
4. **保存**: pickle形式で保存

## Changelog

- 2024-06: 変換スクリプト作成
- 変更なし
