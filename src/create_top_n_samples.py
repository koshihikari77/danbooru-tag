#!/usr/bin/env python3
"""
Danbooru-tags-2024から上位N件のサンプルデータを作成するスクリプト
"""

import polars as pl
import logging
from pathlib import Path
import pickle
from datasets import load_from_disk
import gc
import sys
import argparse

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def filter_active_data(dataset_path: str) -> pl.DataFrame:
    """アクティブデータをフィルタリング"""
    logger.info("データセット読み込み中...")
    dataset = load_from_disk(dataset_path)
    train_dataset = dataset['train']
    
    # メモリ効率のため分割処理
    # まず全体のアクティブデータ数を推定
    logger.info("アクティブデータ数推定中...")
    
    # 最初のチャンクでフィルタリング率を推定
    sample_size = min(100000, len(train_dataset))
    sample_chunk = train_dataset.select(range(sample_size))
    df_sample = pl.from_pandas(sample_chunk.to_pandas())
    
    df_filtered_sample = df_sample.filter(
        (pl.col("is_deleted") == False) &
        (pl.col("is_banned") == False) &
        (pl.col("score") > 0)
    )
    
    filter_rate = len(df_filtered_sample) / len(df_sample)
    logger.info(f"フィルタリング率: {filter_rate:.2%} ({len(df_filtered_sample):,}/{len(df_sample):,})")
    
    # 必要なカラム
    columns_to_keep = [
        'id', 'created_at', 'score', 'rating',
        'image_width', 'image_height', 'file_ext', 'tag_count',
        'tag_count_general', 'tag_count_artist', 'tag_count_character',
        'tag_count_copyright', 'tag_count_meta', 'fav_count',
        'general', 'character', 'copyright', 'artist', 'meta',
        'is_deleted', 'is_banned'
    ]
    
    # 全データをチャンクで処理
    total_size = len(train_dataset)
    chunk_size = 200000
    filtered_dfs = []
    
    logger.info(f"全データ処理開始: {total_size:,}件, チャンクサイズ: {chunk_size:,}件")
    
    for i in range(0, total_size, chunk_size):
        end_idx = min(i + chunk_size, total_size)
        logger.info(f"処理中: {i:,} - {end_idx:,} ({end_idx/total_size:.1%})")
        
        chunk = train_dataset.select(range(i, end_idx))
        df_chunk = pl.from_pandas(chunk.to_pandas())
        
        # フィルタリング
        df_filtered = df_chunk.filter(
            (pl.col("is_deleted") == False) &
            (pl.col("is_banned") == False) &
            (pl.col("score") > 0)
        )
        
        if len(df_filtered) > 0:
            df_filtered = df_filtered.select(columns_to_keep)
            filtered_dfs.append(df_filtered)
        
        # メモリクリーンアップ
        del df_chunk, df_filtered, chunk
        gc.collect()
    
    # 結合
    logger.info("データ結合中...")
    df_all = pl.concat(filtered_dfs)
    
    logger.info(f"アクティブデータ数: {len(df_all):,}件")
    
    return df_all


def extract_top_by_score_per_hour(df: pl.DataFrame, top_n: int) -> pl.DataFrame:
    """時間当たりスコア上位N件を抽出"""
    logger.info(f"時間当たりスコア上位{top_n:,}件抽出中...")
    
    # 日時パース
    df = df.with_columns([
        pl.col("created_at").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.f%z").alias("created_datetime")
    ])
    
    # 最古の日付
    min_date = df.select(pl.col("created_datetime").min()).item()
    logger.info(f"最古日付: {min_date}")
    
    # 時間当たりスコア計算
    df = df.with_columns([
        ((pl.col("created_datetime") - pl.lit(min_date)).dt.total_hours() + 1).alias("hours_since_start")
    ])
    
    df = df.with_columns([
        (pl.col("score") / pl.col("hours_since_start")).alias("score_per_hour")
    ])
    
    # 上位N件抽出
    df_top = df.sort("score_per_hour", descending=True).head(top_n)
    
    logger.info(f"上位{top_n:,}件抽出完了")
    
    return df_top


def extract_random_sample(df: pl.DataFrame, sample_n: int) -> pl.DataFrame:
    """ランダムN件を抽出"""
    logger.info(f"ランダム{sample_n:,}件抽出中...")
    
    if len(df) <= sample_n:
        logger.info(f"データ数が要求数以下のため全件使用: {len(df):,}件")
        return df
    
    # ランダムサンプリング
    df_sample = df.sample(n=sample_n, seed=42, shuffle=True)
    
    logger.info(f"ランダム{sample_n:,}件抽出完了")
    
    return df_sample


