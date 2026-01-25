#!/usr/bin/env python3
"""
Pixivジャンル分析パイプライン - コア分析モジュール

danbooruのタグ共起→コミュニティ検出→ジャンル指標化
"""

import pickle
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import polars as pl
import numpy as np
import re
from collections import Counter, defaultdict
import gc

import networkx as nx
try:
    import leidenalg
    HAS_LEIDEN = True
except ImportError:
    HAS_LEIDEN = False
try:
    import igraph as ig  # leidenalg用
    HAS_IGRAPH = True
except ImportError:
    HAS_IGRAPH = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GenreAnalyzer:
    """Pixivジャンル分析のメインクラス"""
    
    GORE_BLOCKLIST = {
        'guro', 'gore', 'dismemberment', 'decapitation', 'corpse', 'blood',
        'extreme_content', 'death', 'violence', 'injury'
    }
    
    COMMON_GENERIC_TAGS = {
        '1girl', 'solo', 'looking_at_viewer', 'simple_background',
        '1boy', 'monochrome', 'no_humans', 'totally_nude'
    }
    
    def __init__(self, 
                 top1m_path: str = 'data/1_intermediate/danbooru_tags_top20k.pkl',
                 wiki_path: str = 'data/0_raw/danbooru-wiki-2024_df.pkl',
                 rating_filter: str = 'nsfw',
                 remove_generic: bool = False):
        self.top1m_path = top1m_path
        self.wiki_path = wiki_path
        self.rating_filter = rating_filter
        self.remove_generic = remove_generic
        
        self.posts_df: Optional[pl.DataFrame] = None
        self.wiki_df: Optional[pl.DataFrame] = None
        self.filtered_posts: Optional[pl.DataFrame] = None
        self.tag_to_cluster: Dict[str, int] = {}
        self.graph: Optional[nx.Graph] = None
        self.tag_freq: Dict[str, int] = {}
        # 高速パス用（polars）
        self._posts_with_tags: Optional[pl.DataFrame] = None
        self._edge_df: Optional[pl.DataFrame] = None
        
    def load_data(self):
        """pickleファイルからデータ読み込み"""
        logger.info(f"Loading posts from {self.top1m_path}...")
        with open(self.top1m_path, 'rb') as f:
            self.posts_df = pickle.load(f)
        logger.info(f"Posts shape: {self.posts_df.shape}")
        
        logger.info(f"Loading wiki from {self.wiki_path}...")
        with open(self.wiki_path, 'rb') as f:
            self.wiki_df = pickle.load(f)
        logger.info(f"Wiki shape: {self.wiki_df.shape}")

    def _ensure_polars(self, df) -> pl.DataFrame:
        """pandas/polarsをpolarsに統一"""
        if isinstance(df, pl.DataFrame):
            return df
        return pl.from_pandas(df)

    def _with_post_id_and_tags(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        post_id と tags(list[str]) を追加。
        注意: 現状の top20k の `general` は「カンマ区切り」のタグ列で、
        タグ自体がスペースを含む（例: "long hair"）ため、スペースsplitは不可。
        """
        if 'post_id' not in df.columns:
            df = df.with_row_index('post_id')

        general_clean = (
            pl.col('general')
            .cast(pl.Utf8)
            .fill_null("")
            .str.strip_chars()
        )

        # "," があるならカンマ区切りでsplit（タグの中のスペースは保持）
        # カンマが無いデータが来た場合のみスペースsplitへフォールバック
        tags = (
            pl.when(general_clean.str.contains(",", literal=True))
            .then(general_clean.str.split(","))
            .otherwise(general_clean.str.split(" "))
            .alias('tags')
        )
        df = df.with_columns([tags])

        # 空文字を落とす / 汎用タグを落とす（必要なら）
        df = df.with_columns([
            pl.col('tags')
            .list.eval(
                pl.when(pl.element().str.strip_chars() == "")
                .then(None)
                .otherwise(pl.element().str.strip_chars())
            )
            .list.drop_nulls()
            .alias('tags')
        ])

        if self.remove_generic:
            generic = list(self.COMMON_GENERIC_TAGS)
            df = df.with_columns([
                pl.col('tags')
                .list.eval(
                    pl.when(pl.element().is_in(generic))
                    .then(None)
                    .otherwise(pl.element())
                )
                .list.drop_nulls()
                .alias('tags')
            ])

        return df
        
    def filter_posts(self) -> pl.DataFrame:
        """投稿フィルタ: rating + gore除外"""
        if self.posts_df is None:
            raise ValueError("Call load_data() first")
        
        logger.info(f"Filtering posts with rating={self.rating_filter}...")
        df = self._ensure_polars(self.posts_df).clone()
        
        if self.rating_filter == 'safe':
            df = df.filter(pl.col('rating').is_in(['g', 's']))
        elif self.rating_filter == 'nsfw':
            df = df.filter(pl.col('rating').is_in(['q', 'e']))
        
        logger.info(f"After rating filter: {len(df)} posts")

        # tags列を作って、goreをvectorizedに落とす
        df = self._with_post_id_and_tags(df)

        gore = list(self.GORE_BLOCKLIST)
        df = df.with_columns([
            pl.col('tags')
            .list.eval(pl.element().is_in(gore))
            .list.any()
            .alias('_has_gore')
        ])

        gore_count = df.select(pl.col('_has_gore').sum()).item()
        logger.info(f"Found {gore_count} posts with gore tags, removing...")

        df = df.filter(~pl.col('_has_gore')).drop('_has_gore')
        logger.info(f"After gore filter: {len(df)} posts")
        
        self.filtered_posts = df
        self._posts_with_tags = df
        return df
    
    def parse_general_tags(self, include_count: bool = False) -> Dict[str, int]:
        """filtered_posts から general タグをパース"""
        if self.filtered_posts is None:
            raise ValueError("Call filter_posts() first")
        
        logger.info("Parsing general tags (polars fast path)...")
        df = self.filtered_posts
        if 'tags' not in df.columns:
            df = self._with_post_id_and_tags(df)
        freq_df = (
            df.select(pl.col('tags').explode().alias('tag'))
            .filter(pl.col('tag') != "")
            .group_by('tag')
            .len()
            .rename({'len': 'freq'})
        )
        tag_counter = dict(zip(freq_df['tag'].to_list(), freq_df['freq'].to_list()))
        logger.info(f"Total unique general tags: {len(tag_counter)}")
        self.tag_freq = tag_counter
        
        if include_count:
            return self.tag_freq
        else:
            return {tag: 0 for tag in self.tag_freq}
    
    def extract_see_also_links(self) -> Dict[str, Set[str]]:
        """wiki body から see also タグリンクを抽出"""
        if self.wiki_df is None:
            raise ValueError("Call load_data() first")
        
        logger.info("Extracting see also links from wiki...")
        
        link_pattern = re.compile(r'\[\[([^\]]+)\]\]')
        see_also_pattern = re.compile(r'(?:h[1-6]\.|^).*[Ss]ee\s+also.*?(?=(?:h[1-6]\.|$))', re.MULTILINE | re.DOTALL)
        
        tag_links = defaultdict(set)
        
        # polars/pandas 両対応
        wiki_df = self.wiki_df
        is_polars = hasattr(wiki_df, 'iter_rows')
        
        if is_polars:
            rows_iter = enumerate(wiki_df.iter_rows(named=True))
            total_len = len(wiki_df)
        else:
            # pandas
            rows_iter = enumerate(wiki_df.itertuples(index=False, name='Row'))
            total_len = len(wiki_df)
        
        for i, row in rows_iter:
            if i % 50000 == 0:
                logger.info(f"Processed {i}/{total_len} wiki pages")
            
            if is_polars:
                tag = row.get('tag') or row.get('title')
                body = row.get('body')
            else:
                # pandas namedtuple
                tag = getattr(row, 'tag', None) or getattr(row, 'title', None)
                body = getattr(row, 'body', None)
            
            if not tag or not body or not isinstance(body, str):
                continue
            
            see_also_sections = see_also_pattern.findall(body)
            if see_also_sections:
                for section in see_also_sections:
                    links = link_pattern.findall(section)
                    tag_links[tag].update(links)
            else:
                tail = body[-2000:] if len(body) > 2000 else body
                if 'see' in tail.lower() or 'also' in tail.lower():
                    links = link_pattern.findall(tail)
                    tag_links[tag].update(links)
        
        logger.info(f"Extracted see also links for {len(tag_links)} tags")
        
        return dict(tag_links)
    
    def build_cooccurrence_edges(self,
                                 min_freq: int = 100,
                                 max_tags_per_post: int = 30,
                                 top_k_tags: Optional[int] = 30000,
                                 min_cooccur: int = 10,
                                 weight_method: str = 'pmi') -> Tuple[Dict[str, List[Tuple[str, float]]], Dict[str, int]]:
        """投稿データから共起エッジを構築（polars中心で高速化）"""
        if self.filtered_posts is None:
            raise ValueError("Call filter_posts() first")

        logger.info("Building cooccurrence edges (polars fast path)...")

        df = self.filtered_posts
        if 'tags' not in df.columns:
            df = self._with_post_id_and_tags(df)

        # 1) タグ頻度
        # explodeするとpost_idも自動的に複製される形で縦持ちになる
        tags_long = (
            df.select(['post_id', 'tags'])
            .explode('tags')
            .rename({'tags': 'tag'})
            .filter(pl.col('tag') != "")
        )

        freq_df = (
            tags_long
            .group_by('tag')
            .len()
            .rename({'len': 'freq'})
            .filter(pl.col('freq') >= min_freq)
        )

        if top_k_tags is not None:
            freq_df = freq_df.sort('freq', descending=True).head(int(top_k_tags))

        filtered_tag_freq = dict(zip(freq_df['tag'].to_list(), freq_df['freq'].to_list()))
        self.tag_freq = filtered_tag_freq

        # 2) 語彙制限＆投稿内上限（頻度で上位max_tags_per_postだけ残す）
        tags_long = (
            tags_long
            .join(freq_df, on='tag', how='inner')
            .sort(['post_id', 'freq'], descending=[False, True])
            .group_by('post_id')
            .head(max_tags_per_post)
            .select(['post_id', 'tag'])
        )

        # 3) 同一post_idでself-joinしてペア生成 → tag_left < tag_right に絞る
        left = tags_long.rename({'tag': 'tag_left'})
        right = tags_long.rename({'tag': 'tag_right'})

        pairs = (
            left.join(right, on='post_id', how='inner')
            .filter(pl.col('tag_left') < pl.col('tag_right'))
            .group_by(['tag_left', 'tag_right'])
            .len()
            .rename({'len': 'cooccur'})
            .filter(pl.col('cooccur') >= min_cooccur)
        )

        # 4) 重み計算（PMI: log(c*N/(f1*f2))）
        N = int(df.height)
        freq_left = freq_df.rename({'tag': 'tag_left', 'freq': 'freq_left'})
        freq_right = freq_df.rename({'tag': 'tag_right', 'freq': 'freq_right'})

        pairs = (
            pairs
            .join(freq_left, on='tag_left', how='left')
            .join(freq_right, on='tag_right', how='left')
        )

        if weight_method == 'pmi':
            pairs = pairs.with_columns([
                (pl.col('cooccur') * N / (pl.col('freq_left') * pl.col('freq_right')))
                .log()
                .alias('weight')
            ])
            # Leidenは負の重みを受け付けないので、正の相関だけ残す（PMI<=0は捨てる）
            pairs = pairs.filter(pl.col('weight') > 0)
        elif weight_method == 'lift':
            pairs = pairs.with_columns([
                (pl.col('cooccur') * N / (pl.col('freq_left') * pl.col('freq_right')))
                .alias('weight')
            ])
        else:
            pairs = pairs.with_columns([pl.col('cooccur').cast(pl.Float64).alias('weight')])

        self._edge_df = pairs.select(['tag_left', 'tag_right', 'weight'])

        # 互換のため dict へ（必要なら後で削る）
        edges = defaultdict(list)
        for row in self._edge_df.iter_rows(named=True):
            t1 = row['tag_left']
            t2 = row['tag_right']
            w = float(row['weight'])
            edges[t1].append((t2, w))
            edges[t2].append((t1, w))

        logger.info(f"Built {self._edge_df.height} edges")
        return dict(edges), filtered_tag_freq
    
    def build_graph_with_wiki(self,
                              cooccurrence_edges: Dict[str, List[Tuple[str, float]]],
                              wiki_see_also: Dict[str, Set[str]],
                              wiki_weight: float = 0.2) -> nx.Graph:
        """共起エッジ + wiki see also を統合してグラフを構築"""
        logger.info("Building graph with cooccurrence + wiki edges...")
        
        G = nx.Graph()
        allowed_tags = set(self.tag_freq.keys()) if self.tag_freq else None
        
        logger.info("Adding cooccurrence edges...")
        edge_count = 0
        for tag1, neighbors in cooccurrence_edges.items():
            for tag2, weight in neighbors:
                G.add_edge(tag1, tag2, weight=weight)
                edge_count += 1
        
        logger.info(f"Added {edge_count} cooccurrence edges")
        
        logger.info("Adding wiki see also edges...")
        wiki_edge_count = 0
        for tag1, related_tags in wiki_see_also.items():
            # 解析対象語彙以外のwikiタグは混ぜない（ノード爆増の抑制）
            if allowed_tags is not None and tag1 not in allowed_tags:
                continue
            for tag2 in related_tags:
                if allowed_tags is not None and tag2 not in allowed_tags:
                    continue
                if G.has_edge(tag1, tag2):
                    current_weight = G[tag1][tag2]['weight']
                    G[tag1][tag2]['weight'] = current_weight + wiki_weight
                else:
                    G.add_edge(tag1, tag2, weight=wiki_weight)
                wiki_edge_count += 1
        
        logger.info(f"Added/modified {wiki_edge_count} wiki see also edges")
        logger.info(f"Final graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        
        self.graph = G
        return G
    
    def detect_communities(self, resolution: float = 1.0) -> Dict[str, int]:
        """Leiden または Louvain でコミュニティ検出"""
        if self.graph is None:
            raise ValueError("Call build_graph_with_wiki() first")
        
        logger.info(f"Detecting communities with resolution={resolution}...")
        
        if not HAS_IGRAPH:
            logger.error("igraph not available, using networkx-based community detection")
            from networkx.algorithms import community
            communities_list = list(community.greedy_modularity_communities(self.graph))
            tag_to_cluster = {}
            for cluster_id, community_nodes in enumerate(communities_list):
                for tag in community_nodes:
                    tag_to_cluster[tag] = cluster_id
            logger.info(f"Detected {len(communities_list)} communities (networkx)")
            self.tag_to_cluster = tag_to_cluster
            return tag_to_cluster
        
        logger.info("Converting networkx graph to igraph...")
        G = self.graph
        
        edges = [(u, v) for u, v in G.edges()]
        weights = [G[u][v]['weight'] for u, v in G.edges()]

        # 文字列頂点のエッジから安全に構築（TupleList）
        g = ig.Graph.TupleList(edges, directed=False, vertex_name_attr='name')
        g.es['weight'] = weights
        
        if HAS_LEIDEN:
            logger.info("Running Leiden algorithm...")
            partition = leidenalg.find_partition(
                g,
                # resolutionを扱えるRBConfigurationを採用（leidenalgの互換性が高い）
                leidenalg.RBConfigurationVertexPartition,
                weights='weight',
                resolution_parameter=resolution,
                seed=42
            )
        else:
            logger.info("Running Louvain algorithm...")
            partition = g.community_multilevel(weights='weight', return_levels=False)
        
        tag_to_cluster = {}
        for cluster_id, member_indices in enumerate(partition):
            for idx in member_indices:
                tag_to_cluster[g.vs[idx]['name']] = cluster_id
        
        logger.info(f"Detected {len(set(tag_to_cluster.values()))} communities")
        
        self.tag_to_cluster = tag_to_cluster
        return tag_to_cluster
    
    def compute_cluster_metrics(self) -> Tuple[pl.DataFrame, List[Dict]]:
        """クラスタ単位で需要/競争/トレンド/Opportunity を計算"""
        if self.filtered_posts is None or self.tag_to_cluster is None:
            raise ValueError("Call filter_posts() and detect_communities() first")
        
        logger.info("Computing cluster metrics (polars fast path)...")

        df = self.filtered_posts
        if 'tags' not in df.columns:
            df = self._with_post_id_and_tags(df)

        tag_cluster_df = pl.DataFrame({
            'tag': list(self.tag_to_cluster.keys()),
            'cluster_id': list(self.tag_to_cluster.values()),
        })

        # 1) 各postでクラスタ出現回数 → 最頻クラスタ(mode)をpostクラスタとして採用
        exploded = (
            df.select(['post_id', 'score', 'tags'])
            .explode('tags')
            .rename({'tags': 'tag'})
            .join(tag_cluster_df, on='tag', how='inner')
        )

        counts = (
            exploded
            .group_by(['post_id', 'cluster_id'])
            .len()
            .rename({'len': 'tag_hits'})
            .sort(['post_id', 'tag_hits'], descending=[False, True])
        )

        post_cluster = counts.unique(subset=['post_id'], keep='first').select(['post_id', 'cluster_id'])

        post_scores = df.select(['post_id', 'score'])
        post_cluster = post_cluster.join(post_scores, on='post_id', how='left')

        # 2) クラスタ別指標
        metrics_df = (
            post_cluster
            .group_by('cluster_id')
            .agg([
                pl.len().alias('num_posts'),
                pl.col('score').median().alias('demand_median'),
                pl.col('score').max().alias('demand_max'),
                pl.col('score').min().alias('demand_min'),
                pl.col('score').quantile(0.9).alias('q90'),
                pl.col('score').mean().alias('demand_mean'),
            ])
            .with_columns([
                # top10%平均（しきい値>=q90）
                pl.lit(0.0).alias('demand_top10_avg')  # 後で置換
            ])
        )

        # top10%平均は、集計結果(q90)を使って再結合して算出
        post_with_q90 = post_cluster.join(metrics_df.select(['cluster_id', 'q90']), on='cluster_id', how='left')
        top10_avg = (
            post_with_q90
            .with_columns([
                pl.when(pl.col('score') >= pl.col('q90')).then(pl.col('score')).otherwise(None).alias('score_top10')
            ])
            .group_by('cluster_id')
            .agg([
                pl.col('score_top10').mean().alias('demand_top10_avg')
            ])
        )

        metrics_df = metrics_df.drop('demand_top10_avg').join(top10_avg, on='cluster_id', how='left')

        # Opportunity（暫定）: median - log(posts)
        metrics_df = metrics_df.with_columns([
            (pl.col('demand_median') - (pl.col('num_posts').cast(pl.Float64).log())).alias('opportunity'),
            pl.lit(0.0).alias('trend_score'),
            pl.col('num_posts').alias('competition'),
        ])

        # 3) 代表タグ（グローバル頻度で上位）
        tag_freq_df = pl.DataFrame({
            'tag': list(self.tag_freq.keys()),
            'freq': list(self.tag_freq.values()),
        })
        rep_tags = (
            tag_cluster_df
            .join(tag_freq_df, on='tag', how='left')
            .with_columns([pl.col('freq').fill_null(0)])
            .sort(['cluster_id', 'freq'], descending=[False, True])
            .group_by('cluster_id')
            .agg([
                pl.col('tag').head(20).alias('representative_tags'),
                pl.len().alias('num_unique_tags'),
            ])
        )

        metrics_df = metrics_df.join(rep_tags, on='cluster_id', how='left')

        # 4) 互換形式へ
        metrics_list = []
        for row in metrics_df.select([
            'cluster_id', 'num_posts', 'num_unique_tags',
            'demand_median', 'demand_top10_avg', 'demand_max', 'demand_min',
            'competition', 'trend_score', 'opportunity', 'representative_tags'
        ]).iter_rows(named=True):
            metrics_list.append({
                'cluster_id': int(row['cluster_id']),
                'num_posts': int(row['num_posts']),
                'num_unique_tags': int(row['num_unique_tags']) if row['num_unique_tags'] is not None else 0,
                'demand_median': float(row['demand_median']) if row['demand_median'] is not None else 0.0,
                'demand_top10_avg': float(row['demand_top10_avg']) if row['demand_top10_avg'] is not None else 0.0,
                'demand_max': float(row['demand_max']) if row['demand_max'] is not None else 0.0,
                'demand_min': float(row['demand_min']) if row['demand_min'] is not None else 0.0,
                'competition': int(row['competition']),
                'trend_score': float(row['trend_score']),
                'opportunity': float(row['opportunity']),
                'representative_tags': row['representative_tags'] if row['representative_tags'] is not None else [],
            })

        logger.info(f"Computed metrics for {len(metrics_list)} clusters")

        df_metrics = metrics_df.select([
            'cluster_id', 'num_posts', 'num_unique_tags',
            'demand_median', 'demand_top10_avg', 'demand_max', 'demand_min',
            'competition', 'trend_score', 'opportunity'
        ])

        return df_metrics, metrics_list

    def compute_post_cluster(self) -> pl.DataFrame:
        """
        各投稿(post_id)をクラスタへ割り当てたDataFrameを返す。
        割り当ては「投稿内で最頻出のcluster_id（mode）」。
        """
        if self.filtered_posts is None or not self.tag_to_cluster:
            raise ValueError("Call filter_posts() and detect_communities() first")

        df = self.filtered_posts
        if 'tags' not in df.columns:
            df = self._with_post_id_and_tags(df)

        tag_cluster_df = pl.DataFrame({
            'tag': list(self.tag_to_cluster.keys()),
            'cluster_id': list(self.tag_to_cluster.values()),
        })

        exploded = (
            df.select(['post_id', 'id', 'score', 'created_datetime', 'created_at', 'tags'])
            .explode('tags')
            .rename({'tags': 'tag'})
            .join(tag_cluster_df, on='tag', how='inner')
        )

        counts = (
            exploded
            .group_by(['post_id', 'cluster_id'])
            .len()
            .rename({'len': 'tag_hits'})
            .sort(['post_id', 'tag_hits'], descending=[False, True])
        )

        post_cluster = counts.unique(subset=['post_id'], keep='first').select(['post_id', 'cluster_id'])

        post_meta = df.select(['post_id', 'id', 'score', 'created_datetime', 'created_at'])

        # created_datetime が無い場合に備えて created_at からパース
        if 'created_datetime' not in post_meta.columns or post_meta['created_datetime'].null_count() == post_meta.height:
            post_meta = post_meta.with_columns([
                pl.col("created_at").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.f%z", strict=False).alias("created_datetime")
            ])

        return post_cluster.join(post_meta, on='post_id', how='left')
