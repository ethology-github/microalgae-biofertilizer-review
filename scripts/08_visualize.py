# -*- encoding: utf-8 -*-
"""
文献可视化脚本

生成5类可视化图表:
1. publication_trend.png - 年度发表趋势折线图（2015-2026）
2. journal_distribution.png - 期刊分布饼图（前10大期刊）
3. keyword_network.png - 关键词共现网络图（networkx）
4. classification_sankey.html - 分类Sankey图（机制→藻种→应用，plotly）
5. mechanism_by_year.png - 各机制年度堆叠柱状图
"""

import argparse
import sys
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Any

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
import plotly.graph_objects as go

# 添加scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent))


def setup_logging(name: str):
    """简单日志设置"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(name)


def load_json(path: str) -> Any:
    """加载JSON文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, path: str):
    """保存JSON文件"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_year(paper: Dict) -> int:
    """提取文献年份"""
    # 尝试多个字段
    for field in ['year', 'pub_year', 'publication_year', 'date', 'published']:
        year = paper.get(field)
        if year:
            try:
                y = int(str(year)[:4])
                if 2000 <= y <= 2030:
                    return y
            except (ValueError, TypeError):
                pass
    return 2025  # 默认


def extract_journal(paper: Dict) -> str:
    """提取期刊名"""
    for field in ['journal', 'venue', 'source', 'publication']:
        journal = paper.get(field)
        if journal:
            return str(journal).strip()
    return 'Unknown'


def extract_keywords(paper: Dict) -> List[str]:
    """提取关键词"""
    keywords = []
    for field in ['keywords', 'keyword', 'tags', 'index_terms']:
        kws = paper.get(field)
        if kws:
            if isinstance(kws, list):
                keywords.extend([str(k).lower().strip() for k in kws if k])
            elif isinstance(kws, str):
                keywords.extend([k.strip().lower() for k in kws.split(';') if k.strip()])
    return keywords


def get_classification(paper: Dict, dim: str) -> str:
    """获取文献分类"""
    classification = paper.get('classification', {})
    if isinstance(classification, dict):
        result = classification.get(dim, {})
        if isinstance(result, dict):
            return result.get('code', 'Unknown')
        return str(result) if result else 'Unknown'
    return 'Unknown'


def generate_publication_trend(papers: List[Dict], output_dir: Path, formats: List[str]):
    """生成年度发表趋势折线图"""
    # 统计每年文献数
    year_counts = Counter()
    for paper in papers:
        year = extract_year(paper)
        year_counts[year] += 1

    # 填充2015-2026年数据
    years = list(range(2015, 2027))
    counts = [year_counts.get(y, 0) for y in years]

    # 绘图
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(years, counts, 'b-o', linewidth=2, markersize=8, label='Publications')
    ax.fill_between(years, counts, alpha=0.3)

    # 添加数据标签
    for x, y in zip(years, counts):
        if y > 0:
            ax.annotate(str(y), (x, y), textcoords="offset points",
                       xytext=(0, 10), ha='center', fontsize=9)

    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('Number of Publications', fontsize=12)
    ax.set_title('Publication Trend (2015-2026)', fontsize=14, fontweight='bold')
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(2014.5, 2026.5)

    plt.tight_layout()

    for fmt in formats:
        fig.savefig(output_dir / f'publication_trend.{fmt}', dpi=150, bbox_inches='tight')
    plt.close()


def generate_journal_distribution(papers: List[Dict], output_dir: Path, formats: List[str]):
    """生成期刊分布饼图（前10大期刊）"""
    # 统计期刊
    journal_counts = Counter()
    for paper in papers:
        journal = extract_journal(paper)
        if journal and journal != 'Unknown':
            journal_counts[journal] += 1

    # 取前10
    top_journals = journal_counts.most_common(10)
    if not top_journals:
        return

    labels = [j[0][:40] + '...' if len(j[0]) > 40 else j[0] for j in top_journals]
    sizes = [j[1] for j in top_journals]
    total = sum(sizes)
    percentages = [s / total * 100 for s in sizes]

    # 颜色
    colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))

    fig, ax = plt.subplots(figsize=(12, 10))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,
        autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
        colors=colors,
        startangle=90,
        pctdistance=0.75
    )

    # 图例
    legend_labels = [f'{l} ({s}, {p:.1f}%)' for l, s, p in zip(labels, sizes, percentages)]
    ax.legend(wedges, legend_labels, title="Journals", loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9)

    ax.set_title('Journal Distribution (Top 10)', fontsize=14, fontweight='bold')
    plt.tight_layout()

    for fmt in formats:
        fig.savefig(output_dir / f'journal_distribution.{fmt}', dpi=150, bbox_inches='tight')
    plt.close()


def generate_keyword_network(papers: List[Dict], output_dir: Path, formats: List[str]):
    """生成关键词共现网络图"""
    # 收集所有关键词
    keyword_counter = Counter()
    cooccurrence = defaultdict(Counter)

    for paper in papers:
        keywords = extract_keywords(paper)
        # 过滤短词
        keywords = [k for k in keywords if len(k) > 2]
        for kw in keywords:
            keyword_counter[kw] += 1

        # 共现统计（同文献内关键词两两组合）
        unique_kws = set(keywords)
        for i, kw1 in enumerate(unique_kws):
            for kw2 in list(unique_kws)[i+1:]:
                if kw1 != kw2:
                    cooccurrence[kw1][kw2] += 1
                    cooccurrence[kw2][kw1] += 1

    # 取前30个高频词
    top_keywords = [kw for kw, _ in keyword_counter.most_common(30)]

    # 构建网络
    G = nx.Graph()
    for kw in top_keywords:
        G.add_node(kw, size=keyword_counter[kw])

    # 添加边（只保留共现>=2的）
    for kw1 in top_keywords:
        for kw2, count in cooccurrence[kw1].items():
            if kw2 in top_keywords and kw1 < kw2 and count >= 2:
                G.add_edge(kw1, kw2, weight=count)

    # 绘图
    fig, ax = plt.subplots(figsize=(14, 12))

    # 节点大小
    node_sizes = [G.nodes[n].get('size', 1) * 20 for n in G.nodes()]

    # 边宽度
    edge_weights = [G[u][v].get('weight', 1) for u, v in G.edges()]
    max_weight = max(edge_weights) if edge_weights else 1
    edge_widths = [w / max_weight * 3 + 0.5 for w in edge_weights]

    # 布局
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    # 绘制
    nx.draw_networkx_edges(G, pos, alpha=0.3, width=edge_widths, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='lightblue',
                           alpha=0.8, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=7, ax=ax)

    ax.set_title('Keyword Co-occurrence Network (Top 30)', fontsize=14, fontweight='bold')
    ax.axis('off')
    plt.tight_layout()

    for fmt in formats:
        fig.savefig(output_dir / f'keyword_network.{fmt}', dpi=150, bbox_inches='tight')
    plt.close()


def generate_classification_sankey(papers: List[Dict], output_dir: Path):
    """生成分类Sankey图（机制→藻种→应用）"""
    # 统计分类组合
    mechanism_algae = Counter()
    algae_application = Counter()

    for paper in papers:
        mechanism = get_classification(paper, 'mechanism')
        algae_type = get_classification(paper, 'algae_type')
        application = get_classification(paper, 'application')

        if mechanism != 'Unknown' and algae_type != 'Unknown':
            mechanism_algae[(mechanism, algae_type)] += 1
        if algae_type != 'Unknown' and application != 'Unknown':
            algae_application[(algae_type, application)] += 1

    # 构建节点和边
    all_nodes = []
    node_map = {}

    # 添加机制节点
    mechanisms = sorted(set(k[0] for k in mechanism_algae.keys()))
    mechanism_labels = {
        'M1': 'M1: Nitrogen Fixation',
        'M2': 'M2: Phosphorus Solubilization',
        'M3': 'M3: Phytohormone',
        'M4': 'M4: Biostimulant',
        'M5': 'M5: Soil Improvement',
        'M6': 'M6: Unknown'
    }

    algae_labels = {
        'A1': 'A1: Spirulina',
        'A2': 'A2: Chlorella',
        'A3': 'A3: Cyanobacteria',
        'A4': 'A4: Green Algae',
        'A5': 'A5: Diatom',
        'A6': 'A6: Mixed',
        'A7': 'A7: Other'
    }

    application_labels = {
        'C1': 'C1: Field Crops',
        'C2': 'C2: Horticulture',
        'C3': 'C3: Aquaculture',
        'C4': 'C4: Soil Remediation',
        'C5': 'C5: Multiple',
        'C6': 'C6: Unclear'
    }

    # 节点顺序: mechanisms -> algae_types -> applications
    node_idx = 0

    # 添加机制节点
    for m in mechanisms:
        node_map[('mechanism', m)] = node_idx
        all_nodes.append(mechanism_labels.get(m, m))
        node_idx += 1

    # 添加藻种节点
    algae_types = sorted(set(k[1] for k in mechanism_algae.keys()))
    for a in algae_types:
        node_map[('algae', a)] = node_idx
        all_nodes.append(algae_labels.get(a, a))
        node_idx += 1

    # 添加应用节点
    applications = sorted(set(k[1] for k in algae_application.keys()))
    for c in applications:
        node_map[('application', c)] = node_idx
        all_nodes.append(application_labels.get(c, c))
        node_idx += 1

    # 构建边
    sources, targets, values, labels = [], [], [], []

    # mechanism -> algae
    for (m, a), count in mechanism_algae.items():
        if m in node_map and ('algae', a) in node_map:
            sources.append(node_map[('mechanism', m)])
            targets.append(node_map[('algae', a)])
            values.append(count)
            labels.append(f'{m} → {a}: {count}')

    # algae -> application
    for (a, c), count in algae_application.items():
        if ('algae', a) in node_map and ('application', c) in node_map:
            sources.append(node_map[('algae', a)])
            targets.append(node_map[('application', c)])
            values.append(count)

    # 颜色
    node_colors = ['#e74c3c'] * len(mechanisms) + \
                  ['#3498db'] * len(algae_types) + \
                  ['#2ecc71'] * len(applications)

    link_colors = ['rgba(231,76,60,0.4)'] * len([k for k in mechanism_algae.keys() if k[0] in node_map]) + \
                  ['rgba(52,152,219,0.4)'] * len([k for k in algae_application.keys() if k[0] in node_map])

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes,
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors
        )
    )])

    fig.update_layout(
        title_text="Classification Flow: Mechanism → Algae Type → Application",
        font_size=10,
        height=600
    )

    fig.write_html(output_dir / 'classification_sankey.html')


def generate_mechanism_by_year(papers: List[Dict], output_dir: Path, formats: List[str]):
    """生成各机制年度堆叠柱状图"""
    # 统计每年各机制文献数
    years = list(range(2015, 2027))
    mechanisms = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6']
    mechanism_names = {
        'M1': 'Nitrogen Fixation',
        'M2': 'Phosphorus Solubilization',
        'M3': 'Phytohormone',
        'M4': 'Biostimulant',
        'M5': 'Soil Improvement',
        'M6': 'Unknown'
    }

    data = {m: [0] * len(years) for m in mechanisms}

    for paper in papers:
        year = extract_year(paper)
        mechanism = get_classification(paper, 'mechanism')
        if year in years:
            idx = years.index(year)
            if mechanism in data:
                data[mechanism][idx] += 1

    # 绘图
    fig, ax = plt.subplots(figsize=(14, 8))

    bottom = np.zeros(len(years))
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#95a5a6']

    for i, m in enumerate(mechanisms):
        ax.bar(years, data[m], bottom=bottom, label=mechanism_names[m],
               color=colors[i], alpha=0.85)
        bottom += np.array(data[m])

    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('Number of Publications', fontsize=12)
    ax.set_title('Mechanism Distribution by Year (Stacked)', fontsize=14, fontweight='bold')
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45)
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    for fmt in formats:
        fig.savefig(output_dir / f'mechanism_by_year.{fmt}', dpi=150, bbox_inches='tight')
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description='文献可视化脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
生成5类可视化图表:
  1. publication_trend.png   - 年度发表趋势折线图
  2. journal_distribution.png - 期刊分布饼图
  3. keyword_network.png     - 关键词共现网络图
  4. classification_sankey.html - 分类Sankey图
  5. mechanism_by_year.png   - 各机制年度堆叠柱状图
        """
    )
    parser.add_argument('--input', '-i', required=True,
                       help='输入质量评分JSON文件路径')
    parser.add_argument('--output', '-o', required=True,
                       help='输出目录路径')
    parser.add_argument('--formats', '-f', default='png',
                       help='图片格式，逗号分隔 (default: png)')

    args = parser.parse_args()

    logger = setup_logging('visualize')
    logger.info("开始生成可视化图表")

    # 解析格式
    formats = [fmt.strip().lower() for fmt in args.formats.split(',')]
    formats = [f if f != 'jpg' else 'jpeg' for f in formats]

    # 确保格式有效
    valid_formats = ['png', 'jpeg', 'svg', 'pdf']
    for fmt in formats:
        if fmt not in valid_formats:
            logger.warning(f"不支持的格式: {fmt}，跳过")

    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载数据
    logger.info(f"加载数据: {args.input}")
    papers = load_json(args.input)

    if not isinstance(papers, list):
        papers = [papers]

    logger.info(f"共加载 {len(papers)} 篇文献")

    # 生成图表
    logger.info("生成 publication_trend.png...")
    try:
        generate_publication_trend(papers, output_dir, formats)
        logger.info("  完成")
    except Exception as e:
        logger.error(f"  失败: {e}")

    logger.info("生成 journal_distribution.png...")
    try:
        generate_journal_distribution(papers, output_dir, formats)
        logger.info("  完成")
    except Exception as e:
        logger.error(f"  失败: {e}")

    logger.info("生成 keyword_network.png...")
    try:
        generate_keyword_network(papers, output_dir, formats)
        logger.info("  完成")
    except Exception as e:
        logger.error(f"  失败: {e}")

    logger.info("生成 classification_sankey.html...")
    try:
        generate_classification_sankey(papers, output_dir)
        logger.info("  完成")
    except Exception as e:
        logger.error(f"  失败: {e}")

    logger.info("生成 mechanism_by_year.png...")
    try:
        generate_mechanism_by_year(papers, output_dir, formats)
        logger.info("  完成")
    except Exception as e:
        logger.error(f"  失败: {e}")

    logger.info(f"所有可视化图表已保存到: {output_dir}")
    logger.info("完成!")

    return 0


if __name__ == '__main__':
    sys.exit(main())
