# -*- encoding: utf-8 -*-
"""
sciai-engine 深度分析脚本 (Phase 3-4)

已验证可用的API:
- api_ner_sci_en_v2: 英文科研实体识别 ✓ (返回研究问题/方法/度量指标/设备/软件等)
- paper_classification_cn: 中文科技文献分类 ✓

不可用API (Server not available):
- keywords_extraction_en: 英文关键词提取 ✗

Token: 8HSXyLFdbCZf
认证方式: form-data, {"data": [base64文本], "token": "8HSXyLFdbCZf"}
配额: 500次/批（每POST算1次）
  - 106篇分3批，每批2API = 6次总消耗
"""

import argparse
import base64
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).parent))
from utils import setup_logging, load_json, save_json

# ============================================================
# 配置
# ============================================================
BASE_URL = "https://sciengine.las.ac.cn/"
TOKEN = "8HSXyLFdbCZf"
BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 5
NO_PROXY = {"http": None, "https": None}

# API 映射（已验证可用）
APIS = {
    "ner":      "api_ner_sci_en_v2",   # 英文科研实体识别
    "classify": "paper_classification_cn",  # 中文科技文献分类
}

# NER 实体类别（英文 v2 版本）
NER_CATEGORIES = [
    "研究问题", "方法模型", "数据资料",
    "仪器设备", "度量指标", "软件系统",
]


# ============================================================
# 核心工具
# ============================================================

def encode_item(item: str) -> str:
    """Base64 编码文本"""
    return base64.b64encode(item.encode("utf-8")).decode("ascii")


def build_text(paper: Dict) -> str:
    """拼接论文标题+摘要"""
    parts = []
    if paper.get("title"):
        parts.append(f"Title: {paper['title']}")
    if paper.get("abstract"):
        parts.append(f"Abstract: {paper['abstract']}")
    return "\n".join(parts) or ""


def call_api(endpoint: str, texts_b64: List[str]) -> Optional[Dict]:
    """
    调用 sciai-engine API（form-data 模式，文本已 base64）
    返回解析后的响应，或 None（失败）
    """
    payload = {"data": texts_b64, "token": TOKEN}
    url = BASE_URL + endpoint

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(url, data=payload, proxies=NO_PROXY, timeout=120)
            if resp.status_code == 200:
                try:
                    return json.loads(resp.text)
                except json.JSONDecodeError:
                    # eval() 模式（SDK 中的处理方式）
                    try:
                        return eval(resp.text)
                    except Exception:
                        return {"raw": resp.text}
            elif resp.status_code == 401 or resp.text == '{"info": "Token incorrect!"}':
                print(f"  [ERROR] Token incorrect!")
                return None
            elif "Server not available" in resp.text:
                print(f"  [WARNING] Server not available for {endpoint}")
                return None
            elif resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", RETRY_DELAY * (attempt + 1)))
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [ERROR] HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  [ERROR] {e}")
        time.sleep(RETRY_DELAY * (attempt + 1))
    return None


# ============================================================
# 批量分析
# ============================================================

