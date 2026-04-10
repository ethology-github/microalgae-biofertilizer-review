# -*- encoding: utf-8 -*-
"""
文献质量评分脚本 (0-20分)

评分维度:
A. 方法学质量 (0-10分)
   - 对照组(0-3): 无对照0/有对照非随机1/随机对照3
   - 样本量(0-3): n<300/30-1001/100-5002/n>5003
   - 统计分析(0-4): 无0/基础t检验1/多因素分析2/高级统计3-4

B. 期刊质量 (0-6分)
   - SCI Q16分/Q24分/Q3-Q42分/非SCI有同行评审1分/未知0分
   - Q1期刊关键词: Nature, Science, Cell, PNAS, Nature Biotechnology, 
     Nature Microbiology, The ISME Journal, Environmental Science & Technology, ACS等

C. 相关性 (0-4分)
   - 完全匹配4/多关键词3/部分涉及2/弱相关1

决策: ≥12纳入/8-11复核/<8排除
"""

import argparse
import re
import sys
from pathlib import Path

# 添加scripts目录到路径以导入utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import setup_logging, load_json, save_json, ProgressTracker


# ===== Q1期刊关键词 (高影响力期刊) =====
Q1_JOURNAL_KEYWORDS = [
    'nature', 'science', 'cell', 'pnas', 'proceedings of the national academy of sciences',
    'nature biotechnology', 'nature microbiology', 'nature plants', 'nature food',
    'nature sustainability', 'nature communications',
    'the isme journal', 'isme journal',
    'environmental science & technology', 'environmental science and technology',
    'es&t',
    'acs nano', 'acs catalysis', 'acs sustainability', 'acs environmental',
    'journal of hazardous materials', 'bioresource technology',
    'water research', 'soil biology and biochemistry',
    'plant physiology', 'plant cell', 'plant journal',
    'molecular plant', 'plant biotechnology journal',
    'global change biology', 'trends in plant science',
    'advanced science', 'advanced materials',
    'scientific reports', 'plos one', 'elife'
]

# Q2期刊关键词
Q2_JOURNAL_KEYWORDS = [
    'scientific reports', 'plos one', 'elife',
    'frontiers in plant science', 'frontiers in microbiology',
    'biomolecules', 'antioxidants', 'molecules',
    'sustainability', 'scientia horticulturae',
    'journal of applied phycology', 'algal research',
    'bioresource technology reports', 'energy reports'
]

# 统计方法关键词
STATISTICAL_ADVANCED = [
    'mixed effect', 'mixed-effect', 'linear mixed', 'generalized linear',
    'cox regression', 'survival analysis', 'kaplan-meier',
    'principal component analysis', 'pca', 'factor analysis',
    'structural equation modeling', 'sem',
    'machine learning', 'random forest', 'support vector',
    'neural network', 'deep learning',
    'bayesian', 'markov chain monte carlo', 'mcmc',
    'multivariate analysis of variance', 'manova',
    'permanova', 'adonis', 'betadisper'
]

STATISTICAL_MULTIFACTOR = [
    'anova', 'analysis of variance', 'repeated measures',
    'multiple regression', 'multivariate regression',
    'logistic regression', 'negative binomial',
    'generalized estimating equation', 'gee',
    'duncan', 'tukey', 'lsd', 'scheffe',
    'Bonferroni', 'FDR', 'false discovery rate',
    'kenward-roger', 'satterthwaite'
]

STATISTICAL_BASIC = [
    't-test', 't test', 'student t', 'paired t',
    'chi-square', 'chi square', 'chi-square test',
    'mann-whitney', 'wilcoxon', 'kruskal-wallis',
    'fisher exact', 'correlation analysis',
    'pearson', 'spearman'
]

# 研究设计关键词
RCT_KEYWORDS = [
    'randomized controlled trial', 'randomised controlled trial',
    'rct', 'randomized design', 'randomised design',
    'randomly assigned', 'randomly分配', '随机分配',
    'random block', 'randomized block', 'rcbd'
]

CONTROL_KEYWORDS = [
    'control group', 'control treatment', '对照组', '对照处理',
    'control', 'contrast', 'reference group',
    'placebo', 'blank control', 'negative control',
    'positive control', 'standard control'
]


