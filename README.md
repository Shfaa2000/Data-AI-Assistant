# Data-AI Assistant

A training project for building a reliable and explainable Data-AI Assistant using synthetic multi-cloud billing data.

The current version implements local data ingestion, validation, cleaning, SQLite analytics, BigQuery publishing, reusable FinOps SQL analysis, Trusted Evidence generation, FastAPI endpoints, HTTP clients, and automated tests.

LLM and RAG integration remain future milestones.

## Project Goal

The project builds a reusable pipeline that can:

- Load cloud billing data.
- Validate the dataset structure.
- Clean and normalize selected fields.
- Profile data quality.
- Investigate unusual billing records.
- Store and query data locally using SQLite.
- Load validated data into BigQuery staging.
- Reconcile local and cloud financial metrics.
- Publish verified data to a BigQuery table.
- Run reusable FinOps SQL analytics.
- Build a trusted Evidence JSON snapshot.
- Expose analytical results through FastAPI.
- Prepare verified data for future LLM and RAG integration.

## Dataset

The project uses:

`focus_cloud_billing_sample_1000.csv`

The dataset contains 1,000 synthetic cloud billing charge lines from:

- AWS
- Microsoft
- Oracle

The dataset is used only for training and development.

## Current Architecture

```text
Raw CSV
    ↓
Pandas Ingestion
    ↓
Validation
    ↓
Cleaning
    ↓
Cleaned CSV
    ↓
Local Object Landing Zone
    ↓
BigQuery Staging
    ↓
Financial Reconciliation
    ↓
Published BigQuery Table
    ↓
SQL Views and FinOps Analytics
    ↓
Trusted Evidence JSON
    ↓
FastAPI
    ↓
HTTP Clients
```

## Key Project Structure

```text
Data-AI-Assistant/
│
├── main.py
├── run_cloud_pipeline.py
├── run_finops_analytics.py
├── run_finops_client.py
├── run_finops_evidence.py
├── run_evidence_client.py
├── run_with_log.py
├── finops_api.py
│
├── data/
│   ├── raw/
│   └── processed/
│
├── queries/
│   └── bigquery/
│       ├── billing_period_distribution.sql
│       ├── provider_cost_ladder.sql
│       ├── service_breakdown.sql
│       ├── service_cost_ranking.sql
│       ├── temporal_coverage.sql
│       └── v_service_costs.sql
│
├── src/
│   ├── __init__.py
│   ├── analytics.py
│   ├── cleaning.py
│   ├── config.py
│   ├── database.py
│   ├── evidence.py
│   ├── ingestion.py
│   ├── investigations.py
│   ├── object_storage.py
│   ├── pipeline_manifest.py
│   ├── service_breakdown.py
│   └── validation.py
│
├── tests/
│   └── test_evidence.py
│
├── .gitignore
├── .env.example
├── requirements.txt
└── README.md
```

The `reports/` directory is generated locally at runtime and is intentionally excluded from Git.

## Google Cloud Resources

The current training environment uses:

- Project: `data-ai-assistant-training`
- Dataset: `cloud_finops`
- Reference table: `billing_cleaned`
- Staging table: `billing_staging`
- Published table: `billing_pipeline_day2`
- Analytical view: `v_service_costs`
- BigQuery location: `US`

## Data Quality Controls

The pipeline includes checks for:

- Required columns.
- Column order and reference schema compatibility.
- Missing and completely empty fields.
- Negative billed-cost records.
- Zero-cost records.
- Date-field compatibility.
- Resource-field completeness.
- Charge-frequency normalization.
- Availability-zone validity.
- Outlier investigation.
- Financial reconciliation before publishing.

The staging table is validated before the published table is updated.

## Financial Reconciliation

The pipeline compares these critical metrics:

- Row count.
- Billed cost.
- Effective cost.
- Negative row count.
- Zero-cost row count.

The final recorded Evidence reconciliation completed with:

```text
RECONCILIATION_CHECKS: 5/5 PASS
EVIDENCE_STATUS: VERIFIED
```

Aggregate reconciliation verifies the recorded totals, but it does not replace complete row-level reconciliation.

## FinOps Analytics

The SQL analytics currently support:

