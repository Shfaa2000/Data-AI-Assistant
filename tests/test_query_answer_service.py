import json
from types import SimpleNamespace

from src.finops_query.query_answer import (
    QueryAnswerStatus,
)
from src.finops_query.query_answer_service import (
    generate_finops_answer,
)
from src.finops_query.query_dynamic_evidence import (
    DynamicQueryEvidence,
)


class FakeInteractions:
    def __init__(self):
        self.last_call = None

    def create(
        self,
        **kwargs,
    ):
        self.last_call = kwargs

        return SimpleNamespace(
            output_text=json.dumps(
                {
                    "status": "answered",
                    "answer": (
                        "The total billed cost "
                        "for AWS is 123.45."
                    ),
                    "evidence_references": [
                        {
                            "row_index": 0,
                            "columns": [
                                "billed_cost"
                            ],
                        }
                    ],
                }
            )
        )


class FakeGeminiClient:
    def __init__(self):
        self.interactions = (
            FakeInteractions()
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
            "filters": [],
            "limit": 100,
        },
        source_table=(
            "project.dataset.billing_table"
        ),
        columns=["billed_cost"],
        rows=[
            {
                "billed_cost": 123.45
            }
        ],
        row_count=1,
        total_bytes_processed=1_000_000,
        job_id="job-1",
        location="US",
    )


def test_generates_and_validates_final_answer():
    client = FakeGeminiClient()

    answer = generate_finops_answer(
        client=client,
        evidence=make_evidence(),
        model_name="fake-model",
    )

    assert (
        answer.status
        == QueryAnswerStatus.ANSWERED
    )
    assert "123.45" in answer.answer

    call = client.interactions.last_call

    assert call["model"] == "fake-model"

    assert (
        call["response_format"]["type"]
        == "text"
    )

    assert (
        call["response_format"]["mime_type"]
        == "application/json"
    )

    assert (
        "schema"
        in call["response_format"]
    )