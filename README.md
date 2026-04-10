# Microalgae Biofertilizer Literature Review

> Automated literature review workflow for microalgae-based biofertilizers

## Overview

Automated pipeline for systematic literature review of microalgae biofertilizer research.

## Databases

- AMiner (paper_search + paper_qa_search)
- PubMed (via NCBI E-utilities)
- sciai-engine (deep analysis: entity recognition, keyword extraction, paper classification)

## Workflow Phases

1. Multi-database search
2. Deduplication & merge
3. Screening & filtering
4. Classification & quality scoring
5. Visualization
6. Report generation

## Installation

```bash
pip install -r requirements.txt
export AMINER_API_KEY="your_key"
export SCIAIENGINE_TOKEN="your_token"
```

## Quick Start

```bash
python scripts/01-search-aminer.py
python scripts/02-search-pubmed.py
python scripts/04-deduplicate-merge.py
python scripts/05-screen-filter.py
python scripts/08-visualize.py
python scripts/09-generate-report.py
python scripts/10-export-pdf.py
```

## License

MIT
