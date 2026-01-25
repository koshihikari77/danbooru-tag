#!/usr/bin/env python3
"""
danbooruジャンル分析パイプライン実行スクリプト

実行流:
1. GenreAnalyzer インスタンス化
2. load_data() → filter_posts()
3. parse_general_tags()
4. extract_see_also_links()
5. build_cooccurrence_edges()
6. build_graph_with_wiki()
7. detect_communities()
8. compute_cluster_metrics()
9. 結果を parquet / markdown に出力
"""

import sys
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
# `GenreAnalyzer` は `src/analyze_cluster/genre_analyzer.py` にある
sys.path.insert(0, str(project_root / 'src' / 'analyze_cluster'))

from genre_analyzer import GenreAnalyzer
import polars as pl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """パイプライン実行"""
    
    logger.info("="*70)
    logger.info("Starting danbooruジャンル分析パイプライン (top20k)")
    logger.info("="*70)
    
    # 出力ディレクトリ準備
    output_dir = Path(__file__).parent.parent / 'data' / '2_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    
    # アナライザー初期化
    analyzer = GenreAnalyzer(
        top1m_path='data/1_intermediate/danbooru_tags_top20k.pkl',
        wiki_path='data/0_raw/danbooru-wiki-2024_df.pkl',
        rating_filter='nsfw',
        remove_generic=False
    )
    
    # ステップ1: データ読み込み
    logger.info("\n[Step 1] Loading data...")
    analyzer.load_data()
    
    # ステップ2: 投稿フィルタ
    logger.info("\n[Step 2] Filtering posts (NSFW + gore)...")
    filtered = analyzer.filter_posts()
    logger.info(f"Filtered posts: {len(filtered)}")
    
    # ステップ3: タグパース
    logger.info("\n[Step 3] Parsing general tags...")
    tag_freq = analyzer.parse_general_tags(include_count=True)
    logger.info(f"Unique tags: {len(tag_freq)}")
    top_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    logger.info(f"Top 20 tags: {top_tags}")
    
    # ステップ4: wiki see also 抽出
    logger.info("\n[Step 4] Extracting wiki see also links...")
    wiki_links = analyzer.extract_see_also_links()
    logger.info(f"Wiki links: {len(wiki_links)}")
    
    # ステップ5: 共起エッジ構築
    logger.info("\n[Step 5] Building cooccurrence edges...")
    edges, filtered_tag_freq = analyzer.build_cooccurrence_edges(
        min_freq=50,
        max_tags_per_post=30,
        top_k_tags=10000,
        min_cooccur=5,
        weight_method='pmi'
    )
    logger.info(f"Edges: {sum(len(v) for v in edges.values()) // 2}")
    logger.info(f"Filtered tags: {len(filtered_tag_freq)}")
    
    # ステップ6: グラフ構築
    logger.info("\n[Step 6] Building graph with wiki edges...")
    graph = analyzer.build_graph_with_wiki(
        cooccurrence_edges=edges,
        wiki_see_also=wiki_links,
        wiki_weight=0.2
    )
    logger.info(f"Graph nodes: {graph.number_of_nodes()}, edges: {graph.number_of_edges()}")
    
    # ステップ7: コミュニティ検出
    logger.info("\n[Step 7] Detecting communities...")
    clusters = analyzer.detect_communities(resolution=1.0)
    logger.info(f"Clusters: {len(set(clusters.values()))}")
    
    # ステップ8: 指標計算
    logger.info("\n[Step 8] Computing cluster metrics...")
    df_metrics, metrics_list = analyzer.compute_cluster_metrics()
    logger.info(f"Computed metrics: {len(metrics_list)}")

    # danbooru-only: 投稿→クラスタ割当（後段の固有タグ/lift・例投稿で利用）
    post_cluster_df = analyzer.compute_post_cluster()
    
    # 結果出力（Parquet）
    logger.info("\n[Step 9] Saving results...")
    
    # 指標 DataFrame
    metrics_output = output_dir / 'genres.parquet'
    df_metrics.write_parquet(str(metrics_output))
    logger.info(f"Saved metrics to {metrics_output}")
    
    # タグ → クラスタマッピング
    tag_clusters_list = [
        {'tag': tag, 'cluster_id': cid}
        for tag, cid in clusters.items()
    ]
    df_tag_clusters = pl.DataFrame(tag_clusters_list)
    tag_clusters_output = output_dir / 'tag_clusters.parquet'
    df_tag_clusters.write_parquet(str(tag_clusters_output))
    logger.info(f"Saved tag clusters to {tag_clusters_output}")
    
    # Markdown サマリー
    logger.info("\n[Step 10] Generating markdown summary...")
    markdown_path = output_dir.parent / 'analysis' / 'genre_rank.md'
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    # プロジェクト直下にも出したい用途があるので、別ディレクトリも用意
    project_analysis_dir = Path(__file__).parent.parent / 'analysis'
    project_analysis_dir.mkdir(parents=True, exist_ok=True)

    # クラスタの「固有タグ（lift）」を計算
    # lift = P(tag|cluster) / P(tag)
    tags_long = (
        filtered
        .select(['post_id', 'tags'])
        .explode('tags')
        .rename({'tags': 'tag'})
        .filter(pl.col('tag').is_not_null() & (pl.col('tag') != ""))
    )
    post_cluster_key = post_cluster_df.select(['post_id', 'cluster_id'])
    tags_long = tags_long.join(post_cluster_key, on='post_id', how='inner')

    total_posts = filtered.height
    global_tag = tags_long.group_by('tag').len().rename({'len': 'global_posts'})
    cluster_posts = post_cluster_key.group_by('cluster_id').len().rename({'len': 'cluster_posts'})
    cluster_tag = tags_long.group_by(['cluster_id', 'tag']).len().rename({'len': 'cluster_tag_posts'})

    tag_lift = (
        cluster_tag
        .join(global_tag, on='tag', how='left')
        .join(cluster_posts, on='cluster_id', how='left')
        .with_columns([
            (pl.col('cluster_tag_posts') / pl.col('cluster_posts')).alias('p_tag_given_cluster'),
            (pl.col('global_posts') / pl.lit(total_posts)).alias('p_tag'),
        ])
        .with_columns([
            (pl.col('p_tag_given_cluster') / pl.col('p_tag')).alias('lift'),
            (pl.col('p_tag_given_cluster') / pl.col('p_tag')).log().alias('log_lift'),
        ])
        # ノイズ抑制（小さすぎる共起は外す）
        .filter((pl.col('cluster_tag_posts') >= 10) & (pl.col('global_posts') >= 50))
        .sort(['cluster_id', 'log_lift'], descending=[False, True])
        .group_by('cluster_id')
        .agg([pl.col('tag').head(15).alias('distinctive_tags')])
    )
    distinctive_map = {row['cluster_id']: row['distinctive_tags'] for row in tag_lift.to_dicts()}
    
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write("# danbooruジャンル分析結果\n\n")
        f.write("## 概要\n\n")
        f.write(f"- 対象データ: `danbooru_tags_top20k.pkl`\n")
        f.write(f"- レーティングフィルタ: NSFW (q,e)\n")
        f.write(f"- 投稿数: {len(filtered)}\n")
        f.write(f"- 一般タグ数: {len(tag_freq)}\n")
        f.write(f"- グラフノード数: {graph.number_of_nodes()}\n")
        f.write(f"- グラフエッジ数: {graph.number_of_edges()}\n")
        f.write(f"- 検出クラスタ数: {len(set(clusters.values()))}\n\n")
        f.write("## 読み方（重要）\n\n")
        f.write("- このクラスタは「一緒に付くタグの塊（共起コミュニティ）」です。\n")
        f.write("- `代表タグ` は“頻出タグ”なので汎用タグに寄りがちです。\n")
        f.write("- なので後段で `固有タグ（lift上位）` と `例投稿のタグ束` を併記します。\n\n")
        
        f.write("## 上位ジャンル（danbooru-only）\n\n")
        
        # opportunity でソート
        # 小さすぎるクラスタは解釈が難しいので、メインは投稿数で足切り
        main_metrics = [m for m in metrics_list if m['num_posts'] >= 50]
        niche_metrics = [m for m in metrics_list if m['num_posts'] < 50]
        sorted_metrics = sorted(main_metrics, key=lambda x: x['opportunity'], reverse=True)[:20]
        
        for rank, metric in enumerate(sorted_metrics, 1):
            cluster_id = metric['cluster_id']
            f.write(f"### #{rank} Cluster {cluster_id}\n\n")
            f.write(f"- **投稿数**: {metric['num_posts']}\n")
            f.write(f"- **ユニークタグ数**: {metric['num_unique_tags']}\n")
            f.write(f"- **需要（中央値）**: {metric['demand_median']:.2f}\n")
            f.write(f"- **需要（上位10%平均）**: {metric['demand_top10_avg']:.2f}\n")
            f.write(f"- **競争（投稿数）**: {metric['competition']}\n")
            f.write(f"- **Opportunity**: {metric['opportunity']:.2f}\n")
            f.write(f"- **代表タグ**: `{', '.join(metric['representative_tags'][:15])}`\n\n")
            dtags = distinctive_map.get(cluster_id, [])
            if dtags:
                f.write(f"- **固有タグ（lift上位）**: `{', '.join(dtags)}`\n\n")

        if niche_metrics:
            f.write("## ニッチ（投稿数<50で高スコアになりがち：参考枠）\n\n")
            for metric in sorted(niche_metrics, key=lambda x: x['demand_median'], reverse=True)[:20]:
                f.write(f"- Cluster {metric['cluster_id']}: posts={metric['num_posts']}, median={metric['demand_median']:.2f}, tags=`{', '.join(metric['representative_tags'][:10])}`\n")
            f.write("\n")
    
    logger.info(f"Saved markdown to {markdown_path}")
    
    # danbooru-only: クラスタ別の例投稿（上位スコア + タグ束）を作る
    logger.info("\n[Step 11] Building per-cluster example posts (danbooru-only)...")

    examples = (
        post_cluster_df
        .sort(['cluster_id', 'score'], descending=[False, True])
        .group_by('cluster_id')
        .agg([
            pl.col('id').head(5).alias('top_post_ids'),
            pl.col('score').head(5).alias('top_post_scores'),
            pl.col('created_datetime').head(5).alias('top_post_created')
        ])
    )

    examples_output = output_dir / 'cluster_examples.parquet'
    examples.write_parquet(str(examples_output))
    logger.info(f"Saved examples to {examples_output}")

    # Markdown にも例投稿を追記（タグ束付き）
    # id -> tags(先頭20) を作って結合
    tags_by_id = (
        filtered
        .select(['id', 'tags'])
        .with_columns([pl.col('tags').list.head(20).alias('tags20')])
        .select(['id', 'tags20'])
    )

    # 例投稿のタグ束を cluster_idごとに作る（id毎）
    example_rows = (
        post_cluster_df
        .sort(['cluster_id', 'score'], descending=[False, True])
        .group_by('cluster_id')
        .agg([pl.col('id').head(5).alias('top_post_ids')])
        .explode('top_post_ids')
        .rename({'top_post_ids': 'id'})
        .join(tags_by_id, on='id', how='left')
        .group_by('cluster_id')
        .agg([
            pl.col('id').alias('example_ids'),
            pl.col('tags20').alias('example_tags20')
        ])
    )

    with open(markdown_path, 'a', encoding='utf-8') as f:
        f.write("\n## 上位ジャンルの例投稿（上位スコア）\n\n")
        top20 = [m['cluster_id'] for m in sorted_metrics]
        ex_map = {row['cluster_id']: row for row in examples.filter(pl.col('cluster_id').is_in(top20)).to_dicts()}
        tag_map = {row['cluster_id']: row for row in example_rows.filter(pl.col('cluster_id').is_in(top20)).to_dicts()}
        for rank, metric in enumerate(sorted_metrics, 1):
            cid = metric['cluster_id']
            f.write(f"### #{rank} Cluster {cid} の例投稿\n\n")
            row = ex_map.get(cid)
            if not row:
                f.write("- 例投稿: なし\n\n")
                continue
            ids = row['top_post_ids']
            scores = row['top_post_scores']
            f.write("- 例投稿（id:score）:\n")
            for pid, sc in zip(ids, scores):
                f.write(f"  - {pid}:{sc}\n")
            trow = tag_map.get(cid)
            if trow and trow.get('example_tags20'):
                f.write("- 例投稿のタグ束（先頭20）:\n")
                for pid, tags20 in zip(trow['example_ids'], trow['example_tags20']):
                    f.write(f"  - {pid}: `{', '.join(tags20) if tags20 else ''}`\n")
            f.write("\n")

    # 追加: 全クラスタを上位と同形式で列挙（プロジェクト直下）
    all_md_path = project_analysis_dir / 'genre_rank_all.md'

    # metrics_list は「postクラスタ（mode）」で投稿が付いたクラスタだけになりがちなので、
    # 検出されたクラスタID全体から辞書を組み立てる
    detected_cluster_ids = sorted(set(clusters.values()))
    metrics_by_cid = {m['cluster_id']: m for m in metrics_list}

    # 代表タグのfallback（クラスタに属するタグをグローバル頻度でソート）
    cluster_to_tags = {}
    for tag, cid in clusters.items():
        cluster_to_tags.setdefault(cid, []).append(tag)
    for cid, tags in cluster_to_tags.items():
        cluster_to_tags[cid] = sorted(tags, key=lambda t: tag_freq.get(t, 0), reverse=True)

    # 例投稿マップ（ある分だけ）
    ex_map_all = {row['cluster_id']: row for row in examples.to_dicts()}
    tag_map_all = {row['cluster_id']: row for row in example_rows.to_dicts()}

    # 並びは opportunity降順（無い場合は末尾へ）
    def sort_key(cid: int):
        m = metrics_by_cid.get(cid)
        if m is None:
            return (1, 0.0, -cid)
        return (0, -float(m.get('opportunity', 0.0)), -cid)

    ordered_cids = sorted(detected_cluster_ids, key=sort_key)

    with open(all_md_path, 'w', encoding='utf-8') as f:
        f.write("# danbooruジャンル分析結果（全クラスタ一覧）\n\n")
        f.write("## 概要\n\n")
        f.write(f"- 対象データ: `danbooru_tags_top20k.pkl`\n")
        f.write(f"- レーティングフィルタ: NSFW (q,e)\n")
        f.write(f"- 投稿数: {len(filtered)}\n")
        f.write(f"- 検出クラスタ数: {len(detected_cluster_ids)}\n\n")
        f.write("## 全クラスタ（上位クラスタと同形式）\n\n")

        for rank, cid in enumerate(ordered_cids, 1):
            m = metrics_by_cid.get(cid)
            rep_tags = (m.get('representative_tags') if m else None) or cluster_to_tags.get(cid, [])
            rep_tags = rep_tags[:15]
            dtags = distinctive_map.get(cid, [])

            f.write(f"### #{rank} Cluster {cid}\n\n")
            if m:
                f.write(f"- **投稿数**: {m['num_posts']}\n")
                f.write(f"- **ユニークタグ数**: {m['num_unique_tags']}\n")
                f.write(f"- **需要（中央値）**: {m['demand_median']:.2f}\n")
                f.write(f"- **需要（上位10%平均）**: {m['demand_top10_avg']:.2f}\n")
                f.write(f"- **競争（投稿数）**: {m['competition']}\n")
                f.write(f"- **Opportunity**: {m['opportunity']:.2f}\n")
            else:
                f.write("- **投稿数**: 0\n")
                f.write("- **ユニークタグ数**: 0\n")
                f.write("- **需要（中央値）**: N/A\n")
                f.write("- **需要（上位10%平均）**: N/A\n")
                f.write("- **競争（投稿数）**: 0\n")
                f.write("- **Opportunity**: N/A\n")

            f.write(f"- **代表タグ**: `{', '.join(rep_tags)}`\n\n")
            if dtags:
                f.write(f"- **固有タグ（lift上位）**: `{', '.join(dtags)}`\n\n")

            # 例投稿
            erow = ex_map_all.get(cid)
            if erow:
                ids = erow.get('top_post_ids', [])
                scores = erow.get('top_post_scores', [])
                f.write("- **例投稿（id:score）**:\n")
                for pid, sc in zip(ids, scores):
                    f.write(f"  - {pid}:{sc}\n")
                f.write("\n")

            trow = tag_map_all.get(cid)
            if trow and trow.get('example_tags20'):
                f.write("- **例投稿のタグ束（先頭20）**:\n")
                for pid, tags20 in zip(trow.get('example_ids', []), trow.get('example_tags20', [])):
                    f.write(f"  - {pid}: `{', '.join(tags20) if tags20 else ''}`\n")
                f.write("\n")

    logger.info(f"Saved all-clusters markdown to {all_md_path}")
    
    logger.info("\n" + "="*70)
    logger.info("Pipeline complete!")
    logger.info("="*70)
    logger.info(f"\nOutputs:")
    logger.info(f"  - {metrics_output}")
    logger.info(f"  - {tag_clusters_output}")
    logger.info(f"  - {markdown_path}")
    logger.info(f"  - {examples_output}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        sys.exit(1)