def analyze_papers(papers: List[Dict], api_counter: List[int], logger) -> List[Dict]:
    """
    分批调用 NER + 分类 API
    api_counter: [已消耗次数]
    """
    total = len(papers)
    n_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    results = []

    for batch_idx in range(n_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, total)
        batch = papers[start:end]
        texts_b64 = [encode_item(build_text(p)) for p in batch]

        logger.info(f"\n--- Batch {batch_idx + 1}/{n_batches}: 篇 {start+1}-{end} ---")

        batch_results = {}

        # 1. NER 实体识别
        logger.info(f"  [{batch_idx+1}] api_ner_sci_en_v2...")
        ner_resp = call_api(APIS["ner"], texts_b64)
        api_counter[0] += 1
        batch_results["ner"] = ner_resp
        if ner_resp:
            logger.info(f"    成功 | 配额: {api_counter[0]}/500")
        time.sleep(1.5)

        # 2. 文献分类
        logger.info(f"  [{batch_idx+1}] paper_classification_cn...")
        cls_resp = call_api(APIS["classify"], texts_b64)
        api_counter[0] += 1
        batch_results["classify"] = cls_resp
        if cls_resp:
            logger.info(f"    成功 | 配额: {api_counter[0]}/500")
        time.sleep(1.5)

        # 合并结果到论文
        for i, paper in enumerate(batch):
            ner_data = ner_resp.get(str(i), ner_resp.get(i)) if ner_resp else None
            cls_data = cls_resp.get(str(i), cls_resp.get(i)) if cls_resp else None

            # 从 NER 中提取关键词（"研究问题"类别）
            ner_keywords = []
            if ner_data and isinstance(ner_data, dict):
                for cat in NER_CATEGORIES:
                    items = ner_data.get(cat, [])
                    if items:
                        ner_keywords.extend(items)

            paper_result = {**paper, "sciai": {
                "batch": batch_idx + 1,
                "api_calls_used": api_counter[0],
                "ner": ner_data,
                "ner_categories": NER_CATEGORIES,
                "ner_keywords": ner_keywords,  # 从NER提取的关键词
                "classify": cls_data,
            }}
            results.append(paper_result)

        # 配额告警
        if api_counter[0] >= 450:
            logger.warning(f"⚠️  配额剩余 {500 - api_counter[0]}，跳过剩余批次")
            for remaining in papers[end:]:
                results.append({**remaining, "sciai": {"status": "skipped", "reason": "quota_exceeded"}})
            break

    return results


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="sciai-engine 深度分析脚本")
    parser.add_argument("--input", required=True,
                        help="输入JSON (Phase 3 screened_papers.json)")
    parser.add_argument("--output", default="data/interim/sciai_analyzed_papers.json",
                        help="输出JSON路径")
    parser.add_argument("--test", action="store_true",
                        help="仅测试API连通性")
    args = parser.parse_args()

    logger = setup_logging("sciai_engine")
    logger.info("=" * 60)
    logger.info("sciai-engine 深度分析")
    logger.info("Token: 8HSXyLFdbCZf")
    logger.info(f"Base: {BASE_URL}")
    logger.info(f"配额上限: 500 次")
    logger.info(f"可用API: api_ner_sci_en_v2, paper_classification_cn")
    logger.info(f"不可用: keywords_extraction_en (Server not available)")
    logger.info("=" * 60)

    # 测试 API 连通性
    logger.info("\n测试 api_ner_sci_en_v2...")
    test_b64 = [encode_item("Microalgae biofertilizer plant growth promotion and nitrogen fixation in agriculture.")]
    test_resp = call_api(APIS["ner"], test_b64)
    if test_resp:
        logger.info(f"  NER 测试成功: {str(test_resp)[:200]}")
    else:
        logger.error("  NER API 失败")
        return 1

    logger.info("测试 paper_classification_cn...")
    test_cls = call_api(APIS["classify"], test_b64)
    if test_cls:
        logger.info(f"  Classification 测试成功: {str(test_cls)[:200]}")
    else:
        logger.error("  Classification API 失败")
        return 1

    if args.test:
        logger.info("\n[TEST MODE] 跳过批量处理")
        return 0

    # 加载数据
    papers = load_json(args.input)
    total = len(papers)
    estimated_calls = ((total + BATCH_SIZE - 1) // BATCH_SIZE) * 2

    logger.info(f"\n加载论文: {total} 篇")
    logger.info(f"预计配额消耗: ~{estimated_calls} 次")
    if estimated_calls > 500:
        logger.warning(f"⚠️  估算({estimated_calls}) > 500，建议减少篇数")

    # 执行
    api_counter = [0]
    results = analyze_papers(papers, api_counter, logger)

    # 统计
    analyzed = sum(1 for r in results if r["sciai"].get("ner") is not None)
    classified = sum(1 for r in results if r["sciai"].get("classify") is not None)
    skipped = sum(1 for r in results if r["sciai"].get("status") == "skipped")

    logger.info(f"\n=== 处理完成 ===")
    logger.info(f"NER 分析成功: {analyzed} 篇")
    logger.info(f"分类成功: {classified} 篇")
    logger.info(f"跳过(配额不足): {skipped} 篇")
    logger.info(f"实际配额消耗: {api_counter[0]} / 500 次")
    logger.info(f"剩余配额: {500 - api_counter[0]} 次")

    save_json(results, args.output)
    logger.info(f"\n>>> 结果已保存: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
