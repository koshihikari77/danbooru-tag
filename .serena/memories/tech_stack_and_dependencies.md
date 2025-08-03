# 技術スタックと依存関係

## 言語・環境
- Python 3.10+（現在3.12使用）
- 依存関係管理: uv
- 仮想環境: uvで管理

## 主要ライブラリ
### スクレイピング・データ取得
- beautifulsoup4>=4.13.4 (HTMLパーサー)
- lxml>=6.0.0 (XMLパーサー)
- requests>=2.32.4 (HTTP)
- selenium>=4.33.0 (ブラウザ自動化)

### データ処理
- polars>=1.31.0 (高速データフレーム)
- pandas>=2.3.0 (データ分析)
- pyarrow>=20.0.0 (列指向データ)
- datasets>=3.6.0 (Hugging Face datasets)

### AI・検索
- llama-index>=0.12.52 (AI検索エンジン)
- llama-index-experimental>=0.5.5

### その他
- pybooru>=4.2.2 (Danbooru API)
- undetected-chromedriver>=3.5.5 (Chrome自動化)
- webdriver-manager>=4.0.2 (WebDriver管理)

## 環境構築コマンド
```bash
cd danbooru_tag
uv sync
```