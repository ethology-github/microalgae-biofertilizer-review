# Microalgae Biofertilizer Review

A systematic literature review and network analysis of microalgae-based biofertilizers for agricultural applications.

## Overview

This project collects, analyzes, and visualizes research data on microalgae biofertilizers, including their effects on crop yield, soil health, and nutrient content.

## Features

- **Data Collection**: Automated fetching of research papers and citation data
- **Network Analysis**: Build and analyze citation/collaboration networks using NetworkX
- **Data Visualization**: Generate interactive plots with Plotly and static figures with Matplotlib
- **Report Generation**: Produce structured reports in PDF and DOCX formats
- **Fuzzy Matching**: Robust paper deduplication using RapidFuzz
- **Web Scraping**: Extract structured data from academic websites with BeautifulSoup4/lxml

## Project Structure

```
microalgae-biofertilizer-review/
├── README.md
├── pyproject.toml
├── .gitignore
├── outputs/
│   ├── data/          # JSON data files
│   ├── figures/       # PNG/SVG plots and charts
│   └── reports/       # PDF/DOCX generated reports
└── src/               # Source code (to be added)
```

## Quick Start

### Prerequisites

- Python 3.11 or higher
- uv package manager (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/microalgae-biofertilizer-review.git
cd microalgae-biofertilizer-review

# Install dependencies with uv
uv sync

# Or with pip
pip install -e .
```

### Environment Variables

Create a `.env` file in the project root:

```env
# API Keys (optional)
OPENALEX_API_KEY=your_key_here
CROSSREF_API_KEY=your_key_here

# Paths
DATA_DIR=outputs/data
FIGURE_DIR=outputs/figures
REPORT_DIR=outputs/reports
```

### Running the Project

```bash
# Run the main data collection
uv run python -m src.collect

# Run network analysis
uv run python -m src.analyze

# Generate reports
uv run python -m src.report

# Run all steps
uv run python -m src.main
```

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint
uv run ruff check .
```

## References

- OpenAlex API Documentation
- Crossref API Documentation
- NetworkX Documentation
- Plotly Python Library

## License

This project is licensed under the MIT License - see the LICENSE file for details.
