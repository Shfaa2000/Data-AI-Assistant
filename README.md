# Data-AI Assistant

A training project focused on building a small Data-AI Assistant using cloud billing data.

The project starts with reliable data ingestion, validation, profiling, and analytics, and will gradually evolve toward SQL, ETL, LLM applications, RAG, and a small final assistant.

## Project Goal

The goal is to build a reusable and explainable pipeline that can:

- Load cloud billing data.
- Validate the dataset structure.
- Profile data quality.
- Analyze cloud costs.
- Investigate unusual billing records.
- Produce reliable analytical summaries.
- Later support SQL-based analytics.
- Later support document-based AI questions using RAG.

## Dataset

The current training dataset is:

`focus_cloud_billing_sample_1000.csv`

It contains 1,000 synthetic cloud billing records from multiple providers, including:

- AWS
- Microsoft
- Oracle

The dataset is used only for learning and development.

## Current Project Structure

```text
Data-AI-Assistant/
│
├── main.py
│
├── data/
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── ingestion.py
│   ├── profiling.py
│   ├── analytics.py
│   ├── investigations.py
│   └── validation.py
│
├── tests/
├── reports/
│
├── .gitignore
├── .env.example
├── requirements.txt
└── README.md