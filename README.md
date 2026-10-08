# Data-AI Assistant — FinOps MVP

A beginner-friendly Data and AI assistant for cloud billing analysis.

The project contains three focused paths:

1. A data pipeline that validates, cleans, profiles, stores, and publishes cloud billing data.
2. A FinOps Query assistant that converts English financial questions into validated GoogleSQL, executes them in BigQuery, and returns evidence-grounded answers.
3. A FinOps RAG assistant that answers documentation questions using trusted PDF sources and returns the retrieved source metadata.

## Project Status

The current MVP supports:

- Local and BigQuery cloud billing data processing.
- Gemini-generated Query Plans and SQL Proposals.
- Two Gemini calls for answered financial queries.
- Local Query Plan, SQL safety, and SQL semantic validation.
- BigQuery Dry Run with configurable execution limits.
- BigQuery result validation and Dynamic Evidence generation.
- Evidence-grounded final financial answers.
- Query access through CLI and FastAPI.
- PDF document loading and text extraction.
- Configurable text chunking with overlap.
- Gemini document and question embeddings.
- Local RAG index storage and reuse.
- Cosine similarity retrieval.
- Grounded RAG answers with file, page, chunk, URL, and similarity metadata.
- Explicit insufficient-evidence responses when the documents do not support an answer.

The Query and RAG paths are currently separate. Automatic routing between them is planned for a later project stage.

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

The data path can run locally for verification or publish the cleaned dataset to BigQuery.

### 2. FinOps Query Assistant

```text
User Question
  -> CLI or FastAPI
  -> Assistant Service
  -> Safe BigQuery Schema Context
  -> Gemini Call 1
  -> Query Plan + SQL Proposal
  -> Query Plan Validation
  -> SQL Safety Validation
  -> SQL Semantic Validation
  -> BigQuery Parameters
  -> BigQuery Dry Run
  -> Optional BigQuery Execution
  -> Query Result Validation
  -> Dynamic Evidence
  -> Gemini Call 2
  -> Final Answer Validation
  -> CLI or FastAPI Response
```

Gemini proposes the Query Plan and SQL, but the backend owns validation, execution decisions, BigQuery access, and financial evidence.

### 3. FinOps RAG Assistant

```text
PDF Documents
  -> Page Text Extraction
  -> Text Normalization
  -> Chunking with Source Metadata
  -> Document Embeddings
  -> Local RAG Index
  -> User Question Embedding
  -> Cosine Similarity
  -> Top K Retrieved Chunks
  -> Grounded Gemini Answer
  -> Answer with Source Metadata
```

The complete PDF is not sent to Gemini. Only the chunks retrieved as most relevant to the user question are included in the answer prompt.

If the retrieved context does not contain enough evidence, the assistant returns an insufficient-evidence response instead of using outside knowledge.

## Why Two Gemini Calls in the Query Path?

The Query assistant uses two Gemini calls:

1. Gemini Call 1 returns a structured Query Plan and SQL Proposal.
2. Gemini Call 2 receives validated Dynamic Evidence and creates the final English answer.

The first result is validated before BigQuery is contacted. The second call does not receive unrestricted database access or the complete table; it receives only the validated evidence needed for the answer.

This design reduces model usage while preserving the important safety and grounding boundaries.

## Simplified Query Architecture

The Query path is organized into six focused files:

| File | Responsibility |
|---|---|
| `models.py` | Defines the Pydantic contracts shared across the Query journey. |
| `schema.py` | Reads the real BigQuery schema and builds a safe semantic context. |
| `query_service.py` | Performs Gemini Call 1 and validates the Query Plan and generated SQL. |
| `bigquery_service.py` | Binds parameters, performs Dry Run and execution, validates results, and builds Dynamic Evidence. |
| `answer_service.py` | Performs Gemini Call 2 and validates the grounded final answer. |
| `assistant_service.py` | Coordinates the complete Query journey and returns one shared result contract. |

The CLI and FastAPI interfaces call the same Assistant Service, so the core business logic is not duplicated.

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

- Sum, average, minimum, maximum, and supported count operations.
- Dimension filters with supported comparison operators.
- Date ranges.
- Grouping by supported dimensions.
- Ascending and descending sorting.
- Result limits.
- Clarification and unsupported-question states.

The Query assistant supports a defined semantic scope. It does not claim to answer every possible natural-language or financial question.

## Query Safety and Grounding

Before execution, the backend checks that the generated SQL:

- Contains exactly one read-only `SELECT` statement.
- Uses the allowed BigQuery table and physical columns.
- Does not use DML, DDL, joins, subqueries, CTEs, window functions, or `SELECT *`.
- Uses named parameters for user-provided values.
- Defines exactly the parameters used by SQL.
- Matches the validated metrics, dimensions, filters, time range, sorting, and limit in the Query Plan.
- Uses the negative-cost scope when the negative billed cost metric is requested.
- Stays within the configured BigQuery byte limit.

After execution, the backend checks that:

- Returned columns match the Query Plan.
- Row counts satisfy the configured and planned limits.
- Metric values are finite numbers or `null`.
- Dynamic Evidence contains only the verified query result.
- Final answer references point to real evidence rows and columns.
- Financial numbers in the answer exist in the question or referenced evidence.

## RAG Grounding

The RAG path:

- Reads text-based PDF documents.
- Keeps the source filename, page number, source URL, and Chunk ID.
- Creates document embeddings with a Gemini embedding model.
- Stores the RAG index locally as a generated runtime artifact.
- Converts the user question into an embedding.
- Uses cosine similarity to retrieve the closest chunks.
- Sends only the retrieved context to Gemini.
- Instructs Gemini not to use outside knowledge.
- Returns `not_found` when the context is insufficient.
- Displays the retrieved source metadata with the answer.

