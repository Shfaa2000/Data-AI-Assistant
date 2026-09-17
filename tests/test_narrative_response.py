import pytest
from pydantic import ValidationError

from src.narrative_response import NarrativeResponse


def make_answered_payload() -> dict:
    """إنشاء جواب صحيح ومدعوم لإعادة استخدامه في الاختبارات."""

    return {
        "status": "answered",
        "answer": (
            "قيمة Billed Cost هي 16.041693، "
            "وقيمة Effective Cost هي 13.0."
        ),
        "used_metrics": [
            "billed_cost",
            "effective_cost",
        ],
        "limitations": [
            "The evidence covers only loaded billing periods.",
        ],
        "unsupported_reason": None,
    }


def make_unsupported_payload() -> dict:
    """إنشاء جواب صحيح لحالة لا تدعمها البيانات."""

    return {
        "status": "unsupported",
        "answer": (
            "لا تكفي البيانات الحالية لإثبات "
            "أن الخدمة مستغلة بالكامل."
        ),
        "used_metrics": [],
        "limitations": [
            "No utilization metrics are available.",
        ],
        "unsupported_reason": (
            "The supplied data does not include "
            "utilization metrics."
        ),
    }


def test_accepts_valid_answered_response():
    result = NarrativeResponse.model_validate(
        make_answered_payload()
    )

    assert result.status == "answered"
    assert result.used_metrics == [
        "billed_cost",
        "effective_cost",
    ]
    assert result.unsupported_reason is None


def test_accepts_valid_unsupported_response():
    result = NarrativeResponse.model_validate(
        make_unsupported_payload()
    )

    assert result.status == "unsupported"
    assert result.used_metrics == []
    assert result.unsupported_reason is not None


def test_rejects_unknown_status():
    payload = make_answered_payload()
    payload["status"] = "success"

    with pytest.raises(ValidationError):
        NarrativeResponse.model_validate(payload)


def test_rejects_empty_answer():
    payload = make_answered_payload()
    payload["answer"] = "   "

    with pytest.raises(ValidationError):
        NarrativeResponse.model_validate(payload)


def test_rejects_unknown_metric():
    payload = make_answered_payload()
    payload["used_metrics"] = [
        "billed_cost",
        "invented_metric",
    ]

    with pytest.raises(ValidationError):
        NarrativeResponse.model_validate(payload)


def test_answered_requires_used_metric():
    payload = make_answered_payload()
    payload["used_metrics"] = []

    with pytest.raises(ValidationError):
        NarrativeResponse.model_validate(payload)


def test_answered_rejects_unsupported_reason():
    payload = make_answered_payload()
    payload["unsupported_reason"] = (
        "This reason must not exist for answered."
    )

    with pytest.raises(ValidationError):
        NarrativeResponse.model_validate(payload)


def test_unsupported_requires_reason():
    payload = make_unsupported_payload()
    payload["unsupported_reason"] = None

    with pytest.raises(ValidationError):
        NarrativeResponse.model_validate(payload)


def test_rejects_empty_limitations():
    payload = make_answered_payload()
    payload["limitations"] = []

    with pytest.raises(ValidationError):
        NarrativeResponse.model_validate(payload)


def test_rejects_extra_field():
    payload = make_answered_payload()
    payload["confidence"] = 0.99

    with pytest.raises(ValidationError):
        NarrativeResponse.model_validate(payload)