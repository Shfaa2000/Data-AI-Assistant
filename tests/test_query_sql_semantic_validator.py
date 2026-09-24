import pytest

from src.finops_query.query_plan import (
    FinOpsQueryPlan,
)
from src.finops_query.query_sql_proposal import (
    GeneratedSqlProposal,
)
from src.finops_query.query_sql_safety_validator import (
    validate_sql_safety,
)
from src.finops_query.query_sql_semantic_validator import (
    SqlSemanticValidationError,
    validate_sql_semantics,
)


FULL_TABLE_ID = (
    "data-ai-assistant-training."
    "cloud_finops."
    "billing_pipeline_day2"
)

SCHEMA_CONTEXT = {
    "allowed_table": FULL_TABLE_ID,
    "fields": [
        {
            "semantic_name": "billed_cost",
            "kind": "metric",
            "physical_column": "BilledCost",
            "data_type": "FLOAT64",
            "allowed_aggregations": [
                "sum",
                "avg",
                "min",
                "max",
            ],
            "value_scope": "all_values",
        },
        {
            "semantic_name": "negative_billed_cost",
            "kind": "metric",
            "physical_column": "BilledCost",
            "data_type": "FLOAT64",
            "allowed_aggregations": [
                "sum"
            ],
            "value_scope": "negative_values",
        },
        {
            "semantic_name": "provider",
            "kind": "dimension",
            "physical_column": "ProviderName",
            "data_type": "STRING",
            "allowed_aggregations": [],
            "value_scope": "all_values",
        },
        {
            "semantic_name": "service",
            "kind": "dimension",
            "physical_column": "ServiceName",
            "data_type": "STRING",
            "allowed_aggregations": [],
            "value_scope": "all_values",
        },
        {
            "semantic_name": "time_range",
            "kind": "time",
            "physical_column": "BillingPeriodStart",
            "data_type": "TIMESTAMP",
            "allowed_aggregations": [],
            "value_scope": "all_values",
        },
    ],
}


def make_plan(
    *,
    metric="billed_cost",
    aggregation="sum",
    dimensions=None,
    filters=None,
    sort_by=None,
    sort_direction=None,
    limit=100,
):
    return FinOpsQueryPlan.model_validate(
        {
            "status": "ready",
            "intent": (
                "Answer a financial "
                "aggregation question."
            ),
            "metrics": [
                {
                    "name": metric,
                    "aggregation": aggregation,
                }
            ],
            "dimensions": dimensions or [],
            "filters": filters or [],
            "time_range": None,
            "sort_by": sort_by,
            "sort_direction": sort_direction,
            "limit": limit,
            "clarification_question": None,
            "unsupported_reason": None,
        }
    )


def validate(
    plan,
    proposal,
):
    statement = validate_sql_safety(
        proposal=proposal,
        schema_context=SCHEMA_CONTEXT,
    )

    validate_sql_semantics(
        plan=plan,
        proposal=proposal,
        schema_context=SCHEMA_CONTEXT,
        statement=statement,
    )


def test_accepts_matching_metric_and_filter():
    plan = make_plan(
        filters=[
            {
                "column": "provider",
                "operator": "eq",
                "value": "AWS",
            }
        ]
    )

    proposal = GeneratedSqlProposal.model_validate(
        {
            "sql": (
                "SELECT SUM(BilledCost) "
                "AS billed_cost "
                f"FROM `{FULL_TABLE_ID}` "
                "WHERE ProviderName "
                "= @provider"
            ),
            "parameters": [
                {
                    "name": "provider",
                    "data_type": "STRING",
                    "value": "AWS",
                }
            ],
        }
    )

    validate(plan, proposal)


def test_rejects_wrong_aggregation():
    plan = make_plan(
        aggregation="sum"
    )

    proposal = GeneratedSqlProposal.model_validate(
        {
            "sql": (
                "SELECT AVG(BilledCost) "
                "AS billed_cost "
                f"FROM `{FULL_TABLE_ID}`"
            ),
            "parameters": [],
        }
    )

    with pytest.raises(
        SqlSemanticValidationError,
        match="metrics",
    ):
        validate(plan, proposal)


def test_rejects_missing_filter():
    plan = make_plan(
        filters=[
            {
                "column": "provider",
                "operator": "eq",
                "value": "AWS",
            }
        ]
    )

    proposal = GeneratedSqlProposal.model_validate(
        {
            "sql": (
                "SELECT SUM(BilledCost) "
                "AS billed_cost "
                f"FROM `{FULL_TABLE_ID}`"
            ),
            "parameters": [],
        }
    )

    with pytest.raises(
        SqlSemanticValidationError,
        match="does not implement filter",
    ):
        validate(plan, proposal)


def test_rejects_wrong_filter_value():
    plan = make_plan(
        filters=[
            {
                "column": "provider",
                "operator": "eq",
                "value": "AWS",
            }
        ]
    )

    proposal = GeneratedSqlProposal.model_validate(
        {
            "sql": (
                "SELECT SUM(BilledCost) "
                "AS billed_cost "
                f"FROM `{FULL_TABLE_ID}` "
                "WHERE ProviderName "
                "= @provider"
            ),
            "parameters": [
                {
                    "name": "provider",
                    "data_type": "STRING",
                    "value": "Microsoft",
                }
            ],
        }
    )

    with pytest.raises(
        SqlSemanticValidationError,
        match="does not implement filter",
    ):
        validate(plan, proposal)


def test_accepts_grouping_sorting_and_limit():
    plan = make_plan(
        dimensions=["service"],
        filters=[
            {
                "column": "provider",
                "operator": "eq",
                "value": "AWS",
            }
        ],
        sort_by="billed_cost",
        sort_direction="desc",
        limit=5,
    )

    proposal = GeneratedSqlProposal.model_validate(
        {
            "sql": (
                "SELECT "
                "ServiceName AS service, "
                "SUM(BilledCost) "
                "AS billed_cost "
                f"FROM `{FULL_TABLE_ID}` "
                "WHERE ProviderName "
                "= @provider "
                "GROUP BY ServiceName "
                "ORDER BY billed_cost DESC "
                "LIMIT 5"
            ),
            "parameters": [
                {
                    "name": "provider",
                    "data_type": "STRING",
                    "value": "AWS",
                }
            ],
        }
    )

    validate(plan, proposal)


def test_requires_negative_value_scope():
    plan = make_plan(
        metric="negative_billed_cost",
        aggregation="sum",
    )

    proposal = GeneratedSqlProposal.model_validate(
        {
            "sql": (
                "SELECT SUM(BilledCost) "
                "AS negative_billed_cost "
                f"FROM `{FULL_TABLE_ID}`"
            ),
            "parameters": [],
        }
    )

    with pytest.raises(
        SqlSemanticValidationError,
        match="negative_values",
    ):
        validate(plan, proposal)


def test_accepts_negative_value_scope():
    plan = make_plan(
        metric="negative_billed_cost",
        aggregation="sum",
    )

    proposal = GeneratedSqlProposal.model_validate(
        {
            "sql": (
                "SELECT SUM(BilledCost) "
                "AS negative_billed_cost "
                f"FROM `{FULL_TABLE_ID}` "
                "WHERE BilledCost < 0"
            ),
            "parameters": [],
        }
    )

    validate(plan, proposal)