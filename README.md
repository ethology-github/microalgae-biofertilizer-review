# 微藻类生物肥文献综述系统

系统性的微藻类生物肥料（Microalgae Biofertilizer）文献综述工具，覆盖 AMiner、PubMed、sciai-engine 三大数据库，实现从检索到报告的全流程自动化。

---

## 功能特性

| 特性 | 说明 |
|------|------|
| 多数据库检索 | AMiner + PubMed + sciai-engine，覆盖中英文学术资源 |
| PRISMA 筛选 | 两阶段筛选（标题摘要 → 全文评估），符合系统性综述规范 |
| 质量评分 | 0-20 分评分体系（方法学 + 期刊级别 + 主题相关性） |
| 四维分类 | 机制（M）/ 藻种（A）/ 应用场景（C）/ 研究类型（R） |
| NER 分析 | sciai-engine 实体识别，提取研究问题 / 方法 / 度量指标 |
| 可视化 | 年度趋势、期刊分布、藻种词云、机制柱状图、作物桑基图 |
| 报告导出 | Markdown → Word/PDF，支持 IMRAD 结构化输出 |

---

## 项目结构

```
microalgae-biofertilizer-review/
├── SKILL.md                        # 技能定义文档
├── README.md                       # 本文档
├── pyproject.toml                  # Python 项目配置
├── requirements.txt                # 依赖列表
│
├── scripts/                        # 核心脚本（按执行顺序）
│   ├── 01_search_aminer.py         # AMiner 多策略检索
│   ├── 02_search_pubmed.py        # PubMed 检索
│   ├── 03_search_sciai.py         # sciai-engine NER + 分类
│   ├── 04_deduplicate_merge.py    # 去重与合并
│   ├── 05_screen_filter.py        # 两阶段筛选
│   ├── 06_classify.py             # 四维分类标注
│   ├── 07_quality_score.py        # 质量评分
│   ├── 08_visualize.py            # 可视化图表生成
│   ├── 09_generate_report.py      # IMRAD 报告生成
│   ├── 10_export_pdf.py           # PDF 导出
│   └── utils.py                   # 通用工具函数
│
├── references/                     # 参考配置
│   ├── keywords.md                 # 关键词体系与 MeSH 词表
│   ├── search-config.md            # 各数据库检索策略与 API 参数
│   └── quality-checklist.md        # 质量评估清单
│
├── data/                           # 数据目录
│   └── interim/                    # 中间结果
│       ├── raw/                    # 原始检索结果
│       ├── deduplicated/           # 去重后数据
│       ├── screened/               # 筛选后数据
│       ├── classified/             # 分类结果
│       └── sciai_analyzed/         # sciai NER + 分类结果
│
├── outputs/                        # 输出目录
│   ├── report.md                   # 生成的综述报告
│   ├── report.docx                 # Word 格式
│   ├── report.pdf                  # PDF 格式
│   ├── figures/                    # 可视化图表
│   └── visualizations/             # 交互式图表
│
├── evals/                          # 评测用例
└── tests/                          # 单元测试
```

---

## 环境准备

### 依赖安装

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### API Token 配置

本项目需要配置两个学术数据库的 API 凭证：

---

#### 1. AMiner Token

**获取地址**：https://open.aminer.cn/open/board?tab=control

**说明**：
- 注册并登录 AMiner Open Platform
- 进入控制台 → API Key 管理 → 创建新 Token
- 免费接口（`/api/paper/search`）每日有配额限制
- 付费语义搜索（`/api/paper/qa/search`）¥0.05/次，按需使用

**配置方式**：

```bash
# 方式A：写入 ~/.zshrc（永久生效）
echo 'export AMINER_API_KEY="你的Token值"' >> ~/.zshrc
source ~/.zshrc

# 方式B：临时设置（当前终端有效）
export AMINER_API_KEY="你的Token值"

# 方式C：运行时传入
python scripts/01_search_aminer.py --api-key "你的Token值"
```

> **注意**：Token 即 JWT 字符串，以 `eyJhbGci...` 开头

---

#### 2. sciai-engine Token

**获取地址**：https://sciengine.las.ac.cn/

**说明**：
- 使用飞书账号登录（项目组统一认证）
- 首次登录需联系管理员开通权限
- Token 信息可在飞书文档中查看：https://zhipu-ai.feishu.cn/wiki/IZJjwPf9MiWgXYkuyQDcOxTvnOd
- Token 格式示例：`8HSXyLFdbCZf`（一串短字符）

**配置方式**：

```bash
# 写入 ~/.zshrc（永久生效）
echo 'export SCIAI_TOKEN="你的Token值"' >> ~/.zshrc
source ~/.zshrc

# 验证配置
echo $SCIAI_TOKEN
```

> **注意**：sciai-engine 的 Token 是飞书 SSO 统一认证生成的，格式为短字符串（非 JWT）

---

#### 3. 快速验证

