---
name: microalgae-biofertilizer-review
description: Conduct systematic literature reviews on microalgae-based biofertilizers
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
license: MIT
metadata:
  skill-author: Gao
  version: "1.0"
  topic: microalgae biofertilizer systematic review
  language: zh-CN
---

# 微藻类生物肥文献综述技能 (Microalgae Biofertilizer Review)

## 1. Overview - 技能目标

本技能用于系统性文献综述（Systematic Literature Review），聚焦微藻类生物肥料（Microalgae Biofertilizer）研究领域，实现以下目标：

- **检索全面性**: 覆盖 AMiner、PubMed、sciai-engine 三大数据库
- **筛选规范性**: 遵循 PRISMA 原则的两阶段筛选流程
- **评估标准化**: 0-20分质量评分体系（方法学+期刊+相关性）
- **分类体系化**: 按机制(M)、藻种(A)、应用(C)、研究类型(R)四维度分类
- **报告结构化**: IMRAD 格式输出，支持 PDF 导出

---

## 2. When to Use This Skill - 触发条件

在以下4种场景中应调用本技能：

| # | 触发条件 | 任务描述 |
|---|----------|----------|
| 1 | **新建综述项目** | 启动微藻生物肥领域系统性文献综述 |
| 2 | **更新现有综述** | 定期（如每3个月）更新已发表综述的检索结果 |
| 3 | **专题补充检索** | 针对特定机制（如固氮、解磷）或特定藻种（如Chlorella、Spirulina）进行深度检索 |
| 4 | **质量评估审计** | 对已纳入文献进行二次质量评估或分类复核 |

---

## 3. Workflow Overview - 流程图（Phase 1-6）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           微藻生物肥文献综述工作流                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: 多数据库检索                                                       │
│  ┌───────────┐   ┌───────────┐   ┌───────────────┐                         │
│  │ AMiner    │   │ PubMed    │   │ sciai-engine  │                         │
│  │ (5检索式) │   │ (5检索式) │   │ (语义搜索)     │                         │
│  └─────┬─────┘   └─────┬─────┘   └──────┬───────┘                         │
│        └───────────┬───┴───────────┬─────┘                                 │
│                    ▼               ▼                                       │
│            合并 raw_papers.json (初始文献池 ~1000-2000篇)                    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 2: 去重与合并                                                        │
│  ┌─────────────────────────────────────────┐                               │
│  │ DOI精确匹配 → 标题相似度(Levenshtein≥0.85) → 作者+年份+关键词            │ │
│  └──────────────────┬──────────────────────┘                               │
│                     ▼                                                      │
│            deduplicated_papers.json (~800-1500篇)                           │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 3: 初筛与分类                                                        │
│  ┌──────────────────┐   ┌──────────────────┐                                │
│  │ 阶段一: 标题摘要  │ → │ 阶段二: 全文评估  │                                │
│  │ 快速判断相关性    │   │ 逐项核对标准      │                                │
│  └────────┬─────────┘   └────────┬─────────┘                                │
│           ▼                       ▼                                         │
│  screened_papers.json + classification_labels.json                          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 4: 质量评估 (0-20分)                                                 │
│  ┌───────────────┬───────────────┬───────────────┐                         │
│  │ 方法学质量    │ 期刊质量      │ 主题相关性    │                         │
│  │ (0-10分)      │ (0-6分)       │ (0-4分)       │                         │
│  └───────────────┴───────────────┴───────────────┘                         │
│           │                                               │                 │
│           └───────────────┬───────────────────────────────┘                 │
│                           ▼                                                │
│              ┌────────────┴────────────┐                                   │
│              │ ≥12分: 优先纳入           │                                   │
│              │ 8-11分: 双人复核          │                                   │
│              │ <8分: 排除                │                                   │
│              └────────────┬─────────────┘                                   │
│                           ▼                                                  │
│                  quality_assessed_papers.json                               │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 5: 可视化                                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐             │
│  │ 年度发文 │ │ 期刊分布 │ │ 藻种词云 │ │ 机制分类 │ │ 作物应用 │             │
│  │ 趋势图   │ │ 饼图     │ │ (中文)   │ │ 柱状图   │ │ 桑基图   │             │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘                 │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 6: 报告生成                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │ IMRAD结构: Introduction → Methods → Results → Discussion → Conclusion │
│  └────────────────────────────────┬────────────────────────────────┘        │
│                                   ▼                                         │
│                          outputs/report.md                                  │
│                                   ▼                                         │
│                          outputs/report.pdf                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Phase 1: Multi-Database Search - 多数据库检索

