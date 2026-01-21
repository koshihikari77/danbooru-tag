# tag_counts_all.pkl

## 概要

danbooru_tags_top1m.pklからタグごとの出現回数を集計したデータ（全タグ版）。

主な用途:
- タグの人気度分析
- タグの使用頻度調査
- タグ選択の基準データ

## Origin

| 項目 | 値 |
|------|-----|
| 入力データ | danbooru_tags_top1m.pkl (1_intermediate) |
| 変換スクリプト | workspace/create_tag_counts.py |
| 作成日 | 2024年1月 |

## Acquisition

### 取得方法

```bash
# タグカウント作成
python workspace/create_tag_counts.py
```

### 再現手順

1. `data/1_intermediate/danbooru_tags_top1m.pkl` が存在することを確認
2. `python workspace/create_tag_counts.py` 実行

### レート制限/ポリシー

- ローカルファイル処理のため不要

### 失敗時のハンドリング

- チャンク単位（100,000件）で処理・メモリ効率化
- Counterオブジェクトでメモリ効率的な集計

## Schema

### フィールド定義

| カラム | 型 | 説明 | 例 |
|--------|-----|------|-----|
| tag | String | タグ名 | "1girl" |
| tag_type | String | タグタイプ (general/character/copyright/artist/meta/all) | "general" |
| count | Int64 | 出現回数 | 823509 |

### データ例

```json
{
  "tag": "1girl",
  "tag_type": "general",
  "count": 823509
}
```

## Stats

### 基本統計

| 項目 | 値 |
|------|-----|
| 総レコード数 | 185,180件（全タグ種類） |
| ファイル形式 | pickle (polars DataFrame) |
| ファイルサイズ | 9.1MB |

### 全体上位20タグ（タイプ統合）

| ランク | タグ | 出現回数 |
|-------|------|---------|
| 1 | 1girl | 823,509回 |
| 2 | breasts | 779,517回 |
| 3 | highres | 700,280回 |
| 4 | long hair | 599,797回 |
| 5 | solo | 541,671回 |
| 6 | blush | 536,928回 |
| 7 | looking at viewer | 467,720回 |
| 8 | large breasts | 413,162回 |
| 9 | nipples | 325,520回 |
| 10 | open mouth | 307,111回 |
| 11 | commentary request | 304,316回 |
| 12 | navel | 304,090回 |
| 13 | smile | 290,015回 |
| 14 | absurdres | 280,635回 |
| 15 | 1boy | 221,848回 |
| 16 | hetero | 221,616回 |
| 17 | blue eyes | 220,889回 |
| 18 | ass | 218,987回 |
| 19 | commentary | 217,558回 |
| 20 | short hair | 216,074回 |

### タイプ別統計

| タグタイプ | 種類数 | 総出現回数 | 個別ファイル |
|-----------|---------|-----------|------------|
| general | 26,210種類 | 7,765,263回 | tag_counts_general.pkl |
| character | 63,036種類 | 8,239,625回 | tag_counts_character.pkl |
| copyright | 19,640種類 | 8,830,848回 | tag_counts_copyright.pkl |
| artist | 72,011種類 | 817,880回 | tag_counts_artist.pkl |
| meta | 591種類 | 1,770,526回 | tag_counts_meta.pkl |
| **合計** | **181,488種類** | **26,424,142回** | - |

**注意**: タイプ間で重複するタグがあるため、タイプ別合計種類数（181,488種類）は全種類数（185,180種類）より少ない。

### タイプ別上位10タグ

#### General 上位10
| ランク | タグ | 出現回数 |
|-------|------|---------|
| 1 | highres | 471,678回 |
| 2 | 1girl | 449,956回 |
| 3 | solo | 380,832回 |
| 4 | long hair | 265,392回 |
| 5 | looking at viewer | 258,448回 |
| 6 | blue eyes | 244,896回 |
| 7 | breasts | 239,456回 |
| 8 | short hair | 235,632回 |
| 9 | blush | 223,104回 |
| 10 | smile | 207,008回 |

