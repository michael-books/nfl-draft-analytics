# NFL Draft Analytics

> **Who actually becomes elite?** — An analysis of NFL Draft hit rates by round, position, and pick number using Pro Football Reference data (2010–2024).

**[Live Demo →](https://nfl-draft-analytics-r2t5xjb4fax5zaehevidas.streamlit.app)**

## Overview

This project scrapes NFL Draft results and First-Team All-Pro selections from Pro Football Reference, calculates All-Pro "hit rates" by draft round and position, and presents findings as:

- A **Jupyter Notebook** with a full analytical narrative
- A **Streamlit interactive dashboard** for live exploration

## Project Structure

```
nfl-draft-analytics/
├── data/
│   ├── raw/                  # Cached CSVs from scraping
│   └── processed/            # Cleaned & merged outputs
├── src/
│   ├── scraper.py            # Fetch & cache PFR pages
│   ├── cleaner.py            # Normalize, deduplicate, fix types
│   ├── merger.py             # Join draft + All-Pro, add is_allpro flag
│   ├── analyzer.py           # Hit-rate aggregations (pure pandas)
│   └── charts.py             # Plotly figure factory
├── notebooks/
│   └── nfl_draft_analysis.ipynb
├── app/
│   └── streamlit_app.py
└── requirements.txt
```

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Scrape the data

Run from the project root (takes ~3 minutes — respects PFR's rate limits):

```python
from src.scraper import scrape_all_years
scrape_all_years(list(range(2010, 2025)), "data/", delay=3.0)
```

Or open the notebook and run the scraping cell with `RESCRAPE = True`.

### 3. Clean, merge, and build the processed dataset

```python
from src.cleaner import clean_draft_data, clean_allpro_data
from src.merger import merge_datasets, filter_analysis_cohort

draft_df  = clean_draft_data("data/raw/",  "data/processed/draft_cleaned.csv")
allpro_df = clean_allpro_data("data/raw/", "data/processed/allpro_cleaned.csv")

from src.merger import merge_datasets, filter_analysis_cohort
merged = merge_datasets(draft_df, allpro_df)
cohort = filter_analysis_cohort(merged)
cohort.to_csv("data/processed/merged_dataset.csv", index=False)
```

### 4. Launch the Streamlit dashboard

```bash
streamlit run app/streamlit_app.py
```

### 5. Open the notebook

```bash
jupyter notebook notebooks/nfl_draft_analysis.ipynb
```

## Key Findings

1. **Round 1 dominance is real, but not absolute.** First-round picks produce All-Pros at ~3–5× the rate of later rounds, but even Round 1 has only a ~15–25% hit rate.
2. **The Round 1/2 cliff is sharp.** There is a dramatic drop in All-Pro probability at the round boundary.
3. **Position matters.** QB and elite pass-rusher positions produce the highest All-Pro rates.
4. **Late-round value exists** in certain positions — rounds 3–5 can yield surprising hit rates.

## Data Source

All data from [Pro Football Reference](https://www.pro-football-reference.com).
Please respect their `robots.txt` and rate limits (this project uses a 3-second delay between requests).

## Analysis Cohort

Draft classes **2010–2021** only — ensuring every player has had ≥3 full NFL seasons by end of 2024.
All-Pro selections from 2010–2024 are used to determine who earned the flag.

## Tech Stack

- **Python 3.10+**
- pandas, plotly, requests, beautifulsoup4, lxml
- Streamlit (dashboard), Jupyter (notebook)
