#!/usr/bin/env python3
"""
スケーラブル階層スクレイパー
Copyrights, artists, projects and mediaを除く全tagに対応可能な設計
"""

import time
import json
import logging
import os
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum
import re

# ログ用ディレクトリ作成
os.makedirs('tmp', exist_ok=True)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tmp/scalable_scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """新しいノードタイプ分類"""
    TAG_AND_TAG_GROUP = "tag_and_tag_group"      # リンク + 下位リスト + tag group名なし
    TAG_GROUP_ONLY = "tag_group_only"            # 下位リストあり
    FINAL_TAG_ONLY = "final_tag_only"            # 最終タグ
    TRADITIONAL_TAG_GROUP = "traditional_tag_group"  # "tag group"名含有

@dataclass
class ScrapingConfig:
    """スクレイピング設定"""
    rate_limit: float = 1.0
    exclude_sections: List[str] = None
    include_sections: List[str] = None
    ignore_elements: List[str] = None
    max_depth: int = 10
    
    # 範囲指定機能
    target_groups: List[str] = None      # 特定グループのみ処理
    max_groups: int = None               # 処理グループ数上限
    skip_first_n: int = 0               # 最初のN個をスキップ
    group_name_patterns: List[str] = None # 名前パターンマッチ
    
    def __post_init__(self):
        if self.exclude_sections is None:
            self.exclude_sections = [
                "copyrights, artists, projects and media",
                "see also"
            ]
        if self.ignore_elements is None:
            self.ignore_elements = ["see also"]

