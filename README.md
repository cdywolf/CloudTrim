# 🔍 CloudTrim

**A Cloud Cost Optimization Engine (FinOps) with intelligent waste detection and anomaly analysis.**

[![CI/CD Pipeline](https://github.com/cdywolf/CloudTrim/actions/workflows/ci.yml/badge.svg)](https://github.com/cdywolf/CloudTrim/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 The Problem

AWS cloud bills are often opaque. Companies frequently overspend by **20% to 30%** due to:
- Forgotten or untagged resources (Shadow IT)
- Orphaned EBS volumes costing money for no reason
- Undetected abnormal cost spikes

## 💡 The Solution

CloudTrim is a FinOps analysis engine that:
1. **Ingests** AWS billing data (CUR format)
2. **Detects** waste and anomalies automatically
3. **Estimates** potential savings with **95% confidence intervals**
4. **Explains** each finding in natural language (Hybrid AI)
5. **Visualizes** everything in an interactive dashboard

## 🚀 Key Features

### 📊 Rigorous Statistical Analysis
- **Confidence Intervals**: No magic numbers, just reliable ranges based on data variability.
- **Anomaly Detection**: MAD (Median Absolute Deviation) + Z-score algorithm to spot suspicious cost spikes.
- **Recovery Rate**: Conservative estimation of actually actionable waste.

### 🤖 Hybrid AI Insights
- **Template Mode** (Default): Instant, 100% reliable business logic explanations.
- **LLM Mode** (Optional): Enriched explanations via OpenAI/Groq if an API key is configured.
- **Actionable Recommendations**: Concrete, step-by-step action plans for every detected issue.

### 🎨 Interactive Dashboard
- Chart.js visualizations (costs by service, region, and time evolution)
- Anomaly table with a "💡 Explain" button for instant AI insights
- Fully responsive design (Bootstrap 5)

## 🏗️ Technical Architecture


**Tech Stack:**
- **Backend**: Python 3.10+, FastAPI, Pydantic, DuckDB
- **Frontend**: Jinja2, Chart.js, Bootstrap 5
- **Testing & Quality**: pytest (30+ unit/integration tests), Ruff (linter), GitHub Actions (CI/CD)
- **Deployment**: Docker, GitHub Container Registry (GHCR), Render

---

## 🛠️ Local Installation

### Prerequisites
- Python 3.10+
- pip
- Git

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/cdywolf/CloudTrim.git
cd CloudTrim

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.\.venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Generate synthetic test data (simulates 30 days of AWS CUR)
cloudtrim generate --days 30 --out data/sample_cur.csv

# 5. Ingest data into the local DuckDB database
cloudtrim ingest --csv data/sample_cur.csv --db data/cloudtrim.duckdb

# 6. Run the CLI analysis to see text-based insights
cloudtrim analyze --db data/cloudtrim.duckdb

# 7. Start the local server (API + Dashboard)
cloudtrim serve --db data/cloudtrim.duckdb

# Build the image
docker build -t cloudtrim:latest .

# Run the container (mounts the local data folder to persist the database)
docker run -p 8000:8000 -v ${PWD}/data:/app/data cloudtrim:latest

# Run all unit and integration tests
pytest

# Run tests with an HTML coverage report
pytest --cov=src/cloudtrim --cov-report=html

# Check code style and formatting
ruff check src/ tests/