Scanned or image-only PDFs require OCR and are outside the current MVP.

## Project Structure

```text
.
├── data/
│   ├── raw/
│   ├── processed/
│   ├── rag_documents/
│   └── rag_index/
├── queries/
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
│   ├── finops_query/
│   │   ├── models.py
│   │   ├── schema.py
│   │   ├── query_service.py
│   │   ├── bigquery_service.py
│   │   ├── answer_service.py
│   │   └── assistant_service.py
│   └── finops_rag/
│       ├── document_loader.py
│       ├── retriever.py
│       └── rag_service.py
├── finops_api.py
├── main.py
├── run_cloud_pipeline.py
├── run_finops_query_generation_live.py
├── run_finops_rag.py
├── run_queries.py
├── .env.example
├── .gitignore
└── requirements.txt
```

PDF documents and the generated local RAG index are excluded from Git. The repository keeps the code and configuration needed to rebuild the index.

## Requirements

- Python 3.10 or later.
- A Google Cloud project with BigQuery enabled.
- Google Application Default Credentials or equivalent configured BigQuery credentials.
- A Gemini API key.
- Text-based PDF documentation for the RAG path.

## Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install the direct project dependencies:

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

Add the real Gemini API key only to `.env`. Never commit `.env` or credential files.

## Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API key | Keep secret |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project ID | `data-ai-assistant-training` |
| `FINOPS_DATASET_ID` | BigQuery dataset | `cloud_finops` |
| `FINOPS_TABLE_ID` | Published billing table | `billing_pipeline_day2` |
| `BIGQUERY_LOCATION` | BigQuery location | `US` |
| `GEMINI_MODEL` | Gemini answer model | `gemini-3.5-flash-lite` |
| `FINOPS_EXECUTE_QUERIES` | Enables real BigQuery execution | `false` or `true` |
| `FINOPS_MAXIMUM_BYTES_BILLED` | Maximum bytes allowed per query | `104857600` |
| `FINOPS_MAX_RESULT_ROWS` | Maximum accepted result rows | `100` |
| `FINOPS_QUERY_TIMEOUT_SECONDS` | BigQuery execution timeout | `60` |
| `RAG_EMBEDDING_MODEL` | Gemini embedding model | `gemini-embedding-001` |
| `RAG_TOP_K` | Number of retrieved chunks | `3` |
| `RAG_REBUILD_INDEX` | Rebuilds the local RAG index | `false` or `true` |

Keep `FINOPS_EXECUTE_QUERIES=false` when checking Query generation and Dry Run only.

Set it to `true` only when real BigQuery execution is intended.

Set `RAG_REBUILD_INDEX=true` after adding, removing, or changing PDF documents. After the new index is built successfully, return it to `false` to reuse the saved index.

## Running the Data Pipeline

Run the local data preparation path:

```bash
python main.py
```

Run the cloud pipeline without publishing:

```bash
python run_cloud_pipeline.py --local-only
```

Run the cloud pipeline with BigQuery publishing:

```bash
python run_cloud_pipeline.py
```

Run the analytical SQL files:

```bash
python run_queries.py
```

## Running the FinOps Query CLI

Enable real execution when required:

```env
FINOPS_EXECUTE_QUERIES=true
```

Run:

```bash
python run_finops_query_generation_live.py
```

Then enter an English financial question.

Example:

```text
What was the total billed cost for AWS from September 1, 2024 to September 30, 2024?
```

## Running the FastAPI Interface

Start the server:

```bash
python -m uvicorn finops_api:app --reload
```

Open:

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

FastAPI and the Query CLI use the same Assistant Service and return the same core result contract.

The current RAG path is intentionally exposed through CLI only.

## Running the FinOps RAG CLI

Place text-based PDF documents inside:

```text
data/rag_documents/
```

Register their official source URLs in the RAG runner configuration.

When building or rebuilding the index:

```env
RAG_REBUILD_INDEX=true
```

Run:

```bash
python run_finops_rag.py
```

After a successful index build, change:

```env
RAG_REBUILD_INDEX=false
```

Future questions will reuse the saved local index.

Example supported question:

```text
What is FOCUS?
```

Example question not supported by theoretical documentation:

```text
What was the total AWS billed cost in September 2024?
```

For unsupported evidence, the RAG assistant should return a `not_found` result instead of inventing an answer.

## Example Query Questions

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

## Main BigQuery Resources

- Project: `data-ai-assistant-training`
- Dataset: `cloud_finops`
- Location: `US`
- Schema reference table: `billing_cleaned`
- Staging table: `billing_staging`
- Published table: `billing_pipeline_day2`

## Current Limitations

- The Query assistant supports only the declared FinOps semantic schema.
- Complex joins, subqueries, CTEs, and window functions are outside the current SQL subset.
- Questions requiring unavailable fields or business rules return clarification or unsupported states.
- The RAG path currently supports text-based PDF documents only.
- Scanned PDFs require OCR, which is not part of the current MVP.
- RAG is currently available through CLI only.
- Automatic routing between Query and RAG is not implemented yet.
- Tools and optional LangChain integration are planned for a later stage.
- Gemini quotas, BigQuery permissions, and cloud costs depend on the configured Google accounts and services.

## Dataset Note

The repository uses a small synthetic billing dataset for training and demonstration.

It contains examples for AWS, Microsoft, and Oracle and must not be treated as production financial data.

## Repository Safety

Do not commit:

- `.env`
- API keys
- Google Cloud credential JSON files
- Local databases
- Local PDF documents
- Generated RAG index files
- Generated runtime artifacts unless intentionally required

Commit `.env.example` only, with placeholder or non-secret values.