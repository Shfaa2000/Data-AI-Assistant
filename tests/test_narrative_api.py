import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import finops_api as api_module
from src.narrative_api_dependencies import (
    get_gemini_client,
)
from src.narrative_response import (
    NarrativeResponse,
)
from src.narrative_grounding import (
    NarrativeGroundingError,
)


class FakeGeminiClient:
    """بديل محلي لا يتصل بخدمة Gemini."""


def make_envelope(
    narrative_status: str = "answered",
) -> dict:
    """إنشاء Envelope تجريبية صالحة."""

    if narrative_status == "answered":
        narrative = {
            "status": "answered",
            "answer": (
                "قيمة Effective Cost أقل من "
                "قيمة Billed Cost."
            ),
            "used_metrics": [
                "billed_cost",
                "effective_cost",
            ],
            "limitations": [
                "النتيجة تغطي الفترات المحملة فقط.",
            ],
            "unsupported_reason": None,
        }
    else:
        narrative = {
            "status": "unsupported",
            "answer": (
                "لا تتوفر بيانات استخدام تثبت "
                "استغلال الخدمة بالكامل."
            ),
            "used_metrics": [],
            "limitations": [
                "لا توجد مقاييس استخدام موارد.",
            ],
            "unsupported_reason": (
                "البيانات المالية لا تحتوي "
                "على مقاييس utilization."
            ),
        }

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
        "narrative": narrative,
    }


@pytest.fixture
def http_client():
    """إنشاء TestClient مع Gemini Dependency وهمية."""

    def fake_gemini_dependency():
        return FakeGeminiClient()

    api_module.app.dependency_overrides[
        get_gemini_client
    ] = fake_gemini_dependency

    with TestClient(api_module.app) as client:
        yield client

    api_module.app.dependency_overrides.clear()


def test_answered_request_returns_envelope(
    http_client,
    monkeypatch,
):
    def fake_service(
        client,
        user_question,
    ):
        assert isinstance(
            client,
            FakeGeminiClient,
        )
        assert user_question == "اشرح التكلفة."

        return (
            make_envelope("answered"),
            {
                "interaction_id": "interaction-123",
            },
        )

    monkeypatch.setattr(
        api_module,
        "generate_narrative_service",
        fake_service,
    )

    response = http_client.post(
        "/v1/narratives",
        json={
            "question": "اشرح التكلفة.",
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["narrative"]["status"]
        == "answered"
    )
    assert (
        response.json()["provenance"][
            "evidence_id"
        ]
        == "evidence-123"
    )
    assert "trace" not in response.json()


def test_unsupported_is_still_http_200(
    http_client,
    monkeypatch,
):
    def fake_service(
        client,
        user_question,
    ):
        return (
            make_envelope("unsupported"),
            {
                "interaction_id": "interaction-123",
            },
        )

    monkeypatch.setattr(
        api_module,
        "generate_narrative_service",
        fake_service,
    )

    response = http_client.post(
        "/v1/narratives",
        json={
            "question": (
                "هل الخدمة مستغلة بالكامل؟"
            ),
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["narrative"]["status"]
        == "unsupported"
    )


def test_missing_question_returns_422(
    http_client,
):
    response = http_client.post(
        "/v1/narratives",
        json={},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "question",
    [
        "",
        "   ",
        "\n\t",
    ],
)
def test_empty_question_returns_422(
    http_client,
    question,
):
    response = http_client.post(
        "/v1/narratives",
        json={
            "question": question,
        },
    )

    assert response.status_code == 422


def test_extra_field_returns_422(
    http_client,
):
    response = http_client.post(
        "/v1/narratives",
        json={
            "question": "اشرح التكلفة.",
            "prompt": "غير مسموح",
        },
    )

    assert response.status_code == 422


def test_missing_evidence_returns_503(
    http_client,
    monkeypatch,
):
    def fake_service(
        client,
        user_question,
    ):
        raise FileNotFoundError(
            "Fake missing evidence."
        )

    monkeypatch.setattr(
        api_module,
        "generate_narrative_service",
        fake_service,
    )

    response = http_client.post(
        "/v1/narratives",
        json={
            "question": "اشرح التكلفة.",
        },
    )

    assert response.status_code == 503


def test_invalid_model_response_returns_502(
    http_client,
    monkeypatch,
):
    def fake_service(
        client,
        user_question,
    ):
        NarrativeResponse.model_validate(
            {
                "status": "answered",
                "answer": "جواب غير صالح.",
                "used_metrics": [],
                "limitations": [
                    "اختبار."
                ],
                "unsupported_reason": None,
            }
        )

    monkeypatch.setattr(
        api_module,
        "generate_narrative_service",
        fake_service,
    )

    response = http_client.post(
        "/v1/narratives",
        json={
            "question": "اشرح التكلفة.",
        },
    )

    assert response.status_code == 502


def test_unexpected_error_returns_500(
    http_client,
    monkeypatch,
):
    def fake_service(
        client,
        user_question,
    ):
        raise RuntimeError(
            "Unexpected test error."
        )

    monkeypatch.setattr(
        api_module,
        "generate_narrative_service",
        fake_service,
    )

    response = http_client.post(
        "/v1/narratives",
        json={
            "question": "اشرح التكلفة.",
        },
    )

    assert response.status_code == 500

def test_ungrounded_response_returns_502(
    http_client,
    monkeypatch,
):
    def fake_service(
        client,
        user_question,
    ):
        raise NarrativeGroundingError(
            "Model returned an unapproved number."
        )

    monkeypatch.setattr(
        api_module,
        "generate_narrative_service",
        fake_service,
    )

    response = http_client.post(
        "/v1/narratives",
        json={
            "question": "اشرح التكلفة.",
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": (
            "Narrative provider returned "
            "an ungrounded response."
        )
    }