import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import src.narrative_service as narrative_service


class FakeInteractions:
    """بديل محلي عن Gemini Interactions للاختبارات."""

    def __init__(
        self,
        output_text: str,
    ):
        self.output_text = output_text
        self.last_request = None

    def create(
        self,
        **kwargs,
    ):
        """حفظ الطلب وإرجاع Interaction تجريبية."""

        self.last_request = kwargs

        usage = SimpleNamespace(
            total_input_tokens=100,
            total_output_tokens=30,
            total_thought_tokens=200,
            total_tool_use_tokens=0,
            total_tokens=330,
        )

        steps = [
            SimpleNamespace(
                type="thought",
            ),
            SimpleNamespace(
                type="model_output",
            ),
        ]

        return SimpleNamespace(
            id="interaction-test",
            model=kwargs["model"],
            created=datetime(
                2026,
                9,
                14,
                tzinfo=timezone.utc,
            ),
            status="completed",
            usage=usage,
            steps=steps,
            output_text=self.output_text,
        )


class FakeClient:
    """Client وهمية تمنع الاتصال الحقيقي بـGemini."""

    def __init__(
        self,
        output_text: str,
    ):
        self.interactions = FakeInteractions(
            output_text
        )


def make_fake_evidence():
    """إنشاء Evidence تجريبية تكفي لاختبار Service."""

    return SimpleNamespace(
        evidence_id="evidence-test",
        pipeline_run_id="pipeline-test",
        source_table="project.dataset.table",
        object_uri="local://bucket/test.csv",
    )


def make_fake_payload() -> dict:
    """إنشاء Payload مالية ثابتة للاختبار."""

    return {
        "provider": "AWS",
        "service": (
            "Amazon Elastic Compute Cloud"
        ),
        "currency": "USD",
        "billed_cost": 16.041693050500022,
        "effective_cost": 13.0,
        "negative_billed_cost": -2.6137,
        "limitations": [
            "No utilization metrics are included.",
        ],
    }


def prepare_dependencies(
    monkeypatch,
):
    """استبدال قراءة الملفات بدوال محلية ثابتة."""

    evidence = make_fake_evidence()
    payload = make_fake_payload()

    monkeypatch.setattr(
        narrative_service,
        "load_verified_evidence",
        lambda *args, **kwargs: evidence,
    )

    monkeypatch.setattr(
        narrative_service,
        "build_service_narrative_payload",
        lambda loaded_evidence: payload,
    )

    return evidence, payload


def test_generates_answered_envelope_and_trace(
    monkeypatch,
):
    prepare_dependencies(monkeypatch)

    model_output = json.dumps(
        {
            "status": "answered",
            "answer": (
                "قيمة Billed Cost هي "
                "16.041693050500022 USD، "
                "وقيمة Effective Cost هي "
                "13.0 USD، ولذلك فإن "
                "Effective Cost هي الأقل."
            ),
            "used_metrics": [
                "billed_cost",
                "effective_cost",
            ],
            "limitations": [
                (
                    "No utilization metrics "
                    "are included."
                ),
            ],
            "unsupported_reason": None,
        },
        ensure_ascii=False,
    )

    client = FakeClient(
        model_output
    )

    question = (
        "اذكر Billed Cost وEffective Cost "
        "وحدد أيهما أقل."
    )

    envelope, trace = (
        narrative_service.generate_finops_narrative(
            client=client,
            user_question=question,
        )
    )

    assert (
        envelope["provenance"]["evidence_id"]
        == "evidence-test"
    )

    assert (
        envelope["execution"]["interaction_id"]
        == "interaction-test"
    )

    assert (
        envelope["narrative"]["status"]
        == "answered"
    )

    assert (
        envelope["narrative"]["used_metrics"]
        == [
            "billed_cost",
            "effective_cost",
        ]
    )

    assert (
        trace["interaction_status"]
        == "completed"
    )

    assert (
        trace["narrative_status"]
        == "answered"
    )

    assert trace["total_tokens"] == 330

    request = (
        client.interactions.last_request
    )

    assert (
        request["model"]
        == "gemini-3.6-flash"
    )

    assert question in request["input"]

    assert (
        '"provider": "AWS"'
        in request["input"]
    )

    assert (
        request["response_format"]["mime_type"]
        == "application/json"
    )

    assert (
        "schema"
        in request["response_format"]
    )


def test_accepts_unsupported_as_valid_result(
    monkeypatch,
):
    prepare_dependencies(monkeypatch)

    model_output = json.dumps(
        {
            "status": "unsupported",
            "answer": (
                "لا تكفي البيانات لإثبات أن "
                "خدمة EC2 مستغلة بالكامل."
            ),
            "used_metrics": [],
            "limitations": [
                (
                    "No utilization metrics "
                    "are included."
                ),
            ],
            "unsupported_reason": (
                "The payload contains costs but "
                "does not contain utilization "
                "metrics."
            ),
        },
        ensure_ascii=False,
    )

    client = FakeClient(
        model_output
    )

    envelope, trace = (
        narrative_service.generate_finops_narrative(
            client=client,
            user_question=(
                "هل خدمة EC2 مستغلة بالكامل؟"
            ),
        )
    )

    assert (
        envelope["narrative"]["status"]
        == "unsupported"
    )

    assert (
        envelope["narrative"][
            "unsupported_reason"
        ]
        is not None
    )

    assert (
        envelope["narrative"]["used_metrics"]
        == []
    )

    assert (
        trace["narrative_status"]
        == "unsupported"
    )


def test_rejects_invalid_model_json(
    monkeypatch,
):
    prepare_dependencies(monkeypatch)

    client = FakeClient(
        "This is not valid JSON."
    )

    with pytest.raises(
        ValidationError
    ):
        narrative_service.generate_finops_narrative(
            client=client,
            user_question="اشرح التكلفة.",
        )


def test_rejects_extra_model_field(
    monkeypatch,
):
    prepare_dependencies(monkeypatch)

    model_output = json.dumps(
        {
            "status": "answered",
            "answer": (
                "قيمة Billed Cost هي "
                "16.041693050500022 USD."
            ),
            "used_metrics": [
                "billed_cost",
            ],
            "limitations": [
                "Limited evidence.",
            ],
            "unsupported_reason": None,
            "confidence": 0.99,
        },
        ensure_ascii=False,
    )

    client = FakeClient(
        model_output
    )

    with pytest.raises(
        ValidationError
    ):
        narrative_service.generate_finops_narrative(
            client=client,
            user_question="اشرح التكلفة.",
        )