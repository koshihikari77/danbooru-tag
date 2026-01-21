# danbooru-tags-2024

## 概要

Danbooruの画像投稿メタデータセット。HuggingFace `isek-ai/danbooru-tags-2024` から取得した画像投稿のメタデータ（スコア、タグ、画像情報等）を含む。

主な用途:
- 人気投稿の分析
- タグの使用頻度分析
- 機械学習用トレーニングデータ

## Origin

| 項目 | 値 |
|------|-----|
| データソース | HuggingFace |
| データセット名 | isek-ai/danbooru-tags-2024 |
| URL | https://huggingface.co/datasets/isek-ai/danbooru-tags-2024 |
| 取得時バージョン | 2024 |
| ライセンス | Danbooruのコンテンツは各権利者に帰属 |

## Acquisition

### 取得方法

```bash
# HuggingFace datasets ライブラリを使用
from datasets import load_dataset

dataset = load_dataset("isek-ai/danbooru-tags-2024")
dataset.save_to_disk("data/0_raw/danbooru-tags-2024")
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
- ディスク容量不足: ストレージ空き容量確認（6GB以上必要）

## Schema

### データ構造

Arrow形式で12ファイルに分割保存。

### フィールド定義

| フィールド | 型 | 説明 | 例 |
|-----------|-----|------|-----|
| id | int64 | 投稿ID | 1 |
| created_at | string | 作成日時 (ISO 8601) | "2005-05-24T12:35:31.000+09:00" |
| updated_at | string | 更新日時 (ISO 8601) | "2025-01-19T01:46:35.057+09:00" |
| score | int64 | 総合スコア | 1564 |
| up_score | int64 | アップボート数 | 1555 |
| down_score | int64 | ダウンボート数 | 0 |
| fav_count | int64 | お気に入り数 | 184 |
| rating | string | レーティング (g/s/q/e) | "s" |
| image_width | int64 | 画像幅 (px) | 459 |
| image_height | int64 | 画像高さ (px) | 650 |
| file_ext | string | ファイル拡張子 | "jpg" |
| tag_count | int64 | 総タグ数 | 68 |
| tag_count_general | int64 | 一般タグ数 | 60 |
| tag_count_artist | int64 | アーティストタグ数 | 1 |
| tag_count_character | int64 | キャラクタータグ数 | 1 |
| tag_count_copyright | int64 | 著作権タグ数 | 2 |
| tag_count_meta | int64 | メタタグ数 | 4 |
| parent_id | float64 | 親投稿ID | null |
| has_children | bool | 子投稿の有無 | false |
| has_active_children | bool | アクティブ子投稿の有無 | false |
| has_visible_children | bool | 表示可能子投稿の有無 | false |
| is_pending | bool | 承認待ち | false |
| is_flagged | bool | フラグ付き | false |
| is_deleted | bool | 削除済み | false |
| is_banned | bool | 禁止済み | false |
| bit_flags | int64 | ビットフラグ | 0 |
| general | string | 一般タグ (スペース区切り) | "1girl 2000s_(style) ..." |
| character | string | キャラクタータグ (スペース区切り) | "kousaka_tamaki" |
| copyright | string | 著作権タグ (スペース区切り) | "to_heart_(series) to_heart_2" |
| artist | string | アーティストタグ (スペース区切り) | "kyogoku_shin" |
| meta | string | メタタグ (スペース区切り) | "bad_id bad_link commentary" |

### データ例

```json
{
  "id": 1,
  "created_at": "2005-05-24T12:35:31.000+09:00",
  "updated_at": "2025-01-19T01:46:35.057+09:00",
  "score": 1564,
  "rating": "s",
  "image_width": 459,
  "image_height": 650,
  "tag_count": 68,
  "general": "1girl 2000s_(style) ;p animal_ear_fluff animal ears aqua_panties",
  "character": "kousaka_tamaki",
  "copyright": "to_heart_(series) to_heart_2",
  "artist": "kyogoku_shin",
  "meta": "bad_id bad_link commentary"
}
```

## Stats

### 基本統計

| 項目 | 値 |
|------|-----|
| 総レコード数 | 8,603,394件 |
| データサイズ | 5.27 GB (5,658,326,580 bytes) |
| ファイル数 | 12個 |
| ID範囲 | 1 - 740,639 |
| 作成日時ユニーク数 | 716,276 |
| 更新日時ユニーク数 | 716,878 |

### スコア・エンゲージメント

| 項目 | 最小 | 最大 | 平均 |
|------|------|------|------|
| score | -167 | 1,564 | 7.53 |
| up_score | 0 | 1,555 | 7.53 |
| down_score | -175 | 0 | -0.14 |
| fav_count | 0 | 1,864 | 23.10 |

### 画像属性

| 項目 | 最小 | 最大 | 平均 |
|------|------|------|------|
| image_width | 1 | 30,000 | 862 |
| image_height | 1 | 39,401 | 976 |

### タグ統計

| 項目 | 平均 | 最小 | 最大 |
|------|------|------|------|
| tag_count | 23.78 | 3 | 953 |
| tag_count_general | 18.24 | 0 | - |
| tag_count_artist | 0.90 | 0 | - |
| tag_count_character | 1.57 | 0 | - |
| tag_count_copyright | 1.28 | 0 | - |
| tag_count_meta | 1.79 | 0 | - |

### 欠損値分布

| フィールド | NULL件数 | NULL率 |
|-----------|----------|--------|
| parent_id | 638,459 | 7.4% |
| general | 5 | 0.0001% |
| character | 116,714 | 1.4% |
| copyright | 47,596 | 0.6% |
| artist | 85,223 | 1.0% |
| meta | 105,732 | 1.2% |

### 値の分布

| フィールド | ユニーク値数 |
|-----------|-------------|
| rating | 4 (g/s/q/e) |
| file_ext | 5 (jpg/png/gif/webm/mp4) |
| general (組み合わせ) | 693,834 |
| character (組み合わせ) | 99,063 |
| copyright (組み合わせ) | 29,364 |
| artist (組み合わせ) | 53,777 |
| meta (組み合わせ) | 13,924 |

### ステータス分布

| ステータス | True件数 | 割合 |
|-----------|----------|------|
| has_children | 653,857 | 7.6% |
| is_deleted | 860,339 | 10.0% |
| is_banned | 103,241 | 1.2% |

## Quality

### 既知の品質問題

-一部のタグフィールドがNULL（character: 1.4%, artist: 1.0%）
- parent_idが7.4%でNULL（親投稿のない投稿）
- 削除済み投稿が10%含まれる

### データの癖・特殊な値

- `rating` フィールド: g(general), s(safe), q(questionable), e(explicit)
- タグ文字列: スペース区切り（カンマ区切りではない）
- IDは連続していない（削除済み投稿の影響）

### 注意点

- 大規模データセット（5.27GB）のため、メモリ効率的な処理が必要
- 削除済み投稿（is_deleted=true）は除外して使用すべき
- タグ文字列の空白区切りに注意（カンマ区切りではない）

## Lineage

### 変換先

```
danbooru-tags-2024 (0_raw)
    ↓ src/incremental_pickle.py (フィルタリング: deleted/banned除外, score>0, 上位20,000件)
    ↓ src/lightweight_sample.py (テスト用5,000件抽出)
danbooru_tags_top20k.pkl (1_intermediate)
```

### 変換処理の概要

1. **フィルタリング**: is_deleted=false, is_banned=false, score>0
2. **score_per_hour計算**: 時間当たりスコアを計算
3. **上位抽出**: score_per_hour上位20,000件を抽出
4. **保存**: polars DataFrameとしてpickle保存

## Changelog

- 2024-06: データセット取得
- 2024-06: danbooru_tags_top20k.pkl 作成
- 変更なし
