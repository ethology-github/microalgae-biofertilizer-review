# -*- encoding: utf-8 -*-
"""
AMiner多策略文献检索脚本

功能:
- 免费策略: GET /api/paper/search (title=1)
- 付费策略: POST /api/paper/qa/search (¥0.05, topic_high)
- 批量详情: POST /api/paper/info

检索式覆盖:
- microalgae + biofertilizer
- cyanobacteria + biofertilizer
- chlorella + biofertilizer
- spirulina + biofertilizer
- microalgae + bio-fertilizer + agriculture
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# 添加scripts目录到路径以导入utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import setup_logging, save_json, ProgressTracker

# ===== 常量定义 =====
AMINDER_BASE_URL = "https://datacenter.aminer.cn/gateway/open_platform"

SEARCH_QUERIES = [
    "microalgae biofertilizer",
    "cyanobacteria biofertilizer",
    "chlorella biofertilizer",
    "spirulina biofertilizer",
    "microalgae bio-fertilizer agriculture",
]

HEADERS = {
    "Content-Type": "application/json",
    "X-Platform": "openclaw",
}


def search_by_title_free(token: str, query: str, max_results: int = 500) -> List[Dict[str, Any]]:
    """
    使用免费策略搜索 - GET /api/paper/search (title=1)
    
    Args:
        token: AMiner JWT token (Bearer token)
        query: 检索词
        max_results: 最大结果数
    
    Returns:
        论文列表
    """
    logger = setup_logging("aminer_search")
    url = f"{AMINDER_BASE_URL}/api/paper/search"
    
    headers = {**HEADERS, "Authorization": token}
    params = {
        "query": query,
        "size": min(max_results, 100),
        "page": 1,
        "title": 1,  # 只搜索标题
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 响应格式: {"code": 200, "data": [...papers], "total": N}
        # data 直接是数组，不是 {"papers": [...]} 对象
        papers = data.get("data", []) if isinstance(data.get("data"), list) else []
        logger.info(f"免费策略搜索 '{query}': 获取 {len(papers)} 条结果")
        return papers
    except requests.exceptions.RequestException as e:
        logger.error(f"免费策略请求失败: {e}")
        return []


def search_by_topic_paid(token: str, query: str, max_results: int = 500) -> List[Dict[str, Any]]:
    """
    使用付费策略搜索 - POST /api/paper/qa/search (¥0.05, topic_high)
    
    Args:
        token: AMiner JWT token (Bearer token)
        query: 检索词
        max_results: 最大结果数
    
    Returns:
        论文列表
    """
    logger = setup_logging("aminer_search")
    url = f"{AMINDER_BASE_URL}/api/paper/qa/search"
    
    headers = {**HEADERS, "Authorization": token}
    payload = {
        "query": query,
        "size": min(max_results, 100),
        "page": 1,
        "use_topic": True,  # 布尔值 true，语义搜索开关
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 响应格式: {"code": 200, "data": [...papers], "total": N}
        papers = data.get("data", []) if isinstance(data.get("data"), list) else []
        logger.info(f"付费策略搜索 '{query}': 获取 {len(papers)} 条结果")
        return papers
    except requests.exceptions.RequestException as e:
        logger.error(f"付费策略请求失败: {e}")
        return []


def fetch_batch_details(token: str, paper_ids: List[str]) -> List[Dict[str, Any]]:
    """
    批量获取论文详情 - POST /api/paper/info
    
    Args:
        token: AMiner JWT token (Bearer token)
        paper_ids: 论文ID列表
    
    Returns:
        论文详情列表
    """
    logger = setup_logging("aminer_search")
    url = f"{AMINDER_BASE_URL}/api/paper/info"
    
    headers = {**HEADERS, "Authorization": token}
    payload = {"ids": paper_ids}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # 响应格式: {"code": 200, "data": {...}, "papers": [...]} 或 {"code": 200, "data": [...papers]}
        data_field = data.get("data", {})
        if isinstance(data_field, dict):
            papers = data_field.get("papers", [])
        elif isinstance(data_field, list):
            papers = data_field
        else:
            papers = []
        logger.info(f"批量获取详情: 请求 {len(paper_ids)} 条, 返回 {len(papers)} 条")
        return papers
    except requests.exceptions.RequestException as e:
        logger.error(f"批量详情请求失败: {e}")
        return []


def deduplicate_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    对论文列表进行去重
    
    Args:
        papers: 原始论文列表
    
    Returns:
        去重后的论文列表
    """
    seen_ids = set()
    unique_papers = []
    
    for paper in papers:
        paper_id = paper.get("id") or paper.get("paperId")
        if paper_id and paper_id not in seen_ids:
            seen_ids.add(paper_id)
            unique_papers.append(paper)
    
    return unique_papers


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AMiner多策略文献检索")
    parser.add_argument("--token", required=True, help="AMiner JWT token")
    parser.add_argument("--output", default="aminer_results.json", help="输出文件路径")
    parser.add_argument("--max-results", type=int, default=500, help="每个检索式最大结果数")
    args = parser.parse_args()
    
    logger = setup_logging("aminer_search")
    logger.info("=" * 60)
    logger.info("AMiner多策略文献检索开始")
    logger.info("=" * 60)
    
    all_papers = []
    
    # 免费策略搜索
    logger.info("\n>>> 阶段1: 免费策略搜索 (GET /api/paper/search)")
    for query in SEARCH_QUERIES:
        papers = search_by_title_free(args.token, query, args.max_results)
        all_papers.extend(papers)
        time.sleep(0.5)  # 避免请求过快
    
    # 付费策略搜索
    logger.info("\n>>> 阶段2: 付费策略搜索 (POST /api/paper/qa/search)")
    for query in SEARCH_QUERIES:
        papers = search_by_topic_paid(args.token, query, args.max_results)
        all_papers.extend(papers)
        time.sleep(1)  # 付费接口间隔更长
    
    # 去重
    logger.info(f"\n>>> 去重: 原始 {len(all_papers)} 条 -> 去重后")
    all_papers = deduplicate_papers(all_papers)
    logger.info(f">>> 去重后: {len(all_papers)} 条")
    
    # 提取paperId用于批量获取详情
    paper_ids = [p.get("id") or p.get("paperId") for p in all_papers if p.get("id") or p.get("paperId")]
    
    if paper_ids:
        # 批量获取详情
        logger.info(f"\n>>> 批量获取详情: {len(paper_ids)} 篇论文")
        details = fetch_batch_details(args.token, paper_ids)
        
        if details:
            all_papers = details
            logger.info(f">>> 详情获取完成: {len(all_papers)} 篇")
    
    # 保存结果
    save_json(all_papers, args.output)
    logger.info(f"\n>>> 结果已保存: {args.output} ({len(all_papers)} 条)")
    
    # 统计
    logger.info("\n=== 检索统计 ===")
    logger.info(f"检索式数量: {len(SEARCH_QUERIES)}")
    logger.info(f"最终结果数: {len(all_papers)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