def check_control_group(text):
    """检查对照组设置情况 (0-3分)"""
    text_lower = text.lower()

    # 检查随机对照
    for kw in RCT_KEYWORDS:
        if kw.lower() in text_lower:
            return 3, "随机对照试验(RCT)"

    # 检查有对照但非随机
    has_control = any(kw.lower() in text_lower for kw in CONTROL_KEYWORDS)
    if has_control:
        return 1, "有对照但非随机"
    return 0, "无对照"


def check_sample_size(text):
    """检查样本量 (0-3分)"""
    text_lower = text.lower()

    # 尝试提取样本量数字
    # 匹配模式: n=XXX, n:XXX, N=XXX, sample size: XXX, samples: XXX
    patterns = [
        r'n\s*[=:]\s*(\d+)',
        r'N\s*[=:]\s*(\d+)',
        r'sample\s*size\s*[=:]\s*(\d+)',
        r'samples?\s*[=:]\s*(\d+)',
        r'n\s*=\s*(\d+)',
        r'total\s*(?:of\s*)?(\d+)',
        r'(\d+)\s*(?:subjects?|patients?|participants?|plants?|plots?|trials?)'
    ]

    sample_size = 0
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            try:
                size = int(match)
                # 取最大值作为样本量
                if size > sample_size:
                    sample_size = size
            except ValueError:
                continue

    # 根据样本量评分
    if sample_size >= 500:
        return 3, f"样本量n={sample_size}"
    elif sample_size >= 100:
        return 2, f"样本量n={sample_size}"
    elif sample_size >= 30:
        return 1, f"样本量n={sample_size}"
    else:
        return 0, "样本量<30或未知"


def check_statistical_analysis(text):
    """检查统计分析方法 (0-4分)"""
    text_lower = text.lower()

    # 检查高级统计
    advanced_count = sum(1 for kw in STATISTICAL_ADVANCED if kw.lower() in text_lower)
    if advanced_count >= 2:
        return 4, f"高级统计({advanced_count}种)"
    elif advanced_count == 1:
        return 3, "高级统计"

    # 检查多因素分析
    multifactor_count = sum(1 for kw in STATISTICAL_MULTIFACTOR if kw.lower() in text_lower)
    if multifactor_count >= 2:
        return 2, f"多因素分析({multifactor_count}种)"
    elif multifactor_count == 1:
        return 2, "多因素分析"

    # 检查基础统计
    basic_count = sum(1 for kw in STATISTICAL_BASIC if kw.lower() in text_lower)
    if basic_count >= 1:
        return 1, f"基础统计(t检验/卡方等)"

    return 0, "无统计分析"


def check_journal_quality(paper):
    """检查期刊质量 (0-6分)"""
    journal = str(paper.get('journal', '') or paper.get('venue', '') or '').lower()
    title = str(paper.get('title', '') or '').lower()

    # 检查是否被SCI收录
    is_sci = paper.get('is_sci', None)
    sci_quartile = str(paper.get('quartile', '') or paper.get('sci_quartile', '') or '').lower()

    # 首先检查Q1期刊关键词
    q1_match = any(kw in journal or kw in title for kw in Q1_JOURNAL_KEYWORDS)
    if q1_match:
        return 6, "SCI Q1期刊"

    # 检查Q2期刊
    q2_match = any(kw in journal or kw in title for kw in Q2_JOURNAL_KEYWORDS)
    if q2_match:
        return 4, "SCI Q2期刊"

    # 根据quartile判断
    if 'q1' in sci_quartile:
        return 6, "SCI Q1"
    elif 'q2' in sci_quartile:
        return 4, "SCI Q2"
    elif 'q3' in sci_quartile or 'q4' in sci_quartile:
        return 2, "SCI Q3/Q4"

    # 非SCI但有同行评审
    if is_sci is False or 'non-sci' in sci_quartile:
        return 1, "非SCI有同行评审"

    # 尝试从期刊名判断
    if journal:
        # 知名期刊通常为SCI
        known_journals = ['journal', 'international', 'research', 'review', 'bulletin']
        has_review = any(kw in journal for kw in known_journals)
        if has_review:
            return 1, "期刊论文(同行评审)"

    return 0, "期刊信息未知"


