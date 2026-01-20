#!/usr/bin/env python3
"""
軽量サンプル版: 最初の10万件から上位5000件を抽出
"""

import polars as pl
import logging
from pathlib import Path
import pickle
from datasets import load_from_disk

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def lightweight_sample():
    """軽量サンプル処理"""
    input_path = "data/0_raw/danbooru-tags-2024"
    output_file = "data/danbooru_tags_sample5k.pkl"
    sample_size = 100000  # 最初の10万件
    top_n = 5000  # 上位5000件
    
    logger.info(f"軽量サンプル処理開始: {input_path}")
    
    # データセット読み込み
    dataset = load_from_disk(input_path)
    train_dataset = dataset['train']
    
    logger.info(f"総データ数: {len(train_dataset):,}件")
    logger.info(f"サンプルサイズ: {sample_size:,}件を処理")
    
    # 最初のN件をサンプルとして取得
    sample = train_dataset.select(range(sample_size))
    df = pl.from_pandas(sample.to_pandas())
    
    logger.info(f"サンプル読み込み完了: {len(df):,}件")
    
    # フィルタリング
    df_filtered = df.filter(
        (pl.col("is_deleted") == False) & 
        (pl.col("is_banned") == False) &
        (pl.col("score") > 0)
    )
    
    logger.info(f"アクティブデータ: {len(df_filtered):,}件")
    
    # 必要なカラムのみ選択
    columns_to_keep = [
        'id', 'created_at', 'score', 'rating', 
        'image_width', 'image_height', 'file_ext', 'tag_count',
        'tag_count_general', 'tag_count_artist', 'tag_count_character', 
        'tag_count_copyright', 'tag_count_meta', 'fav_count',
        'general', 'character', 'copyright', 'artist', 'meta'
    ]
    
    df_final = df_filtered.select(columns_to_keep)
    
    # 時間当たりスコア計算
    logger.info("時間当たりスコア計算中...")
    df_final = df_final.with_columns([
        pl.col("created_at").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.f%z").alias("created_datetime")
    ])
    
    min_date = df_final.select(pl.col("created_datetime").min()).item()
    logger.info(f"最古日付: {min_date}")
    
    df_final = df_final.with_columns([
        ((pl.col("created_datetime") - pl.lit(min_date)).dt.total_hours() + 1).alias("hours_since_start")
    ])
    
    df_final = df_final.with_columns([
        (pl.col("score") / pl.col("hours_since_start")).alias("score_per_hour")
    ])
    
    # 上位抽出
    logger.info(f"上位{top_n:,}件を抽出中...")
    top_df = df_final.sort("score_per_hour", descending=True).head(top_n)
    
    # pickle保存
    logger.info(f"結果保存: {output_file}")
    with open(output_file, 'wb') as f:
        pickle.dump(top_df, f)
    
    # 統計表示
    logger.info(f"サンプル処理完了: {len(top_df):,}件")
    logger.info(f"ファイルサイズ: {Path(output_file).stat().st_size:,} bytes")
    
    # 上位10件表示
    logger.info("時間当たりスコア上位10件:")
    top_10 = top_df.head(10).select(['id', 'score', 'score_per_hour', 'rating', 'tag_count'])
    for row in top_10.iter_rows(named=True):
        logger.info(f"  ID:{row['id']}, Score:{row['score']}, Score/h:{row['score_per_hour']:.3f}, Rating:{row['rating']}, Tags:{row['tag_count']}")

if __name__ == "__main__":
    lightweight_sample()