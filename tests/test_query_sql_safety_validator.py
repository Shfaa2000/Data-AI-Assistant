import pytest

from src.finops_query.query_sql_proposal import (
    GeneratedQueryParameter,
    GeneratedSqlProposal,
)
from src.finops_query.query_sql_safety_validator import (
    SqlSafetyValidationError,
    validate_sql_safety,
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
            "physical_column": "BilledCost",
        },
        {
            "semantic_name": "effective_cost",
            "physical_column": "EffectiveCost",
        },
        {
            "semantic_name": "provider",
            "physical_column": "ProviderName",
        },
        {
            "semantic_name": "service",
            "physical_column": "ServiceName",
        },
        {
            "semantic_name": "currency",
            "physical_column": "BillingCurrency",
        },
        {
            "semantic_name": "time_range",
            "physical_column": "BillingPeriodStart",
        },
    ],
}


def provider_parameter():
    return GeneratedQueryParameter(
        name="provider",
        data_type="STRING",
        value="AWS",
    )


def test_accepts_safe_parameterized_select():
    proposal = GeneratedSqlProposal(
        sql=(
            "SELECT SUM(BilledCost) "
            "AS billed_cost "
            f"FROM `{FULL_TABLE_ID}` "
            "WHERE ProviderName = @provider"
        ),
        parameters=[
            provider_parameter()
        ],
    )

    statement = validate_sql_safety(
        proposal=proposal,
        schema_context=SCHEMA_CONTEXT,
    )

    assert statement is not None


def test_rejects_delete_statement():
    proposal = GeneratedSqlProposal(
        sql=(
            f"DELETE FROM `{FULL_TABLE_ID}` "
            "WHERE ProviderName = @provider"
        ),
        parameters=[
            provider_parameter()
        ],
    )

    with pytest.raises(
        SqlSafetyValidationError,
        match="Only a SELECT",
    ):
        validate_sql_safety(
            proposal,
            SCHEMA_CONTEXT,
        )


def test_rejects_multiple_statements():
    proposal = GeneratedSqlProposal(
        sql=(
            f"SELECT BilledCost "
            f"FROM `{FULL_TABLE_ID}`; "
            f"SELECT EffectiveCost "
            f"FROM `{FULL_TABLE_ID}`"
        ),
        parameters=[],
    )

    with pytest.raises(
        SqlSafetyValidationError,
        match="Exactly one",
    ):
        validate_sql_safety(
            proposal,
            SCHEMA_CONTEXT,
        )


def test_rejects_unapproved_table():
    proposal = GeneratedSqlProposal(
        sql=(
            "SELECT SUM(BilledCost) "
            "AS billed_cost "
            "FROM "
            "`data-ai-assistant-training."
            "cloud_finops.secret_table`"
        ),
        parameters=[],
    )

    with pytest.raises(
        SqlSafetyValidationError,
        match="Table is not allowed",
    ):
        validate_sql_safety(
            proposal,
            SCHEMA_CONTEXT,
        )


def test_rejects_unknown_column():
    proposal = GeneratedSqlProposal(
        sql=(
            "SELECT SUM(TotalCost) "
            "AS billed_cost "
            f"FROM `{FULL_TABLE_ID}`"
        ),
        parameters=[],
    )

    with pytest.raises(
        SqlSafetyValidationError,
        match="Column is not allowed",
    ):
        validate_sql_safety(
            proposal,
            SCHEMA_CONTEXT,
        )


def test_rejects_select_star():
    proposal = GeneratedSqlProposal(
        sql=(
            f"SELECT * "
            f"FROM `{FULL_TABLE_ID}`"
        ),
        parameters=[],
    )

    with pytest.raises(
        SqlSafetyValidationError,
        match="SELECT",
    ):
        validate_sql_safety(
            proposal,
            SCHEMA_CONTEXT,
        )


def test_rejects_parameter_mismatch():
    proposal = GeneratedSqlProposal(
        sql=(
            "SELECT SUM(BilledCost) "
            "AS billed_cost "
            f"FROM `{FULL_TABLE_ID}`"
        ),
        parameters=[
            provider_parameter()
        ],
    )

    with pytest.raises(
        SqlSafetyValidationError,
        match="parameter names",
    ):
        validate_sql_safety(
            proposal,
            SCHEMA_CONTEXT,
        )


def test_rejects_join():
    proposal = GeneratedSqlProposal(
        sql=(
            "SELECT SUM(a.BilledCost) "
            "AS billed_cost "
            f"FROM `{FULL_TABLE_ID}` AS a "
            f"JOIN `{FULL_TABLE_ID}` AS b "
            "ON a.Id = b.Id"
        ),
        parameters=[],
    )

    with pytest.raises(
        SqlSafetyValidationError,
        match="Joins",
    ):
        validate_sql_safety(
            proposal,
            SCHEMA_CONTEXT,
        )