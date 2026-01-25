#!/usr/bin/env python3
"""
GenreAnalyzerの軽量テスト用スクリプト

top20k の一部（例: 5000件）でテストして、
- タグパース（スペース区切り）
- gore フィルタ
- rating フィルタ
が正しく動いているか確認
"""

import sys
import pickle
import logging
from pathlib import Path

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from genre_analyzer import GenreAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_filter_and_parse(sample_size: int = 5000):
    """
    軽量テスト: 最初の sample_size 件でフィルタとパースをテスト
    """
    
    logger.info("="*60)
    logger.info("Test 1: Load and filter light subset")
    logger.info("="*60)
    
    # step1: pickleを読み込んで最初のN件を抽出
    logger.info(f"Loading top20k pickle and extracting first {sample_size} rows...")
    try:
        with open('data/1_intermediate/danbooru_tags_top20k.pkl', 'rb') as f:
            full_df = pickle.load(f)
        
        logger.info(f"Full top1m shape: {full_df.shape}")
        
        # 最初の sample_size 件を抽出
        test_df = full_df.head(sample_size)
        logger.info(f"Test subset shape: {test_df.shape}")
        
        # 一時的に test_df に置き換えるため、アナライザーをモック
        analyzer = GenreAnalyzer(rating_filter='nsfw', remove_generic=False)
        analyzer.posts_df = test_df.clone()
        
        # filter_posts テスト
        logger.info("\nTesting filter_posts()...")
        filtered = analyzer.filter_posts()
        logger.info(f"Filtered shape: {filtered.shape}")
        
        # rating 分布確認
        logger.info("\nRating distribution in test subset:")
        rating_counts = test_df['rating'].value_counts().to_dicts()
        for row in rating_counts:
            # polars は {'rating': value, 'count': count} の形式
            logger.info(f"  {row['rating']}: {row['count']}")
        
        # フィルタ後の rating 分布
        logger.info("\nRating distribution after NSFW filter (q,e):")
        rating_filtered = filtered['rating'].value_counts().to_dicts()
        for row in rating_filtered:
            logger.info(f"  {row['rating']}: {row['count']}")
        
        # general タグサンプル確認
        logger.info("\nSample general tags (from filtered):")
        for i in range(min(3, len(filtered))):
            general_str = filtered['general'][i]
            tags = general_str.split() if general_str else []
            logger.info(f"  Post {i}: {len(tags)} tags, first 5: {tags[:5]}")
        
        # parse_general_tags テスト
        logger.info("\nTesting parse_general_tags()...")
        tag_freq = analyzer.parse_general_tags(include_count=True)
        logger.info(f"Unique general tags: {len(tag_freq)}")
        logger.info(f"Top 10 tags:")
        for tag, freq in sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {tag}: {freq}")
        
        logger.info("\n" + "="*60)
        logger.info("Test 1: PASSED")
        logger.info("="*60)
        
        return True
        
    except FileNotFoundError as e:
        logger.error(f"Pickle file not found: {e}")
        return False
    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return False


def test_wiki_extraction():
    """
    軽量テスト: wiki から see also リンク抽出をテスト
    """
    
    logger.info("\n" + "="*60)
    logger.info("Test 2: Wiki see also extraction")
    logger.info("="*60)
    
    try:
        analyzer = GenreAnalyzer()
        
        logger.info("Loading wiki pickle...")
        with open('data/0_raw/danbooru-wiki-2024_df.pkl', 'rb') as f:
            wiki_df = pickle.load(f)
        
        analyzer.wiki_df = wiki_df.head(1000)  # 最初の 1000 件でテスト
        logger.info(f"Wiki test subset shape: {analyzer.wiki_df.shape}")
        
        logger.info("Extracting see also links...")
        links = analyzer.extract_see_also_links()
        
        logger.info(f"Found see also links for {len(links)} tags")
        
        # サンプル表示
        count = 0
        for tag, linked_tags in links.items():
            if linked_tags:
                logger.info(f"  {tag} -> {linked_tags}")
                count += 1
                if count >= 5:
                    break
        
        logger.info("\n" + "="*60)
        logger.info("Test 2: PASSED")
        logger.info("="*60)
        
        return True
        
    except FileNotFoundError as e:
        logger.error(f"Wiki pickle file not found: {e}")
        return False
    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return False


if __name__ == '__main__':
    result1 = test_filter_and_parse(sample_size=5000)
    result2 = test_wiki_extraction()
    
    if result1 and result2:
        logger.info("\n✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n✗ Some tests failed")
        sys.exit(1)
