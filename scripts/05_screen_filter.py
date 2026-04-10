# -*- encoding: utf-8 -*-
"""
两阶段文献筛选脚本

Stage 1 (标题筛选): 用关键词匹配过滤明显不相关文献
Stage 2 (摘要筛选): 对标题通过的文章进行摘要级别筛选

纳入标准:
- 微藻+生物肥+农业应用
- 期刊/综述
- 中英文
- 2015至今
- 有摘要

排除标准:
- 非微藻、纯工艺、专利/会议摘要、无摘要、重复
"""

import argparse
import re
import sys
from pathlib import Path

# 添加scripts目录到路径以导入utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import setup_logging, load_json, save_json, ProgressTracker


# ===== 关键词定义 =====
# 微藻关键词 (中文)
MICROALGAE_CN = [
    '微藻', '蓝藻', '绿藻', '螺旋藻', '小球藻', '盐藻', '硅藻', '甲藻',
    '螺旋藻', '栅藻', '杜氏藻', '眼点藻', '红球藻', '雨生红球藻',
    '集胞藻', '鱼腥藻', '固氮藻', '念珠藻', '颤藻', '席藻',
    '莱茵衣藻', '亚心形扁藻', '扁藻', '小球藻属', '螺旋藻属',
    'Chlorella', 'Spirulina', 'Scenedesmus', 'Nannochloropsis',
    'Dunaliella', 'Haematococcus', 'Arthrospira', 'Anabaena',
    'Nostoc', 'Cyanobacteria', 'Microcystis', 'Chlamydomonas',
    'Phaeodactylum', 'Thalassiosira', 'Skeletonema', 'Tetraselmis',
    'Isochrysis', 'Pavlova', 'Chaetoceros', 'Amphora'
]

# 微藻关键词 (英文)
MICROALGAE_EN = [
    'microalgae', 'micro-algae', 'cyanobacteria', 'blue-green algae',
    'chlorella', 'spirulina', 'scenedesmus', 'nannochloropsis',
    'dunaliella', 'haematococcus', 'arthrospira', 'anabaena',
    'nostoc', 'chlamydomonas', 'phaeodactylum', 'tetraselmis',
    'isochrysis', 'pavlova', 'chaetoceros', 'diatom', 'dinoflagellate',
    'botryococcus', 'ochlorella', 'auxenochlorella'
]

# 生物肥关键词 (中文)
BIOFERTILIZER_CN = [
    '生物肥', '生物肥料', '微生物肥', '藻肥', '有机肥', '生物有机肥',
    '微生物菌肥', '生物刺激素', '藻类肥料', '微藻肥料',
    '固氮', '解磷', '解钾', '促生', '植物生长促进'
]

# 生物肥关键词 (英文)
BIOFERTILIZER_EN = [
    'biofertilizer', 'bio-fertilizer', 'biofertilisers', 'bio-fertilisers',
    'algal fertilizer', 'algal fertiliser', 'microalgal fertilizer',
    'microalgae fertilizer', 'microalgae biofertilizer', 'algal biofertilizer',
    'biostimulant', 'biostimulator', 'plant growth promotion',
    'nitrogen fixation', 'nitrogen-fixing', 'phosphorus solubilization',
    'potassium solubilization', 'phytohormone', 'plant growth regulator'
]

# 农业应用关键词 (中文)
AGRICULTURE_CN = [
    '农业', '农作', '作物', '植物', '土壤', '增产', '促生长',
    '水稻', '小麦', '玉米', '大豆', '番茄', '黄瓜', '蔬菜',
    '水果', '花卉', '园艺', '大田', '盆栽', '温室', '育苗',
    '种子', '发芽', '根际', '根瘤', '叶面', '土壤改良',
    '盐碱地', '重金属', '退化土壤', '有机农业', '可持续农业'
]

