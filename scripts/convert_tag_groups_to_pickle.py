#!/usr/bin/env python3
"""
Tag Groupデータをpolars DataFrameに変換してpickle保存
"""

import json
import polars as pl
import logging
from pathlib import Path

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_tag_groups_to_pickle():
    """Tag Groupデータをpickle化"""
    input_file = "data/0_raw/scalable_scraping_result.json"
    output_file = "data/tag_groups.pkl"
    
    logger.info(f"JSON読み込み開始: {input_file}")
    
    # JSONファイル読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # normalized_data.itemsを取得
    normalized_items = data['normalized_data']['items']
    logger.info(f"アイテム数: {len(normalized_items)}")
    
    # 辞書をリストに変換
    records = []
    for key, item in normalized_items.items():
        # pathをリストから文字列に変換
        path_str = " → ".join(item.get('path', []))
        
        record = {
            'name': item['name'],
            'url': item.get('url', ''),
            'path': path_str,
            'parent': item.get('parent', ''),
            'depth': item['depth'],
            'has_nested_list': item.get('has_nested_list', False),
            'classification': item['classification'],
            'should_follow': item.get('should_follow', False)
        }
        records.append(record)
    
    # polars DataFrameに変換
    logger.info("polars DataFrameに変換中...")
    df = pl.DataFrame(records)
    
    # pickle保存
    logger.info(f"pickle保存: {output_file}")
    Path(output_file).parent.mkdir(exist_ok=True)
    
    import pickle
    with open(output_file, 'wb') as f:
        pickle.dump(df, f)
    
    # 基本情報表示
    logger.info(f"変換完了: {len(df)}件")
    logger.info(f"カラム: {df.columns}")
    logger.info(f"ファイルサイズ: {Path(output_file).stat().st_size:,} bytes")

if __name__ == "__main__":
    convert_tag_groups_to_pickle()