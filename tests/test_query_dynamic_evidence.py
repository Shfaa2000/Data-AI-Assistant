from types import SimpleNamespace

from src.finops_query.query_bigquery_execution import (
    QueryExecutionResult,
)
from src.finops_query.query_dynamic_evidence import (
    build_dynamic_query_evidence,
)

def test_builds_small_dynamic_evidence():
    query_plan = {
        "status": "ready",
        "intent": "Calculate total billed cost for AWS.",
        "metrics": [
            {
                "name": "billed_cost",
                "aggregation": "sum",
            }
        ],
        "dimensions": [],
        "filters": [
            {
                "column": "provider",
                "operator": "eq",
                "value": "AWS",
            }
        ],
        "limit": 100,
    }

    result = QueryExecutionResult(
        columns=["billed_cost"],
        rows=[{"billed_cost": 125.50}],
        total_rows=1,
        total_bytes_processed=1_000_000,
        job_id="job-1",
        location="US",
    )

    evidence = build_dynamic_query_evidence(
        user_question="What is the total billed cost for AWS?",
        query_plan=query_plan,
        source_table=(
            "data-ai-assistant-training."
            "cloud_finops.billing_pipeline_day2"
        ),
        result=result,
    )

    assert evidence.evidence_type == "bigquery_query_result"
    assert evidence.row_count == 1
    assert evidence.rows == [{"billed_cost": 125.50}]
    assert evidence.source_table.endswith(
        "billing_pipeline_day2"
    )

    evidence_dict = evidence.model_dump()

    assert "credentials" not in evidence_dict
    assert "api_key" not in evidence_dict
    assert "physical_schema" not in evidence_dict