from src.finops_query.query_catalog import (
    PhysicalColumn,
    PhysicalTable,
    QuerySchemaCatalog,
)
from src.finops_query.query_schema_context import (
    build_query_schema_context,
)


PROJECT_ID = "data-ai-assistant-training"
DATASET_ID = "cloud_finops"
TABLE_ID = "billing_pipeline_day2"

FULL_TABLE_ID = (
    f"{PROJECT_ID}."
    f"{DATASET_ID}."
    f"{TABLE_ID}"
)


def make_catalog() -> QuerySchemaCatalog:
    return QuerySchemaCatalog(
        tables=[
            PhysicalTable(
                project_id=PROJECT_ID,
                dataset_id=DATASET_ID,
                table_id=TABLE_ID,
                columns=[
                    PhysicalColumn(
                        name="BilledCost",
                        data_type="FLOAT64",
                        is_nullable=True,
                        ordinal_position=1,
                    ),
                    PhysicalColumn(
                        name="EffectiveCost",
                        data_type="FLOAT64",
                        is_nullable=True,
                        ordinal_position=2,
                    ),
                    PhysicalColumn(
                        name="ProviderName",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=3,
                    ),
                    PhysicalColumn(
                        name="ServiceName",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=4,
                    ),
                    PhysicalColumn(
                        name="BillingCurrency",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=5,
                    ),
                    PhysicalColumn(
                        name="BillingPeriodStart",
                        data_type="TIMESTAMP",
                        is_nullable=True,
                        ordinal_position=6,
                    ),
                ],
            )
        ]
    )


def test_builds_safe_schema_context():
    context = build_query_schema_context(
        catalog=make_catalog(),
        full_table_id=FULL_TABLE_ID,
    )

    assert (
        context["allowed_table"]
        == FULL_TABLE_ID
    )

    semantic_names = {
        field["semantic_name"]
        for field in context["fields"]
    }

    assert "billed_cost" in semantic_names
    assert "provider" in semantic_names
    assert "time_range" in semantic_names


def test_context_does_not_expose_credentials():
    context = build_query_schema_context(
        catalog=make_catalog(),
        full_table_id=FULL_TABLE_ID,
    )

    context_text = str(context).lower()

    assert "api_key" not in context_text
    assert "credentials" not in context_text
    assert "password" not in context_text