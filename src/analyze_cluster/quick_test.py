#!/usr/bin/env python3
"""
GenreAnalyzerの各メソッドをシンプルにテスト
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from genre_analyzer import GenreAnalyzer

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_basic_flow():
    """基本フロー: load → filter → parse → edges → graph → cluster"""
    
    logger.info("Test: Basic pipeline flow with top20k")
    logger.info("="*60)
    
    try:
        # インスタンス化
        logger.info("1. Creating analyzer...")
        analyzer = GenreAnalyzer(
            top1m_path='data/1_intermediate/danbooru_tags_top20k.pkl',
            wiki_path='data/0_raw/danbooru-wiki-2024_df.pkl',
            rating_filter='nsfw',
            remove_generic=False
        )
        logger.info("   ✓ Analyzer created")
        
        # データ読み込み
        logger.info("2. Loading data...")
        analyzer.load_data()
        logger.info(f"   ✓ Posts: {analyzer.posts_df.shape}")
        logger.info(f"   ✓ Wiki: {analyzer.wiki_df.shape}")
        
        # フィルタ
        logger.info("3. Filtering posts...")
        filtered = analyzer.filter_posts()
        logger.info(f"   ✓ Filtered: {len(filtered)} posts")
        
        # タグパース
        logger.info("4. Parsing tags...")
        tag_freq = analyzer.parse_general_tags(include_count=True)
        logger.info(f"   ✓ Unique tags: {len(tag_freq)}")
        
        # wiki see also
        logger.info("5. Extracting wiki see also...")
        wiki_links = analyzer.extract_see_also_links()
        logger.info(f"   ✓ Wiki links: {len(wiki_links)}")
        
        # 共起エッジ
        logger.info("6. Building cooccurrence edges...")
        edges, filtered_tag_freq = analyzer.build_cooccurrence_edges(
            min_freq=50,
            max_tags_per_post=30,
            top_k_tags=5000,
            min_cooccur=3,
            weight_method='pmi'
        )
        logger.info(f"   ✓ Edges: {sum(len(v) for v in edges.values()) // 2}")
        logger.info(f"   ✓ Filtered tags: {len(filtered_tag_freq)}")
        
        # グラフ構築
        logger.info("7. Building graph...")
        graph = analyzer.build_graph_with_wiki(
            cooccurrence_edges=edges,
            wiki_see_also=wiki_links,
            wiki_weight=0.2
        )
        logger.info(f"   ✓ Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        
        # コミュニティ検出
        logger.info("8. Detecting communities...")
        clusters = analyzer.detect_communities(resolution=1.0)
        logger.info(f"   ✓ Clusters: {len(set(clusters.values()))}")
        
        # 指標計算
        logger.info("9. Computing metrics...")
        df_metrics, metrics_list = analyzer.compute_cluster_metrics()
        logger.info(f"   ✓ Metrics: {len(metrics_list)} clusters with scores")
        
        # 結果表示
        logger.info("\n" + "="*60)
        logger.info("Top 5 genres by opportunity:")
        sorted_metrics = sorted(metrics_list, key=lambda x: x['opportunity'], reverse=True)[:5]
        for i, metric in enumerate(sorted_metrics, 1):
            logger.info(f"  {i}. Cluster {metric['cluster_id']}: opportunity={metric['opportunity']:.2f}, posts={metric['num_posts']}")
        
        logger.info("\n✓ All tests passed!")
        return True
        
    except Exception as e:
        logger.exception(f"Test failed: {e}")
        return False


if __name__ == '__main__':
    success = test_basic_flow()
    sys.exit(0 if success else 1)
