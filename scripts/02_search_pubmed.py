# -*- encoding: utf-8 -*-
"""
PubMed E-utilities 文献检索脚本

功能:
- 使用 NCBI ESearch + EFetch
- 免费无需API密钥
- 禁用代理（NCBI不支持代理）

检索式:
- (microalgae OR cyanobacteria OR chlorella OR spirulina) AND (biofertilizer OR bio-fertilizer OR algal fertilizer)
"""

import argparse
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# 禁用代理（NCBI不支持代理访问）
session = requests.Session()
session.trust_env = False

# 添加scripts目录到路径以导入utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import setup_logging, save_json

# ===== 常量定义 =====
PUBMED_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SEARCH_QUERY = (
    "(microalgae OR cyanobacteria OR chlorella OR spirulina) AND "
    "(biofertilizer OR bio-fertilizer OR algal fertilizer)"
)


def search_pubmed(query: str, max_results: int = 200, email: Optional[str] = None) -> List[str]:
    """
    使用ESearch搜索PubMed获取PMIDs
    """
    logger = setup_logging("pubmed_search")
    url = f"{PUBMED_EUTILS_BASE}/esearch.fcgi"
    
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": min(max_results, 10000),
        "retmode": "json",
        "usehistory": "n",
    }
    
    if email:
        params["email"] = email
    
    try:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        idlist = data.get("esearchresult", {}).get("idlist", [])
        count = data.get("esearchresult", {}).get("count", "0")
        
        logger.info(f"ESearch '{query}': 找到 {count} 条, 获取 {len(idlist)} 条PMIDs")
        return idlist
    except requests.exceptions.RequestException as e:
        logger.error(f"ESearch请求失败: {e}")
        return []
    except (KeyError, ValueError) as e:
        logger.error(f"ESearch解析失败: {e}")
        return []


def fetch_full_details(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    使用EFetch获取完整XML格式的论文详情（含摘要）
    """
    logger = setup_logging("pubmed_search")
    
    if not pmids:
        return []
    
    papers = []
    batch_size = 100
    
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        url = f"{PUBMED_EUTILS_BASE}/efetch.fcgi"
        
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "rettype": "abstract",
            "retmode": "xml",
        }
        
        try:
            response = session.get(url, params=params, timeout=60)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            for article in root.findall(".//PubmedArticle"):
                paper = {}
                
                medline_citation = article.find("MedlineCitation")
                if medline_citation is not None:
                    article_data = medline_citation.find("Article")
                    if article_data is not None:
                        paper["title"] = "".join(article_data.find("ArticleTitle").itertext()) if article_data.find("ArticleTitle") is not None else ""
                        
                        abstract = article_data.find("Abstract")
                        if abstract is not None:
                            abstract_texts = []
                            for ab in abstract.findall("AbstractText"):
                                label = ab.get("Label", "")
                                text = "".join(ab.itertext())
                                if label:
                                    abstract_texts.append(f"{label}: {text}")
                                else:
                                    abstract_texts.append(text)
                            paper["abstract"] = " | ".join(abstract_texts)
                        
                        author_list = []
                        for author in article_data.findall("AuthorList/Author"):
                            last_name = author.find("LastName")
                            fore_name = author.find("ForeName")
                            if last_name is not None:
                                name = f"{fore_name.text} {last_name.text}" if fore_name is not None else last_name.text
                                author_list.append(name)
                        paper["authors"] = author_list
                        
                        # 年份
                        pub_date = article_data.find("ArticleDate")
                        if pub_date is not None:
                            paper["year"] = pub_date.get("Year", "")
                        else:
                            journal_info = article_data.find("Journal")
                            if journal_info is not None:
                                jour_date = journal_info.find("JournalDate")
                                if jour_date is not None:
                                    paper["year"] = jour_date.get("Year", "")
                
                pubmed_data = article.find("PubmedData")
                if pubmed_data is not None:
                    article_id_list = pubmed_data.find("ArticleIdList")
                    if article_id_list is not None:
                        for article_id in article_id_list.findall("ArticleId"):
                            if article_id.get("IdType") == "pubmed":
                                paper["pmid"] = article_id.text
                
                paper["source"] = "pubmed"
                papers.append(paper)
            
            logger.info(f"EFetch批次 {i//batch_size + 1}: 处理 {len(batch)} 条")
            time.sleep(0.5)
        except requests.exceptions.RequestException as e:
            logger.error(f"EFetch批次请求失败: {e}")
            continue
        except ET.ParseError as e:
            logger.error(f"EFetch XML解析失败: {e}")
            continue
    
    logger.info(f"EFetch完成: 获取 {len(papers)} 篇论文详情")
    return papers


def normalize_pubmed_data(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化PubMed数据格式"""
    normalized = []
    
    for paper in papers:
        norm_paper = {
            "id": paper.get("pmid", ""),
            "pmid": paper.get("pmid", ""),
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", ""),
            "authors": paper.get("authors", []),
            "source": "pubmed",
            "year": paper.get("year", ""),
            "journal": "",
            "doi": "",
        }
        normalized.append(norm_paper)
    
    return normalized


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PubMed E-utilities文献检索")
    parser.add_argument("--query", default=SEARCH_QUERY, help="检索式")
    parser.add_argument("--output", default="pubmed_results.json", help="输出文件路径")
    parser.add_argument("--max-results", type=int, default=200, help="最大结果数")
    parser.add_argument("--email", help="NCBI联系邮箱（可选）")
    args = parser.parse_args()
    
    logger = setup_logging("pubmed_search")
    logger.info("=" * 60)
    logger.info("PubMed E-utilities文献检索开始")
    logger.info("=" * 60)
    
    # ESearch获取PMIDs
    logger.info(f"\n>>> 阶段1: ESearch检索")
    pmids = search_pubmed(args.query, args.max_results, args.email)
    
    if not pmids:
        logger.warning("未找到任何结果")
        save_json([], args.output)
        return 0
    
    logger.info(f">>> 共获取 {len(pmids)} 个PMIDs")
    
    # EFetch获取完整详情
    logger.info(f"\n>>> 阶段2: EFetch获取详情")
    papers = fetch_full_details(pmids)
    
    # 标准化数据
    papers = normalize_pubmed_data(papers)
    
    # 保存结果
    save_json(papers, args.output)
    logger.info(f"\n>>> 结果已保存: {args.output} ({len(papers)} 条)")
    
    # 统计
    logger.info("\n=== 检索统计 ===")
    logger.info(f"检索式: {args.query}")
    logger.info(f"PMIDs数量: {len(pmids)}")
    logger.info(f"最终结果数: {len(papers)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