### 4.1 脚本概览

| 脚本 | 数据库 | 检索式数 | API费用 |
|------|--------|----------|---------|
| `01-search-aminer.py` | AMiner | 5个 | 免费+付费(语义) Token认证 |
| `02-search-pubmed.py` | PubMed | 5个 | 免费 |
| `03-search-sciai.py` | sciai-engine | 按需 | ¥0.05/次(语义) |

### 4.2 AMiner 检索

**Token 配置**: 环境变量 `AMINER_TOKEN` (JWT token)

**免费接口检索**:
```bash
cd /Users/gao/microalgae-biofertilizer-review
python scripts/01-search-aminer.py --token "${AMINER_TOKEN}"
```

**输出**: `data/raw/aminer_papers.json`

**5个检索式**:
1. `微藻 生物肥` (中文基础)
2. `(Chlorella OR Spirulina) biofertilizer` (英文核心)
3. `microalgae nitrogen fixation plant growth promotion` (英文扩展)
4. `藻类有机肥 植物促生` (中文扩展)
5. `(Anabaena OR Nostoc) cyanobacteria biofertilizer` (蓝藻固氮)

**付费语义搜索** (按需):
```bash
# 仅在免费检索结果不足时使用
python scripts/01-search-aminer.py --token "${AMINER_TOKEN}" --semantic
```

### 4.3 PubMed 检索

**无需 API Key**，直接调用 E-utilities

**检索命令**:
```bash
cd /Users/gao/microalgae-biofertilizer-review
python scripts/02-search-pubmed.py
```

**输出**: `data/raw/pubmed_papers.json`

**5个检索式**:
1. `((microalgae[Title/Abstract]) AND (biofertilizer[Title/Abstract]))`
2. `(chlorella[MeSH Terms]) AND (biofertilizer[MeSH Terms])`
3. `((microalgae[Title/Abstract]) AND (nitrogen fixation[Title/Abstract]) AND (plant[Title/Abstract]))`
4. `((algal extract[Title/Abstract]) AND (plant growth promotion[Title/Abstract]))`
5. `(cyanobacteria[Title/Abstract]) AND (biofertilizer[Title/Abstract])`

**限速**: 每次请求间隔≥0.33秒

### 4.4 sciai-engine 深度分析 (Phase 3-4)

**Token**: `8HSXyLFdbCZf`（已嵌入脚本，无需环境变量）

**认证方式**: form-data，文本需 base64 编码（SDK自动处理）

**已验证可用的API**:
- `api_ner_sci_en_v2` — 英文科研实体识别（研究问题/方法/度量指标/设备/软件）
- `paper_classification_cn` — 中文科技文献学科分类

**不可用API**:
- `keywords_extraction_en` — Server not available（英文关键词提取）

**使用方式**（读取 Phase 3 筛选结果，进行深度分析）:
```bash
cd /Users/gao/microalgae-biofertilizer-review
python scripts/03-search-sciai.py \
  --input data/interim/screened_papers.json \
  --output data/interim/sciai_analyzed_papers.json
```

**输出**: `data/interim/sciai_analyzed_papers.json`（含NER实体+分类结果）

**配额消耗**（106篇示例）:
| 阶段 | API调用次数 |
|------|-----------|
| Batch 1 (篇1-50, NER) | 1 |
| Batch 1 (篇1-50, 分类) | 1 |
| Batch 2 (篇51-100, NER) | 1 |
| Batch 2 (篇51-100, 分类) | 1 |
| Batch 3 (篇101-106, NER) | 1 |
| Batch 3 (篇101-106, 分类) | 1 |
| **合计** | **6次**（剩余494次） |