#### Character 上位10
| ランク | タグ | 出現回数 |
|-------|------|---------|
| 1 | original | 277,760回 |
| 2 | touhou | 42,251回 |
| 3 | fate | 50,578回 |
| 4 | pokémon | 30,817回 |
| 5 | kantai collection | 28,299回 |
| 6 | pokémon | 30,817回 |
| 7 | kaguya-sama | 27,760回 |
| 8 | f/series | 30,923回 |
| 9 | order | 38,788回 |
| 10 | idolmaster | 30,919回 |

#### Copyright 上位10
| ランク | タグ | 出現回数 |
|-------|------|---------|
| 1 | fate/grand order | 70,814回 |
| 2 | genshin impact | 56,644回 |
| 3 | blue archive | 69,751回 |
| 4 | hololive | 43,938回 |
| 5 | touhou project | 42,251回 |
| 6 | fate | 50,578回 |
| 7 | azur lane | 41,784回 |
| 8 | lane | 39,991回 |
| 9 | idolmaster | 30,919回 |
| 10 | pokémon | 30,817回 |

#### Artist 上位10
| ランク | タグ | 出現回数 |
|-------|------|---------|
| 1 | hara (harayutaka) | 2,128回 |
| 2 | m-da s-tarou | 2,103回 |
| 3 | nyantcha | 1,877回 |
| 4 | hews | 1,754回 |
| 5 | ebifurya | 1,692回 |
| 6 | neocoill | 1,493回 |
| 7 | tony taka | 1,352回 |
| 8 | afrobull | 1,345回 |
| 9 | fumihiko (fu mihi ko) | 1,314回 |
| 10 | a1 (initial-g) | 1,282回 |

#### Meta 上位10
| ランク | タグ | 出現回数 |
|-------|------|---------|
| 1 | highres | 471,678回 |
| 2 | commentary request | 304,316回 |
| 3 | absurdres | 280,635回 |
| 4 | commentary | 217,558回 |
| 5 | bad id | 111,376回 |
| 6 | english commentary | 95,970回 |
| 7 | bad pixiv id | 80,619回 |
| 8 | photoshop (medium) | 78,875回 |
| 9 | translated | 47,006回 |
| 10 | commission | 37,131回 |

## Quality

### 既知の品質問題

- なし

### データの癖・特殊な値

- タグはカンマ区切りで正確に分割されている
- タイプ間で重複するタグがある（例: "highres"がgeneralとmetaの両方に存在）
- 各タイプ内ではタグ名は一意

### 注意点

- このファイル（tag_counts_all.pkl）は全185,180種類のタグを含む
- タイプ別の詳細は個別ファイル（tag_counts_*.pkl）を参照
- タイプ間の重複タグは統合してカウントしている

## Lineage

### 入力

```
danbooru_tags_top1m.pkl (1_intermediate)
```

### 出力

```
tag_counts_all.pkl (1_intermediate) - 全タグ（185,180種類）
tag_counts_general.pkl (1_intermediate)
tag_counts_character.pkl (1_intermediate)
tag_counts_copyright.pkl (1_intermediate)
tag_counts_artist.pkl (1_intermediate)
tag_counts_meta.pkl (1_intermediate)
```

### 変換処理の概要

1. **データ読み込み**: danbooru_tags_top1m.pkl を読み込み
2. **タグ分割**: 各タグタイプ（general, character, copyright, artist, meta）の文字列をカンマ区切りで分割
3. **カウント**: Counterオブジェクトで各タグの出現回数を集計
4. **DataFrame変換**: Counterをpolars DataFrameに変換
5. **ソート**: 出現回数で降順ソート
6. **統合**: タイプ間で同じタグ名がある場合は合計
7. **保存**: pickle形式で保存

### タグ分割の修正履歴

- 2024-01-20: 初版はスペース区切りで分割（不正確）
- 2024-01-20: カンマ区切りに修正（正確）

## Changelog

- 2024-01-20: create_tag_counts.py 作成
- 2024-01-20: タグ分割方法をスペース区切りからカンマ区切りに修正
- 2024-01-20: tag_counts_all.pklを全185,180種類に拡張（元は20件のみ）
- 変更なし