class RateLimiter:
    """レート制限クラス"""
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.last_request = 0.0
    
    def wait_if_needed(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_request = time.time()

class ScalableHierarchyScraper:
    """スケーラブル階層スクレイパー"""
    
    def __init__(self, config: ScrapingConfig = None):
        self.config = config or ScrapingConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit)
        self.visited_urls: Set[str] = set()
        self.hierarchy_data = {}
        self.complete_paths = {}
        self.excluded_sections = set(s.lower() for s in self.config.exclude_sections)
        self.ignored_elements = set(e.lower() for e in self.config.ignore_elements)
        
        logger.info(f"除外セクション: {self.config.exclude_sections}")
        logger.info(f"無視要素: {self.config.ignore_elements}")
    
    def should_exclude_section(self, section_name: str) -> bool:
        """セクションを除外すべきかチェック"""
        section_lower = section_name.lower().strip()
        
        for excluded in self.excluded_sections:
            if excluded in section_lower:
                return True
        return False
    
    def should_ignore_element(self, element_text: str) -> bool:
        """要素を無視すべきかチェック"""
        element_lower = element_text.lower().strip()
        
        for ignored in self.ignored_elements:
            if ignored in element_lower:
                return True
        return False
    
    
    def _create_item_data(self, name: str, url: str, path: List[str], has_link: bool, 
                         has_nested_list: bool, should_follow: bool = False) -> Dict:
        """アイテムデータを作成"""
        return {
            'name': name,
            'url': url,
            'path': path,
            'parent': path[-2] if len(path) >= 2 else None,
            'depth': len(path),  # 階層深度: パスの長さ = 何階層目か
            'has_nested_list': has_nested_list,
            'classification': self._classify_node(name, has_link, has_nested_list).value,
            'should_follow': should_follow
        }
    
    def should_follow_link(self, link_text: str) -> bool:
        """want.md新仕様: List of/Tag group以外のリンクは追跡しない"""
        link_lower = link_text.lower().strip()
        
        # 追跡対象: "tag group"または"list of"を含むリンク
        if 'tag group' in link_lower or 'list of' in link_lower:
            return True
        
        return False
    
    def convert_wiki_to_post_url(self, wiki_url: str) -> str:
        """want.md新仕様: wikiページのリンクをpostページに変換"""
        if '/wiki_pages/' in wiki_url:
            # wiki_pages/tag_groups → posts?tags=tag_groups
            tag_name = wiki_url.split('/wiki_pages/')[-1]
            return f"https://danbooru.donmai.us/posts?tags={tag_name}"
        return wiki_url
    
    def _classify_priority(self, classification: str) -> int:
        """分類の優先度を返す（高いほど優先）"""
        priorities = {
            'tag_and_tag_group': 4,      # 最優先
            'traditional_tag_group': 3,
            'tag_group_only': 2,
            'final_tag_only': 1          # 最低優先
        }
        return priorities.get(classification, 0)
    
    def _add_item(self, result: Dict, name: str, item_data: Dict):
        """アイテムを追加、重複がある場合は優先度で解決"""
        if name in result['items']:
            existing = result['items'][name]
            new_priority = self._classify_priority(item_data['classification'])
            existing_priority = self._classify_priority(existing['classification'])
            
            # 優先度比較（高い方を採用、同じなら短いパスを採用）
            if (new_priority > existing_priority or 
                (new_priority == existing_priority and len(item_data['path']) < len(existing['path']))):
                result['items'][name] = item_data
        else:
            result['items'][name] = item_data

    def should_process_group(self, group_name: str, index: int, processed_count: int, 
                           item_path: List[str] = None) -> tuple[bool, str]:
        """グループを処理すべきかチェック（除外処理、target_groups、範囲指定統合）"""
        
        # 除外処理チェック（最優先）
        if item_path is not None:
            for path_segment in item_path:
                if self.should_exclude_section(path_segment):
                    return False, f"除外パス内（{path_segment}）"
        
        # グループ名直接除外チェック
        if self.should_exclude_section(group_name):
            return False, f"除外グループ（{group_name}）"
        
        # スキップ数チェック
        if index < self.config.skip_first_n:
            return False, f"スキップ（{index+1}/{self.config.skip_first_n}番目）"
        
        # 処理数上限チェック
        if self.config.max_groups is not None and processed_count >= self.config.max_groups:
            return False, f"上限到達（{processed_count}/{self.config.max_groups}）"
        
        # target_groupsフィルタチェック（統合）
        if self.config.target_groups is not None:
            # 直接一致チェック
            if group_name in self.config.target_groups:
                return True, ""
            
            # pathベースマッチング（_should_skip_by_target_groupsから統合）
            if item_path is not None:
                # pathの中にtarget_groupsのいずれかが含まれている場合は処理対象
                path_matches_target = False
                for target_group in self.config.target_groups:
                    # より厳密なマッチング：完全パス内にtargetが含まれている必要がある
                    full_path_str = ' -> '.join(item_path).lower()
                    if target_group.lower() in full_path_str:
                        path_matches_target = True
                        logger.debug(f"  階層的処理対象: {group_name} (path: {' -> '.join(item_path)})")
                        break
                
                if not path_matches_target:
                    logger.debug(f"target_groups フィルタでスキップ: {group_name} (path: {' -> '.join(item_path)})")
                    return False, f"対象外グループ"
            else:
                # pathがない場合は対象外
                return False, f"対象外グループ"
        
        # パターンマッチングチェック
        if self.config.group_name_patterns is not None:
            import fnmatch
            matched = False
            for pattern in self.config.group_name_patterns:
                if fnmatch.fnmatch(group_name.lower(), pattern.lower()):
                    matched = True
                    break
            if not matched:
                return False, f"パターン不一致"
        
        return True, ""
    
    def _remove_post_page_noise(self, soup: BeautifulSoup):
        """postページ特有の不要な要素を除去"""
        
        # 除去対象のセレクタ（postページのナビゲーション等）
        noise_selectors = [
            'header',           # ヘッダー部分
            'nav',              # ナビゲーション
            '#top',             # トップ部分
            '#nav',             # ナビゲーション
            '#main-menu',       # メインメニュー
            '#subnav-menu',     # サブナビメニュー
            '.search-form',     # 検索フォーム
            '#notice',          # 通知
            '#sidebar',         # サイドバー全体
            'aside',            # サイドバー要素
            '#blacklist-box',   # ブラックリスト
            '#page-footer',     # フッター
            '.post-preview',    # 投稿プレビュー
            '#post-sections',   # 投稿セクション
            '.paginator',       # ページネーション
        ]
        
        # wikiコンテンツ部分のみを取得（postページ内のwiki部分）
        wiki_content = soup.find('div', {'id': 'wiki-page-body'})
        if wiki_content:
            # wiki部分が見つかった場合、それ以外を除去
            for element in soup.find_all():
                if not wiki_content.find_parent() or element not in wiki_content.find_all():
                    if element != wiki_content and not wiki_content in element.find_all():
                        continue
        else:
            # wiki部分が見つからない場合、一般的なノイズ要素を除去
            for selector in noise_selectors:
                for element in soup.select(selector):
                    element.decompose()
        
        # 不要な見出しテキストも除去
        unwanted_headings = [
            'Search', 'Options', 'Edit', 'Related', 'Blacklisted', 'Recent Changes',
            'Tags', 'Comments', 'Notes', 'Artists', 'Pools', 'Wiki', 'Forum'
        ]
        
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if heading.get_text(strip=True) in unwanted_headings:
                heading.decompose()
    
    def webfetch_with_parse(self, url: str, prompt: str) -> Optional[BeautifulSoup]:
        """curlを使用してコンテンツを取得しHTMLパース"""
        logger.info(f"curl実行中: {url}")
        
        try:
            import subprocess
            import tempfile
            import os
            
            self.rate_limiter.wait_if_needed()
            
            # 一時ファイルを作成
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.html', delete=False) as temp_file:
                temp_filename = temp_file.name
            
            # curlコマンドを構築
            curl_command = [
                'curl',
                '--compressed',
                '--silent',
                '--show-error',
                '--fail',
                '--location',
                '--max-time', '30',
                '-H', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                '-H', 'Accept-Language: en-US,en;q=0.5',
                '-H', 'Referer: https://danbooru.donmai.us/',
                '-o', temp_filename,
                url
            ]
            
            # curlを実行
            result = subprocess.run(curl_command, capture_output=True, text=True, timeout=35)
            
            if result.returncode == 0:
                # ファイルを読み込み
                with open(temp_filename, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 一時ファイルを削除
                os.unlink(temp_filename)
                
                if html_content.strip():
                    soup = BeautifulSoup(html_content, 'html.parser')
                    logger.info(f"  ✅ 正常取得: {len(html_content)} bytes")
                    return soup
                else:
                    logger.warning(f"  ❌ 空のレスポンス")
                    return None
            else:
                # エラーハンドリング
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                
                if result.returncode == 22:  # HTTP error
                    if "403" in error_msg:
                        logger.error(f"  ❌ アクセス拒否（403 Forbidden）: {url}")
                        logger.error(f"     サイトがアクセスを制限している可能性があります")
                    elif "404" in error_msg:
                        logger.warning(f"  ❌ ページが見つかりません（404）: {url}")
                    elif "429" in error_msg:
                        logger.warning(f"  ⚠️ レート制限に引っかかりました（429）: {url}")
                        logger.warning(f"     レート制限間隔を増やすことを検討してください（現在: {self.config.rate_limit}秒）")
                    else:
                        logger.error(f"  ❌ HTTPエラー: {error_msg}")
                elif result.returncode == 28:  # Timeout
                    logger.warning(f"  ⏰ タイムアウト: {url}")
                else:
                    logger.error(f"  ❌ curlエラー (code {result.returncode}): {error_msg}")
                
                # 一時ファイルを削除
                if os.path.exists(temp_filename):
                    os.unlink(temp_filename)
                
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning(f"  ⏰ curlプロセスタイムアウト: {url}")
            return None
        except FileNotFoundError:
            logger.error(f"  ❌ curlコマンドが見つかりません。curlがインストールされているか確認してください")
            return None
        except Exception as e:
            logger.error(f"  ❌ 予期しないエラー: {e}")
            return None
    
    
    def extract_hierarchy_from_page(self, soup: BeautifulSoup, base_path: List[str], 
                                   page_url: str = "") -> Dict:
        """ページから階層構造を抽出（除外ルール適用）"""
        result = {
            'headings': [],
            'items': {},  # 統合されたアイテム管理
            'excluded_sections': [],
            'ignored_elements': []
        }
        
        # postページ特有の不要な要素を除去
        self._remove_post_page_noise(soup)
        
        # 見出しを抽出（除外チェック付き）
        current_path = base_path.copy()
        current_heading_stack = []
        current_section = None
        section_excluded = False
        
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul']):
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(element.name[1])
                text = element.get_text(strip=True)
                
                if text:
                    # スタック調整
                    while current_heading_stack and current_heading_stack[-1]['level'] >= level:
                        current_heading_stack.pop()
                    
                    current_heading_stack.append({'level': level, 'text': text})
                    result['headings'].append({'level': level, 'text': text})
                    
                    # want.md要件: 見出しの次にulがある場合はtag group扱いもする
                    next_sibling = element.find_next_sibling()
                    if next_sibling and next_sibling.name == 'ul':
                        # 現在のパスを構築
                        heading_path = base_path.copy()
                        for heading in current_heading_stack[:-1]:  # 自分以外の親見出し
                            heading_path.append(heading['text'])
                        heading_path.append(text)
                    
                        item_data = self._create_item_data(
                            text, None, heading_path, has_link=False, 
                            has_nested_list=True, should_follow=False
                        )
                        self._add_item(result, text, item_data)
            
            elif element.name == 'ul' and element.parent.name != 'li' :
                # 除外されていないセクションのリストのみ処理
                self._process_list_items_with_exclusion(
                    element, current_path, current_heading_stack, result
                )
        
        return result
    
    def _process_list_items_with_exclusion(self, ul_element, base_path: List[str], 
                                         heading_stack: List[Dict], result: Dict):
        """除外ルールを適用してリスト項目を処理"""
        current_path = base_path.copy()
        
        # 現在の見出しをパスに追加
        for heading in heading_stack:
            current_path.append(heading['text'])
        
        # target_groupsフィルタはメインページ（base_pathが空）の時のみ適用
        apply_target_filter = len(base_path) == 0
        self._process_list_recursive(ul_element, current_path, result, depth=0, apply_target_filter=apply_target_filter)
    
    def _process_list_recursive(self, ul_element, current_path: List[str], 
                               result: Dict, depth: int = 0, apply_target_filter: bool = True):
        """再帰的にリスト構造を処理"""
        if depth > self.config.max_depth:
            logger.warning(f"  最大深度 {self.config.max_depth} に到達、処理停止")
            return
        
        for li in ul_element.find_all('li', recursive=False):
            # 既に処理済みのli要素はスキップ
            if li.get('processed') == 'true':
                continue
                
            text = li.get_text(strip=True)
            if not text:
                continue
            
            # ネストしたulのテキストを除去して正確なli文字列を取得
            # 子要素のulと兄弟要素のulの両方をチェック
            nested_ul = li.find('ul')  # 子要素のul
            sibling_ul = li.find_next_sibling('ul')  # 兄弟要素のul
            
            # 既に処理された兄弟ulはスキップ
            if sibling_ul and sibling_ul.get('processed') == 'true':
                logger.debug(f"    [兄弟ulデバッグ] 既に処理済みのulをスキップ: {li.get_text(strip=True)[:50]}...")
                sibling_ul = None
            
            if nested_ul:
                # より安全なテキスト抽出: liの直接の子テキストのみを取得
                clean_text = ""
                for child in li.children:
                    if hasattr(child, 'name') and child.name == 'ul':
                        continue  # ul要素はスキップ
                    if hasattr(child, 'strip'):
                        clean_text += child.strip()
                    elif hasattr(child, 'get_text'):
                        clean_text += child.get_text(strip=True)
                clean_text = clean_text.strip()
                
                # デバッグ出力
                if clean_text and len(clean_text) > 0:
                    logger.debug(f"    [階層デバッグ] 親要素テキスト抽出: '{clean_text}' (nested_ul有り)")
            elif sibling_ul:
                # 兄弟ulの場合、テキスト除去は不要（別要素のため）
                clean_text = text.strip()
            else:
                clean_text = text
            
            # 無視要素チェック
            if self.should_ignore_element(clean_text):
                result['ignored_elements'].append(clean_text)
                logger.debug(f"  要素無視: {clean_text}")
                continue
            
            # リンクチェック
            link = li.find('a')
            if link and 'href' in link.attrs:
                href = link['href']
                link_text = link.get_text(strip=True)
                full_path = current_path + [link_text]
                
                # デバッグ出力：パス構築の詳細
                logger.debug(f"    [パスデバッグ] アイテム='{link_text}', current_path={' -> '.join(current_path)}, full_path={' -> '.join(full_path)}")
                
                # pathベースのtarget_groupsフィルタリング
                if apply_target_filter and self.config.target_groups is not None:
                    path_matches_target = False
                    for target in self.config.target_groups:
                        # より厳密なマッチング：完全パス内にtargetが含まれている必要がある
                        full_path_str = ' -> '.join(full_path).lower()
                        if target.lower() in full_path_str:
                            path_matches_target = True
                            break
                    
                    # 対象外のpathはスキップ
                    if not path_matches_target:
                        logger.debug(f"  target_groups フィルタでスキップ: {link_text} (path: {' -> '.join(full_path)})")
                        continue
                
                # want.md新仕様: リンク追跡制限チェック  
                should_follow = self.should_follow_link(link_text)
                
                # ネストしたリストの存在判定（子要素 or 兄弟要素）
                has_nested_list = nested_ul is not None or sibling_ul is not None
                
                
                # デバッグ: animal earsのような項目の詳細
                if 'animal ears' in link_text.lower():
                    logger.debug(f"    [分析] {link_text}: has_nested={has_nested_list}, has_link=True, tag_group_in_name={'tag group' in link_text.lower()}")
                    if nested_ul is not None:
                        logger.debug(f"        [ネスト詳細] child nested_ul found: {len(nested_ul.find_all('li'))} nested items")
                    if sibling_ul is not None:
                        logger.debug(f"        [兄弟詳細] sibling ul found: {len(sibling_ul.find_all('li'))} items")
                
                # 統一アイテム処理
                item_data = self._create_item_data(
                    link_text, href if should_follow else None, full_path, 
                    has_link=True, has_nested_list=has_nested_list, should_follow=should_follow
                )
                self._add_item(result, link_text, item_data)
            else:
                full_path = current_path + [clean_text]
                
                # 統合処理判定（メインページでのみ）
                if apply_target_filter:
                    should_process, skip_reason = self.should_process_group(
                        clean_text, index=0, processed_count=0, item_path=full_path
                    )
                    if not should_process:
                        logger.debug(f"統合フィルタでスキップ: {clean_text} - {skip_reason}")
                        continue
                
                # 統一アイテム処理（リンクなし）
                has_nested_list = nested_ul is not None or sibling_ul is not None
                item_data = self._create_item_data(
                    clean_text, None, full_path, has_link=False, 
                    has_nested_list=has_nested_list, should_follow=False
                )
                self._add_item(result, clean_text, item_data)
            
            # ネストしたリストを再帰処理（子要素 or 兄弟要素）
            if nested_ul:
                nested_path = current_path + [clean_text]
                self._process_list_recursive(nested_ul, nested_path, result, depth + 1, apply_target_filter=apply_target_filter)
            elif sibling_ul:
                # 兄弟ulの場合、この要素が実際に兄弟ulの「親」であることを確認
                # 兄弟ulは現在のliの直後にある場合のみ処理
                if li.find_next_sibling() == sibling_ul and sibling_ul.get('processed') != 'true':
                    # 兄弟ul用のパス構築：リンクがある場合はリンクテキストを使用
                    if link and 'href' in link.attrs:
                        parent_name = link.get_text(strip=True)
                    else:
                        parent_name = clean_text
                    
                    nested_path = current_path + [parent_name]
                    logger.debug(f"    [階層デバッグ] 兄弟ul処理: 親='{parent_name}', パス={' -> '.join(nested_path)}")
                    
                    # 兄弟ulを処理する前にマークして重複処理を防ぐ
                    sibling_ul['processed'] = 'true'
                    self._process_list_recursive(sibling_ul, nested_path, result, depth + 1, apply_target_filter=apply_target_filter)
                    # 兄弟ul内のli要素を処理済みとしてマーク（重複処理防止）
                    for sibling_li in sibling_ul.find_all('li', recursive=False):
                        sibling_li['processed'] = 'true'
                else:
                    logger.debug(f"    [兄弟ulデバッグ] 兄弟ul処理をスキップ: 直後でないか既に処理済み")
    
    def _classify_node(self, name: str, has_link: bool, has_nested_list: bool) -> NodeType:
        """新しい4-way分類システム"""
        has_tag_group_in_name = 'tag group' in name.lower()
        
        if has_nested_list and has_link and not has_tag_group_in_name:
            return NodeType.TAG_AND_TAG_GROUP  # Type A
        elif has_nested_list and not has_link and not has_tag_group_in_name:
            return NodeType.TAG_GROUP_ONLY     # Type B
        elif has_tag_group_in_name:
            return NodeType.TRADITIONAL_TAG_GROUP  # Type C
        else:
            return NodeType.FINAL_TAG_ONLY     # Type D
    
    def scrape_complete_hierarchy_scalable(self, start_url: str = None) -> Dict:
        """スケーラブル完全階層構造スクレイピング"""
        if not start_url:
            # want.md新仕様: 常にpostページから開始
            start_url = "https://danbooru.donmai.us/posts?tags=tag_groups"
        
        logger.info("スケーラブル階層構造スクレイピング開始")
        logger.info(f"除外セクション: {self.config.exclude_sections}")
        
        # デフォルト構造を初期化
        default_result = {
            'headings': [],
            'items': {},
            'excluded_sections': [],
            'ignored_elements': []
        }
        
        # メインページから開始
        self.rate_limiter.wait_if_needed()
        soup = self.webfetch_with_parse(start_url, "Extract complete hierarchical structure excluding copyrights and media sections")
        
        if not soup:
            logger.error("メインページの取得に失敗 - デフォルト構造を返します")
            return default_result
        
        # メインページを解析
        main_result = self.extract_hierarchy_from_page(soup, [], start_url)
        
        logger.info(f"メインページ解析完了:")
        logger.info(f"  取得したアイテム: {len(main_result['items'])}")
        logger.info(f"  除外したセクション: {len(main_result['excluded_sections'])}")
        
        # 追跡可能なアイテムを順次処理（再帰的）
        processed_count = 0
        followable_items = [item for item in main_result['items'].values() if item.get('should_follow', False)]
        total_followable = len(followable_items)
        
        # 範囲制限情報を表示
        range_info = []
        if self.config.skip_first_n > 0:
            range_info.append(f"skip={self.config.skip_first_n}")
        if self.config.max_groups is not None:
            range_info.append(f"max={self.config.max_groups}")
        if self.config.target_groups is not None:
            range_info.append(f"targets={len(self.config.target_groups)}")
        if self.config.group_name_patterns is not None:
            range_info.append(f"patterns={len(self.config.group_name_patterns)}")
        
        range_str = f" (制限: {', '.join(range_info)})" if range_info else ""
        logger.info(f"\nアイテム処理開始: {total_followable}個{range_str}")
        
        for i, item in enumerate(followable_items):
            logger.info(f"\n進捗 [{i+1}/{total_followable}]: {item['name']}")
            
            # 範囲制限チェック（pathを含めて階層的に判定）
            should_process, skip_reason = self.should_process_group(
                item['name'], i, processed_count, item_path=item.get('path', [])
            )
            if not should_process:
                logger.info(f"  スキップ（{skip_reason}）: {item['name']}")
                continue
            
            if not item.get('url'):
                logger.warning(f"  スキップ（URL無効）: {item['name']}")
                continue
            
            # want.md新仕様: wiki→post URL変換
            original_url = item['url']
            if original_url.startswith('/'):
                full_url = f"https://danbooru.donmai.us{original_url}"
            else:
                full_url = original_url
            
            # wiki形式のURLをpost形式に変換
            full_url = self.convert_wiki_to_post_url(full_url)
            
            if full_url in self.visited_urls:
                logger.info(f"  スキップ（既訪問）: {item['name']}")
                continue
            
            self.visited_urls.add(full_url)
            self.rate_limiter.wait_if_needed()
            
            item_soup = self.webfetch_with_parse(
                full_url, 
                f"Extract detailed structure for {item['name']} excluding see also sections"
            )
            
            if item_soup:
                item_result = self.extract_hierarchy_from_page(
                    item_soup, item['path'], full_url
                )
                
                # 結果をマージ
                self._merge_results(main_result, item_result)
                processed_count += 1
                
                logger.info(f"  処理完了: +{len(item_result['items'])} items")
                
                # さらにネストしたアイテムを処理（再帰）
                nested_followable = [nested_item for nested_item in item_result['items'].values() if nested_item.get('should_follow', False)]
                if nested_followable:
                    logger.info(f"  ネストしたアイテム {len(nested_followable)}個を発見")
                    # 再帰処理は必要に応じて実装
            else:
                logger.warning(f"  取得失敗: {item['name']}")
        
        logger.info(f"\n処理完了: {processed_count}/{total_followable} アイテムを処理")
        return main_result
    
    def _merge_results(self, main_result: Dict, group_result: Dict):
        """結果をマージ"""
        # 統合されたitemsをマージ
        for name, item_data in group_result['items'].items():
            self._add_item(main_result, name, item_data)
        
        main_result['excluded_sections'].extend(group_result['excluded_sections'])
        main_result['ignored_elements'].extend(group_result['ignored_elements'])
    
    def normalize_data(self, hierarchy_result: Dict) -> Dict:
        """データ正規化処理 - 統合されたitems構造で処理"""
        logger.info("\nデータ正規化処理開始...")
        
        normalized_result = {
            'headings': [],
            'items': {},
            'excluded_sections': [],
            'ignored_elements': [],
            'normalization_log': [],
            'removed_duplicates': []
        }
        
        # headingsの正規化
        for heading in hierarchy_result.get('headings', []):
            normalized_heading = {
                'level': heading['level'],
                'text': heading['text'].lower()
            }
            if normalized_heading['text'] != heading['text']:
                normalized_result['normalization_log'].append({
                    'action': 'lowercase',
                    'original': heading['text'],
                    'normalized': normalized_heading['text']
                })
            normalized_result['headings'].append(normalized_heading)
        
        # itemsの正規化（重複削除を含む）
        seen_items = {}
        for name, item in hierarchy_result.get('items', {}).items():
            normalized_name = name.lower()
            normalized_path = [segment.lower() for segment in item['path']]
            
            # 名前ベースの重複チェック
            if normalized_name in seen_items:
                # 重複の場合、優先度で解決
                existing_item = seen_items[normalized_name]
                new_priority = self._classify_priority(item['classification'])
                existing_priority = self._classify_priority(existing_item['classification'])
                
                # 優先度比較（高い方を採用、同じなら短いパスを採用）
                if (new_priority > existing_priority or 
                    (new_priority == existing_priority and len(normalized_path) < len(existing_item['path']))):
                    # 新しいアイテムの方が優先される場合
                    normalized_item = {
                        'name': normalized_name,
                        'url': item.get('url'),
                        'path': normalized_path,
                        'parent': item.get('parent', '').lower() if item.get('parent') else None,
                        'depth': item.get('depth', len(normalized_path)),  # 階層深度を保持
                        'has_nested_list': item.get('has_nested_list', False),
                        'classification': item.get('classification'),
                        'should_follow': item.get('should_follow', False)
                    }
                    normalized_result['items'][normalized_name] = normalized_item
                    seen_items[normalized_name] = normalized_item
                
                normalized_result['removed_duplicates'].append({
                    'duplicate': normalized_name,
                    'kept_classification': normalized_result['items'][normalized_name]['classification'],
                    'kept_path': ' → '.join(normalized_result['items'][normalized_name]['path']),
                    'discarded_classification': item['classification'],
                    'discarded_path': ' → '.join(normalized_path)
                })
                continue
            
            normalized_item = {
                'name': normalized_name,
                'url': item.get('url'),
                'path': normalized_path,
                'parent': item.get('parent', '').lower() if item.get('parent') else None,
                'depth': item.get('depth', len(normalized_path)),  # 階層深度を保持
                'has_nested_list': item.get('has_nested_list', False),
                'classification': item.get('classification'),
                'should_follow': item.get('should_follow', False)
            }
            
            if normalized_name != name:
                normalized_result['normalization_log'].append({
                    'action': 'lowercase',
                    'original': name,
                    'normalized': normalized_name
                })
            
            normalized_result['items'][normalized_name] = normalized_item
            seen_items[normalized_name] = normalized_item
        
        # excluded_sectionsとignored_elementsの正規化
        for section in hierarchy_result.get('excluded_sections', []):
            normalized_section = section.lower()
            if normalized_section != section:
                normalized_result['normalization_log'].append({
                    'action': 'lowercase',
                    'original': section,
                    'normalized': normalized_section
                })
            normalized_result['excluded_sections'].append(normalized_section)
        
        for element in hierarchy_result.get('ignored_elements', []):
            normalized_element = element.lower()
            if normalized_element != element:
                normalized_result['normalization_log'].append({
                    'action': 'lowercase',
                    'original': element,
                    'normalized': normalized_element
                })
            normalized_result['ignored_elements'].append(normalized_element)
        
        # 統合処理（breasts + tag group:breasts → breasts）
        consolidated_items = self._consolidate_redundant_items(normalized_result['items'])
        normalized_result['items'] = consolidated_items
        
        # 重複削除チェック
        seen_paths = {}
        
        logger.info(f"  正規化ログ: {len(normalized_result['normalization_log'])}件")
        logger.info(f"  重複削除: {len(normalized_result['removed_duplicates'])}件")
        
        return normalized_result
    
    def _consolidate_redundant_items(self, items: Dict) -> Dict:
        """冗長な項目の統合処理（breasts + tag group:breasts → breasts）"""
        consolidated = {}
        to_remove = []
        consolidation_log = []
        
        for name, item in items.items():
            # tag group:X パターンの検出
            if name.startswith('tag group:'):
                base_name_full = name.replace('tag group:', '').strip()
                
                # "X tags" → "X" の変換も試行
                base_name_options = [base_name_full]
                if base_name_full.endswith(' tags'):
                    base_name_options.append(base_name_full.replace(' tags', ''))
                
                # 対応するベース項目が存在するかチェック
                matching_base = None
                for base_option in base_name_options:
                    if base_option in items:
                        matching_base = base_option
                        break
                
                if matching_base:
                    base_item = items[matching_base]
                    tag_group_item = item
                    
                    # より汎用的な項目（ベース項目）を保持
                    # ただし、より詳細な階層情報がある場合はそれを採用
                    if len(base_item.get('path', [])) >= len(tag_group_item.get('path', [])):
                        # ベース項目を保持、tag group項目を削除
                        to_remove.append(name)
                        consolidation_log.append({
                            'action': 'consolidate',
                            'kept': matching_base,
                            'removed': name,
                            'reason': 'base_item_preferred'
                        })
                    else:
                        # tag group項目の方が詳細な階層を持つ場合、そちらを保持
                        # ただし名前はベース名に変更
                        consolidated[matching_base] = {
                            **tag_group_item,
                            'name': matching_base
                        }
                        to_remove.append(name)
                        to_remove.append(matching_base)  # 元のベース項目も削除
                        consolidation_log.append({
                            'action': 'consolidate',
                            'kept': matching_base,
                            'removed': name,
                            'reason': 'tag_group_more_detailed'
                        })
        
        # 統合結果を適用
        for name, item in items.items():
            if name not in to_remove:
                consolidated[name] = item
        
        # ログ出力
        if consolidation_log:
            logger.info(f"統合処理実行: {len(consolidation_log)}件")
            for log_entry in consolidation_log:
                logger.info(f"  統合: {log_entry['removed']} → {log_entry['kept']} ({log_entry['reason']})")
            logger.info(f"統合前: {len(items)} items, 統合後: {len(consolidated)} items")
        
        return consolidated
    
    def run_scalable_scraping(self, start_url: str = None) -> Dict:
        """スケーラブルスクレイピング実行"""
        logger.info("=" * 70)
        logger.info("スケーラブル階層スクレイパー実行開始")
        logger.info("対象: Copyrights, artists, projects and mediaを除く全tag")
        logger.info("=" * 70)
        
        start_time = time.time()
        
        # 階層構造取得
        hierarchy_result = self.scrape_complete_hierarchy_scalable(start_url)
        
        # データ正規化
        normalized_result = self.normalize_data(hierarchy_result)
        
        execution_time = time.time() - start_time
        
        # 統計情報
        final_stats = {
            'execution_time': execution_time,
            'total_items': len(hierarchy_result.get('items', {})),
            'total_followable_items': len([item for item in hierarchy_result.get('items', {}).values() if item.get('should_follow', False)]),
            'excluded_sections': len(set(hierarchy_result.get('excluded_sections', []))),
            'ignored_elements': len(set(hierarchy_result.get('ignored_elements', []))),
            'normalization_changes': len(normalized_result.get('normalization_log', [])),
            'removed_duplicates': len(normalized_result.get('removed_duplicates', []))
        }
        
        # 包括的結果
        comprehensive_result = {
            'metadata': {
                'scraper_version': 'scalable_v1.0',
                'target_scope': 'all_tags_except_copyrights_media',
                'execution_time': execution_time,
                'config': {
                    'exclude_sections': self.config.exclude_sections,
                    'ignore_elements': self.config.ignore_elements,
                    'rate_limit': self.config.rate_limit,
                    'target_groups': self.config.target_groups
                }
            },
            'raw_hierarchy_data': hierarchy_result,
            'normalized_data': normalized_result,
            'statistics': final_stats
        }
        
        self._print_scalable_summary(comprehensive_result)
        
        return comprehensive_result
    
    def _print_scalable_summary(self, result: Dict):
        """スケーラブル実行結果サマリーを表示"""
        stats = result['statistics']
        
        logger.info(f"\n実行時間: {stats['execution_time']:.2f}秒")
        logger.info(f"取得したアイテム数: {stats['total_items']}")
        logger.info(f"追跡可能アイテム数: {stats['total_followable_items']}")
        logger.info(f"除外したセクション数: {stats['excluded_sections']}")
        logger.info(f"無視した要素数: {stats['ignored_elements']}")
        logger.info(f"正規化変更数: {stats['normalization_changes']}")
        logger.info(f"重複削除数: {stats['removed_duplicates']}")
        
        logger.info(f"\n✅ 全tag対応スケーラブルシステム動作確認完了")

def main():
    """メイン実行"""
    import argparse
    
    # コマンドライン引数の処理
    parser = argparse.ArgumentParser(description='Danbooru Tag階層スクレイパー')
    parser.add_argument('--target-groups', nargs='+', help='処理対象のタググループ')
    parser.add_argument('--max-groups', type=int, help='処理するグループ数の上限')
    parser.add_argument('--skip-first-n', type=int, default=0, help='最初のN個をスキップ')
    parser.add_argument('--rate-limit', type=float, default=1.0, help='レート制限（秒）')
    
    args = parser.parse_args()
    
    # 設定作成
    config = ScrapingConfig(
        target_groups=args.target_groups,
        max_groups=args.max_groups,
        skip_first_n=args.skip_first_n,
        rate_limit=args.rate_limit,
        exclude_sections=[
            "Copyrights, artists, projects and media", 
            "see also"
        ],
        ignore_elements=["see also"],
        max_depth=10
    )
    
    # スクレイパー実行
    scraper = ScalableHierarchyScraper(config)
    result = scraper.run_scalable_scraping()
    
    # 結果をJSONファイルに保存
    output_file = 'tmp/scalable_scraping_result.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nスケーラブルスクレイピング結果を保存: {output_file}")
    
    return result

if __name__ == "__main__":
    result = main()