# 农业应用关键词 (英文)
AGRICULTURE_EN = [
    'agriculture', 'agricultural', 'crop', 'crops', 'plant', 'plants',
    'soil', 'soils', 'yield', 'yields', 'growth', 'plant growth',
    'nitrogen fixation', 'phosphorus solubilization', 'potassium mobilization',
    'rhizosphere', 'rhizobia', 'inoculant', 'inoculum', 'fertilizer',
    'fertiliser', 'nitrogen', 'phosphorus', 'potassium', 'NPK',
    'field trial', 'field experiment', 'greenhouse', 'pot experiment',
    'hydroponic', 'hydroponics', 'seedling', 'seed germination',
    'salt stress', 'drought stress', 'heavy metal', 'phytoremediation',
    'sustainable agriculture', 'organic farming', 'organic agriculture'
]

# 排除的类型
EXCLUDE_TYPES = [
    'patent', 'patents', '专利',
    'conference abstract', 'conference proceeding', '会议摘要', '会议论文',
    'meeting abstract', 'symposium abstract',
    'editorial', '编辑前言', '社论',
    'news', 'news article', '新闻', '新闻稿',
    'review article', 'review of...', '系统评价'  # 但综述是纳入的，这里指非系统评价类
]

# 纳入的文献类型
INCLUDE_TYPES = [
    'journal article', 'article', '期刊论文', '研究论文',
    'review', '综述', '系统综述', 'meta-analysis', 'meta分析'
]


def compile_keywords():
    """编译所有关键词为正则表达式模式"""
    all_keywords = []

    # 微藻 (中英文合并)
    for kw in MICROALGAE_CN + MICROALGAE_EN:
        all_keywords.append(re.escape(kw.lower()))

    # 生物肥 (中英文合并)
    for kw in BIOFERTILIZER_CN + BIOFERTILIZER_EN:
        all_keywords.append(re.escape(kw.lower()))

    # 农业 (中英文合并)
    for kw in AGRICULTURE_CN + AGRICULTURE_EN:
        all_keywords.append(re.escape(kw.lower()))

    # 编译组合模式
    pattern = '|'.join(all_keywords)
    return re.compile(pattern, re.IGNORECASE)


# 预编译关键词模式
KEYWORD_PATTERN = compile_keywords()


def check_year_valid(paper, min_year=2015):
    """检查文献年份是否在有效范围内"""
    year = paper.get('year') or paper.get('published_year') or paper.get('date')
    if not year:
        return True  # 没有年份信息，默认保留
    try:
        year_int = int(str(year)[:4])
        return year_int >= min_year
    except (ValueError, TypeError):
        return True  # 无法解析年份，默认保留


def check_document_type(paper):
    """检查文献类型，排除专利和会议摘要"""
    doc_type = str(paper.get('type', '') or paper.get('document_type', '') or '').lower()
    title = str(paper.get('title', '') or '').lower()
    abstract = str(paper.get('abstract', '') or '').lower()

    # 检查是否为例外类型
    for exclude in EXCLUDE_TYPES:
        if exclude.lower() in doc_type or exclude.lower() in title:
            # 如果同时包含微藻和生物肥关键词，可能是误判
            microalgae_found = any(kw.lower() in title + abstract for kw in
                                  MICROALGAE_CN + MICROALGAE_EN)
            biofert_found = any(kw.lower() in title + abstract for kw in
                               BIOFERTILIZER_CN + BIOFERTILIZER_EN)
            if microalgae_found and biofert_found:
                continue  # 关键文献即使标题像专利也保留
            return False
    return True


def check_has_abstract(paper):
    """检查是否有摘要"""
    abstract = paper.get('abstract') or paper.get('ab') or paper.get('abstract_cn')
    return bool(abstract and len(str(abstract).strip()) > 50)


