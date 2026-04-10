---
title: 微藻类生物肥文献综述 - 数据库检索策略配置
version: 1.0
date: 2026-04-10
description: 为微藻类生物肥文献综述系统化检索配置各数据库检索策略
---

# 数据库检索策略配置

## 通用配置

```yaml
通用参数:
  时间范围: "2010-01-01 至 2026-04-10"
  语言限制: ["zh", "en"]
  最大结果数: 500
  去重策略: "以DOI为主键，标题相似度辅助判断"
  学科领域: ["Agriculture", "Biology", "Environmental Science", "Biochemistry"]
  输出格式: "JSON + BibTeX"
```

---

## 1. AMiner

**API文档**: https://datacenter.aminer.cn/gateway/open_platform

**认证方式**:
- Header: `Authorization: ${AMINER_API_KEY}`
- Header: `X-Platform: openclaw`

### 1.1 免费接口 - 论文检索

**接口**: `GET /api/paper/search`

**参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 检索词 |
| page | int | 否 | 页码，默认1 |
| size | int | 否 | 每页条数，默认20，最大100 |
| sort | string | 否 | 排序方式：relevance / cite / time |

**检索式示例**:

```json
// 检索式1: 微藻生物肥基础检索
{
  "query": "微藻 生物肥",
  "page": 1,
  "size": 100,
  "sort": "cite"
}

// 检索式2: Chlorella/Spirulina作为生物肥料
{
  "query": "(Chlorella OR Spirulina) biofertilizer",
  "page": 1,
  "size": 100,
  "sort": "relevance"
}

// 检索式3: 微藻固氮与植物促生
{
  "query": "microalgae nitrogen fixation plant growth promotion",
  "page": 1,
  "size": 100,
  "sort": "cite"
}
```

### 1.2 付费接口 - 语义搜索

**接口**: `POST /api/paper/qa/search`

**费用**: ¥0.05/次

**适用场景**: 当关键词检索结果不足时，使用语义搜索发现隐含相关文献

```json
// 请求体
{
  "query": "藻类提取物促进作物生长的机制研究",
  "topn": 50,
  "category": "paper"
}

// 响应体结构
{
  "code": 0,
  "data": {
    "result": [
      {
        "id": "string",
        "title": "string",
        "authors": ["string"],
        "abstract": "string",
        "year": int,
        "venue": "string",
        "citation": int,
        "score": float
      }
    ]
  }
}
```

### 1.3 免费接口 - 批量获取论文信息

**接口**: `POST /api/paper/info`

**费用**: 免费

**适用场景**: 根据检索到的paper ID批量获取详细信息

```json
// 请求体
{
  "ids": ["paper_id_1", "paper_id_2", "..."],
  "fields": ["title", "authors", "abstract", "year", "venue", "citation", "doi"]
}
```

### 1.4 AMiner检索式汇总

| # | 检索式 | 策略 | 预期命中率 |
|---|--------|------|------------|
| 1 | 微藻 生物肥 | 基础中文 | 高 |
| 2 | (Chlorella OR Spirulina) biofertilizer | 英文核心术语 | 高 |
| 3 | microalgae nitrogen fixation plant growth promotion | 英文扩展 | 中 |
| 4 | 藻类有机肥 植物促生 | 中文扩展 | 中 |
| 5 | (Anabaena OR Nostoc) cyanobacteria biofertilizer | 蓝藻固氮 | 中 |

---

## 2. PubMed / NCBI E-utilities

**API文档**: https://eutils.ncbi.nlm.nih.gov/

**认证方式**: 免费，无需API Key

### 2.1 核心接口

**ESearch** - 检索论文ID
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax={retmax}&retmode=json
```

**ESummary** - 获取论文摘要
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids}&retmode=json
```

### 2.2 检索策略设计

#### 2.2.1 主题词(MeSH)与自由词组合

**MeSH主题词**:
- Microalgae (微藻)
- Biofertilizers (生物肥料)
- Chlorella (小球藻)
- Spirulina (螺旋藻)
- Nitrogen Fixation (固氮作用)
- Plant Growth Promotion (植物促生)

#### 2.2.2 布尔逻辑检索式

```text
// 核心检索式
(微藻[Title/Abstract] OR microalgae[Title/Abstract] OR chlorella[Title/Abstract] OR spirulina[Title/Abstract]) 
AND 
(生物肥[Title/Abstract] OR biofertilizer[Title/Abstract] OR 生物肥料[Title/Abstract])

// 带时间限制
((微藻 OR microalgae) AND (生物肥 OR biofertilizer)) AND 2010:2026[dp]

// 扩展检索式 - 固氮相关
((微藻 OR microalgae OR cyanobacteria) AND (固氮 OR nitrogen fixation) AND (植物 OR plant)) 
NOT (human[Title])

// 蓝藻生物肥专项
(Anabaena[Title/Abstract] OR Nostoc[Title/Abstract] OR cyanobacteria[Title/Abstract]) 
AND (biofertilizer[Title/Abstract] OR biofertilizer[MeSH Terms])

// 藻类提取物与植物促生
((藻类提取物[Title/Abstract] OR algal extract[Title/Abstract]) AND (促生[Title/Abstract] OR promotion[Title/Abstract]))
```

