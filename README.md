# Data-AI Assistant — FinOps MVP

A beginner-friendly Data and AI assistant for cloud billing analysis.

The project combines four focused capabilities:

1. A repeatable data pipeline for validating, cleaning, profiling, storing, and publishing cloud billing data.
2. A FinOps Query assistant that converts English financial questions into validated GoogleSQL and executes them in BigQuery.
3. A FinOps RAG assistant that answers documentation questions from trusted PDF sources.
4. A unified Router that chooses the correct path and exposes one shared response through CLI and FastAPI.

## Project Status

The current MVP supports:

- Local and BigQuery cloud billing data processing.
- Data validation, cleaning, profiling, and reconciliation.
- Gemini-generated Query Plans and SQL Proposals.
- Structured Pydantic contracts for model output.
- Local Query Plan, SQL safety, and SQL semantic validation.
- BigQuery named parameters.
- BigQuery Dry Run with configurable cost limits.
- Optional real BigQuery execution.
- Query result validation.
- Dynamic Evidence generation.
- Evidence-grounded final financial answers.
- PDF loading and page-level text extraction.
- Configurable RAG chunking with source metadata.
- Gemini document and question embeddings.
- Local RAG index storage and reuse.
- Cosine similarity retrieval.
- Grounded RAG answers with visible sources.
- A Gemini Router for Query, RAG, clarification, and unsupported states.
- One unified Assistant Service shared by CLI and FastAPI.
- Basic console logging for route, status, duration, and source count.

The MVP is functionally complete. Future work may add a frontend, deployment, authentication, OCR, or optional orchestration libraries, but these are not required for the current beginner MVP.

## Unified Architecture

```text
User Question
  -> Unified CLI or FastAPI
  -> FinOps Assistant Service
  -> Gemini Router
      -> Query Tool
          -> FinOps Query Assistant
          -> BigQuery
          -> Dynamic Evidence
          -> Grounded Financial Answer
      -> RAG Tool
          -> Local RAG Index
          -> Retrieved PDF Chunks
          -> Grounded Documentation Answer
      -> Needs Clarification
      -> Unsupported
  -> Unified Result
  -> CLI or FastAPI
```

The Router only classifies the question. It does not execute SQL, search documents, or generate the final domain answer.

The Query and RAG tools are lightweight wrappers around the existing services. Their purpose is to convert different internal results into one shared response shape.

## Unified Result Contract

All unified requests return:

```json
{
  "status": "answered",
  "route": "query",
  "answer": "The total effective cost for Microsoft is 1.98.",
  "sources": [
    {
      "source_type": "bigquery",
      "source_name": "project.dataset.table",
      "location": "US"
    }
  ]
}
```

Possible routes:

- `query`
- `rag`
- `needs_clarification`
- `unsupported`

The business `status` is separate from the HTTP status code.

## Data Pipeline

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

## FinOps Query Journey

```text
Financial Question
  -> Safe BigQuery Schema Context
  -> Gemini Query Generation
  -> Query Plan + SQL Proposal
  -> Pydantic Contract Validation
  -> Query Plan Validation
  -> SQL Safety Validation
  -> SQL Semantic Validation
  -> BigQuery Parameters
  -> BigQuery Dry Run
  -> Optional Real Execution
  -> Query Result Validation
  -> Dynamic Evidence
  -> Gemini Final Answer
  -> Final Answer Validation
```

Gemini proposes the Query Plan and SQL, but the backend owns validation, execution decisions, BigQuery access, and evidence.

### Query Files

| File | Responsibility |
|---|---|
| `models.py` | Defines the Pydantic contracts used across the Query journey. |
| `schema.py` | Reads the real BigQuery schema and builds a safe semantic context. |
| `query_service.py` | Performs Query generation and validates the Query Plan and SQL. |
| `bigquery_service.py` | Binds parameters, performs Dry Run and execution, validates results, and builds Dynamic Evidence. |
| `answer_service.py` | Produces and validates the evidence-grounded final answer. |
| `assistant_service.py` | Coordinates the complete Query journey and returns one shared result. |

### Supported Metrics

- `billed_cost`
- `effective_cost`
- `negative_billed_cost`

### Supported Dimensions

- `provider`
- `service`
- `currency`

### Supported Operations

- Sum
- Average
- Minimum
- Maximum
- Supported count operations
- Dimension filters
- Date ranges
- Grouping
- Ascending and descending sorting
- Result limits

### Query Safety

Before execution, the backend checks that SQL:

- Contains one read-only `SELECT` statement.
- Uses the allowed BigQuery table.
- Uses only allowed physical columns.
- Does not use DML or DDL.
- Does not use unsupported joins, CTEs, subqueries, or window functions.
- Does not use `SELECT *`.
- Uses named parameters for user values.
- Defines exactly the parameters referenced by SQL.
- Matches the metrics, dimensions, filters, time range, sorting, and limit in the Query Plan.
- Applies the negative-cost condition when required.
- Remains within the configured BigQuery byte limit.

After execution, the backend checks that:

- Returned columns match the Query Plan.
- Row counts stay within the allowed limit.
- Metric values are finite numbers or `null`.
- Dynamic Evidence contains only the verified result.
- Evidence references point to real rows and columns.
- Financial numbers in the final answer exist in the question or referenced evidence.

## FinOps RAG Journey

```text
PDF Documents
  -> Page Text Extraction
  -> Text Normalization
  -> Chunking with Metadata
  -> Document Embeddings
  -> Local RAG Index
  -> Question Embedding
  -> Cosine Similarity
  -> Top K Chunks
  -> Grounded Gemini Answer
  -> Answer with Sources
```

The complete PDFs are not sent to Gemini. Only the most relevant retrieved chunks are included in the answer prompt.

Each retrieved source may contain:

- PDF filename
- Page number
- Chunk ID
- Official source URL
- Similarity score

If the retrieved context does not contain enough evidence, the RAG assistant returns `not_found` instead of using outside knowledge.

Scanned or image-only PDFs require OCR and are outside the current MVP.

## Router and Tool Layer

The unified assistant uses three small components:

| Component | Responsibility |
|---|---|
| `router.py` | Classifies a question as Query, RAG, clarification, or unsupported. |
| `service.py` | Calls the selected tool and returns one unified result. |
| Query Tool | Wraps the existing Query Assistant Service. |
| RAG Tool | Wraps the existing RAG Assistant Service. |

The tools do not duplicate the internal Query or RAG logic.

## Model Calls

When using the unified assistant:

### Query Question

1. Router call selects `query`.
2. Query generation call returns the Query Plan and SQL Proposal.
3. Final answer call converts Dynamic Evidence into a natural-language answer.

### RAG Question

1. Router call selects `rag`.
2. The embedding model converts the question to a vector.
3. The answer model creates the grounded answer from retrieved chunks.

Embedding generation is separate from natural-language answer generation.

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
│   ├── finops_assistant/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   └── service.py
│   ├── finops_query/
│   │   ├── models.py
│   │   ├── schema.py
│   │   ├── query_service.py
│   │   ├── bigquery_service.py
│   │   ├── answer_service.py
│   │   └── assistant_service.py
│   └── finops_rag/
│       ├── __init__.py
│       ├── document_loader.py
│       ├── retriever.py
│       ├── rag_service.py
│       └── assistant_service.py
├── finops_api.py
├── main.py
├── run_cloud_pipeline.py
├── run_finops_query_generation_live.py
├── run_finops_rag.py
├── run_finops_assistant.py
├── run_queries.py
├── .env.example
├── .gitignore
└── requirements.txt
```

PDF documents and the generated local RAG index are excluded from Git. The repository contains the code and configuration needed to rebuild the index.

## Requirements

- Python 3.11 or later is recommended.
- A Google Cloud project with BigQuery enabled.
- Google Application Default Credentials or equivalent BigQuery credentials.
- A Gemini API key.
- Text-based PDF documents for the RAG path.

Python 3.10 may still run, but recent Google packages can display support warnings.

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

Add the real Gemini API key only to `.env`. Never commit `.env` or credential files.

## Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API key | Keep secret |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project ID | `data-ai-assistant-training` |
| `FINOPS_DATASET_ID` | BigQuery dataset | `cloud_finops` |
| `FINOPS_TABLE_ID` | Published billing table | `billing_pipeline_day2` |
| `BIGQUERY_LOCATION` | BigQuery location | `US` |
| `GEMINI_MODEL` | Gemini answer and Router model | `gemini-3.5-flash-lite` |
| `FINOPS_EXECUTE_QUERIES` | Enables real BigQuery execution | `false` or `true` |
| `FINOPS_MAXIMUM_BYTES_BILLED` | Maximum bytes allowed per query | `104857600` |
| `FINOPS_MAX_RESULT_ROWS` | Maximum result rows | `100` |
| `FINOPS_QUERY_TIMEOUT_SECONDS` | Query timeout in seconds | `60` |
| `RAG_EMBEDDING_MODEL` | Gemini embedding model | `gemini-embedding-001` |
| `RAG_TOP_K` | Number of retrieved chunks | `3` |
| `RAG_REBUILD_INDEX` | Rebuilds the local RAG index | `false` or `true` |

Keep `FINOPS_EXECUTE_QUERIES=false` when checking Query generation and Dry Run only.

Set it to `true` only when real BigQuery execution is intended.

Set `RAG_REBUILD_INDEX=true` after adding, removing, or changing PDF documents. Return it to `false` after a successful rebuild.

## Running the Data Pipeline

Run local preparation:

```bash
python main.py
```

Run the cloud pipeline without publishing:

```bash
python run_cloud_pipeline.py --local-only
```

Run with BigQuery publishing:

```bash
python run_cloud_pipeline.py
```

Run the analytical SQL files:

```bash
python run_queries.py
```

## Running the Query CLI

For real execution:

```env
FINOPS_EXECUTE_QUERIES=true
```

Run:

```bash
python run_finops_query_generation_live.py
```

Example:

```text
What are the top 5 services by billed cost for AWS?
```

## Running the RAG CLI

Place text-based PDF files inside:

```text
data/rag_documents/
```

Register their official URLs in:

```text
src/finops_rag/assistant_service.py
```

To rebuild the index:

```env
RAG_REBUILD_INDEX=true
```

Run:

```bash
python run_finops_rag.py
```

After the build succeeds:

```env
RAG_REBUILD_INDEX=false
```

Example:

```text
What is FOCUS?
```

## Running the Unified CLI

Run:

```bash
python run_finops_assistant.py
```

Financial example:

```text
What is the total effective cost for Microsoft?
```

Expected route:

```text
query
```

Documentation example:

```text
What is FOCUS?
```

Expected route:

```text
rag
```

Ambiguous example:

```text
What is the cost?
```

Expected route:

```text
needs_clarification
```

Outside-scope example:

```text
Write a poem.
```

Expected route:

```text
unsupported
```

## Running FastAPI

Start the server:

```bash
python -m uvicorn finops_api:app --reload
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

