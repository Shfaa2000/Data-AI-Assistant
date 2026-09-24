import pytest

from src.finops_query.query_catalog import (
    PhysicalColumn,
    PhysicalTable,
    QuerySchemaCatalog,
)
from src.finops_query.query_mapping import (
    QUERY_FIELD_MAPPINGS,
)
from src.finops_query.query_schema_validator import (
    QuerySchemaValidationError,
    validate_query_schema_mapping,
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


def test_mapping_matches_catalog():
    validate_query_schema_mapping(
        catalog=make_catalog(),
        full_table_id=FULL_TABLE_ID,
    )


def test_rejects_missing_physical_column():
    broken_mappings = dict(
        QUERY_FIELD_MAPPINGS
    )

    broken_mappings["provider"] = (
        broken_mappings["provider"].model_copy(
            update={
                "physical_column": (
                    "InventedProvider"
                )
            }
        )
    )

    with pytest.raises(
        QuerySchemaValidationError,
        match="missing column",
    ):
        validate_query_schema_mapping(
            catalog=make_catalog(),
            full_table_id=FULL_TABLE_ID,
            mappings=broken_mappings,
        )


def test_rejects_wrong_physical_type():
    catalog = make_catalog()
    table = catalog.get_table(
        FULL_TABLE_ID
    )

    billed_column = table.get_column(
        "BilledCost"
    )
    billed_column.data_type = "STRING"

    with pytest.raises(
        QuerySchemaValidationError,
        match="expects",
    ):
        validate_query_schema_mapping(
            catalog=catalog,
            full_table_id=FULL_TABLE_ID,
        )


def test_rejects_missing_semantic_mapping():
    incomplete = dict(
        QUERY_FIELD_MAPPINGS
    )
    incomplete.pop("service")

    with pytest.raises(
        QuerySchemaValidationError,
        match="Missing semantic mappings",
    ):
        validate_query_schema_mapping(
            catalog=make_catalog(),
            full_table_id=FULL_TABLE_ID,
            mappings=incomplete,
        )