### 2.3 完整检索示例

```bash
#!/bin/bash
# PubMed E-utilities 检索脚本

# 基础检索
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=((microalgae+OR+chlorella+OR+spirulina)+AND+(biofertilizer+OR+biomass))+AND+2010:2026[dp]&retmax=500&retmode=json&sort=relevance"

# 获取摘要
# 先用ESearch获取ID列表，再用ESummary获取详情
```

### 2.4 PubMed检索式汇总

| # | 检索式 | 检索字段 | 备注 |
|---|--------|----------|------|
| 1 | ((microalgae[Title/Abstract]) AND (biofertilizer[Title/Abstract])) | Title/Abstract | 基础检索 |
| 2 | (chlorella[MeSH Terms]) AND (biofertilizer[MeSH Terms]) | MeSH | 主题词检索 |
| 3 | ((microalgae[Title/Abstract]) AND (nitrogen fixation[Title/Abstract]) AND (plant[Title/Abstract])) | Title/Abstract | 固氮方向 |
| 4 | ((algal extract[Title/Abstract]) AND (plant growth promotion[Title/Abstract])) | Title/Abstract | 提取物方向 |
| 5 | (cyanobacteria[Title/Abstract]) AND (biofertilizer[Title/Abstract]) | Title/Abstract | 蓝藻方向 |

---

## 3. sciai-engine

**平台**: https://sciengine.las.ac.cn/

**用途**: 深度分析，用于Phase 3-4的文献挖掘与分析

**Token**: `8HSXyLFdbCZf`

**认证方式**: form-data，文本需 base64 编码（参见 `scripts/03_search_sciai.py`）

### 3.1 可用API（已验证）

| API名称 | 功能 | 状态 |
|---------|------|------|
| `api_ner_sci_en_v2` | 英文科研实体识别（研究问题/方法模型/数据资料/仪器设备/度量指标/软件系统） | ✓ 可用 |
| `paper_classification_cn` | 中文科技文献学科分类 | ✓ 可用 |
| `keywords_extraction_en` | 英文关键词提取 | ✗ Server not available |
| `keywords_extraction_cn` | 中文关键词提取 | 未测试 |

### 3.2 NER 实体类别（api_ner_sci_en_v2）

| 类别 | 说明 |
|------|------|
| 研究问题 | 微藻种类、生物肥类型、植物品种、土壤条件等 |
| 方法模型 | 实验方法、分析模型 |
| 数据资料 | 数据集、测量指标 |
| 仪器设备 | 设备名称 |
| 度量指标 | 量化指标 |
| 软件系统 | 软件工具 |

### 3.3 sciai-engine分析流程

```
Phase 3 (初步筛选)
  └─> api_ner_sci_en_v2: 批量提取候选文献关键词和研究问题
  └─> paper_classification_cn: 判断文献学科类别

Phase 4 (深度分析)
  └─> api_ner_sci_en_v2: 识别文献中的科学实体
      - 微藻种类名称（Chlorella, Spirulina, Anabaena等）
      - 生物肥成分与机制
      - 实验方法与度量指标
      - 植物品种与应用场景
```

---

## 4. 检索策略执行顺序

```
Phase 1: 广泛检索
  1. AMiner /api/paper/search - 5个检索式
  2. PubMed ESearch - 5个检索式
  └─> 合并去重，获取初始文献池 (~1000-2000篇)

Phase 2: 补充检索
  1. AMiner /api/paper/qa/search (语义搜索) - 高费用，按需使用
  2. 人工补充重要文献（综述类、高被引）

Phase 3: 初筛
  1. AMiner /api/paper/info 批量获取详情
  2. sciai-engine keywords_extraction_cn 批量关键词
  3. sciai-engine paper_classification_cn 初步分类

Phase 4: 深度分析
  1. sciai-engine api_ner_sci_cn_v2 实体识别
  2. 全文获取与人工筛选
```

---

## 5. 注意事项

1. **AMiner API Key**: 需在环境变量中设置 `AMINER_API_KEY`
2. **sciai-engine Token**: 需在环境变量中设置 `SCIAIENGINE_TOKEN`
3. **PubMed限速**: E-utilities建议每次请求间隔≥0.33秒（每秒3次限制）
4. **结果验证**: 检索完成后随机抽取10%文献进行人工标注验证召回率
5. **更新机制**: 初稿完成后每3个月更新一次检索结果

---

*文档版本: 1.0 | 更新日期: 2026-04-10*