---

## 5. Phase 2: Deduplication and Merging - 去重与合并

### 5.1 去重规则

| 优先级 | 匹配依据 | 阈值 |
|--------|----------|------|
| P1 | DOI 精确匹配 | 100%相同 |
| P2 | 英文标题相似度 | Levenshtein ≥ 0.85 或 token 重叠率 ≥ 90% |
| P3 | 作者 + 年份 + 标题关键词 | 三者中有两者高度相似 |

### 5.2 重复处理原则

- **同一研究多篇发表**: 保留最新、最完整版本
- **中英文同一研究**: 优先保留英文版本
- **会议摘要扩展为论文**: 保留期刊论文
- **合并策略**: 以 DOI 为主键，标题相似度辅助判断

### 5.3 执行命令

```bash
cd /Users/gao/microalgae-biofertilizer-review
python scripts/04-deduplicate-merge.py
```

**输入**: 
- `data/raw/aminer_papers.json`
- `data/raw/pubmed_papers.json`
- `data/raw/sciai_papers.json` (可选)

**输出**: `data/interim/deduplicated_papers.json`

---

## 6. Phase 3: Screening and Classification - 筛选与分类

### 6.1 两阶段筛选流程

**阶段一: 标题+摘要筛选 (快速判断)**
- 是否涉及微藻（Chlorella, Spirulina, Scenedesmus, Nannochloropsis等）
- 是否与植物生长/土壤/生物肥相关
- 是否为同行评审期刊/综述
- 时间范围: 2015年至今

**阶段二: 全文复核**
- 逐项核对纳入/排除标准
- 质量评分（见Phase 4）
- 提取关键信息

### 6.2 分类维度框架

**按机制分类 (M)**:
| 类别 | 说明 |
|------|------|
| M1 | 固氮/解磷/解钾机制研究 |
| M2 | 植物激素（auxin, cytokinin, GA等）分泌研究 |
| M3 | 土壤微生物群落调控机制 |
| M4 | 抗氧化/抗逆性诱导机制 |
| M5 | 营养成分直接供给机制 |

**按藻种分类 (A)**:
| 类别 | 代表藻种 |
|------|----------|
| A1 | 绿藻门: Chlorella, Scenedesmus, Chlamydomonas |
| A2 | 蓝藻门: Spirulina (Arthrospira), Nostoc, Anabaena |
| A3 | 硅藻门: Nannochloropsis, Phaeodactylum |
| A4 | 混合藻类/商品制剂 |
| A5 | 其他微藻 |

**按应用场景分类 (C)**:
| 类别 | 说明 |
|------|------|
| C1 | 大田作物（水稻、小麦、玉米） |
| C2 | 园艺作物（蔬菜、水果、花卉） |
| C3 | 土壤改良（退化土壤、盐碱地、重金属） |
| C4 | 设施农业/有机农业 |
| C5 | 种子处理/育苗 |

**按研究类型分类 (R)**:
| 类别 | 说明 |
|------|------|
| R1 | 田间试验 (Field trial) |
| R2 | 盆栽/温室实验 (Pot/Greenhouse) |
| R3 | 实验室组培/水培实验 (Lab/Hydroponic) |
| R4 | 综述/Meta分析 |
| R5 | 机制研究（无直接应用数据） |

### 6.3 执行命令

```bash
cd /Users/gao/microalgae-biofertilizer-review
python scripts/05-screen-filter.py
python scripts/06-classify.py
```

**输出**: 
- `data/interim/screened_papers.json`
- `data/interim/classification_labels.json`

---

## 7. Phase 4: Quality Assessment - 质量评估 (0-20分)

### 7.1 评分体系

**方法学质量 (0-10分)**:

| 子项 | 分值 | 评分标准 |
|------|------|----------|
| 对照组设计 | 0-3分 | 0:无对照; 1:对照不严格; 2:有合理对照; 3:随机对照(RCB) |
| 样本量与重复 | 0-3分 | 0:n<3; 1:n=3-5; 2:n=6-10有生物学重复; 3:n>10功效有讨论 |
| 统计分析 | 0-4分 | 0:无统计; 1:方法不明确; 2:t检验/ANOVA且P明确; 3:多重比较校正; 4:完备统计(效应量+CI) |

**期刊质量 (0-6分)**:

| 分值 | 期刊级别 |
|------|----------|
| 6分 | SCI Q1 |
| 5分 | SCI Q2 |
| 4分 | SCI Q3 |
| 3分 | SCI Q4 |
| 2分 | 中文核心期刊/EI |
| 1分 | 其他同行评审期刊 |

**主题相关性 (0-4分)**:

| 分值 | 描述 |
|------|------|
| 4分 | 完全匹配: 专门研究微藻生物肥在农业中的应用 |
| 3分 | 高度相关: 微藻与生物刺激素联合研究 |
| 2分 | 中度相关: 微藻基础研究，关联农业但数据有限 |
| 1分 | 弱相关: 提及微藻可能用于肥料，无直接实验数据 |

### 7.2 评分决策

| 分值范围 | 决策 |
|----------|------|
| **≥12分** | 优先纳入 |
| **8-11分** | 需双人复核 |
| **<8分** | 排除 |

> 复核分数差异≥3分时，由第三人（团队负责人）裁定

### 7.3 执行命令

```bash
cd /Users/gao/microalgae-biofertilizer-review
python scripts/07-quality-score.py
```

**输出**: `data/interim/quality_assessed_papers.json`

---

## 8. Phase 5: Visualization - 可视化

### 8.1 五类图表

| # | 图表类型 | 说明 | 输出文件 |
|---|----------|------|----------|
| 1 | 年度发文趋势图 | 2015-2026年发文量折线图 | `figures/annual_trend.png` |
| 2 | 期刊分布饼图 | Q1-Q4期刊占比分布 | `figures/journal_distribution.png` |
| 3 | 藻种词云图 | 高频藻种类别中文词云 | `figures/algae_wordcloud.png` |
| 4 | 机制分类柱状图 | M1-M5各类别文献数量 | `figures/mechanism_bar.png` |
| 5 | 作物应用桑基图 | 藻种→机制→作物流向 | `figures/crop_sankey.png` |

### 8.2 执行命令

```bash
cd /Users/gao/microalgae-biofertilizer-review
python scripts/08-visualize.py
```

---

## 9. Phase 6: Report Generation - 报告生成

### 9.1 IMRAD 报告结构

```
1. Introduction
   - 研究背景与意义
   - 微藻生物肥定义与分类
   - 研究现状与知识缺口
   - 本综述目的与问题

2. Methods
   - 检索策略（数据库、检索式、时间范围）
   - 纳入与排除标准
   - 筛选流程（PRISMA流程图）
   - 质量评估方法
   - 数据提取与分类框架

3. Results
   - 文献筛选结果（数量统计）
   - 年度发文趋势
   - 期刊与作者分布
   - 藻种类别分析
   - 机制分类分析
   - 应用场景分析
   - 质量评分分布

4. Discussion
   - 主要发现总结
   - 研究趋势与热点
   - 机制有效性比较
   - 藻种应用潜力评估
   - 研究局限性与方法学质量

5. Conclusion
   - 主要结论
   - 实践建议
   - 未来研究方向
```

### 9.2 执行命令

```bash
cd /Users/gao/microalgae-biofertilizer-review
python scripts/09-generate-report.py
```

**输出**: `outputs/report.md`

### 9.3 PDF 导出

```bash
cd /Users/gao/microalgae-biofertilizer-review
python scripts/10-export-pdf.py
```

**输出**: `outputs/report.pdf`

---

## 10. Reference Files - 参考文件

