# -*- encoding: utf-8 -*-
"""
文献去重合并脚本

功能:
- 合并多个JSON格式的文献列表
- 三优先级去重策略:
  1. DOI精确匹配
  2. 标题相似度≥85%（模糊匹配）
  3. 作者+年份+关键词组合匹配

策略说明:
- Priority 1 (DOI): 精确匹配，最可靠
- Priority 2 (Title): 使用编辑距离算法，阈值85%
- Priority 3 (Author+Year+Keywords): 综合判断
"""

import argparse
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# 添加scripts目录到路径以导入utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import setup_logging, load_json, save_json

# ===== 常量定义 =====
SIMILARITY_THRESHOLD = 0.85  # 标题相似度阈值


def normalize_string(s: str) -> str:
    """
    标准化字符串用于比较
    
    Args:
        s: 输入字符串
    
    Returns:
        标准化后的字符串
    """
    if not s:
        return ""
    # 转小写，移除多余空格和标点
    s = s.lower().strip()
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s


def calculate_similarity(s1: str, s2: str) -> float:
    """
    计算两个字符串的相似度（使用SequenceMatcher）
    
    Args:
        s1: 字符串1
        s2: 字符串2
    
    Returns:
        相似度分数 [0, 1]
    """
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1, s2).ratio()


def extract_doi(paper: Dict[str, Any]) -> Optional[str]:
    """
    从论文信息中提取DOI
    
    Args:
        paper: 论文字典
    
    Returns:
        DOI字符串或None
    """
    # 尝试多个DOI字段
    doi = paper.get("doi") or paper.get("DOI") or ""
    
    # 清理DOI
    doi = str(doi).strip()
    if doi:
        # 移除URL前缀
        doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi)
        doi = normalize_string(doi)
    
    return doi if doi else None


def extract_year(paper: Dict[str, Any]) -> Optional[str]:
    """
    从论文信息中提取年份
    
    Args:
        paper: 论文字典
    
    Returns:
        年份字符串或None
    """
    year = paper.get("year") or paper.get("Year") or paper.get("pubdate") or ""
    year = str(year).strip()
    
    # 尝试从字符串中提取4位数字
    match = re.search(r'\b(19|20)\d{2}\b', year)
    if match:
        return match.group(0)
    return None


def extract_title(paper: Dict[str, Any]) -> str:
    """
    从论文信息中提取标题
    
    Args:
        paper: 论文字典
    
    Returns:
        标题字符串
    """
    title = paper.get("title") or paper.get("Title") or ""
    return normalize_string(str(title).strip())


def extract_authors(paper: Dict[str, Any]) -> List[str]:
    """
    从论文信息中提取作者列表
    
    Args:
        paper: 论文字典
    
    Returns:
        作者列表
    """
    authors = paper.get("authors") or paper.get("Authors") or paper.get("author") or []
    
    if isinstance(authors, str):
        # 可能是逗号分隔的字符串
        authors = [a.strip() for a in authors.split(",")]
    
    # 标准化
    normalized = []
    for author in authors:
        author = normalize_string(str(author))
        if author:
            normalized.append(author)
    
    return normalized


def extract_keywords(paper: Dict[str, Any]) -> Set[str]:
    """
    从论文信息中提取关键词集合
    
    Args:
        paper: 论文字典
    
    Returns:
        关键词集合
    """
    keywords = paper.get("keywords") or paper.get("Keywords") or paper.get("keyword") or []
    
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",")]
    
    # 标准化并转为集合
    normalized = set()
    for kw in keywords:
        kw = normalize_string(str(kw))
        if kw:
            normalized.add(kw)
    
    return normalized


