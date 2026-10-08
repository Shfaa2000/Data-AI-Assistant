"""Shared project paths and cloud configuration."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

RAG_DOCUMENTS_DIR = (DATA_DIR/ "rag_documents")

RAG_INDEX_DIR = (DATA_DIR/ "rag_index")

RAG_INDEX_PATH = (RAG_INDEX_DIR/ "finops_rag_index.json")

QUERIES_DIR = BASE_DIR / "queries"

DOCS_DIR = BASE_DIR / "docs"
REPORTS_DIR = DOCS_DIR / "reports"

BILLING_FILE = (
    RAW_DATA_DIR
    / "focus_cloud_billing_sample_1000.csv"
)

CLEANED_BILLING_FILE = (
    PROCESSED_DATA_DIR
    / "billing_cleaned.csv"
)

DATABASE_FILE = (
    DATA_DIR
    / "database.sqlite"
)

QUERY_RESULTS_FILE = (
    REPORTS_DIR
    / "query_results.txt"
)

PIPELINE_REPORT_FILE = (
    REPORTS_DIR
    / "latest_pipeline_run.json"
)

GCP_PROJECT_ID = (
    "data-ai-assistant-training"
)

BQ_DATASET_ID = (
    "cloud_finops"
)

BQ_SCHEMA_TABLE_ID = (
    "billing_cleaned"
)

BQ_STAGING_TABLE_ID = (
    "billing_staging"
)

BQ_PIPELINE_TABLE_ID = (
    "billing_pipeline_day2"
)

BQ_SERVICE_COST_VIEW_ID = (
    "v_service_costs"
)