def stage1_title_screen(paper):
    """
    阶段一筛选：标题关键词匹配

    返回: tuple (通过筛选, 原因)
    """
    title = str(paper.get('title', '') or '').lower()

    # 必须包含微藻关键词
    has_microalgae = any(
        kw.lower() in title
        for kw in MICROALGAE_CN + MICROALGAE_EN
    )

    # 必须包含生物肥或农业关键词之一
    has_biofertilizer = any(
        kw.lower() in title
        for kw in BIOFERTILIZER_CN + BIOFERTILIZER_EN
    )
    has_agriculture = any(
        kw.lower() in title
        for kw in AGRICULTURE_CN + AGRICULTURE_EN
    )

    if not has_microalgae:
        return False, "Stage1: 无微藻关键词"

    if not (has_biofertilizer or has_agriculture):
        return False, "Stage1: 无生物肥/农业关键词"

    return True, "Stage1: 通过"


def stage2_abstract_screen(paper):
    """
    阶段二筛选：摘要级别筛选

    综合判断相关性，采用打分制
    """
    title = str(paper.get('title', '') or '').lower()
    abstract = str(paper.get('abstract', '') or paper.get('ab', '') or '').lower()
    full_text = title + ' ' + abstract

    score = 0
    reasons = []

    # 微藻关键词匹配 (必须)
    microalgae_count = sum(1 for kw in MICROALGAE_CN + MICROALGAE_EN if kw.lower() in full_text)
    if microalgae_count >= 1:
        score += 2
        reasons.append(f"微藻匹配({microalgae_count})")
    else:
        return False, "Stage2: 无微藻关键词"

    # 生物肥关键词匹配
    bio_count = sum(1 for kw in BIOFERTILIZER_CN + BIOFERTILIZER_EN if kw.lower() in full_text)
    if bio_count >= 1:
        score += 2
        reasons.append(f"生物肥匹配({bio_count})")

    # 农业应用关键词匹配
    agri_count = sum(1 for kw in AGRICULTURE_CN + AGRICULTURE_EN if kw.lower() in full_text)
    if agri_count >= 1:
        score += 1
        reasons.append(f"农业匹配({agri_count})")

    # 排除项检查
    exclude_terms = ['工艺', '工艺优化', '提取工艺', '发酵工艺', '培养工艺',
                     'process', 'processing', 'extraction process', 'fermentation',
                     'bioreactor design', 'cultivation system', 'harvesting process']
    for term in exclude_terms:
        if term.lower() in full_text:
            # 如果排除词出现但也有很强的应用相关性，可能保留
            if score >= 4:
                score -= 1

    # 综合判断
    if score >= 3:
        return True, f"Stage2: 通过 ({'; '.join(reasons)})"
    else:
        return False, f"Stage2: 分数不足 (score={score})"


def screen_paper(paper, include_excluded=False):
    """
    对单篇文献进行完整筛选流程

    Args:
        paper: 文献数据字典
        include_excluded: 是否在排除列表中记录被筛选掉的文献

    Returns:
        tuple: (是否纳入, 筛选原因, 是否为排除记录)
    """
    # 前置检查
    if not check_document_type(paper):
        return False, "排除: 专利/会议摘要类型", True

    if not check_year_valid(paper):
        return False, "排除: 2015年前文献", True

    if not check_has_abstract(paper):
        return False, "排除: 无摘要", True

    # 阶段一：标题筛选
    passed_s1, reason_s1 = stage1_title_screen(paper)
    if not passed_s1:
        return False, reason_s1, True

    # 阶段二：摘要筛选
    passed_s2, reason_s2 = stage2_abstract_screen(paper)
    if not passed_s2:
        return False, reason_s2, True

    return True, "纳入: 通过两阶段筛选", False


def load_excluded_list(excluded_path):
    """加载已排除的文献列表（用于跳过已确认排除的文献）"""
    if excluded_path and Path(excluded_path).exists():
        excluded_data = load_json(excluded_path)
        if excluded_data:
            # 返回DOI和标题的集合用于快速查重
            excluded_dois = {p.get('doi', '').lower() for p in excluded_data if p.get('doi')}
            excluded_titles = {p.get('title', '').lower() for p in excluded_data if p.get('title')}
            return excluded_dois, excluded_titles
    return set(), set()


