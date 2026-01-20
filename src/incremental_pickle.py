#!/usr/bin/env python3
"""
Danbooru-tags-2024をメモリ効率的な分割実行でpickle化
"""

import polars as pl
import logging
from pathlib import Path
import pickle
from datasets import load_from_disk
import gc
import sys

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IncrementalPickler:
    def __init__(self, input_path="data/0_raw/danbooru-tags-2024", chunk_size=50000):
        self.input_path = input_path
        self.chunk_size = chunk_size
        self.state_file = "data/pickle_state.txt"
        self.temp_dir = Path("data/temp_chunks")
        self.temp_dir.mkdir(exist_ok=True)
        
    def save_state(self, processed_chunks: int, total_active: int):
        """処理状態を保存"""
        with open(self.state_file, 'w') as f:
            f.write(f"{processed_chunks},{total_active}")
    
    def load_state(self):
        """処理状態を読み込み"""
        if Path(self.state_file).exists():
            with open(self.state_file, 'r') as f:
                processed_chunks, total_active = map(int, f.read().strip().split(','))
                return processed_chunks, total_active
        return 0, 0
    
    def process_single_chunk(self, chunk_id: int, start_idx: int, end_idx: int):
        """単一チャンクを処理"""
        logger.info(f"=== チャンク {chunk_id}: {start_idx:,} - {end_idx:,} ===")
        
        # データセット読み込み
        dataset = load_from_disk(self.input_path)
        train_dataset = dataset['train']
        
        # チャンクを抽出
        chunk = train_dataset.select(range(start_idx, end_idx))
        df_chunk = pl.from_pandas(chunk.to_pandas())
        
        logger.info(f"チャンク読み込み完了: {len(df_chunk):,}件")
        
        # フィルタリング
        df_filtered = df_chunk.filter(
            (pl.col("is_deleted") == False) & 
            (pl.col("is_banned") == False) &
            (pl.col("score") > 0)
        )
        
        active_count = len(df_filtered)
        logger.info(f"アクティブデータ: {active_count:,}件")
        
        if active_count > 0:
            # 必要なカラムのみ選択
            columns_to_keep = [
                'id', 'created_at', 'score', 'rating', 
                'image_width', 'image_height', 'file_ext', 'tag_count',
                'tag_count_general', 'tag_count_artist', 'tag_count_character', 
                'tag_count_copyright', 'tag_count_meta', 'fav_count',
                'general', 'character', 'copyright', 'artist', 'meta'
            ]
            
            df_final = df_filtered.select(columns_to_keep)
            
            # チャンクを個別保存
            chunk_file = self.temp_dir / f"chunk_{chunk_id:03d}.pkl"
            with open(chunk_file, 'wb') as f:
                pickle.dump(df_final, f)
            
            logger.info(f"チャンク保存完了: {chunk_file}")
        
        # メモリクリーンアップ
        del df_chunk, df_filtered, chunk, train_dataset, dataset
        gc.collect()
        
        return active_count
    
    def run_incremental_processing(self):
        """段階的処理を実行"""
        # データセット情報を取得
        dataset = load_from_disk(self.input_path)
        total_size = len(dataset['train'])
        del dataset
        gc.collect()
        
        logger.info(f"総データ数: {total_size:,}件")
        logger.info(f"チャンクサイズ: {self.chunk_size:,}件")
        
        # 状態復元
        processed_chunks, total_active = self.load_state()
        start_chunk = processed_chunks
        
        if start_chunk > 0:
            logger.info(f"前回の続きから開始: チャンク{start_chunk}から, 累計{total_active:,}件")
        
        # チャンク単位で処理
        chunk_id = start_chunk
        
        for i in range(start_chunk * self.chunk_size, total_size, self.chunk_size):
            end_idx = min(i + self.chunk_size, total_size)
            
            try:
                active_count = self.process_single_chunk(chunk_id, i, end_idx)
                total_active += active_count
                chunk_id += 1
                
                # 状態保存
                self.save_state(chunk_id, total_active)
                
                logger.info(f"進捗: {chunk_id}/{(total_size-1)//self.chunk_size + 1}, 累計アクティブ: {total_active:,}件")
                
                # 5チャンクごとに詳細ログ
                if chunk_id % 5 == 0:
                    logger.info(f"=== 中間報告 ({chunk_id}チャンク完了) ===")
                    logger.info(f"累計アクティブデータ: {total_active:,}件")
                    logger.info(f"処理進捗: {(chunk_id * self.chunk_size / total_size * 100):.1f}%")
                
            except Exception as e:
                logger.error(f"チャンク{chunk_id}でエラー: {e}")
                logger.info(f"現在の状態を保存して終了...")
                self.save_state(chunk_id, total_active)
                return False
        
        logger.info(f"全チャンク処理完了: {total_active:,}件のアクティブデータ")
        return True
    
    def combine_chunks_and_extract_top(self, top_n=20000):
        """チャンクを結合して上位抽出"""
        logger.info("=== チャンク結合と上位抽出 ===")
        
        chunk_files = sorted(self.temp_dir.glob("chunk_*.pkl"))
        logger.info(f"チャンクファイル数: {len(chunk_files)}")
        
        # 最古の日付を推定
        logger.info("最古の日付を推定中...")
        with open(chunk_files[0], 'rb') as f:
            sample_df = pickle.load(f)
        
        sample_df = sample_df.with_columns([
            pl.col("created_at").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.f%z").alias("created_datetime")
        ])
        min_date = sample_df.select(pl.col("created_datetime").min()).item()
        logger.info(f"推定最古日付: {min_date}")
        del sample_df
        gc.collect()
        
        # 上位スコア管理用のヒープ
        import heapq
        top_records = []
        
        # チャンクを順次処理
        for i, chunk_file in enumerate(chunk_files):
            logger.info(f"チャンク結合中: {i+1}/{len(chunk_files)} - {chunk_file.name}")
            
            with open(chunk_file, 'rb') as f:
                df = pickle.load(f)
            
            if len(df) == 0:
                continue
            
            # 時間当たりスコア計算
            df = df.with_columns([
                pl.col("created_at").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.f%z").alias("created_datetime")
            ])
            
            df = df.with_columns([
                ((pl.col("created_datetime") - pl.lit(min_date)).dt.total_hours() + 1).alias("hours_since_start")
            ])
            
            df = df.with_columns([
                (pl.col("score") / pl.col("hours_since_start")).alias("score_per_hour")
            ])
            
            # ヒープで上位管理
            for idx, row in enumerate(df.iter_rows(named=True)):
                score_per_hour = row['score_per_hour']
                
                if len(top_records) < top_n:
                    heapq.heappush(top_records, (score_per_hour, i * 100000 + idx, row))
                elif score_per_hour > top_records[0][0]:
                    heapq.heapreplace(top_records, (score_per_hour, i * 100000 + idx, row))
            
            del df
            gc.collect()
            
            if i % 10 == 0:
                current_min = top_records[0][0] if top_records else 0
                logger.info(f"現在の最小スコア/時間: {current_min:.3f}")
        
        # 最終結果作成
        logger.info("最終結果作成中...")
        final_records = []
        while top_records:
            score_per_hour, idx, record = heapq.heappop(top_records)
            final_records.append(record)
        
        final_records.reverse()  # 降順に
        top_df = pl.DataFrame(final_records)
        
        # 結果保存
        output_file = "data/danbooru_tags_top20k.pkl"
        with open(output_file, 'wb') as f:
            pickle.dump(top_df, f)
        
        logger.info(f"上位データ保存完了: {output_file}")
        logger.info(f"ファイルサイズ: {Path(output_file).stat().st_size:,} bytes")
        
        # 統計表示
        logger.info("時間当たりスコア上位10件:")
        top_10 = top_df.head(10).select(['id', 'score', 'score_per_hour', 'rating', 'tag_count'])
        for row in top_10.iter_rows(named=True):
            logger.info(f"  ID:{row['id']}, Score:{row['score']}, Score/h:{row['score_per_hour']:.3f}, Rating:{row['rating']}, Tags:{row['tag_count']}")
        
        return top_df

def main():
    """メイン処理"""
    if len(sys.argv) > 1:
        action = sys.argv[1]
    else:
        action = "process"
    
    pickler = IncrementalPickler()
    
    if action == "process":
        logger.info("=== 段階的処理開始 ===")
        success = pickler.run_incremental_processing()
        if success:
            logger.info("処理完了。次は 'combine' で結合してください。")
        else:
            logger.info("エラーで中断。修正後、再実行してください。")
    
    elif action == "combine":
        logger.info("=== チャンク結合開始 ===")
        pickler.combine_chunks_and_extract_top()
    
    elif action == "full":
        logger.info("=== 全処理実行 ===")
        success = pickler.run_incremental_processing()
        if success:
            pickler.combine_chunks_and_extract_top()

if __name__ == "__main__":
    main()