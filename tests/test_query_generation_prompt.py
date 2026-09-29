import pytest

from src.finops_query.query_generation_prompt import (
    build_query_generation_prompt,
    normalize_user_question,
)


SCHEMA_CONTEXT = {
    "allowed_table": (
        "data-ai-assistant-training."
        "cloud_finops."
        "billing_pipeline_day2"
    ),
    "fields": [
        {
            "semantic_name": "billed_cost",
            "kind": "metric",
            "physical_column": "BilledCost",
            "data_type": "FLOAT64",
            "allowed_aggregations": [
                "sum"
            ],
            "value_scope": "all_values",
        }
    ],
}


def test_normalizes_user_question():
    question = normalize_user_question(
        "  What is the billed cost?  "
    )

    assert question == (
        "What is the billed cost?"
    )


def test_rejects_empty_question():
    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        normalize_user_question("   ")


def test_generation_prompt_contains_question_and_schema():
    prompt = build_query_generation_prompt(
        user_question=(
            "What is the total billed cost?"
        ),
        schema_context=SCHEMA_CONTEXT,
    )

    assert (
        "What is the total billed cost?"
        in prompt
    )

    assert "billed_cost" in prompt
    assert "Query Plan" in prompt
    assert "SQL Proposal" in prompt

    assert (
        "exactly one GoogleSQL SELECT"
        in prompt
    )

    assert (
        "sql_proposal as null"
        in prompt
    )