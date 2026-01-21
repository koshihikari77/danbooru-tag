# danbooru_tags_top20k.pkl

## 概要

danbooru-tags-2024から時間当たりスコア上位20,000件を抽出した投稿データ。

主な用途:
- 人気投稿の分析
- タグの使用頻度分析
- 機械学習用トレーニングデータ

## Origin

| 項目 | 値 |
|------|-----|
| 生データ | danbooru-tags-2024 (0_raw) |
| 変換スクリプト | src/incremental_pickle.py |
| 作成日 | 2024年6月 |

## Acquisition

### 取得方法

```bash
# 段階的処理のみ
python src/incremental_pickle.py process

# チャンク結合のみ
python src/incremental_pickle.py combine

# 全処理実行
python src/incremental_pickle.py full
```

### 再現手順

1. `data/0_raw/danbooru-tags-2024/` が存在することを確認
2. `python src/incremental_pickle.py full` 実行

### レート制限/ポリシー

- ローカルファイル処理のため不要

### 失敗時のハンドリング

- チャンク単位で処理・保存して失敗時にも再開可能
- メモリ効率的なチャンク処理（デフォルト50,000件/チャンク）

## Schema

### フィールド定義

| カラム | 型 | 説明 | 例 |
|--------|-----|------|-----|
| id | Int64 | 投稿ID | 1 |
| created_at | String | 作成日時（ISO 8601） | "2005-05-24T12:35:31.000+09:00" |
| score | Int64 | スコア | 1564 |
| rating | String | レーティング (s/q/e/g) | "s" |
| image_width | Int64 | 画像幅 | 459 |
| image_height | Int64 | 画像高さ | 650 |
| file_ext | String | ファイル拡張子 | "jpg" |
| tag_count | Int64 | 総タグ数 | 68 |
| tag_count_general | Int64 | 一般タグ数 | 60 |
| tag_count_artist | Int64 | アーティストタグ数 | 1 |
| tag_count_character | Int64 | キャラクタータグ数 | 1 |
| tag_count_copyright | Int64 | 著作権タグ数 | 2 |
| tag_count_meta | Int64 | メタタグ数 | 4 |
| fav_count | Int64 | お気に入り数 | 184 |
| general | String | 一般タグ（スペース区切り） | "1girl 2000s_(style) ..." |
| character | String | キャラクタータグ | "kousaka_tamaki" |
| copyright | String | 著作権タグ | "to_heart_(series) to_heart_2" |
| artist | String | アーティストタグ | "kyogoku_shin" |
| meta | String | メタタグ | "bad_id bad_link commentary" |
| created_datetime | Datetime[μs, UTC] | 作成日時（パース済み） | - |
| hours_since_start | Int64 | 最古データからの経過時間 | - |
| score_per_hour | Float64 | 時間当たりスコア | - |

### データ例

```json
{
  "id": 1,
  "created_at": "2005-05-24T12:35:31.000+09:00",
  "score": 1564,
  "rating": "s",
  "image_width": 459,
  "image_height": 650,
  "tag_count": 68,
  "general": "1girl 2000s_(style) animal_ear_fluff animal ears",
  "character": "kousaka_tamaki",
  "copyright": "to_heart_(series) to_heart_2",
  "artist": "kyogoku_shin",
  "meta": "bad_id bad_link commentary",
  "created_datetime": "2005-05-24T03:35:31",
  "hours_since_start": 0,
  "score_per_hour": 0.0016
}
```

## Stats

### 基本統計

| 項目 | 値 |
|------|-----|
| 総レコード数 | 20,000件 |
| ファイル形式 | pickle (polars DataFrame) |
| ファイルサイズ | 15.92MB |

### フィルタリング条件

| 条件 | 説明 |
|------|------|
| is_deleted == False | 削除済み除外 |
| is_banned == False | 禁止済み除外 |
| score > 0 | スコア正の値のみ |

### 追加カラム

| カラム | 説明 |
|--------|------|
| created_datetime | created_atをパースしたDatetime型 |
| hours_since_start | 最古データからの経過時間（時間） |
| score_per_hour | スコア / hours_since_start （時間当たりスコア） |

## Quality

### 既知の品質問題

- なし

### データの癖・特殊な値

- score_per_hourでソートして上位20,000件を抽出
- created_datetimeはUTC変換済み
- 元のデータからdeleted/banned除外済み

### 注意点

- score_per_hourは経過時間で正規化されているため、新しい投稿ほど有利になりやすい
- タグ文字列はスペース区切り（カンマ区切りではない）

## Lineage

### 入力

```
danbooru-tags-2024 (0_raw)
```

### 出力

```
danbooru_tags_top20k.pkl (1_intermediate)
```

### 変換処理の概要

1. **段階的読み込み**: チャンク単位（50,000件）でArrowファイルを読み込み
2. **フィルタリング**: is_deleted=false, is_banned=false, score>0
3. **追加カラム計算**:
   - created_datetime: created_atをパース
   - hours_since_start: 最古データからの経過時間
   - score_per_hour: スコア / hours_since_start
4. **上位抽出**: score_per_hour上位20,000件を抽出
5. **保存**: polars DataFrameとしてpickle保存

### チャンク処理

| 項目 | 値 |
|------|-----|
| チャンクサイズ | 50,000件 |
| 中間保存パス | data/temp_chunks/chunk_XXX.pkl |
| 状態管理ファイル | data/pickle_state.txt |

## Changelog

- 2024-06: incremental_pickle.py 作成
- 2024-06: danbooru_tags_top20k.pkl 作成
- 変更なし