- Provider cost summaries.
- Cost-layer comparisons.
- Temporal coverage.
- Billing-period distribution.
- Service-cost ranking.
- Positive and negative billed-cost separation.
- Service-category and charge-category breakdowns.

The current sample shows that Amazon Elastic Compute Cloud is the highest positive-cost service.

Its recorded breakdown includes:

- Compute / Usage.
- Storage / Usage.
- Compute / Credit.

These results identify investigation priorities but do not independently prove waste, optimization opportunities, or root causes.

## Trusted Evidence

The project builds a versioned Evidence JSON bundle from:

- The latest successful pipeline manifest.
- The published BigQuery table.
- Reconciled financial metrics.
- The highest-cost service.
- The selected service breakdown.
- BigQuery query job IDs.
- Explicit analytical limitations.

Each Evidence bundle receives a unique Evidence ID.

A historical Evidence file is always retained, while `latest.json` is updated only when all reconciliation checks pass and the Evidence status is `VERIFIED`.

## API Endpoints

The FastAPI application provides:

- `GET /health`
- `GET /finops/services`
- `GET /finops/service-breakdown`
- `GET /finops/evidence/latest`

Swagger documentation is available while the API is running:

`http://127.0.0.1:8000/docs`

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

The project currently uses Google Application Default Credentials to access BigQuery.

## Run the Local Analysis

```powershell
python main.py
```

## Run the Cloud Pipeline

Run local validation only:

```powershell
python run_cloud_pipeline.py --local-only
```

Run the complete BigQuery pipeline:

```powershell
python run_cloud_pipeline.py
```

The complete pipeline performs:

1. Local ingestion and validation.
2. Cleaning.
3. SQLite reconciliation.
4. Local object-storage registration.
5. BigQuery staging load.
6. Staging reconciliation.
7. Published-table update.
8. Pipeline Manifest generation.

## Run FinOps Analytics

Create or verify the analytical view when required:

```powershell
python run_finops_analytics.py --create-view
```

Run the service-cost analysis:

```powershell
python run_finops_analytics.py
```

## Build Trusted Evidence

```powershell
python run_finops_evidence.py
```

A successful execution should return:

```text
EVIDENCE_STATUS: VERIFIED
RECONCILIATION_CHECKS: 5/5 PASS
```

## Run the API

```powershell
python -m uvicorn finops_api:app --reload
```

Keep this terminal running.

## Run the HTTP Clients

In another terminal, run the service-breakdown client:

```powershell
python run_finops_client.py
```

Run the Evidence client:

```powershell
python run_evidence_client.py
```

## Run the Tests

```powershell
python -m pytest -q
```

The tests cover:

- Data validation.
- Financial reconciliation.
- Verified Evidence generation.
- Failed Evidence protection.
- API success and failure behavior.

## Cloud Storage Limitation

A real Google Cloud Storage bucket could not be created because Billing is disabled and an eligible online payment method is unavailable in the current environment.

The project therefore uses a local content-addressed object-storage backend based on SHA-256.

The local backend provides:

- Deterministic object identity.
- Duplicate-storage prevention.
- Stored-versus-reused tracking.
- A structured landing-zone path.

BigQuery staging, reconciliation, publishing, analytics, and Evidence generation remain operational.

The local storage backend can later be replaced with Google Cloud Storage without redesigning the complete analytical flow.

## Current Limitations

- The dataset is synthetic and contains only 1,000 rows.
- The provider distribution is highly imbalanced.
- The available periods do not support a reliable monthly trend.
- The project currently uses user-based Application Default Credentials instead of a service account.
- Google Cloud Storage is represented by a local fallback, not a real bucket.
- Aggregate reconciliation does not prove complete row-by-row equality.
- The causes of Microsoft negative Usage records are not fully proven.
- The AWS billed-versus-effective cost gap requires additional source documentation.
- The Evidence bundle does not provide forecasting.
- The Evidence bundle does not prove resource-level root causes.
- LLM and RAG integration have not been implemented yet.

## Future Milestones

Planned milestones include:

- Replacing the local landing zone with Google Cloud Storage.
- Using a dedicated service account.
- Adding row-level reconciliation.
- Expanding temporal and monthly analysis.
- Adding an LLM explanation layer.
- Grounding LLM answers in verified Evidence.
- Adding RAG for project documentation and analytical context.
- Building a small user-facing assistant.