import pytest

from src.narrative_grounding import (
    NarrativeGroundingError,
    validate_narrative_grounding,
)
from src.narrative_response import NarrativeResponse


def make_payload() -> dict:
    """إنشاء Payload مالية ثابتة للاختبارات."""

    return {
        "provider": "AWS",
        "service": "Amazon Elastic Compute Cloud",
        "currency": "USD",
        "billed_cost": 16.041693050500022,
        "effective_cost": 13.0,
        "negative_billed_cost": -2.6137,
        "limitations": [
            "No utilization metrics are included.",
        ],
    }


def make_answered(
    answer: str,
    used_metrics: list[str],
) -> NarrativeResponse:
    """إنشاء Narrative مدعومة للاختبار."""

    return NarrativeResponse(
        status="answered",
        answer=answer,
        used_metrics=used_metrics,
        limitations=[
            "No utilization metrics are included.",
        ],
        unsupported_reason=None,
    )


def make_unsupported(
    answer: str,
) -> NarrativeResponse:
    """إنشاء Narrative غير مدعومة للاختبار."""

    return NarrativeResponse(
        status="unsupported",
        answer=answer,
        used_metrics=[],
        limitations=[
            "No utilization metrics are included.",
        ],
        unsupported_reason=(
            "The payload does not contain "
            "utilization metrics."
        ),
    )


def test_accepts_exact_payload_values():
    narrative = make_answered(
        answer=(
            "قيمة Billed Cost هي "
            "16.041693050500022 USD، "
            "وقيمة Effective Cost هي 13.0 USD."
        ),
        used_metrics=[
            "billed_cost",
            "effective_cost",
        ],
    )

    validate_narrative_grounding(
        payload=make_payload(),
        narrative=narrative,
    )


def test_accepts_negative_payload_value():
    narrative = make_answered(
        answer=(
            "قيمة Negative Billed Cost "
            "هي -2.6137 USD."
        ),
        used_metrics=[
            "negative_billed_cost",
        ],
    )

    validate_narrative_grounding(
        payload=make_payload(),
        narrative=narrative,
    )


def test_rejects_invented_financial_number():
    narrative = make_answered(
        answer="قيمة Billed Cost هي 99.0 USD.",
        used_metrics=[
            "billed_cost",
        ],
    )

    with pytest.raises(
        NarrativeGroundingError
    ):
        validate_narrative_grounding(
            payload=make_payload(),
            narrative=narrative,
        )


def test_rejects_used_metric_missing_from_answer():
    narrative = make_answered(
        answer=(
            "قيمة Billed Cost هي "
            "16.041693050500022 USD."
        ),
        used_metrics=[
            "billed_cost",
            "effective_cost",
        ],
    )

    with pytest.raises(
        NarrativeGroundingError
    ):
        validate_narrative_grounding(
            payload=make_payload(),
            narrative=narrative,
        )


def test_accepts_unsupported_without_numbers():
    narrative = make_unsupported(
        answer=(
            "لا تكفي البيانات لإثبات "
            "أن خدمة EC2 مستغلة بالكامل."
        ),
    )

    validate_narrative_grounding(
        payload=make_payload(),
        narrative=narrative,
    )


def test_rejects_unsupported_with_new_number():
    narrative = make_unsupported(
        answer=(
            "لا يمكن إثبات أن الخدمة "
            "مستغلة بنسبة 100 بالمئة."
        ),
    )

    with pytest.raises(
        NarrativeGroundingError
    ):
        validate_narrative_grounding(
            payload=make_payload(),
            narrative=narrative,
        )