```bash
# 验证 AMiner Token
curl -H "Authorization: $AMINER_API_KEY" \
  "https://datacenter.aminer.cn/gateway/open_platform/api/paper/search?query=test&size=1"

# 验证 sciai Token（NER 接口）
curl -X POST "https://sciengine.las.ac.cn/api/ner/sci_en_v2" \
  -H "Token: $SCIAI_TOKEN" \
  -F "text=Microalgae biofertilizer improves plant growth"
```

---

## 快速开始

### 完整流程（6 阶段）

```bash
cd /Users/gao/microalgae-biofertilizer-review

# ========== Phase 1: 多数据库检索 ==========
# AMiner（需配置 AMINER_API_KEY）
python scripts/01_search_aminer.py \
  --api-key "$AMINER_API_KEY" \
  --output data/interim/raw/aminer_papers.json

# PubMed（无需 API Key）
python scripts/02_search_pubmed.py \
  --output data/interim/raw/pubmed_papers.json

# sciai-engine（需配置 SCIAI_TOKEN，在 Phase 3 使用）
# 读取筛选结果进行 NER 分析
python scripts/03_search_sciai.py \
  --input data/interim/screened_papers.json \
  --output data/interim/sciai_analyzed_papers.json

# ========== Phase 2: 去重与合并 ==========
python scripts/04_deduplicate_merge.py

# ========== Phase 3: 筛选 ==========
python scripts/05_screen_filter.py

# ========== Phase 4: 分类 + 质量评分 ==========
python scripts/06_classify.py
python scripts/07_quality_score.py

# ========== Phase 5: 可视化 ==========
python scripts/08_visualize.py

# ========== Phase 6: 报告生成 ==========
python scripts/09_generate_report.py
python scripts/10_export_pdf.py
```

### 分步执行

| 阶段 | 命令 | 依赖 |
|------|------|------|
| AMiner 检索 | `01_search_aminer.py --api-key "$AMINER_API_KEY"` | AMiner Token |
| PubMed 检索 | `02_search_pubmed.py` | 无 |
| sciai NER | `03_search_sciai.py --input screened.json` | SCIAI_TOKEN |
| 去重合并 | `04_deduplicate_merge.py` | raw/*.json |
| 筛选 | `05_screen_filter.py` | deduplicated.json |
| 分类 | `06_classify.py` | screened.json |
| 质量评分 | `07_quality_score.py` | classified.json |
| 可视化 | `08_visualize.py` | quality_assessed.json |
| 报告生成 | `09_generate_report.py` | 所有中间文件 |
| PDF 导出 | `10_export_pdf.py` | report.docx |

---

## 数据流向

```
[AMiner] ─┐
[PubMed] ─┼──► 04 去重合并 ──► deduplicated_papers.json
[sciai] ──┘                            │
                                     ▼
                              05 筛选 ──► screened_papers.json
                                     │
                                     ▼
                              06 分类 ──► classification_labels.json
                                     │
                                     ▼
                              07 质量评分 ──► quality_assessed_papers.json
                                     │
                                     ▼
                              03 sciai NER ──► sciai_analyzed_papers.json
                                     │
                                     ▼
                              08 可视化 ──► figures/
                                     │
                                     ▼
                              09 生成报告 ──► report.md
                                     │
                                     ▼
                              10 导出 PDF ──► report.pdf
```

---

## 输出说明

| 文件 | 说明 |
|------|------|
| `outputs/report.md` | IMRAD 格式综述报告（含 sciai NER 分析章节） |
| `outputs/report.docx` | Word 格式，可直接提交 |
| `outputs/report.pdf` | PDF 格式，适合分发 |
| `figures/annual_trend.png` | 年度发文趋势折线图 |
| `figures/journal_distribution.png` | 期刊 Q1-Q4 分布饼图 |
| `figures/algae_wordcloud.png` | 藻种类别中文词云 |
| `figures/mechanism_bar.png` | M1-M5 机制分类柱状图 |
| `figures/crop_sankey.png` | 藻种→机制→作物流向桑基图 |

---

## 常见问题

**Q1：AMiner API 返回空结果？**
- 检查 Token 是否过期或已禁用
- 确认 `AMINER_API_KEY` 环境变量已正确设置

**Q2：sciai NER 请求失败？**
- 确认 `SCIAI_TOKEN` 已写入环境变量
- 检查 Token 是否在有效期内

**Q3：PDF 导出失败？**
- 确保已安装 LibreOffice：
  ```bash
  brew install --cask libreoffice
  ```

**Q4：检索结果少于预期？**
- 免费接口有每日配额限制，可升级为付费 Token
- 尝试增加语义搜索（`--semantic` 参数）

---

## 参考资料

- [AMiner Open Platform 文档](https://open.aminer.cn/open/docs)
- [sciai-engine 学术智能分析平台](https://sciengine.las.ac.cn/)
- [sciai Token 飞书配置文档](https://zhipu-ai.feishu.cn/wiki/IZJjwPf9MiWgXYkuyQDcOxTvnOd)
- [PRISMA 2020 系统性综述报告规范](https://www.prisma-statement.org/)
- [MeSH 词表 - 微藻与生物肥相关主题](https://meshb.nlm.nih.gov/)

## License

MIT License
