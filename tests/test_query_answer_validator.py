import pytest

from src.finops_query.query_answer import (
    EvidenceReference,
    FinOpsQueryAnswer,
    QueryAnswerStatus,
)
from src.finops_query.query_answer_validator import (
    QueryAnswerValidationError,
    validate_finops_answer,
)
from src.finops_query.query_dynamic_evidence import (
    DynamicQueryEvidence,
)


def make_evidence(
    rows=None,
):
    evidence_rows = (
        [{"billed_cost": 123.45}]
        if rows is None
        else rows
    )

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
        rows=evidence_rows,
        row_count=len(evidence_rows),
        total_bytes_processed=1_000_000,
        job_id="job-1",
        location="US",
    )


def make_valid_answer():
    return FinOpsQueryAnswer(
        status=QueryAnswerStatus.ANSWERED,
        answer=(
            "The total billed cost for AWS "
            "is 123.45."
        ),
        evidence_references=[
            EvidenceReference(
                row_index=0,
                columns=["billed_cost"],
            )
        ],
    )


def test_accepts_grounded_english_answer():
    validate_finops_answer(
        answer=make_valid_answer(),
        evidence=make_evidence(),
    )


def test_rejects_invented_number():
    answer = FinOpsQueryAnswer(
        status=QueryAnswerStatus.ANSWERED,
        answer=(
            "The total billed cost for AWS "
            "is 999.99."
        ),
        evidence_references=[
            EvidenceReference(
                row_index=0,
                columns=["billed_cost"],
            )
        ],
    )

    with pytest.raises(
        QueryAnswerValidationError
    ):
        validate_finops_answer(
            answer=answer,
            evidence=make_evidence(),
        )


def test_rejects_unknown_row():
    answer = FinOpsQueryAnswer(
        status=QueryAnswerStatus.ANSWERED,
        answer=(
            "The total billed cost for AWS "
            "is 123.45."
        ),
        evidence_references=[
            EvidenceReference(
                row_index=5,
                columns=["billed_cost"],
            )
        ],
    )

    with pytest.raises(
        QueryAnswerValidationError
    ):
        validate_finops_answer(
            answer=answer,
            evidence=make_evidence(),
        )


def test_rejects_unknown_column():
    answer = FinOpsQueryAnswer(
        status=QueryAnswerStatus.ANSWERED,
        answer=(
            "The total billed cost for AWS "
            "is 123.45."
        ),
        evidence_references=[
            EvidenceReference(
                row_index=0,
                columns=["total_cost"],
            )
        ],
    )

    with pytest.raises(
        QueryAnswerValidationError
    ):
        validate_finops_answer(
            answer=answer,
            evidence=make_evidence(),
        )


def test_rejects_arabic_answer():
    answer = FinOpsQueryAnswer(
        status=QueryAnswerStatus.ANSWERED,
        answer=(
            "إجمالي التكلفة هو 123.45."
        ),
        evidence_references=[
            EvidenceReference(
                row_index=0,
                columns=["billed_cost"],
            )
        ],
    )

    with pytest.raises(
        QueryAnswerValidationError
    ):
        validate_finops_answer(
            answer=answer,
            evidence=make_evidence(),
        )


def test_accepts_no_data_answer():
    answer = FinOpsQueryAnswer(
        status=QueryAnswerStatus.NO_DATA,
        answer=(
            "No matching financial data "
            "was found."
        ),
        evidence_references=[],
    )

    validate_finops_answer(
        answer=answer,
        evidence=make_evidence(
            rows=[]
        ),
    )


def test_accepts_null_metric_as_no_data():
    answer = FinOpsQueryAnswer(
        status=QueryAnswerStatus.NO_DATA,
        answer=(
            "No matching financial data "
            "was found."
        ),
        evidence_references=[],
    )

    validate_finops_answer(
        answer=answer,
        evidence=make_evidence(
            rows=[
                {
                    "billed_cost": None
                }
            ]
        ),
    )


def test_rejects_answered_status_without_data():
    answer = FinOpsQueryAnswer(
        status=QueryAnswerStatus.ANSWERED,
        answer=(
            "The total billed cost "
            "was calculated."
        ),
        evidence_references=[
            EvidenceReference(
                row_index=0,
                columns=["billed_cost"],
            )
        ],
    )

    with pytest.raises(
        QueryAnswerValidationError
    ):
        validate_finops_answer(
            answer=answer,
            evidence=make_evidence(
                rows=[
                    {
                        "billed_cost": None
                    }
                ]
            ),
        )

def test_accepts_financial_values_rounded_to_two_decimals():
    evidence = DynamicQueryEvidence(
        user_question=(
            "What are the top 5 services "
            "by billed cost for AWS?"
        ),
        intent=(
            "Retrieve the top 5 services "
            "by billed cost for AWS."
        ),
        query_plan={
            "status": "ready",
            "intent": (
                "Retrieve the top 5 services "
                "by billed cost for AWS."
            ),
            "metrics": [
                {
                    "name": "billed_cost",
                    "aggregation": "sum",
                }
            ],
            "dimensions": ["service"],
            "filters": [],
            "sort_by": "billed_cost",
            "sort_direction": "desc",
            "limit": 5,
        },
        source_table=(
            "project.dataset.billing_table"
        ),
        columns=[
            "service",
            "billed_cost",
        ],
        rows=[
            {
                "service": "Amazon EC2",
                "billed_cost": (
                    16.04169305050002
                ),
            },
            {
                "service": "Amazon RDS",
                "billed_cost": (
                    0.7532270852000001
                ),
            },
        ],
        row_count=2,
        total_bytes_processed=40_986,
        job_id="job-1",
        location="US",
    )

    answer = FinOpsQueryAnswer(
        status=QueryAnswerStatus.ANSWERED,
        answer=(
            "The top 5 services include "
            "Amazon EC2 at 16.04 and "
            "Amazon RDS at 0.75."
        ),
        evidence_references=[
            EvidenceReference(
                row_index=0,
                columns=[
                    "service",
                    "billed_cost",
                ],
            ),
            EvidenceReference(
                row_index=1,
                columns=[
                    "service",
                    "billed_cost",
                ],
            ),
        ],
    )

    validate_finops_answer(
        answer=answer,
        evidence=evidence,
    )