# Data-AI Assistant — FinOps MVP

A beginner-friendly Data and AI assistant for cloud billing analysis.

The project has two clear paths:

1. A data pipeline that validates, cleans, profiles, stores, and publishes billing data.
2. A FinOps assistant that accepts an English question through a CLI or FastAPI endpoint, generates safe GoogleSQL with Gemini, executes it in BigQuery, and returns an evidence-grounded English answer.

## Project Status

The current MVP supports:

- A local and BigQuery data pipeline.
- Gemini-generated Query Plans and SQL Proposals.
- Two Gemini calls per answered question.
- Local validation before BigQuery execution.
- BigQuery Dry Run and configurable execution limits.
- Result validation and Dynamic Evidence generation.
- Evidence-grounded final answers.
- CLI and FastAPI interfaces using the same Assistant Core.
- Automated tests for the data and FinOps query paths.

RAG over documents is not part of this version and can be added as a later project path.

## Architecture

### 1. Data Pipeline

```text
Raw CSV
  -> Ingestion
  -> Validation
  -> Cleaning
  -> Profiling and Investigations
  -> Cleaned CSV
  -> SQLite Reconciliation
  -> BigQuery Staging
  -> BigQuery Reconciliation
  -> Published BigQuery Table
  -> Pipeline Manifest
```

The data path can run locally for safe verification or publish the cleaned dataset to BigQuery.

### 2. FinOps Assistant

```text
User Question (CLI or FastAPI)
  -> Assistant Core
  -> BigQuery Schema Catalog
  -> Gemini Call 1: Query Plan + SQL Proposal
  -> Query Plan, SQL Safety, and Semantic Validation
  -> BigQuery Dry Run
  -> Optional BigQuery Execution
  -> Query Result Validation
  -> Dynamic Evidence
  -> Gemini Call 2: Final English Answer
  -> Final Answer Validation
  -> CLI or API Response
```

Gemini proposes the query and writes the final response. The backend owns validation, execution decisions, BigQuery access, and financial evidence.

## Why Two Gemini Calls?

The assistant originally used three Gemini calls:

1. Generate a Query Plan.
2. Generate an SQL Proposal.
3. Generate the final answer.

The first two stages are now combined. Gemini Call 1 returns both the Query Plan and SQL Proposal in one structured response. The backend still validates both contracts before BigQuery is contacted.

Gemini Call 2 receives only validated Dynamic Evidence and produces the final English answer.

This reduces model usage while keeping the important validation boundaries.

## Supported Query Capabilities

### Metrics

- `billed_cost`
- `effective_cost`
- `negative_billed_cost`

### Dimensions

- `provider`
- `service`
- `currency`

### Operations

- Sum, average, minimum, and maximum for supported metrics.
- Dimension filters and supported comparison operators.
- Date ranges.
- Grouping by supported dimensions.
- Ascending and descending sorting.
- Result limits.
- Clarification and unsupported-question states.

The MVP supports a defined semantic scope. It does not claim to answer every possible natural-language or financial question.

## Safety and Grounding

Before execution, the backend checks that the generated SQL:

- Contains exactly one read-only `SELECT` statement.
- Uses the allowed BigQuery table and physical columns.
- Does not use DML, DDL, joins, subqueries, CTEs, window functions, or `SELECT *`.
- Uses named parameters for user-provided values.
- Matches the validated Query Plan.
- Stays within the configured BigQuery byte limit.

After execution, the backend checks that:

- Returned columns match the Query Plan.
- Row counts and values satisfy the result contract.
- Dynamic Evidence contains the verified query result.
- The final answer references real evidence rows and columns.
- Financial numbers in the answer are present in the evidence or are permitted rounded representations.

## Project Structure

```text
.
├── data/
│   └── raw/
├── queries/
│   └── bigquery/
├── src/
│   ├── analytics.py
│   ├── cleaning.py
│   ├── config.py
│   ├── database.py
│   ├── ingestion.py
│   ├── investigations.py
│   ├── pipeline_manifest.py
│   ├── profiling.py
│   ├── validation.py
│   └── finops_query/
├── tests/
├── finops_api.py
├── main.py
├── run_cloud_pipeline.py
├── run_finops_query_generation_live.py
├── run_queries.py
├── .env.example
└── requirements.txt
```

