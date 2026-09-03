from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

QUERIES_DIR = BASE_DIR / "queries"
REPORTS_DIR = BASE_DIR / "reports"

BILLING_FILE = RAW_DATA_DIR / "focus_cloud_billing_sample_1000.csv"
CLEANED_BILLING_FILE = PROCESSED_DATA_DIR / "billing_cleaned.csv"
DATABASE_FILE = DATA_DIR / "database.sqlite"


GCP_PROJECT_ID = "data-ai-assistant-training"
BQ_DATASET_ID = "cloud_finops"
BQ_SCHEMA_TABLE_ID = "billing_cleaned"
BQ_PIPELINE_TABLE_ID = "billing_pipeline_day2"
BQ_STAGING_TABLE_ID = "billing_staging"
BQ_SERVICE_COST_VIEW_ID = "v_service_costs"

OBJECT_STORAGE_BACKEND = "local"

LOCAL_OBJECT_STORAGE_ROOT = (
    CLEANED_BILLING_FILE.parent
    / "object_storage"
)

LOCAL_OBJECT_STORAGE_BUCKET = "finops-landing"

LOCAL_OBJECT_STORAGE_PREFIX = "raw/billing"

PIPELINE_MANIFESTS_DIR = (
    BASE_DIR
    / "reports"
    / "manifests"
)

EVIDENCE_DIR = (
    REPORTS_DIR
    / "evidence"
)

LATEST_EVIDENCE_FILE = (
    EVIDENCE_DIR
    / "latest.json"
)