class Deduplicator:
    """
    文献去重器
    """
    
    def __init__(self, similarity_threshold: float = SIMILARITY_THRESHOLD):
        """
        初始化去重器
        
        Args:
            similarity_threshold: 标题相似度阈值
        """
        self.similarity_threshold = similarity_threshold
        self.seen_dois: Set[str] = set()
        self.seen_titles: List[Tuple[str, Dict]] = []  # (normalized_title, original_paper)
        self.seen_combinations: Dict[str, List[Dict]] = defaultdict(list)
    
    def _get_combination_key(self, paper: Dict[str, Any]) -> Optional[str]:
        """
        生成作者+年份+关键词组合键
        
        Args:
            paper: 论文字典
        
        Returns:
            组合键字符串
        """
        year = extract_year(paper)
        authors = extract_authors(paper)
        keywords = extract_keywords(paper)
        
        if not year or not authors:
            return None
        
        # 使用前3个作者和年份生成键
        key_authors = "|".join(sorted(authors[:3]))
        key_kw = "|".join(sorted(list(keywords)[:5])) if keywords else ""
        
        return f"{year}:{key_authors}:{key_kw}"
    
    def is_duplicate(self, paper: Dict[str, Any]) -> Tuple[bool, str]:
        """
        检查论文是否重复
        
        Args:
            paper: 待检查的论文
        
        Returns:
            (是否重复, 重复原因)
        """
        # Priority 1: DOI精确匹配
        doi = extract_doi(paper)
        if doi:
            if doi in self.seen_dois:
                return True, "doi_exact"
            self.seen_dois.add(doi)
        
        # Priority 2: 标题相似度
        title = extract_title(paper)
        if title:
            for seen_title, seen_paper in self.seen_titles:
                similarity = calculate_similarity(title, seen_title)
                if similarity >= self.similarity_threshold:
                    return True, f"title_similarity_{similarity:.2f}"
        
        # Priority 3: 作者+年份+关键词组合
        combo_key = self._get_combination_key(paper)
        if combo_key:
            # 检查是否有相同组合
            for seen_paper in self.seen_combinations[combo_key]:
                seen_title = extract_title(seen_paper)
                similarity = calculate_similarity(title, seen_title)
                if similarity >= self.similarity_threshold:
                    return True, f"author_year_keywords_similarity_{similarity:.2f}"
        
        return False, ""
    
    def add_paper(self, paper: Dict[str, Any]) -> None:
        """
        将论文添加到已见集合
        
        Args:
            paper: 论文字典
        """
        title = extract_title(paper)
        if title:
            self.seen_titles.append((title, paper))
        
        combo_key = self._get_combination_key(paper)
        if combo_key:
            self.seen_combinations[combo_key].append(paper)


def merge_and_deduplicate(
    input_files: List[str],
    output_file: str,
    enable_deduplication: bool = True
) -> List[Dict[str, Any]]:
    """
    合并多个文件并去重
    
    Args:
        input_files: 输入文件路径列表
        output_file: 输出文件路径
        enable_deduplication: 是否启用去重
    
    Returns:
        合并去重后的论文列表
    """
    logger = setup_logging("deduplicate_merge")
    
    logger.info("=" * 60)
    logger.info("文献去重合并开始")
    logger.info("=" * 60)
    
    # 加载所有文件
    all_papers = []
    for input_file in input_files:
        papers = load_json(input_file)
        logger.info(f"加载 {input_file}: {len(papers)} 条")
        all_papers.extend(papers)
    
    logger.info(f"\n原始总数: {len(all_papers)} 条")
    
    if not enable_deduplication:
        logger.info("去重已禁用，直接保存合并结果")
        save_json(all_papers, output_file)
        return all_papers
    
    # 去重
    deduplicator = Deduplicator()
    unique_papers = []
    duplicate_count = 0
    
    for paper in all_papers:
        is_dup, reason = deduplicator.is_duplicate(paper)
        
        if is_dup:
            duplicate_count += 1
            logger.debug(f"去重: {reason} - {paper.get('title', '')[:50]}")
        else:
            unique_papers.append(paper)
            deduplicator.add_paper(paper)
    
    # 统计
    logger.info(f"\n=== 去重统计 ===")
    logger.info(f"原始论文数: {len(all_papers)}")
    logger.info(f"重复论文数: {duplicate_count}")
    logger.info(f"去重后论文数: {len(unique_papers)}")
    logger.info(f"去重率: {100*duplicate_count/len(all_papers):.1f}%")
    
    # 按来源统计
    source_stats = defaultdict(int)
    for paper in unique_papers:
        source = paper.get("source", "unknown")
        source_stats[source] += 1
    
    logger.info("\n=== 来源统计 ===")
    for source, count in sorted(source_stats.items()):
        logger.info(f"  {source}: {count} 条")
    
    # 保存结果
    save_json(unique_papers, output_file)
    logger.info(f"\n>>> 结果已保存: {output_file}")
    
    return unique_papers


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="文献去重合并脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python 04_deduplicate_merge.py --input aminer_results.json pubmed_results.json --output merged.json
  
  # 禁用去重
  python 04_deduplicate_merge.py --input aminer_results.json pubmed_results.json --output merged.json --no-deduplicate

去重策略 (三优先级):
  1. DOI精确匹配 - 最可靠
  2. 标题相似度≥85% - 使用编辑距离
  3. 作者+年份+关键词组合 - 综合判断
        """
    )
    parser.add_argument(
        "--input",
        required=True,
        nargs="+",
        help="输入JSON文件路径（至少一个）"
    )
    parser.add_argument(
        "--output",
        default="merged_results.json",
        help="输出JSON文件路径"
    )
    parser.add_argument(
        "--deduplicate",
        action="store_true",
        default=True,
        help="启用去重（默认启用）"
    )
    parser.add_argument(
        "--no-deduplicate",
        action="store_true",
        help="禁用去重"
    )
    args = parser.parse_args()
    
    # 处理去重参数
    enable_deduplication = args.deduplicate and not args.no_deduplicate
    
    try:
        merge_and_deduplicate(args.input, args.output, enable_deduplication)
        return 0
    except Exception as e:
        logger = setup_logging("deduplicate_merge")
        logger.error(f"合并失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
