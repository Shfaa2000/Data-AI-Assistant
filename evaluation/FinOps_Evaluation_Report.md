# FinOps Assistant — Manual Baseline Evaluation Report

**Evaluation date:** 21 October 2026  
**Evaluation type:** Manual baseline and exploratory testing  
**Project stage:** Working MVP before evaluation-driven improvements

## 1. Evaluation Goal

The goal was to test the current assistant with varied questions, compare
financial answers against independent BigQuery reference queries, and record
real failure patterns before changing the implementation.

This evaluation intentionally uses a simple manual approach. It does not build
an automated evaluation platform. The current goal is to discover issues,
understand their causes, and create a trustworthy baseline.

## 2. Tested Environment

- Python: 3.10.8
- Gemini answer/query model: `gemini-3.5-flash-lite`
- Embedding model: `gemini-embedding-001`
- BigQuery location: `US`
- BigQuery table: `data-ai-assistant-training.cloud_finops.billing_pipeline_day2`
- RAG index size: 99 chunks
- RAG Top K: 3
- Interfaces checked: Query CLI, unified CLI, manual BigQuery runner
- FastAPI: user confirmed that the endpoint is working; detailed response logs
  were not included in this report.
- Git commit: e897ca2

## 3. Evaluation Method

For financial questions, the system result was checked in two stages:

1. An independent reference SQL query was executed directly on BigQuery.
2. Its result was compared with `dynamic_evidence.rows`.
3. The final natural-language answer was compared with Dynamic Evidence.

For RAG questions, the selected route, final status, answer meaning, and
document sources were reviewed.

For unsupported and unclear questions, the test checked that the system stopped
without executing an unsafe or unsupported BigQuery query.

## 4. Result Summary

| Test area | Executed | Expected result | Unexpected result |
|---|---:|---:|---:|
| Independent reference SQL | 13 | 13 | 0 |
| Query pipeline | 13 | 8 | 5 |
| Unified assistant | 16 | 15 | 1 |
| FastAPI smoke test | Confirmed by user | Working | No failure reported |

The rows above should not be combined into one global accuracy percentage
because some reference queries validate the same questions that were executed
through the Query pipeline.

## 5. Successful Financial Checks

The following tested patterns completed successfully:

- Total negative billed cost for Microsoft.
- Total effective cost for Microsoft.
- Top three Microsoft services by effective cost.
- Top two providers by billed cost.
- Average AWS billed cost.
- Maximum billed cost by provider.
- Top five AWS services by billed cost during September 2024.
- Total billed cost in USD.

Examples of verified results:

- Microsoft effective cost: BigQuery and Dynamic Evidence returned
  `1.9765141858600002`; the final answer correctly rounded it to `1.98`.
- Microsoft negative billed cost: the evidence returned `-0.1619713001`;
  the final answer correctly rounded it to `-0.16`.
- AWS average billed cost: the reference result was
  `0.019115327620382167`; the final answer correctly presented `0.02`.
- The Top 3 Microsoft services and Top 2 providers matched the independent
  BigQuery reference results.

These cases show that when the Query pipeline completes, the final answer is
grounded in the returned BigQuery evidence and uses acceptable rounding.

## 6. Discovered Issues

### Issue 1 — Grouped SQL Sometimes Omits LIMIT

**Severity:** Medium  
**Stage:** Query generation / semantic validation

Affected questions:

- What is the total billed cost by service?
- What is the total billed cost by provider?
- What is the total negative billed cost for each provider?
- What is the total billed cost by currency?

Observed error:

```text
SqlValidationError: Grouped queries must include LIMIT.
```

The independent reference SQL queries executed successfully, so the data and
BigQuery connection were not the problem. Gemini created grouped SQL without
the `LIMIT` required by the local safety policy. The Validator correctly
stopped the query before execution.

**General correction:** Strengthen the query-generation rule so every plan with
one or more dimensions must generate `LIMIT <plan.limit>`, even when the user
does not explicitly ask for Top N. Keep the Validator because it protects
BigQuery from unbounded grouped results.

**Retest:** Run the four affected questions after changing the prompt. Do not
add a separate special case for each question.

### Issue 2 — One TIMESTAMP Format Was Not Accepted

**Severity:** Medium  
**Stage:** BigQuery parameter conversion

Affected question:

- What was the total billed cost for AWS from September 1, 2024 to
  September 30, 2024?

Observed error:

```text
ValueError: Invalid isoformat string: '2024-09-01 00:00:00 UTC'
```

The reference SQL executed successfully and returned
`18.006638618399986`. A similar Top 5 question also succeeded because Gemini
returned the timestamp without the `UTC` suffix. Therefore, the problem is not
the date range or BigQuery data; it is inconsistent timestamp text returned by
the model.

**General correction:** Normalize common UTC representations before calling
`datetime.fromisoformat`, and also instruct Gemini to return strict ISO-8601
timestamps such as `2024-09-01T00:00:00Z`.

Suggested normalization:

```python
timestamp_text = str(value).strip()

if timestamp_text.endswith(" UTC"):
    timestamp_text = (
        timestamp_text[:-4]
        + "+00:00"
    )

timestamp_text = timestamp_text.replace(
    "Z",
    "+00:00",
)

parsed_value = datetime.fromisoformat(
    timestamp_text
)
```

**Retest:** Run the failed total-cost date question and at least one other date
question after the correction.

### Issue 3 — One Supported RAG Question Returned not_found

**Severity:** Medium  
**Stage:** RAG retrieval or evidence sufficiency

Affected question:

- Why is cultural alignment important when implementing FinOps?

Observed behavior:

- Router correctly selected `rag`.
- The saved index loaded successfully with 99 chunks.
- The final status was `not_found`.
- Other related Azure FinOps questions were answered successfully.

Because `retrieve_chunks` always returns the Top 3 records, this result most
likely means the retrieved chunks did not contain enough direct evidence and
Gemini returned `INSUFFICIENT_EVIDENCE`.

**General investigation:** Inspect the three retrieved chunks and their scores.
If the relevant paragraph is ranked just below them, test `RAG_TOP_K=5` or
improve chunking. Do not force Gemini to answer without evidence.
6. Keep the cultural-alignment RAG case as a documented retrieval
issue; increasing Top K from 3 to 5 did not solve it.

### Issue 4 — Unsupported Query Displays BigQuery as a Source

**Severity:** Low  
**Stage:** Unified result formatting

For the annual-budget question, the Query tool correctly returned
`unsupported`, but the unified result still listed the allowed BigQuery table
as a source even though no SQL was executed.

**General correction:** Add the BigQuery source only when execution or a valid
Dry Run actually occurred. Do not attach it to `unsupported` or
`needs_clarification` results.

## 7. Warnings That Did Not Break the Tests

- Python 3.10 support warnings from Google libraries.
- The Gemini SDK warning about direct automatic function calling.

These warnings did not cause the recorded functional failures. A later cleanup
can upgrade Python to 3.11 or newer and review the Gemini SDK call style.

## 8. Issue Classification Guide

| Observed result | Most likely stage |
|---|---|
| Wrong route | Router |
| Correct route but wrong intent | Query Plan prompt |
| Correct plan but invalid or mismatched SQL | SQL generation or semantic validation |
| Reference SQL and Dynamic Evidence differ | SQL filters, aggregation, dates, or parameters |
| Evidence is correct but final answer differs | Answer generation or answer validation |
| RAG retrieves unrelated chunks | Retriever, embeddings, or chunking |
| RAG chunks are relevant but answer is wrong | RAG prompt or generation |
| Reference question itself is unclear | Test-case design |

## 9. Recommended Next Steps

1. Keep this report as the baseline before fixes.
2. Record the current Git commit hash.
3. Apply the general LIMIT prompt correction.
4. Normalize UTC timestamp strings in the BigQuery parameter converter.
5. Retest only the five failed Query cases first.
6. Inspect or retest the cultural-alignment RAG case with more retrieved chunks.
7. Remove the misleading BigQuery source from unsupported unified responses.
8. Add the after-fix results to this report instead of deleting the original
   baseline findings.

## 10. Conclusion

The evaluation achieved its main goal: it confirmed that the core Query and RAG
flows work and discovered concrete failures that were not visible during the
initial happy-path tests. The failures are concentrated in three general areas:
grouped-query limits, timestamp normalization, and one RAG retrieval case.

The project does not need a large automated evaluation platform at this stage.
The current manual baseline, independent reference SQL catalog, and focused
retests are sufficient for a junior MVP and provide clear evidence of how the
system behaves and where it should improve.
