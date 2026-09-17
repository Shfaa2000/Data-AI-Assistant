import json

import pytest

from src.narrative_prompt import (
    build_narrative_prompt,
)


def make_payload() -> dict:
    return {
        "provider": "AWS",
        "service": "Amazon Elastic Compute Cloud",
        "currency": "USD",
        "billed_cost": 16.041693,
        "effective_cost": 13.0,
        "negative_billed_cost": -2.6137,
        "limitations": [
            "لا تتوفر مؤشرات استخدام.",
        ],
    }


def extract_data_json(prompt: str) -> str:
    """استخراج قسم JSON من الـPrompt لأجل الاختبار."""

    return (
        prompt
        .split("<data_json>", maxsplit=1)[1]
        .split("</data_json>", maxsplit=1)[0]
        .strip()
    )


def test_prompt_contains_user_question():
    question = (
        "اذكر Billed Cost وEffective Cost."
    )

    prompt = build_narrative_prompt(
        payload=make_payload(),
        user_question=question,
    )

    assert question in prompt


def test_prompt_contains_valid_payload_json():
    payload = make_payload()

    prompt = build_narrative_prompt(
        payload=payload,
        user_question="اشرح القيم.",
    )

    embedded_payload = json.loads(
        extract_data_json(prompt)
    )

    assert embedded_payload == payload


def test_prompt_keeps_arabic_as_readable_text():
    prompt = build_narrative_prompt(
        payload=make_payload(),
        user_question="اشرح التكلفة.",
    )

    assert "اشرح التكلفة." in prompt
    assert "لا تتوفر مؤشرات استخدام." in prompt
    assert "\\u0627" not in prompt


def test_prompt_contains_required_sections():
    prompt = build_narrative_prompt(
        payload=make_payload(),
        user_question="اشرح القيم.",
    )

    assert "<role>" in prompt
    assert "<source_policy>" in prompt
    assert "<rules>" in prompt
    assert "<data_json>" in prompt
    assert "<user_question>" in prompt


@pytest.mark.parametrize(
    "question",
    [
        "",
        "   ",
        "\n\t",
    ],
)
def test_rejects_empty_user_question(question):
    with pytest.raises(ValueError):
        build_narrative_prompt(
            payload=make_payload(),
            user_question=question,
        )


def test_rejects_empty_payload():
    with pytest.raises(ValueError):
        build_narrative_prompt(
            payload={},
            user_question="اشرح القيم.",
        )