## Requirements

- Python 3.11 or later is recommended.
- A Google Cloud project with BigQuery enabled.
- Google Application Default Credentials or an equivalent configured BigQuery credential.
- A Gemini API key.

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy the environment template on Windows:

```bash
copy .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

Add the real Gemini key only to `.env`. Never commit `.env` or credential files.

## Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API key | Keep secret |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project ID | `data-ai-assistant-training` |
| `FINOPS_DATASET_ID` | BigQuery dataset | `cloud_finops` |
| `FINOPS_TABLE_ID` | Published billing table | `billing_pipeline_day2` |
| `BIGQUERY_LOCATION` | BigQuery location | `US` |
| `GEMINI_MODEL` | Gemini model name | `gemini-3.5-flash-lite` |
| `FINOPS_EXECUTE_QUERIES` | Enables real query execution | `false` or `true` |
| `FINOPS_MAXIMUM_BYTES_BILLED` | Maximum bytes allowed per query | `104857600` |
| `FINOPS_MAX_RESULT_ROWS` | Maximum rows accepted by the backend | `100` |
| `FINOPS_QUERY_TIMEOUT_SECONDS` | BigQuery execution timeout | `60` |

Keep `FINOPS_EXECUTE_QUERIES=false` when testing query generation and Dry Run only.

Change it to `true` only when real BigQuery execution is intended.

## Running the Data Pipeline

Run the local data preparation path:

```bash
python main.py
```

Run the cloud pipeline without publishing to BigQuery:

```bash
python run_cloud_pipeline.py --local-only
```

Run the cloud pipeline and publish to BigQuery:

```bash
python run_cloud_pipeline.py
```

Run the analytical SQL files:

```bash
python run_queries.py
```

## Running the FinOps Assistant from the CLI

Set this value in `.env` when real execution is required:

```text
FINOPS_EXECUTE_QUERIES=true
```

Start the CLI:

```bash
python run_finops_query_generation_live.py
```

Then enter an English financial question.

Example:

```text
What are the top 5 services by billed cost for AWS?
```

## Running the FastAPI Interface

Start the API:

```bash
python -m uvicorn finops_api:app --reload
```

Open the interactive documentation:

```text
http://127.0.0.1:8000/docs
```

Available endpoints:

- `GET /health`
- `POST /finops/query`

Example request:

```json
{
  "question": "What are the top 5 services by billed cost for AWS?"
}
```

The CLI and FastAPI paths both call the same Assistant Core, so the business logic is not duplicated.

## Example Questions

```text
What is the total billed cost for AWS?
```

```text
What are the top 5 services by billed cost for AWS?
```

```text
What is the total effective cost for Microsoft?
```

```text
What is the negative billed cost for Microsoft?
```

```text
What was the total billed cost for AWS from September 1, 2024 to September 30, 2024?
```

## Running the Tests

Run the complete test suite:

```bash
python -m pytest -q
```

The tests use controlled test doubles where needed and do not require every test to call the real Gemini or BigQuery services.

## Main BigQuery Resources

- Project: `data-ai-assistant-training`
- Dataset: `cloud_finops`
- Location: `US`
- Schema reference table: `billing_cleaned`
- Staging table: `billing_staging`
- Published table: `billing_pipeline_day2`

## Current Limitations

- The assistant supports the declared FinOps semantic schema only.
- Complex joins, subqueries, CTEs, and window functions are outside the MVP SQL subset.
- Questions requiring unavailable fields or unsupported business logic return an unsupported or clarification state.
- Model quotas and BigQuery permissions depend on the configured Google accounts and services.
- RAG and document-question routing are planned future paths, not current features.

## Dataset Note

The repository uses a small synthetic billing dataset for training and demonstration.

It contains 1,000 rows across AWS, Microsoft, and Oracle examples and must not be treated as production financial data.

## Repository Safety

Do not commit:

- `.env`
- API keys
- Google Cloud credential JSON files
- Local databases
- Generated runtime artifacts unless intentionally required for documentation

Commit `.env.example` only, with placeholder or non-secret values.