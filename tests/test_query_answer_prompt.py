from src.finops_query.query_answer_prompt import (
    build_finops_answer_prompt,
    build_narrative_evidence_payload,
)
from src.finops_query.query_dynamic_evidence import (
    DynamicQueryEvidence,
)


def make_evidence():
    return DynamicQueryEvidence(
        user_question=(
            "What is the total billed cost "
            "for AWS?"
        ),
        intent=(
            "Calculate total billed cost "
            "for AWS."
        ),
        query_plan={
            "status": "ready",
            "intent": (
                "Calculate total billed cost "
                "for AWS."
            ),
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
        },
        source_table=(
            "project.dataset.billing_table"
        ),
        columns=[
            "billed_cost"
        ],
        rows=[
            {
                "billed_cost": 123.45
            }
        ],
        row_count=1,
        total_bytes_processed=1_000_000,
        job_id="job-secret-metadata",
        location="US",
    )


def test_payload_excludes_internal_execution_metadata():
    payload = (
        build_narrative_evidence_payload(
            make_evidence()
        )
    )

    assert "job_id" not in payload
    assert "location" not in payload
    assert (
        "total_bytes_processed"
        not in payload
    )

    assert payload["rows"] == [
        {
            "billed_cost": 123.45
        }
    ]


def test_prompt_contains_question_and_rows():
    prompt = build_finops_answer_prompt(
        make_evidence()
    )

    assert (
        "What is the total billed cost"
        in prompt
    )
    assert "123.45" in prompt
    assert "job-secret-metadata" not in prompt
    assert "Return only JSON" in prompt