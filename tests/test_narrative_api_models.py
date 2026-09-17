import pytest
from pydantic import ValidationError

from src.narrative_api_models import (
    NarrativeEnvelopeResponse,
    NarrativeRequest,
)


def make_envelope() -> dict:
    """إنشاء Envelope تجريبية صالحة لاختبار نموذج HTTP."""

    return {
        "provenance": {
            "evidence_id": "evidence-123",
            "pipeline_run_id": "run-123",
            "source_table": (
                "project.dataset.billing"
            ),
            "object_uri": (
                "local://finops-landing/billing.csv"
            ),
        },
        "execution": {
            "interaction_id": "interaction-123",
            "model_name": "gemini-3.6-flash",
            "interaction_status": "completed",
            "generated_at_utc": (
                "2026-09-15T08:00:00Z"
            ),
        },
        "narrative": {
            "status": "answered",
            "answer": (
                "قيمة Billed Cost موثقة "
                "في البيانات المرسلة."
            ),
            "used_metrics": [
                "billed_cost",
            ],
            "limitations": [
                "النتيجة تغطي الفترات المحملة فقط.",
            ],
            "unsupported_reason": None,
        },
    }


def test_request_accepts_valid_question():
    request = NarrativeRequest(
        question="  اشرح التكلفة.  "
    )

    assert request.question == "اشرح التكلفة."


@pytest.mark.parametrize(
    "question",
    [
        "",
        "   ",
        "\n\t",
    ],
)
def test_request_rejects_empty_question(
    question,
):
    with pytest.raises(ValidationError):
        NarrativeRequest(question=question)


def test_request_rejects_too_long_question():
    with pytest.raises(ValidationError):
        NarrativeRequest(question="س" * 1001)


def test_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        NarrativeRequest(
            question="اشرح التكلفة.",
            unexpected_field="not allowed",
        )


def test_envelope_response_accepts_valid_data():
    response = (
        NarrativeEnvelopeResponse.model_validate(
            make_envelope()
        )
    )

    assert (
        response.provenance.evidence_id
        == "evidence-123"
    )
    assert (
        response.execution.interaction_status
        == "completed"
    )
    assert response.narrative.status == "answered"


def test_envelope_response_rejects_missing_field():
    envelope = make_envelope()

    del envelope["provenance"]["object_uri"]

    with pytest.raises(ValidationError):
        NarrativeEnvelopeResponse.model_validate(
            envelope
        )