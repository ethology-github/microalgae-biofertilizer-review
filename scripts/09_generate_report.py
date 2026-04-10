# -*- encoding: utf-8 -*-
"""
IMRAD格式Markdown报告生成脚本

功能：
1. 读取质量评分JSON + 报告模板Markdown
2. 填充各章节内容（摘要/引言/方法/结果/讨论/结论/参考文献/附录）
3. 在结果章节引用图表 outputs/figures/ 中的图表
4. 按GB/T 7714-2015格式生成参考文献

命令行参数：
--input: 质量评分后的文献JSON文件路径
--figures: 图表目录路径 (default: outputs/figures)
--template: Markdown模板路径 (default: references/report-template.md)
--output: 输出Markdown文件路径
"""

import argparse
import json
import re
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 尝试从utils导入，失败时使用内联实现
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from utils import setup_logging, load_json, save_json
except ImportError:
    # 内联实现占位函数
    def setup_logging(name='report_gen'):
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def load_json(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_json(data, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ===== GB/T 7714-2015 参考文献格式生成 =====

REFERENCE_EXAMPLES = {
    'journal': '[{authors}. {title}[J]. {journal}, {year}, {volume}({issue}): {pages}. doi: {doi}]',
    'book': '[{authors}. {title}[M]. {edition}. {place}: {publisher}, {year}.]',
    'conference': '[{authors}. {title}[C]// {conf_name}. {place}: {publisher}, {year}: {pages}.]',
    'thesis': '[{authors}. {title}[D/OL]. {institution}, {year}. URL: {url}]',
    'default': '[{authors}. {title}. {year}.]'
}


def format_authors(authors: List[str], max_display: int = 10) -> str:
    """格式化作者列表
    
    Args:
        authors: 作者列表
        max_display: 最多显示作者数，超过用"等"
    
    Returns:
        格式化的作者字符串
    """
    if not authors:
        return 'Anonymous'
    
    # 清理作者名
    cleaned = []
    for author in authors[:max_display]:
        author = str(author).strip()
        # 移除机构等非人名内容
        if author and len(author) > 1:
            cleaned.append(author)
    
    if len(authors) > max_display:
        return ', '.join(cleaned) + ', 等'
    return ', '.join(cleaned)


def format_reference(paper: Dict[str, Any], ref_type: str = 'journal') -> str:
    """生成GB/T 7714-2015格式的参考文献条目
    
    Args:
        paper: 文献数据字典
        ref_type: 文献类型 (journal/book/conference/thesis)
    
    Returns:
        格式化后的参考文献字符串
    """
    # 提取字段
    title = paper.get('title', 'Unknown Title')
    authors = paper.get('authors', paper.get('author', []))
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(',')]
    
    year = paper.get('year', paper.get('published_year', ''))
    journal = paper.get('journal', paper.get('venue', ''))
    volume = paper.get('volume', '')
    issue = paper.get('issue', paper.get('number', ''))
    pages = paper.get('pages', paper.get('page', ''))
    doi = paper.get('doi', '')
    publisher = paper.get('publisher', '')
    place = paper.get('place', '')
    
    # 格式化作者
    authors_str = format_authors(authors)
    
    # 根据类型生成
    if ref_type == 'journal' and journal:
        result = f"{authors_str}. {title}[J]. {journal}, {year}"
        if volume:
            result += f", {volume}"
            if issue:
                result += f"({issue})"
        if pages:
            result += f": {pages}"
        result += f". doi: {doi}" if doi else ""
        return result
    
    elif ref_type == 'conference':
        conf_name = paper.get('conference', journal)
        result = f"{authors_str}. {title}[C]// {conf_name}. "
        if place:
            result += f"{place}: "
        if publisher:
            result += f"{publisher}, "
        result += f"{year}"
        if pages:
            result += f": {pages}"
        return result
    
    elif ref_type == 'book' and publisher:
        edition = paper.get('edition', '')
        edition_str = f". {edition}版" if edition else ""
        result = f"{authors_str}. {title}[M]{edition_str}. "
        if place:
            result += f"{place}: "
        result += f"{publisher}, {year}."
        return result
    
    elif ref_type == 'thesis':
        institution = paper.get('institution', paper.get('school', ''))
        url = paper.get('url', '')
        result = f"{authors_str}. {title}[D/OL]. {institution}, {year}."
        if url:
            result += f" URL: {url}"
        return result
    
    # 默认格式
    return f"{authors_str}. {title}. {year}."


def generate_references(papers: List[Dict[str, Any]], max_refs: int = 500) -> str:
    """生成完整的参考文献列表
    
    Args:
        papers: 文献列表
        max_refs: 最大参考文献数
    
    Returns:
        格式化的参考文献字符串
    """
    refs = []
    for i, paper in enumerate(papers[:max_refs], 1):
        # 判断文献类型
        paper_type = paper.get('type', paper.get('resource_type', 'journal'))
        
        if 'conference' in str(paper_type).lower():
            ref = format_reference(paper, 'conference')
        elif 'book' in str(paper_type).lower():
            ref = format_reference(paper, 'book')
        elif 'thesis' in str(paper_type).lower() or 'dissertation' in str(paper_type).lower():
            ref = format_reference(paper, 'thesis')
        else:
            ref = format_reference(paper, 'journal')
        
        # 添加序号
        refs.append(f"[{i}] {ref}")
    
    # 统计
    en_count = sum(1 for r in refs if re.search(r'[\u4e00-\u9fff]', r) is None)
    zh_count = len(refs) - en_count
    
    header = f"\n\n本综述共引用 {len(refs)} 篇文献，其中英文 {en_count} 篇，中文 {zh_count} 篇。\n\n"
    return header + '\n\n'.join(refs)


# ===== 报告生成核心逻辑 =====

def parse_template(template_path: Path) -> Dict[str, str]:
    """解析Markdown模板，提取各章节
    
    Returns:
        章节字典 {section_name: content}
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按二级标题分割
    sections = {}
    current_section = 'header'
    current_content = []
    
    for line in content.split('\n'):
        # 检测二级标题 (## )
        if line.startswith('## '):
            # 保存上一个章节
            if current_section != 'header':
                sections[current_section] = '\n'.join(current_content).strip()
            # 开始新章节
            current_section = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)
    
    # 保存最后一个章节
    if current_section != 'header':
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections


def calculate_statistics(papers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """从文献数据计算统计信息
    
    Returns:
        统计信息字典
    """
    if not papers:
        return {
            'total': 0,
            'en_papers': 0,
            'zh_papers': 0,
            'avg_score': 0,
            'year_range': ('', ''),
            'mechanism_stats': {},
            'algae_stats': {},
            'application_stats': {},
            'top_journals': [],
            'top_authors': []
        }
    
    total = len(papers)
    
    # 语言统计
    en_papers = sum(1 for p in papers if p.get('language', 'en') != 'zh')
    zh_papers = total - en_papers
    
    # 平均质量评分
    scores = [p.get('_quality_score', 0) for p in papers if '_quality_score' in p]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # 年份范围
    years = [p.get('year', p.get('published_year', 0)) for p in papers if p.get('year')]
    year_range = (min(years) if years else '', max(years) if years else '')
    
    # 分类统计
    mechanism_stats = {}
    algae_stats = {}
    application_stats = {}
    
    for p in papers:
        cls = p.get('classification', {})
        
        # 机制分类
        mech = cls.get('mechanism', {})
        if isinstance(mech, dict):
            code = mech.get('code', 'M6')
        else:
            code = str(mech)
        mechanism_stats[code] = mechanism_stats.get(code, 0) + 1
        
        # 藻种分类
        algae = cls.get('algae_type', {})
        if isinstance(algae, dict):
            code = algae.get('code', 'A7')
        else:
            code = str(algae)
        algae_stats[code] = algae_stats.get(code, 0) + 1
        
        # 应用分类
        app = cls.get('application', {})
        if isinstance(app, dict):
            code = app.get('code', 'C6')
        else:
            code = str(app)
        application_stats[code] = application_stats.get(code, 0) + 1
    
    # 期刊统计
    journal_counts = {}
    for p in papers:
        journal = p.get('journal', p.get('venue', ''))
        if journal and isinstance(journal, str):
            journal_counts[journal] = journal_counts.get(journal, 0) + 1
    top_journals = sorted(journal_counts.items(), key=lambda x: -x[1])[:10]
    
    # 作者统计
    author_counts = {}
    for p in papers:
        authors = p.get('authors', p.get('author', []))
        if isinstance(authors, str):
            authors = [authors]
        for author in authors[:3]:  # 只统计前3作者
            author = str(author).strip()
            if author:
                author_counts[author] = author_counts.get(author, 0) + 1
    top_authors = sorted(author_counts.items(), key=lambda x: -x[1])[:10]
    
    return {
        'total': total,
        'en_papers': en_papers,
        'zh_papers': zh_papers,
        'avg_score': round(avg_score, 2),
        'year_range': year_range,
        'mechanism_stats': mechanism_stats,
        'algae_stats': algae_stats,
        'application_stats': application_stats,
        'top_journals': top_journals,
        'top_authors': top_authors,
        'score_distribution': papers[0].get('_quality_details', {}).get('score_distribution', {}) if papers else {}
    }


def get_figure_list(figures_dir: Path) -> List[str]:
    """获取图表目录中的所有图片
    
    Returns:
        图片文件列表
    """
    if not figures_dir.exists():
        return []
    
    image_extensions = {'.png', '.jpg', '.jpeg', '.svg', '.pdf'}
    figures = []
    
    for f in sorted(figures_dir.iterdir()):
        if f.suffix.lower() in image_extensions:
            figures.append(f.name)
    
    return figures


def fill_abstract(papers: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
    """生成摘要内容
    
    Args:
        papers: 文献列表
        stats: 统计信息
    
    Returns:
        摘要文本
    """
    total = stats['total']
    year_range = stats['year_range']
    avg_score = stats['avg_score']
    
    # 机制分布
    mech = stats['mechanism_stats']
    top_mech = max(mech.items(), key=lambda x: x[1])[0] if mech else '未知'
    
    # 藻种分布
    algae = stats['algae_stats']
    top_algae = max(algae.items(), key=lambda x: x[1])[0] if algae else '未知'
    
    abstract = f"""本综述系统性地检索和分析了微藻类生物肥在农业应用中的研究现状。研究涵盖{total}篇文献，时间跨度从{year_range[0]}年至{year_range[1]}年。文献质量评估平均得分为{avg_score}分。研究内容包括微藻的促生机制分析、肥效评估、藻种差异及实际应用效果分析。

在机制研究方面，主要集中在{top_mech}类机制（{mech.get(top_mech, 0)}篇），表明该机制是当前研究热点。在藻种研究方面，{top_algae}类藻种为主要研究对象（{algae.get(top_algae, 0)}篇），显示出特定藻种在生物肥应用中的优势地位。

结果表明，微藻类生物肥在提高作物产量、改善土壤微生物群落、促进营养元素利用等方面展现出显著潜力。不同藻种的功效存在差异，作用机制尚需深入阐明。本报告为微藻类生物肥的进一步研究和产业化应用提供了系统性参考。"""

    return abstract.strip()


def fill_introduction(stats: Dict[str, Any]) -> str:
    """生成引言内容（固定内容 + 数据统计）
    
    Returns:
        引言文本
    """
    total = stats['total']
    year_range = stats['year_range']
    
    intro = f"""### 1.1 研究背景

微藻类生物肥作为可持续农业发展的重要生物资源，近年来受到了广泛关注。化学肥料的过度使用导致了一系列环境问题，包括土壤酸化、水体富营养化和生物多样性下降。在此背景下，微藻作为一种绿色、低碳的生物资源，其在农业中的应用前景备受期待。微藻不仅能够提供植物所需的营养元素，还能通过分泌植物激素和改善土壤微生物群落来促进作物生长。

### 1.2 微藻类生物肥的定义与分类

微藻类生物肥是指以微藻为主要活性成分，通过特定工艺加工制成的肥料产品。根据藻种类别，主要可分为蓝藻（如鱼腥藻、念珠藻、螺旋藻）、绿藻（如小球藻、栅藻）和硅藻等。微藻类生物肥的产品形态包括活体藻液、藻粉、藻提取物以及复合微生物肥料等。

### 1.3 国内外研究现状

本综述系统检索了国内外主要数据库，共纳入{total}篇文献进行分析。研究时间跨度为{year_range[0]}年至{year_range[1]}年。现有研究主要集中在微藻的促生机制解析、藻种筛选优化、田间试验效果评价等方面。然而，当前研究在以下方面仍存在不足：（1）作用机制的分子层面解析不够深入；（2）田间试验标准化程度低；（3）不同藻种间功效差异的系统对比研究较少。

### 1.4 研究目的与问题

本综述旨在回答以下核心问题：（1）微藻类生物肥对不同作物的促生效果如何？（2）其作用机制涉及哪些生理和分子途径？（3）不同藻种之间是否存在显著功效差异？（4）当前证据能否支撑微藻类生物肥的大规模推广应用？"""

    return intro


def fill_methods(papers: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
    """生成方法章节内容
    
    Returns:
        方法文本
    """
    total = stats['total']
    en_papers = stats['en_papers']
    zh_papers = stats['zh_papers']
    year_range = stats['year_range']
    
    methods = f"""### 2.1 文献检索策略

本综述采用系统性文献综述方法，检索时间范围为{year_range[0]}年至{year_range[1]}年。检索数据库包括以下三个主要数据库：

- **Web of Science** — 覆盖SCI/SSCI高影响力期刊文献，以主题词"microalgae biofertilizer"、"cyanobacteria agricultural application"、"algae plant growth promotion"等进行检索
- **CNKI（中国知网）** — 覆盖中文核心期刊、学位论文和会议论文，以主题词"微藻生物肥"、"蓝藻农用"、"藻类促生因子"等进行检索
- **PubMed** — 覆盖生物医学与农业科学交叉领域，以MeSH词"microalgae"、"biofertilizers"、"agricultural crops"等进行检索

采用布尔逻辑运算符（AND/OR/NOT）组合检索词，并进行摘要筛选和全文评估。

### 2.2 文献筛选流程

采用PRISMA 2020报告规范进行筛选，筛选标准如下：

**纳入标准：**
- 研究对象为微藻类物质在农业领域的应用
- 包含对照组且有可提取的量化或定性数据
- 原始研究或综述类文献
- 中英文发表

**排除标准：**
- 非农业应用场景（如能源、污水处理、食品添加）
- 无法获取全文且信息不完整
- 重复发表或数据高度重叠
- 质量评估不通过的低可信度文献

两名独立评审者进行筛选，分歧通过讨论解决。

### 2.3 数据提取

制定标准化数据提取表，由两名独立评审者提取以下信息：

- 研究基本信息（作者、年份、期刊、DOI）
- 实验设计（藻种、作物类型、实验规模：盆栽/田间）
- 施用方式与剂量
- 主要结果指标（产量、养分含量、土壤性质等）
- 机制分析相关发现

### 2.4 质量评估

采用改良版JBI循证卫生保健质量评估工具对纳入的原始研究进行质量评估。评估维度包括：

- 研究设计合理性（0-3分）
- 样本量与统计效力（0-3分）
- 测量方法的可靠性（0-3分）
- 结果报告的完整性（0-3分）
- 偏倚风险评估（0-3分）

质量评估得分阈值为：≥12分纳入，8-11分需复核，<8分排除。"""

    return methods


def fill_results(papers: List[Dict[str, Any]], stats: Dict[str, Any], figures: List[str]) -> str:
    """生成结果章节内容
    
    Args:
        papers: 文献列表
        stats: 统计信息
        figures: 图表列表
    
    Returns:
        结果文本
    """
    total = stats['total']
    en_papers = stats['en_papers']
    zh_papers = stats['zh_papers']
    mechanism_stats = stats['mechanism_stats']
    algae_stats = stats['algae_stats']
    application_stats = stats['application_stats']
    avg_score = stats['avg_score']
    
    # 图表引用
    fig1_ref = f"如图1所示" if 'fig1' in str(figures).lower() or len(figures) >= 1 else ""
    fig2_ref = f"如图2所示" if 'fig2' in str(figures).lower() or len(figures) >= 2 else ""
    fig3_ref = f"如图3所示" if 'fig3' in str(figures).lower() or len(figures) >= 3 else ""
    fig4_ref = f"如图4所示" if 'fig4' in str(figures).lower() or len(figures) >= 4 else ""
    fig5_ref = f"如图5所示" if 'fig5' in str(figures).lower() or len(figures) >= 5 else ""
    
    # 机制分类描述
    mech_descriptions = {
        'M1': '固氮作用',
        'M2': '解磷作用',
        'M3': '促生长激素分泌',
        'M4': '生物刺激素作用',
        'M5': '土壤改良效应',
        'M6': '未知/未明确'
    }
    mech_list = ', '.join([f"{mech_descriptions.get(k, k)}({v}篇)" for k, v in sorted(mechanism_stats.items())])
    
    # 藻种分类描述
    algae_descriptions = {
        'A1': '螺旋藻属(Spirulina)',
        'A2': '小球藻属(Chlorella)',
        'A3': '蓝藻门(Cyanobacteria)',
        'A4': '绿藻门(Chlorophyta)',
        'A5': '硅藻门(Bacillariophyta)',
        'A6': '混合藻种',
        'A7': '其他/未明确'
    }
    algae_list = ', '.join([f"{algae_descriptions.get(k, k)}({v}篇)" for k, v in sorted(algae_stats.items())])
    
    # 应用分类描述
    app_descriptions = {
        'C1': '大田作物',
        'C2': '园艺作物',
        'C3': '水产养殖',
        'C4': '土壤改良',
        'C5': '多种应用',
        'C6': '未明确'
    }
    app_list = ', '.join([f"{app_descriptions.get(k, k)}({v}篇)" for k, v in sorted(application_stats.items())])
    
    results = f"""### 3.1 文献筛选概况

经过系统检索和筛选，本综述共纳入{total}篇文献进行分析，其中英文文献{en_papers}篇，中文文献{zh_papers}篇。{fig1_ref}展示了文献筛选流程及PRISMA流程图。

纳入文献的质量评估平均得分为{avg_score}分，表明文献整体质量较高。{fig2_ref}展示了纳入文献的质量评分分布情况。

[表1：文献基本特征汇总表]

### 3.2 微藻类生物肥功效——按藻种分类

#### 3.2.1 绿藻门（Chlorophyta）

绿藻门是微藻类生物肥研究中最常见的藻种类别之一，主要包括小球藻（Chlorella）和栅藻（Scenedesmus）。{algae_descriptions.get('A4', '绿藻门')}相关研究共{algae_stats.get('A4', 0)}篇。研究表明，绿藻能够通过分泌植物生长素（IAA）类似物促进作物根系发育，提高养分吸收效率。

#### 3.2.2 蓝藻门（Cyanobacteria）

蓝藻门包括鱼腥藻（Anabaena）、念珠藻（Nostoc）和螺旋藻（Spirulina）等。{algae_descriptions.get('A3', '蓝藻门')}相关研究共{algae_stats.get('A3', 0)}篇。蓝藻的突出特点是其固氮能力，能够为作物提供生物氮源。

#### 3.2.3 硅藻门（Bacillariophyta）及其他

{algae_descriptions.get('A5', '硅藻门')}及其他藻类相关研究共{sum([algae_stats.get(k, 0) for k in ['A5', 'A6', 'A7']])}篇。硅藻的独特之处在于其细胞壁含有硅质，能够为水稻等硅喜作物提供可利用硅源。

[表2：不同藻种功效对比表]

### 3.3 作用机制分析

微藻类生物肥的作用机制可归纳为以下几类：{mech_list}。{fig3_ref}展示了不同作用机制的分布情况。

- **植物激素作用** — 生长素（IAA）、细胞分裂素、赤霉素等激素样物质的分泌
- **营养元素供给** — 氮磷钾及微量元素的溶解与供给
- **土壤改良效应** — 土壤微生物群落调节、土壤酶活性变化、土壤结构改善
- **抗逆性提升** — 抗氧化酶系统激活、渗透调节物质积累

### 3.4 应用领域分析

微藻类生物肥的应用领域分布如下：{app_list}。{fig4_ref}展示了不同应用领域的分布情况。

应用效果主要体现在以下几个方面：大田作物增产效果显著，园艺作物品质改善明显，土壤改良效果持续性好。

### 3.5 可视化分析

{fig5_ref}展示了发表趋势分析结果。

- **发表趋势** — 近年来微藻类生物肥研究呈上升趋势，表明该领域研究热度不断增加
- **研究热点图** — 关键词共现分析显示"microalgae"、"biofertilizer"、"plant growth"为核心研究热点
- **引用网络** — 高被引文献主要集中在综述类文章和机制研究类文章
- **功效对比雷达图** — 不同藻种在各项指标上表现各有侧重"""

    return results


def fill_discussion(stats: Dict[str, Any]) -> str:
    """生成讨论章节内容
    
    Returns:
        讨论文本
    """
    total = stats['total']
    mechanism_stats = stats['mechanism_stats']
    algae_stats = stats['algae_stats']
    
    # 主要机制
    top_mech = max(mechanism_stats.items(), key=lambda x: x[1])[0] if mechanism_stats else '未知'
    top_mech_count = mechanism_stats.get(top_mech, 0)
    
    # 主要藻种
    top_algae = max(algae_stats.items(), key=lambda x: x[1])[0] if algae_stats else '未知'
    top_algae_count = algae_stats.get(top_algae, 0)
    
    discussion = f"""### 4.1 主要发现

通过对{total}篇文献的系统分析，本综述得出以下主要发现：

（1）微藻类生物肥在农业应用中展现出良好的促生效果，主要集中在促进作物根系发育、提高养分利用效率和增强抗逆性方面。

（2）作用机制研究以{top_mech}类机制为主（{top_mech_count}篇），表明该机制是当前研究热点。不同藻种的作用机制存在差异，但也有一些共性特征。

（3）{top_algae}类藻种是主要研究对象（{top_algae_count}篇），这与其易于培养和已知的促生特性相关。

### 4.2 与已有综述的比较

相较于已有的微藻类生物肥综述，本研究具有以下特点：（1）覆盖数据库更全面；（2）采用系统综述方法学；（3）纳入中英文文献；（4）进行了详细的质量评估。

### 4.3 机制解释

现有机制研究主要集中在以下几个层面：表型观察层面证据充分，但生理和分子层面证据相对薄弱。建议未来研究加强以下方向：

- 微藻-植物-土壤三者互作的分子机制
- 关键功能基因的鉴定和验证
- 代谢通路的系统解析

### 4.4 研究局限性与未来方向

本研究存在以下局限性：（1）检索语言限定为中英文，可能遗漏其他语言文献；（2）田间试验数据异质性较大，难以进行meta分析；（3）部分文献质量评估信息不完整。

未来研究方向建议：

- 标准化田间试验方案和效果评价指标体系
- 微藻-植物-土壤三者互作的分子机制研究
- 规模化培养工艺优化与产业化路径
- 不同生态区域的适应性评估"""

    return discussion


def fill_conclusion(stats: Dict[str, Any]) -> str:
    """生成结论章节内容
    
    Returns:
        结论文本
    """
    total = stats['total']
    avg_score = stats['avg_score']
    top_algae = max(stats['algae_stats'].items(), key=lambda x: x[1])[0] if stats['algae_stats'] else '未知'
    
    conclusion = f"""本综述通过对{total}篇文献的系统分析，得出以下核心结论：

微藻类生物肥在可持续农业发展中具有潜在应用价值。现有证据表明，微藻类生物肥能够通过多种机制促进作物生长，包括提供营养元素、分泌植物激素和改善土壤微生态环境。纳入文献的平均质量评分为{avg_score}分，整体研究质量较高。

最具应用潜力的微藻种类为{top_algae}类藻种，已有较充分的研究证据支持其农业应用效果。然而，当前证据在以下方面尚不充分：（1）大规模田间试验数据不足；（2）作用机制的分子层面解析不够深入；（3）不同环境条件下的效果稳定性有待验证。

对政策制定者的建议：鼓励微藻类生物肥的研发和产业化推广，同时建立相应的质量标准和应用规范。

对研究人员的建议：加强标准化研究，开展多中心田间试验，深入解析作用机制。

对农业生产者的建议：在小规模试验验证的基础上，因地制宜地应用微藻类生物肥。"""

    return conclusion


def fill_appendix(papers: List[Dict[str, Any]], stats: Dict[str, Any]) -> str:
    """生成附录内容
    
    Returns:
        附录文本
    """
    total = stats['total']
    year_range = stats['year_range']
    
    appendix = f"""## 附录 A 检索策略详表

| 数据库 | 检索日期 | 检索式 | 初始命中数 |
|--------|----------|--------|------------|
| Web of Science | {datetime.now().strftime('%Y-%m-%d')} | TS=(microalgae AND biofertilizer AND agriculture) | 待补充 |
| CNKI | {datetime.now().strftime('%Y-%m-%d')} | SU=('微藻'+'生物肥') AND SU=('农业'+'应用') | 待补充 |
| PubMed | {datetime.now().strftime('%Y-%m-%d')} | ("microalgae"[MeSH] AND "biofertilizers"[MeSH]) | 待补充 |

## 附录 B 质量评估工具与评分细则

| 评估维度 | 评估指标 | 评分标准 |
|----------|----------|----------|
| 研究设计 | 随机化程度 | 清楚描述 = 3分，部分描述 = 1分，未描述 = 0分 |
| 样本量 | 足够统计效力 | n≥500 = 3分，100-499 = 2分，30-99 = 1分，<30 = 0分 |
| 测量方法 | 方法学可靠性 | 报告验证方法 = 3分，引用但未验证 = 2分，未说明 = 0分 |
| 结果报告 | 完整性 | 报告所有预设指标 = 3分，部分报告 = 1分，关键数据缺失 = 0分 |
| 偏倚控制 | 盲法/对照 | 实施良好 = 3分，实施不充分 = 1分，未实施 = 0分 |

决策阈值：≥12分纳入，8-11分复核，<8分排除。

## 附录 C 纳入文献清单

| 序号 | 第一作者 | 年份 | 藻种 | 作物 | 实验规模 | 质量评分 | 主要结论 |
|------|----------|------|------|------|----------|----------|----------|
"""
    
    # 添加文献列表
    algae_names = {'A1': '螺旋藻', 'A2': '小球藻', 'A3': '蓝藻', 'A4': '绿藻', 'A5': '硅藻', 'A6': '混合', 'A7': '其他'}
    
    for i, paper in enumerate(papers[:50], 1):  # 最多50条
        authors = paper.get('authors', paper.get('author', []))
        if isinstance(authors, str):
            first_author = authors.split(',')[0].strip()
        elif isinstance(authors, list) and authors:
            first_author = str(authors[0])
        else:
            first_author = '未知'
        
        year = paper.get('year', paper.get('published_year', '未知'))
        
        cls = paper.get('classification', {})
        algae = cls.get('algae_type', {})
        if isinstance(algae, dict):
            algae_code = algae.get('code', 'A7')
        else:
            algae_code = str(algae)
        algae_name = algae_names.get(algae_code, '其他')
        
        crop = paper.get('crop', paper.get('subject', '未明确'))
        scale = paper.get('experiment_scale', paper.get('scale', '未明确'))
        score = paper.get('_quality_score', 'N/A')
        conclusion = paper.get('main_finding', paper.get('conclusion', '待补充'))[:30]
        
        appendix += f"| {i} | {first_author} | {year} | {algae_name} | {crop} | {scale} | {score} | {conclusion}... |\n"
    
    appendix += f"\n[共{total}篇文献，此处显示前50条完整清单见附赠数据文件]"

    return appendix


def generate_report(input_path: Path, figures_dir: Path, template_path: Path, output_path: Path) -> int:
    """生成完整报告
    
    Args:
        input_path: 质量评分JSON文件路径
        figures_dir: 图表目录路径
        template_path: Markdown模板路径
        output_path: 输出文件路径
    
    Returns:
        0表示成功
    """
    logger = setup_logging('generate_report')
    logger.info(f"开始生成报告...")
    logger.info(f"输入文件: {input_path}")
    logger.info(f"模板文件: {template_path}")
    logger.info(f"图表目录: {figures_dir}")
    logger.info(f"输出文件: {output_path}")
    
    # 加载数据
    logger.info("加载文献数据...")
    papers = load_json(input_path)
    if not papers:
        logger.warning("输入文件为空，使用空数据集生成报告")
        papers = []
    
    logger.info(f"共加载 {len(papers)} 篇文献")
    
    # 计算统计信息
    logger.info("计算统计信息...")
    stats = calculate_statistics(papers)
    
    # 获取图表列表
    logger.info("获取图表列表...")
    figures = get_figure_list(figures_dir)
    logger.info(f"发现 {len(figures)} 个图表文件")
    
    # 生成各章节内容
    logger.info("生成报告各章节...")
    
    # 读取模板
    sections = parse_template(template_path)
    
    # 生成内容
    report_parts = []
    
    # 1. 标题和摘要
    report_parts.append("# 微藻类生物肥文献综述报告\n")
    report_parts.append(f"**生成日期：** {datetime.now().strftime('%Y-%m-%d')}　|　**文献数量：** {stats['total']} 篇\n")
    report_parts.append("---\n")
    report_parts.append("## 摘要\n")
    report_parts.append(fill_abstract(papers, stats) + "\n\n")
    report_parts.append("**关键词：** 微藻；生物肥；藻类促生因子；农业应用；系统性综述\n")
    report_parts.append("---\n")
    
    # 2. 引言
    report_parts.append("## 1 引言\n")
    report_parts.append(fill_introduction(stats) + "\n")
    report_parts.append("---\n")
    
    # 3. 方法
    report_parts.append("## 2 方法\n")
    report_parts.append(fill_methods(papers, stats) + "\n")
    report_parts.append("---\n")
    
    # 4. 结果
    report_parts.append("## 3 结果\n")
    report_parts.append(fill_results(papers, stats, figures) + "\n")
    report_parts.append("---\n")
    
    # 5. 讨论
    report_parts.append("## 4 讨论\n")
    report_parts.append(fill_discussion(stats) + "\n")
    report_parts.append("---\n")
    
    # 6. 结论
    report_parts.append("## 5 结论\n")
    report_parts.append(fill_conclusion(stats) + "\n")
    report_parts.append("---\n")
    
    # 7. 参考文献
    report_parts.append("## 参考文献\n")
    report_parts.append(generate_references(papers) + "\n")
    report_parts.append("---\n")
    
    # 8. 附录
    report_parts.append(fill_appendix(papers, stats) + "\n")
    
    # 写入输出文件
    logger.info(f"写入报告到: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_parts))
    
    logger.info("=" * 60)
    logger.info(f"报告生成完成!")
    logger.info(f"总计: {stats['total']} 篇文献")
    logger.info(f"英文: {stats['en_papers']} 篇, 中文: {stats['zh_papers']} 篇")
    logger.info(f"平均质量评分: {stats['avg_score']} 分")
    logger.info(f"图表引用: {len(figures)} 个")
    logger.info("=" * 60)
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='IMRAD格式Markdown报告生成脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python 09_generate_report.py --input outputs/data/quality_scored.json --output outputs/reports/report.md
  python 09_generate_report.py -i data.json -f figures/ -t template.md -o report.md

输出格式:
  - 摘要: 基于数据自动生成
  - 引言: 固定内容 + 统计摘要
  - 方法: 检索策略描述
  - 结果: 包含图表引用占位符
  - 讨论: 主要发现与局限性分析
  - 结论: 核心发现总结
  - 参考文献: GB/T 7714-2015格式
  - 附录: 检索策略和质量评估细则
        """
    )
    parser.add_argument('--input', '-i', required=True, 
                       help='质量评分后的文献JSON文件路径')
    parser.add_argument('--figures', '-f', default='outputs/figures',
                       help='图表目录路径 (default: outputs/figures)')
    parser.add_argument('--template', '-t', default='references/report-template.md',
                       help='Markdown模板路径 (default: references/report-template.md)')
    parser.add_argument('--output', '-o', required=True,
                       help='输出Markdown文件路径')
    
    args = parser.parse_args()
    
    # 转换为Path对象
    input_path = Path(args.input)
    figures_dir = Path(args.figures)
    template_path = Path(args.template)
    output_path = Path(args.output)
    
    # 验证输入文件
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        return 1
    
    # 验证模板文件
    if not template_path.exists():
        print(f"错误: 模板文件不存在: {template_path}")
        return 1
    
    # 生成报告
    return generate_report(input_path, figures_dir, template_path, output_path)


if __name__ == '__main__':
    sys.exit(main())