Available endpoints:

- `GET /health`
- `POST /finops/query`
- `POST /finops/assistant`

The unified endpoint is:

```text
POST /finops/assistant
```

Example request:

```json
{
  "question": "What is FOCUS?"
}
```

Request validation errors return HTTP `422`.

Unexpected Gemini, BigQuery, or RAG failures return HTTP `500` with a generic public message. Detailed error information remains in the server log.

A successful HTTP request returns `200`, while the JSON business status explains whether the request was answered, unsupported, ambiguous, or not supported by available evidence.

The root address can return `404 Not Found` because no `/` endpoint is defined. This does not mean the server failed. `/docs` and the declared endpoints remain available.

## Logging

The unified service writes concise console logs containing:

- Selected route
- Final business status
- Execution duration
- Number of returned sources

The logs do not include API keys, credentials, complete document text, or full user answers.

## Demo Questions

### Financial Questions

1. `What is the total billed cost for AWS?`
2. `What are the top 5 services by billed cost for AWS?`
3. `What is the total effective cost for Microsoft?`
4. `What is the negative billed cost for Microsoft?`
5. `What was the total billed cost for AWS from September 1, 2024 to September 30, 2024?`

### Documentation Questions

6. `What is FOCUS?`
7. `Why does FOCUS normalize cost and usage data?`
8. `What types of technology billing data does FOCUS cover?`

### Router States

9. `What is the cost?`
10. `Write a poem.`

Exact natural-language wording can vary, but the route, business status, and evidence must remain correct.

## Current Limitations

- The Query assistant supports only the declared FinOps semantic schema.
- Complex joins, CTEs, subqueries, and window functions are outside the supported SQL subset.
- Questions requiring unavailable fields or business rules may return clarification or unsupported states.
- The RAG path supports text-based PDFs only.
- Scanned PDFs require OCR.
- The Router uses an LLM and can occasionally misclassify an ambiguous question.
- The project does not currently include a React frontend.
- Production authentication, rate limiting, monitoring infrastructure, and cloud deployment are outside the current MVP.
- LangChain and LangGraph are not required by the current implementation and may be explored later as learning extensions.
- Gemini quotas, BigQuery permissions, and cloud costs depend on the configured accounts and services.

## Dataset Note

The repository uses a small synthetic billing dataset for training and demonstration.

It contains examples for AWS, Microsoft, and Oracle and must not be treated as production financial data.

## Repository Safety

Do not commit:

- `.env`
- API keys
- Google Cloud credential files
- Local databases
- Local PDF documents
- Generated RAG index files
- Generated runtime artifacts

Commit `.env.example` only with placeholder or non-secret values.