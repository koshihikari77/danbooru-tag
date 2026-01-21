#!/usr/bin/env python3
"""
danbooru_tags_top1m.pklからタグとその出現回数のデータを作成するスクリプト（メモリ効率版）
"""

import polars as pl
import logging
from pathlib import Path
import pickle
from collections import Counter
import gc

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def count_tags_chunked(df: pl.DataFrame, tag_column: str, chunk_size: int = 50000) -> Counter:
    """チャンク単位でタグをカウント"""
    logger.info(f"{tag_column}のタグカウント中（チャンクサイズ: {chunk_size:,}件）...")
    
    # NULL以外のレコードを抽出
    df_filtered = df.filter(pl.col(tag_column).is_not_null())
    
    if len(df_filtered) == 0:
        logger.warning(f"{tag_column}にデータがありません")
        return Counter()
    
    total_rows = len(df_filtered)
    logger.info(f"{tag_column}の有効データ: {total_rows:,}件")
    
    # Counterで集計
    tag_counter = Counter()
    
    for i in range(0, total_rows, chunk_size):
        end_idx = min(i + chunk_size, total_rows)
        
        if i % 500000 == 0:
            logger.info(f"  処理中: {i:,} - {end_idx:,} ({end_idx/total_rows:.1%})")
        
        # チャンクを抽出
        df_chunk = df_filtered[i:end_idx]
        
        # タグ文字列を分割してカウント（カンマ区切り）
        for tag_str in df_chunk[tag_column]:
            if tag_str and isinstance(tag_str, str):
                tags = [tag.strip() for tag in tag_str.split(',') if tag.strip()]
                tag_counter.update(tags)
        
        # メモリクリーンアップ
        del df_chunk
        gc.collect()
    
    logger.info(f"{tag_column}: {len(tag_counter):,}種類のタグ")
    
    return tag_counter


def counter_to_dataframe(counter: Counter, tag_type: str) -> pl.DataFrame:
    """Counterをpolars DataFrameに変換"""
    # DataFrame作成
    data = {"tag": list(counter.keys()), "count": list(counter.values())}
    df = pl.DataFrame(data)
    
    # タイプ追加
    df = df.with_columns([pl.lit(tag_type).alias("tag_type")])
    
    # 降順ソート
    df = df.sort("count", descending=True)
    
    return df


def save_tag_counts(tag_counts: pl.DataFrame, output_path: str, tag_type: str):
    """タグカウントデータを保存"""
    # カラム順序調整
    df_to_save = tag_counts.select(["tag", "tag_type", "count"])
    
    # 保存
    with open(output_path, 'wb') as f:
        pickle.dump(df_to_save, f)
    
    logger.info(f"保存完了: {output_path}")
    logger.info(f"レコード数: {len(df_to_save):,}件")
    logger.info(f"ファイルサイズ: {Path(output_path).stat().st_size / (1024*1024):.2f} MB")
    
    # 上位10件を表示
    top_10 = df_to_save.head(10)
    logger.info(f"{tag_type} タグ上位10件:")
    for row in top_10.iter_rows(named=True):
        logger.info(f"  {row['tag']}: {row['count']:,}回")


def main():
    """メイン処理"""
    logger.info("=== タグカウントデータ作成 ===")
    
    # 入力ファイルパス
    input_path = "data/1_intermediate/danbooru_tags_top1m.pkl"
    logger.info(f"入力ファイル: {input_path}")
    
    # データ読み込み
    logger.info("データ読み込み中...")
    with open(input_path, 'rb') as f:
        df = pickle.load(f)
    
    logger.info(f"読み込み完了: {len(df):,}件")
    
    # 出力ディレクトリ作成
    output_dir = Path("data/1_intermediate")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 各タグタイプを処理
    tag_columns = {
        "general": "general",
        "character": "character",
        "copyright": "copyright",
        "artist": "artist",
        "meta": "meta"
    }
    
    all_tag_counts = []
    
    for tag_type, column_name in tag_columns.items():
        logger.info(f"\n{'='*50}")
        
        # チャンク単位でカウント
        counter = count_tags_chunked(df, column_name, chunk_size=100000)
        
        if len(counter) > 0:
            # DataFrameに変換
            tag_counts_df = counter_to_dataframe(counter, tag_type)
            
            # 個別保存
            output_path = output_dir / f"tag_counts_{tag_type}.pkl"
            save_tag_counts(tag_counts_df, str(output_path), tag_type)
            
            all_tag_counts.append(tag_counts_df)
        
        # メモリクリーンアップ
        del counter
        gc.collect()
    
    # 合計データ作成
    if all_tag_counts:
        logger.info(f"\n{'='*50}")
        logger.info("合計データ作成中...")
        df_combined = pl.concat(all_tag_counts)
        
        # 統計情報
        logger.info("=== 統計情報 ===")
        logger.info(f"総タグ種類数: {df_combined.select('tag').n_unique():,}種類")
        logger.info(f"総出現回数: {df_combined.select('count').sum().item():,}回")
        
        # タグタイプ別の統計
        for tag_type in tag_columns.keys():
            type_stats = df_combined.filter(pl.col("tag_type") == tag_type)
            if len(type_stats) > 0:
                logger.info(f"{tag_type}: {len(type_stats):,}種類, {type_stats.select('count').sum().item():,}回")
        
        # 全体の上位20タグ（タイプ別）
        logger.info("\n=== 全体上位20タグ（タイプ別） ===")
        for tag_type in tag_columns.keys():
            type_stats = df_combined.filter(pl.col("tag_type") == tag_type).sort("count", descending=True).head(20)
            logger.info(f"\n{tag_type} 上位20:")
            for row in type_stats.iter_rows(named=True):
                logger.info(f"  {row['tag']}: {row['count']:,}回")
        
        # 全体のタグ（タイプ統合、全件）
        logger.info("\n=== 全体タグ（タイプ統合・全件） ===")
        df_tag_only = df_combined.group_by("tag").agg(pl.sum("count").alias("count"))
        df_tag_only = df_tag_only.sort("count", descending=True)
        
        # 全件の統計情報
        logger.info(f"総タグ種類数: {len(df_tag_only):,}種類")
        logger.info(f"総出現回数: {df_tag_only.select('count').sum().item():,}回")
        
        # 全体の上位20タグ（タイプ統合）
        logger.info("\n=== 全体上位20タグ（タイプ統合） ===")
        df_top_20 = df_tag_only.head(20)
        for row in df_top_20.iter_rows(named=True):
            logger.info(f"  {row['tag']}: {row['count']:,}回")
        
        # 合計データ保存（タイプ統合・全件）
        df_total = df_tag_only.with_columns([pl.lit("all").alias("tag_type")])
        df_total = df_total.select(["tag", "tag_type", "count"])
        output_path = output_dir / f"tag_counts_all.pkl"
        save_tag_counts(df_total, str(output_path), "all")
    
    logger.info("\n=== 処理完了 ===")


if __name__ == "__main__":
    main()