def check_relevance(paper):
    """检查相关性 (0-4分)"""
    title = str(paper.get('title', '') or '').lower()
    abstract = str(paper.get('abstract', '') or paper.get('ab', '') or '').lower()

    # 微藻关键词
    microalgae_keywords = [
        'microalgae', 'micro-algae', 'cyanobacteria', 'chlorella', 'spirulina',
        'scenedesmus', 'nannochloropsis', 'dunaliella', 'haematococcus',
        'arthrospira', 'anabaena', 'nostoc', 'chlamydomonas',
        'diatom', 'botryococcus', 'algae', '藻'
    ]

    # 生物肥关键词
    biofertilizer_keywords = [
        'biofertilizer', 'bio-fertilizer', 'biofertiliser', 'bio-fertiliser',
        'biostimulant', 'algal fertilizer', 'algal fertiliser',
        'nitrogen fixation', 'phosphorus solubilization', 'potassium solubilization',
        'plant growth', 'phytohormone', '生物肥', '生物肥料', '微生物肥'
    ]

    # 农业应用关键词
    agriculture_keywords = [
        'agriculture', 'agricultural', 'crop', 'soil', 'plant', 'yield',
        'greenhouse', 'field trial', 'seedling', 'germination',
        'salt stress', 'drought', 'heavy metal', 'phytoremediation',
        '农业', '作物', '土壤', '植物', '增产'
    ]

    # 统计匹配数
    micro_count = sum(1 for kw in microalgae_keywords if kw in title or kw in abstract)
    bio_count = sum(1 for kw in biofertilizer_keywords if kw in title or kw in abstract)
    agri_count = sum(1 for kw in agriculture_keywords if kw in title or kw in abstract)

    # 完全匹配: 三类关键词都有
    if micro_count >= 1 and bio_count >= 1 and agri_count >= 1:
        return 4, f"完全匹配(微藻{micro_count}个/生物肥{bio_count}个/农业{agri_count}个)"

    # 多关键词: 微藻+生物肥 或 微藻+农业
    if micro_count >= 1 and (bio_count >= 1 or agri_count >= 1):
        return 3, f"多关键词(微藻{micro_count}个/生物肥{bio_count}个/农业{agri_count}个)"

    # 部分涉及: 只有微藻
    if micro_count >= 1:
        return 2, f"部分涉及(微藻{micro_count}个)"

    # 弱相关
    return 1, "弱相关"


def calculate_quality_score(paper):
    """
    计算文献质量总分 (0-20分)

    返回: tuple (总分, 各维度得分字典, 决策)
    """
    # 合并标题和摘要用于分析
    title = str(paper.get('title', '') or '')
    abstract = str(paper.get('abstract', '') or paper.get('ab', '') or '')
    full_text = title + ' ' + abstract

    # A. 方法学质量
    control_score, control_reason = check_control_group(full_text)
    sample_score, sample_reason = check_sample_size(full_text)
    stat_score, stat_reason = check_statistical_analysis(full_text)
    methodology_score = control_score + sample_score + stat_score

    # B. 期刊质量
    journal_score, journal_reason = check_journal_quality(paper)

    # C. 相关性
    relevance_score, relevance_reason = check_relevance(paper)

    # 总分
    total_score = methodology_score + journal_score + relevance_score

    # 决策
    if total_score >= 12:
        decision = "纳入"
    elif total_score >= 8:
        decision = "复核"
    else:
        decision = "排除"

    scores = {
        'methodology_total': methodology_score,
        'control': {'score': control_score, 'reason': control_reason},
        'sample_size': {'score': sample_score, 'reason': sample_reason},
        'statistics': {'score': stat_score, 'reason': stat_reason},
        'journal': {'score': journal_score, 'reason': journal_reason},
        'relevance': {'score': relevance_score, 'reason': relevance_reason},
        'total': total_score,
        'decision': decision
    }

    return total_score, scores, decision


def score_papers(input_papers):
    """
    对文献列表进行质量评分

    返回: tuple (评分后的文献列表, 统计信息)
    """
    scored_papers = []
    stats = {
        'total': len(input_papers),
        'include': 0,
        'review': 0,
        'exclude': 0,
        'score_distribution': {}
    }

    progress = ProgressTracker(total=len(input_papers), desc="质量评分")

    for paper in input_papers:
        total_score, scores, decision = calculate_quality_score(paper)

        # 添加评分结果到文献
        paper['_quality_score'] = total_score
        paper['_quality_details'] = scores
        paper['_quality_decision'] = decision

        scored_papers.append(paper)

        # 统计
        if decision == "纳入":
            stats['include'] += 1
        elif decision == "复核":
            stats['review'] += 1
        else:
            stats['exclude'] += 1

        # 分数分布
        score_key = f"score_{total_score}"
        stats['score_distribution'][score_key] = stats['score_distribution'].get(score_key, 0) + 1

        progress.update()

    progress.finish()
    return scored_papers, stats