| 文件 | 路径 | 用途 |
|------|------|------|
| **关键词体系** | `references/keywords.md` | 检索式构建、同义词扩展、MeSH词表 |
| **检索策略配置** | `references/search-config.md` | 各数据库API参数、认证方式、检索式汇总 |
| **质量评估清单** | `references/quality-checklist.md` | 纳入/排除标准、评分体系、分类框架 |

---

## 11. Quality Checklist - 终检清单

综述报告发布前，必须逐项核对以下清单：

### 11.1 检索完整性
- [ ] AMiner 5个检索式均已执行
- [ ] PubMed 5个检索式均已执行
- [ ] 去重后无明显DOI/标题重复
- [ ] 重要高被引文献未被遗漏

### 11.2 筛选规范性
- [ ] 两阶段筛选流程已执行
- [ ] 排除文献均有明确理由记录
- [ ] 纳入文献≥8分（或≥12分优先纳入）
- [ ] 8-11分文献已进行双人复核

### 11.3 质量评估
- [ ] 每篇纳入文献均有0-20分评分
- [ ] 评分依据已在备注中说明
- [ ] 期刊分区判定依据年份正确

### 11.4 分类准确性
- [ ] 每篇文献至少有 M/A/C/R 各一个分类标签
- [ ] 分类标签一致性已抽查（≥10%样本）

### 11.5 报告完整性
- [ ] IMRAD五个章节齐全
- [ ] 图表编号和引用正确
- [ ] 讨论部分涵盖局限性分析
- [ ] 结论有实践建议和未来方向

### 11.6 格式规范性
- [ ] 参考文献格式统一（如GB/T 7714或APA）
- [ ] 图表标题中英文双语
- [ ] 无拼写错误和格式混乱

---

## 12. Troubleshooting - 常见问题

### Q1: AMiner API 返回空结果
**可能原因**: Token 无效或过期
**解决方案**: 
```bash
# 检查环境变量
echo $AMINER_TOKEN
# 测试API连接
curl -H "Authorization: $AMINER_TOKEN" "https://datacenter.aminer.cn/gateway/open_platform/api/paper/search?query=test&page=1&size=1"
```

### Q2: PubMed 检索结果少于预期
**可能原因**: 限速触发或网络问题
**解决方案**: 
```bash
# 增加请求间隔（修改脚本中的 delay 参数）
# 手动测试
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=microalgae+biofertilizer&retmax=10&retmode=json"
```

### Q3: 去重后文献数量异常减少
**可能原因**: 相似度阈值过高
**解决方案**: 检查 `04-deduplicate-merge.py` 中 similarity_threshold 参数，默认0.85

### Q4: 质量评分结果离散度大
**可能原因**: 评审者之间标准不一致
**解决方案**: 
- 召开校准会议，统一评分标准
- 对8-11分区间的文献进行双人独立评分
- 差异≥3分时引入第三人裁定

### Q5: 词云/图表无法生成
**可能原因**: 缺少中文字体或依赖库
**解决方案**:
```bash
# 安装字体
brew install font-noto-sans-cjk  # macOS
# 安装依赖
pip install wordcloud matplotlib scipy numpy pandas
```

### Q6: PDF 导出失败
**可能原因**: pandoc 或 XeLaTeX 未安装
**解决方案**:
```bash
# macOS
brew install pandoc
# Linux
sudo apt-get install pandoc texlive-xetex
```

---

## 附录: 快速启动命令

```bash
# 完整流程执行
cd /Users/gao/microalgae-biofertilizer-review

# Step 1: 检索
python scripts/01-search-aminer.py
python scripts/02-search-pubmed.py

# Step 2: 去重合并
python scripts/04-deduplicate-merge.py

# Step 3: 筛选分类
python scripts/05-screen-filter.py
python scripts/06-classify.py

# Step 4: 质量评估
python scripts/07-quality-score.py

# Step 5: 可视化
python scripts/08-visualize.py

# Step 6: 报告生成
python scripts/09-generate-report.py
python scripts/10-export-pdf.py
```

---

*文档版本: 1.0 | 更新日期: 2026-04-10 | 维护者: Gao*
