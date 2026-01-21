# tag_classification_result.pkl

## 概要

tag_groups.pklに特徴分類（feature_category）を追加したデータ。タグがキャラクター固有の特徴かどうかを分類したもの。

主な用途:
- キャラクター特徴の分類・識別
- 人物特徴の分離・置換
- タグ分析・検索

## Origin

| 項目 | 値 |
|------|-----|
| 入力データ | tag_groups.pkl |
| 分類スクリプト | (未特定) |
| 作成日 | 2024年6月 |

## Acquisition

### 取得方法

```python
# tag_groups.pkl に feature_category を追加する処理
# 具体的なスクリプトは未確認
```

### 再現手順

- スクリプトが未特定のため再現手順は不明

### レート制限/ポリシー

- ローカルファイル処理のため不要

### 失敗時のハンドリング

- 入力データの確認

## Schema

### フィールド定義

tag_groups.pklの全カラム + 以下:

| カラム | 型 | 説明 | 例 |
|--------|-----|------|-----|
| (tag_groups.pklの全カラム) | - | - | - |
| feature_category | String | 特徴分類カテゴリ | "character" / "non_character" / "ambiguous" |

### feature_category カテゴリ定義

| カテゴリ | 説明 | 例 |
|---------|------|-----|
| character | キャラクター固有の特徴（目の色、髪型等） | blue_eyes, long_hair |
| non_character | キャラクター非依存の特徴（背景、構図等） | outdoors, solo |
| ambiguous | 判定困難/未分類 | (未特定) |

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
  "should_follow": false,
  "feature_category": "character"
}
```

## Stats

### 基本統計

| 項目 | 値 |
|------|-----|
| 総レコード数 | 15,183件 |
| ファイル形式 | pickle (polars DataFrame) |
| ファイルサイズ | 3.92MB |

### feature_category 分布

| カテゴリ | 件数 | 割合 |
|---------|------|------|
| character | 2,265 | 14.9% |
| non_character | 4,991 | 32.9% |
| ambiguous | 7,927 | 52.2% |

## Quality

### 既知の品質問題

- 半数以上がambiguous（52.2%）で分類が不確定

### データの癖・特殊な値

- 分類が主観的・曖昧なケースが多い
- character/non_characterの境界が明確でない場合あり

### 注意点

- ambiguousの割合が高いため、信頼性には注意が必要
- feature_categoryは手動またはルールベースで分類された可能性あり

## Lineage

### 入力

```
tag_groups.pkl (1_intermediate)
```

### 出力

```
tag_classification_result.pkl (1_intermediate)
```

### 変換処理の概要

1. **入力読み込み**: tag_groups.pkl を読み込む
2. **特徴分類**: 各タグにfeature_categoryを付与
3. **保存**: pickle形式で保存

## Changelog

- 2024-06: feature_category分類実装
- 変更なし
