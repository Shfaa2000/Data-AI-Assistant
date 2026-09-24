import pytest
from pydantic import ValidationError

from src.finops_query.query_plan import (
    FinOpsQueryPlan,
    MetricSelection,
    QueryStatus,
)
from src.finops_query.query_schema import (
    AggregationName,
    MetricName,
)
from src.finops_query.query_sql_proposal import (
    GeneratedQueryParameter,
    GeneratedSqlProposal,
    QueryGenerationResult,
    QueryParameterType,
)


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


def make_sql_proposal() -> GeneratedSqlProposal:
    return GeneratedSqlProposal(
        sql=(
            "SELECT SUM(BilledCost) "
            "AS billed_cost "
            "FROM "
            "`data-ai-assistant-training."
            "cloud_finops."
            "billing_pipeline_day2`"
        ),
        parameters=[],
    )


def test_accepts_valid_sql_proposal():
    proposal = make_sql_proposal()

    assert "SELECT" in proposal.sql
    assert proposal.parameters == []


def test_accepts_named_parameter():
    parameter = GeneratedQueryParameter(
        name="provider",
        data_type=QueryParameterType.STRING,
        value="AWS",
    )

    assert parameter.name == "provider"
    assert parameter.value == "AWS"


def test_rejects_invalid_parameter_name():
    with pytest.raises(ValidationError):
        GeneratedQueryParameter(
            name="@provider",
            data_type=(
                QueryParameterType.STRING
            ),
            value="AWS",
        )


def test_rejects_wrong_parameter_value_type():
    with pytest.raises(ValidationError):
        GeneratedQueryParameter(
            name="row_limit",
            data_type=(
                QueryParameterType.INT64
            ),
            value="ten",
        )


def test_rejects_duplicate_parameters():
    with pytest.raises(ValidationError):
        GeneratedSqlProposal(
            sql=(
                "SELECT BilledCost "
                "FROM `project.dataset.table` "
                "WHERE ProviderName = @provider"
            ),
            parameters=[
                GeneratedQueryParameter(
                    name="provider",
                    data_type=(
                        QueryParameterType.STRING
                    ),
                    value="AWS",
                ),
                GeneratedQueryParameter(
                    name="PROVIDER",
                    data_type=(
                        QueryParameterType.STRING
                    ),
                    value="Microsoft",
                ),
            ],
        )


def test_ready_plan_requires_sql_proposal():
    with pytest.raises(ValidationError):
        QueryGenerationResult(
            plan=make_ready_plan(),
            sql_proposal=None,
        )


def test_non_ready_plan_rejects_sql():
    clarification_plan = FinOpsQueryPlan(
        status=(
            QueryStatus.NEEDS_CLARIFICATION
        ),
        intent="Clarify the requested provider.",
        clarification_question=(
            "Which provider do you mean?"
        ),
    )

    with pytest.raises(ValidationError):
        QueryGenerationResult(
            plan=clarification_plan,
            sql_proposal=make_sql_proposal(),
        )