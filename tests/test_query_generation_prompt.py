import pytest

from src.finops_query.query_generation_prompt import (
    build_query_plan_prompt,
    build_sql_generation_prompt,
    normalize_user_question,
)
from src.finops_query.query_plan import (
    FinOpsQueryPlan,
    MetricSelection,
    QueryStatus,
)
from src.finops_query.query_schema import (
    AggregationName,
    MetricName,
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
                "sum",
            ],
            "value_scope": "all_values",
        }
    ],
}


def make_ready_plan() -> FinOpsQueryPlan:
    return FinOpsQueryPlan(
        status=QueryStatus.READY,
        intent="Calculate total billed cost.",
        metrics=[
            MetricSelection(
                name=MetricName.BILLED_COST,
                aggregation=AggregationName.SUM,
            )
        ],
    )


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


def test_plan_prompt_contains_question_and_schema():
    prompt = build_query_plan_prompt(
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
    assert "Do not generate SQL" in prompt


def test_sql_prompt_contains_validated_plan():
    prompt = build_sql_generation_prompt(
        plan=make_ready_plan(),
        schema_context=SCHEMA_CONTEXT,
    )

    assert "VALIDATED_QUERY_PLAN" in prompt
    assert "BilledCost" in prompt
    assert "exactly one SELECT" in prompt


def test_sql_prompt_rejects_non_ready_plan():
    plan = FinOpsQueryPlan(
        status=QueryStatus.UNSUPPORTED,
        intent="Forecast future cost.",
        unsupported_reason=(
            "Forecasting is not supported."
        ),
    )

    with pytest.raises(
        ValueError,
        match="requires a ready",
    ):
        build_sql_generation_prompt(
            plan=plan,
            schema_context=SCHEMA_CONTEXT,
        )