def main():
    parser = argparse.ArgumentParser(
        description='文献质量评分脚本 (0-20分)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
评分标准:
  A. 方法学质量 (0-10分)
     - 对照组: 无对照0/有对照非随机1/随机对照3
     - 样本量: n<300/30-1001/100-5002/n>5003
     - 统计分析: 无0/基础t检验1/多因素分析2/高级统计3-4

  B. 期刊质量 (0-6分)
     - SCI Q16分/Q24分/Q3-Q42分/非SCI有同行评审1分/未知0分

  C. 相关性 (0-4分)
     - 完全匹配4/多关键词3/部分涉及2/弱相关1

  决策: ≥12纳入/8-11复核/<8排除
        """
    )
    parser.add_argument('--input', '-i', required=True, help='输入文献JSON文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出评分后文献JSON文件路径')
    parser.add_argument('--include', help='输出纳入文献JSON文件路径(可选)')
    parser.add_argument('--review', help='输出需复核文献JSON文件路径(可选)')
    parser.add_argument('--exclude', help='输出排除文献JSON文件路径(可选)')
    parser.add_argument('--summary', help='输出统计摘要JSON文件路径(可选)')

    args = parser.parse_args()

    # 设置日志
    logger = setup_logging('quality_score')
    logger.info("开始文献质量评分")
    logger.info(f"输入文件: {args.input}")
    logger.info(f"输出文件: {args.output}")

    # 加载数据
    logger.info("加载文献数据...")
    papers = load_json(args.input)

    if not papers:
        logger.error("输入文件为空或无法解析")
        return 1

    logger.info(f"共加载 {len(papers)} 篇文献")

    # 评分
    scored_papers, stats = score_papers(papers)

    # 打印统计信息
    logger.info("=" * 60)
    logger.info("质量评分统计:")
    logger.info(f"  总文献数: {stats['total']}")
    logger.info(f"  纳入(≥12分): {stats['include']} ({stats['include']/stats['total']*100:.1f}%)")
    logger.info(f"  复核(8-11分): {stats['review']} ({stats['review']/stats['total']*100:.1f}%)")
    logger.info(f"  排除(<8分): {stats['exclude']} ({stats['exclude']/stats['total']*100:.1f}%)")
    logger.info("=" * 60)

    # 分数分布
    logger.info("分数分布:")
    for score_key in sorted(stats['score_distribution'].keys()):
        count = stats['score_distribution'][score_key]
        logger.info(f"  {score_key.replace('score_', '')}分: {count}篇")

    # 按决策分类
    included = [p for p in scored_papers if p['_quality_decision'] == '纳入']
    to_review = [p for p in scored_papers if p['_quality_decision'] == '复核']
    excluded = [p for p in scored_papers if p['_quality_decision'] == 'exclude']

    # 保存结果
    logger.info(f"保存评分结果到: {args.output}")
    save_json(scored_papers, args.output)

    # 保存分类结果
    if args.include and included:
        logger.info(f"保存纳入文献到: {args.include}")
        save_json(included, args.include)

    if args.review and to_review:
        logger.info(f"保存需复核文献到: {args.review}")
        save_json(to_review, args.review)

    if args.exclude and excluded:
        logger.info(f"保存排除文献到: {args.exclude}")
        save_json(excluded, args.exclude)

    # 保存统计摘要
    if args.summary:
        summary = {
            'total_papers': stats['total'],
            'include_count': stats['include'],
            'review_count': stats['review'],
            'exclude_count': stats['exclude'],
            'include_rate': round(stats['include']/stats['total']*100, 2) if stats['total'] > 0 else 0,
            'score_distribution': stats['score_distribution']
        }
        logger.info(f"保存统计摘要到: {args.summary}")
        save_json(summary, args.summary)

    logger.info("质量评分完成!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
