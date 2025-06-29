# Danbooru Tag Hierarchy Scraper

DanbooruのTag Groupsと個別タグの階層構造を抽出し、包括的な親子関係データベースを構築するスクレイピングシステム。

## 🎯 プロジェクト概要

### 目的
画像に付与されているタグから人物の可変的特徴（目の色、髪の色、胸の大きさなど）を特定・分離し、別の人物特徴への置換を支援する。

### 基本要件
1. **tag group, tagの親子関係**の抽出
2. **tagから親のパス**の特定  
3. **tag groupから属しているtag**の一覧取得

## 🏗️ アーキテクチャ

### コア機能
- **スケーラブル階層スクレイパー**: 全tag groups対応の段階的データ取得
- **4-way分類システム**: タグ種別の自動分類
- **統合処理エンジン**: 冗長なタググループペアの自動統合
- **品質保証システム**: 実データ比較による検証

### 技術スタック
- **言語**: Python 3.12+
- **依存関係管理**: uv
- **HTMLパーサー**: BeautifulSoup4
- **HTTP取得**: curl (subprocess経由)
- **ログ**: 標準logging

## 🚀 使用方法

### 環境セットアップ
```bash
cd danbooru_tag
uv sync
```

### 基本実行
```bash
# 全tag groups処理
python scripts/scalable_hierarchy_scraper.py

# 特定tag group処理
python scripts/scalable_hierarchy_scraper.py --target-groups "Tag group:Body parts"

# レート制限調整
python scripts/scalable_hierarchy_scraper.py --rate-limit 1.0
```

### 検証実行
```bash
# 包括的検証レポート
python tmp/detailed_validation_report.py
```

## 📊 出力データ構造

### メイン出力ファイル
`tmp/scalable_scraping_result.json`

```json
{
  "metadata": {
    "scraper_version": "scalable_v1.0",
    "execution_time": 2.11,
    "config": {
      "target_groups": ["Tag group:Body parts"],
      "rate_limit": 0.5
    }
  },
  "raw_hierarchy_data": {
    "items": {
      "cat ears": {
        "name": "cat ears",
        "path": ["visual characteristics", "body", "tag group:body parts", "tag group:ears tags", "animal ears"],
        "parent": "animal ears",
        "classification": "final_tag_only",
        "should_follow": false
      }
    }
  },
  "normalized_data": {
    "items": {
      "cat ears": {
        "name": "cat ears",
        "path": ["visual characteristics", "body", "tag group:body parts", "tag group:ears tags", "animal ears"],
        "parent": "animal ears",
        "classification": "final_tag_only"
      }
    }
  },
  "statistics": {
    "total_items": 2141,
    "total_followable_items": 32,
    "normalization_changes": 970,
    "removed_duplicates": 75
  }
}
```

## 🎯 4-way分類システム

| 分類 | 定義 | 例 |
|------|------|-----|
| `TAG_AND_TAG_GROUP` | リンク有 + ネストリスト有 + 'tag group'なし | `animal ears` |
| `FINAL_TAG_ONLY` | 最終タグ（ネストリストなし） | `cat ears` |
| `TAG_GROUP_ONLY` | リンクなし + ネストリスト有 | 階層中間ノード |
| `TRADITIONAL_TAG_GROUP` | 'tag group'を名前に含む | `tag group:ears tags` |

## ✨ 統合処理機能

冗長なタググループペアを自動統合：

```
tag group:breasts tags + breasts → breasts
tag group:hair + hair → hair
tag group:ass + ass → ass
```

**統合実績**: 9件のペア統合（2,150項目 → 2,141項目）

## 📈 パフォーマンス

### 処理能力
- **分類項目数**: 2,141項目
- **処理時間**: 約2秒（Body parts）
- **正規化**: 970件の大文字小文字変換
- **重複除去**: 75件の重複処理

### 品質指標
- **テストケース通過率**: 8/8項目（100%）
- **コンプライアンススコア**: 100.0%（EXCELLENT）
- **階層構造検証**: 完全なパス検証済み

## 🔧 技術的特徴

### スケーラブル設計
- **段階的データ取得**: 必要な部分のみ取得
- **メモリ効率**: 大規模データセット対応
- **レート制限**: サーバー負荷軽減（設定可能）

### 堅牢なエラーハンドリング
- **重複処理防止**: processed マーキング
- **循環参照検出**: 階層構造の整合性確保
- **部分失敗対応**: 継続的処理

### 詳細ログ
- **処理トレース**: 各ステップの詳細記録
- **パフォーマンス測定**: 実行時間・統計情報
- **デバッグ支援**: 階層構築過程の可視化

## 📁 プロジェクト構成

```
danbooru_tag/
├── scripts/                          # メインスクリプト
│   └── scalable_hierarchy_scraper.py # 本体スクレイパー (1,004行)
├── docs/                             # ドキュメント
│   ├── want.md                       # 要件仕様
│   ├── test_validation_tags.md       # テストケース定義
│   └── development_history.md        # 開発経緯
├── data/                             # 安定データ
├── tmp/                              # 検証・作業用
│   ├── detailed_validation_report.py # 検証スクリプト
│   ├── scalable_scraping_result.json # 最新結果
│   └── body_parts_validation_summary.md # 検証サマリー
├── CLAUDE.md                         # 開発指針
└── README.md                         # このファイル
```

## 🧪 検証システム

### 実データ比較検証
test_validation_tags.mdで定義された8つのテストケース：

1. ✅ areolae階層構造
2. ✅ large areolae階層構造（修正済み）
3. ✅ breasts統合処理（修正済み）
4. ✅ animal ears sibling ul構造
5. ✅ 4-way分類分布
6. ✅ 正規化処理
7. ✅ 重複除去
8. ✅ 階層パス検証

### 自動品質評価
```bash
python tmp/detailed_validation_report.py
```

**最新結果**: 100.0%コンプライアンス（EXCELLENT評価）

## 🎉 主要成果

### 技術的達成
- **完全階層抽出**: Danbooruの複雑な階層構造を完全解析
- **統合処理**: 冗長データの自動統合による効率化
- **品質保証**: 実データ比較による100%検証

### 実用的価値
- **人物特徴分離**: 可変的特徴タグの自動識別
- **タグ階層マップ**: 完全な親子関係データベース
- **拡張性**: 新しいtag groupsへの自動対応

### 技術的レガシー
- **再利用可能設計**: 他の階層構造サイトへの応用可能
- **スケーラブルパターン**: 大規模Webスクレイピングの参考実装
- **品質保証手法**: 実データ比較検証の確立

## 📝 ライセンス

このプロジェクトは個人研究目的で開発されました。Danbooruのコンテンツは各権利者に帰属します。