def main():
    parser = argparse.ArgumentParser(
        description='两阶段文献筛选脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--input', '-i', required=True, help='输入文献JSON文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出筛选后文献JSON文件路径')
    parser.add_argument('--excluded', '-e', help='输出排除文献JSON文件路径(可选)')
    parser.add_argument('--references', '-r', help='输出参考文献列表(用于报告)')
    parser.add_argument('--min-year', type=int, default=2015, help='最小发表年份(默认2015)')

    args = parser.parse_args()

    # 设置日志
    logger = setup_logging('screen_filter')
    logger.info(f"开始文献筛选流程")
    logger.info(f"输入文件: {args.input}")
    logger.info(f"输出文件: {args.output}")

    # 加载数据
    logger.info("加载文献数据...")
    papers = load_json(args.input)

    if not papers:
        logger.error("输入文件为空或无法解析")
        return 1

    logger.info(f"共加载 {len(papers)} 篇文献")

    # 筛选
    included_papers = []
    excluded_papers = []
    skipped = 0

    progress = ProgressTracker(total=len(papers), desc="筛选进度")

    for paper in papers:
        # 提取摘要用于筛选（如果标题通过的话）
        is_included, reason, is_excluded_record = screen_paper(paper)

        if is_included:
            # 添加筛选原因到文献记录
            paper['_screening_reason'] = reason
            included_papers.append(paper)
            logger.debug(f"纳入: {paper.get('title', 'N/A')[:50]}... - {reason}")
        elif is_excluded_record:
            paper['_screening_reason'] = reason
            excluded_papers.append(paper)
            logger.debug(f"排除: {paper.get('title', 'N/A')[:50]}... - {reason}")
        else:
            skipped += 1
            logger.debug(f"跳过: {paper.get('title', 'N/A')[:50]}... - {reason}")

        progress.update()

    progress.finish()

    # 统计
    logger.info("=" * 60)
    logger.info("筛选统计:")
    logger.info(f"  总文献数: {len(papers)}")
    logger.info(f"  纳入文献: {len(included_papers)} ({len(included_papers)/len(papers)*100:.1f}%)")
    logger.info(f"  排除文献: {len(excluded_papers)} ({len(excluded_papers)/len(papers)*100:.1f}%)")
    logger.info(f"  跳过: {skipped}")
    logger.info("=" * 60)

    # 排除原因统计
    if excluded_papers:
        reason_counts = {}
        for p in excluded_papers:
            reason = p.get('_screening_reason', '未知')
            # 提取主要排除原因
            main_reason = reason.split(':')[0] if ':' in reason else reason
            reason_counts[main_reason] = reason_counts.get(main_reason, 0) + 1

        logger.info("排除原因分布:")
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            logger.info(f"  {reason}: {count}")

    # 保存结果
    logger.info(f"保存纳入文献到: {args.output}")
    save_json(included_papers, args.output)

    # 保存排除文献列表
    if args.excluded:
        logger.info(f"保存排除文献到: {args.excluded}")
        save_json(excluded_papers, args.excluded)

    # 保存参考文献格式列表
    if args.references and included_papers:
        ref_list = []
        for i, p in enumerate(included_papers, 1):
            authors = p.get('authors', [])
            if isinstance(authors, list):
                authors_str = ', '.join(authors[:3]) + (' et al.' if len(authors) > 3 else '')
            else:
                authors_str = str(authors)

            year = p.get('year', 'n.d.')
            title = p.get('title', 'Untitled')
            journal = p.get('journal', p.get('venue', 'Unknown'))

            ref = f"{authors_str} ({year}). {title}. {journal}."
            ref_list.append({'id': i, 'reference': ref, 'doi': p.get('doi', '')})

        save_json(ref_list, args.references)
        logger.info(f"保存参考文献列表到: {args.references}")

    logger.info("筛选完成!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