def save_sample(df: pl.DataFrame, output_path: str, sample_type: str, n: int):
    """サンプルデータを保存"""
    # 不要なカラム削除
    columns_to_save = [
        'id', 'created_at', 'score', 'rating',
        'image_width', 'image_height', 'file_ext', 'tag_count',
        'tag_count_general', 'tag_count_artist', 'tag_count_character',
        'tag_count_copyright', 'tag_count_meta', 'fav_count',
        'general', 'character', 'copyright', 'artist', 'meta'
    ]
    
    df_to_save = df.select(columns_to_save)
    
    # 追加カラム（score_per_hourがある場合）
    if "score_per_hour" in df.columns:
        df_to_save = df_to_save.with_columns([
            pl.col("created_at").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.f%z").alias("created_datetime")
        ])
        df_to_save = df_to_save.with_columns([
            ((df_to_save["created_datetime"] - df_to_save["created_datetime"].min()).dt.total_hours() + 1).alias("hours_since_start")
        ])
        df_to_save = df_to_save.with_columns([
            (pl.col("score") / pl.col("hours_since_start")).alias("score_per_hour")
        ])
    
    # 保存
    with open(output_path, 'wb') as f:
        pickle.dump(df_to_save, f)
    
    logger.info(f"保存完了: {output_path}")
    logger.info(f"ファイルサイズ: {Path(output_path).stat().st_size / (1024*1024):.2f} MB")
    logger.info(f"レコード数: {len(df_to_save):,}件")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='Danbooruサンプルデータ作成')
    parser.add_argument('--input', type=str, default='data/0_raw/danbooru-tags-2024', help='入力データパス')
    parser.add_argument('--method', type=str, choices=['top', 'random'], default='top', help='抽出方法: top(スコア上位), random(ランダム)')
    parser.add_argument('--n', type=int, nargs='+', default=[1000000, 500000, 100000], help='抽出件数（複数指定可）')
    
    args = parser.parse_args()
    
    input_path = args.input
    method = args.method
    sample_sizes = args.n
    
    logger.info("=== Danbooruサンプルデータ作成 ===")
    logger.info(f"入力パス: {input_path}")
    logger.info(f"抽出方法: {method}")
    logger.info(f"抽出件数: {', '.join([f'{n:,}件' for n in sample_sizes])}")
    
    # アクティブデータフィルタリング
    df_active = filter_active_data(input_path)
    
    if len(df_active) < max(sample_sizes):
        logger.warning(f"アクティブデータ数が最大要求数を下回っています: {len(df_active):,} < {max(sample_sizes):,}")
    
    # 各サイズで抽出・保存
    for n in sample_sizes:
        if n > len(df_active):
            logger.warning(f"要求数{n:,}件がアクティブデータ数を超えているためスキップ")
            continue
        
        if method == 'top':
            df_sample = extract_top_by_score_per_hour(df_active, n)
            # ファイル名生成（100万 -> top1m, 50万 -> top500k, 10万 -> top100k）
            if n >= 1000000:
                sample_type = f"top{n//1000000}m"
            else:
                sample_type = f"top{n//1000}k"
        else:  # random
            df_sample = extract_random_sample(df_active, n)
            if n >= 1000000:
                sample_type = f"random{n//1000000}m"
            else:
                sample_type = f"random{n//1000}k"
        
        # 出力パス
        output_dir = Path("data/1_intermediate")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"danbooru_tags_{sample_type}.pkl"
        
        # 保存
        save_sample(df_sample, str(output_path), sample_type, n)
        
        # 統計表示
        logger.info(f"=== {sample_type} 統計 ===")
        logger.info(f"件数: {len(df_sample):,}")
        if "score_per_hour" in df_sample.columns:
            logger.info(f"score_per_hour 範囲: {df_sample.select('score_per_hour').min().item():.6f} - {df_sample.select('score_per_hour').max().item():.6f}")
        logger.info(f"スコア範囲: {df_sample.select('score').min().item()} - {df_sample.select('score').max().item()}")
        logger.info(f"rating分布: {df_sample.group_by('rating').agg(pl.len()).sort('rating', descending=True)}")
        
        # メモリクリーンアップ
        del df_sample
        gc.collect()
    
    logger.info("=== 処理完了 ===")


if __name__ == "__main__":
    main()
