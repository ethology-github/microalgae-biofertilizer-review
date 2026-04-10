# -*- encoding: utf-8 -*-
"""
多维度文献分类脚本

四个分类维度（纯规则匹配，不调用AI）：
- mechanism: M1-固氮/M2-解磷/M3-促生长激素/M4-生物刺激/M5-土壤改良/M6-未知
- algae_type: A1-螺旋藻/A2-小球藻/A3-蓝藻/A4-绿藻/A5-硅藻/A6-混合/A7-其他
- application: C1-大田作物/C2-园艺作物/C3-水产养殖/C4-土壤改良/C5-多种应用/C6-未明确
- research_type: R1-实验研究/R2-田间试验/R3-综述/R4-机理研究/R5-方法论/R6-未明确
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

sys.path.insert(0, str(Path(__file__).parent))
from utils import setup_logging, load_json, save_json


# ===== 分类规则定义 =====

# 机制分类关键词
MECHANISM_KEYWORDS = {
    'M1': ['nitrogen fixation', '固氮', 'nifH', '固氮菌', 'azotobacter', 'nitrogenase', '固氮作用'],
    'M2': ['phosphorus solubilization', '解磷', '溶磷', 'phytase', 'phosphatase', '解磷菌', '溶磷菌', 'phosphate solubilization'],
    'M3': ['IAA', 'auxin', 'gibberellin', 'cytokinin', '生长素', '赤霉素', '细胞分裂素', 'indole-3-acetic', 'phytohormone', 'plant hormone', 'ACC deaminase'],
    'M4': ['biostimulant', 'antioxidant', 'stress tolerance', '生物刺激素', '抗氧化', '耐盐', '抗旱', '抗逆', 'ascorbic acid', 'glutathione', 'SOD', 'catalase', 'polyamine'],
    'M5': ['soil improvement', '土壤改良', 'soil remediation', '盐碱地', 'soil fertility', 'soil quality', '有机质', '土壤微生物', 'soil structure', 'bioremediation', 'phytoremediation'],
}

# 藻类分类关键词
ALGAE_KEYWORDS = {
    'A1': ['spirulina', 'arthrospira', '螺旋藻', 'Spirulina platensis'],
    'A2': ['chlorella', '小球藻', 'Chlorella vulgaris', 'Chlorella pyrenoidosa', 'Nannochloropsis'],
    'A3': ['cyanobacteria', '蓝藻', 'anabaena', 'nostoc', 'arthrospira', 'microcystis', '鱼腥藻', '念珠藻', '蓝绿藻'],
    'A4': ['chlorophyta', '绿藻', 'chlamydomonas', 'scenedesmus', 'chlorella', '绿藻门', '衣藻', '栅藻', '杜氏藻'],
    'A5': ['diatom', '硅藻', 'phaeodactylum', 'thalassiosira', 'skeletonema', 'chaetoceros', '硅藻门'],
    'A6': ['microalgae', 'mixed', 'consortium', '混合', '复合', '多种藻', '微藻组合'],
}

# 应用分类关键词
APPLICATION_KEYWORDS = {
    'C1': ['field crop', '大田', 'wheat', 'rice', 'corn', 'maize', 'soybean', 'barley', 'sorghum', '作物', '粮食作物', 'cereal', 'crop'],
    'C2': ['horticulture', '园艺', 'vegetable', 'fruit', 'flower', 'planting', '蔬菜', '水果', '花卉', 'leafy', 'tomato', 'lettuce'],
    'C3': ['aquaculture', '水产', 'fish', 'shrimp', 'crab', 'crustacean', '藻类养殖', '海参', '鲍鱼', 'larvae', ' zooplankton'],
    'C4': ['soil', '土壤', 'land', 'remediation', 'bioremediation', '盐碱', 'saline', '重金属', '污染'],
    'C5': ['multiple', 'various', '多种应用', 'multi-purpose', 'comprehensive'],
}

# 研究类型分类关键词
RESEARCH_TYPE_KEYWORDS = {
    'R1': ['experiment', '实验', 'pot experiment', '室内实验', '培养实验', 'laboratory', 'in vitro', 'greenhouse'],
    'R2': ['field trial', '田间试验', 'field experiment', '大田试验', '田间应用', '现场试验', 'open field'],
    'R3': ['review', '综述', 'meta-analysis', '系统综述', 'meta analysis', 'bibliometric', 'survey'],
    'R4': ['mechanism', '机理', 'pathway', 'gene', '蛋白', 'transcriptome', 'metabolome', '基因表达', '信号通路'],
    'R5': ['method', '方法', 'methodology', 'extraction', '培养方法', '培养条件', 'optimization', 'cultivation'],
}


def classify_dimension(text: str, keywords_dict: Dict[str, List[str]], default: str) -> Tuple[str, float]:
    """
    对单个维度进行分类
    
    Args:
        text: 待分类文本（标题+摘要）
        keywords_dict: 关键词字典
        default: 默认分类代码
    
    Returns:
        (分类代码, 置信度)
    """
    text_lower = text.lower()
    scores = {}
    
    for code, keywords in keywords_dict.items():
        score = 0
        for kw in keywords:
            # 不区分大小写匹配
            if kw.lower() in text_lower:
                score += 1
        if score > 0:
            scores[code] = score
    
    if not scores:
        return default, 0.3
    
    # 返回得分最高的分类，置信度基于得分
    best_code = max(scores, key=scores.get)
    # 归一化置信度：得分越高置信度越高，最高为0.9
    confidence = min(0.3 + scores[best_code] * 0.15, 0.9)
    
    return best_code, round(confidence, 2)


def classify_paper(paper: Dict[str, Any], dimensions: List[str]) -> Dict[str, Any]:
    """
    对单篇文献进行多维度分类
    
    Args:
        paper: 文献数据
        dimensions: 要分类的维度列表
    
    Returns:
        分类结果
    """
    # 合并标题和摘要进行匹配
    title = paper.get('title', '') or ''
    abstract = paper.get('abstract', '') or ''
    text = f"{title} {abstract}"
    
    classification = {}
    
    if 'mechanism' in dimensions:
        code, conf = classify_dimension(text, MECHANISM_KEYWORDS, 'M6')
        classification['mechanism'] = {'code': code, 'confidence': conf}
    
    if 'algae_type' in dimensions:
        code, conf = classify_dimension(text, ALGAE_KEYWORDS, 'A7')
        classification['algae_type'] = {'code': code, 'confidence': conf}
    
    if 'application' in dimensions:
        code, conf = classify_dimension(text, APPLICATION_KEYWORDS, 'C6')
        classification['application'] = {'code': code, 'confidence': conf}
    
    if 'research_type' in dimensions:
        code, conf = classify_dimension(text, RESEARCH_TYPE_KEYWORDS, 'R6')
        classification['research_type'] = {'code': code, 'confidence': conf}
    
    return classification


def main():
    parser = argparse.ArgumentParser(description='多维度文献分类脚本')
    parser.add_argument('--input', '-i', required=True, help='输入JSON文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出JSON文件路径')
    parser.add_argument('--dimensions', '-d', default='mechanism,algae_type,application,research_type',
                        help='要分类的维度，逗号分隔 (default: all)')
    parser.add_argument('--batch-size', '-b', type=int, default=100, help='批处理大小')
    
    args = parser.parse_args()
    
    logger = setup_logging('classify')
    
    # 解析维度
    dimensions = [d.strip() for d in args.dimensions.split(',')]
    valid_dimensions = {'mechanism', 'algae_type', 'application', 'research_type'}
    for dim in dimensions:
        if dim not in valid_dimensions:
            logger.error(f'无效维度: {dim}')
            sys.exit(1)
    
    logger.info(f'开始分类，维度: {dimensions}')
    logger.info(f'输入: {args.input}')
    logger.info(f'输出: {args.output}')
    
    # 加载数据
    papers = load_json(args.input)
    if not isinstance(papers, list):
        papers = [papers]
    
    logger.info(f'加载文献数: {len(papers)}')
    
    # 分类统计
    stats = {dim: {} for dim in dimensions}
    
    # 逐篇分类
    for paper in papers:
        classification = classify_paper(paper, dimensions)
        paper['classification'] = classification
        
        # 统计
        for dim in dimensions:
            code = classification[dim]['code']
            stats[dim][code] = stats[dim].get(code, 0) + 1
    
    # 保存结果
    save_json(papers, args.output)
    
    # 输出统计
    logger.info('=== 分类统计 ===')
    for dim in dimensions:
        logger.info(f'\n{dim}:')
        for code, count in sorted(stats[dim].items()):
            logger.info(f'  {code}: {count}')
    
    logger.info(f'\n分类完成，输出: {args.output}')


if __name__ == '__main__':
    main()
