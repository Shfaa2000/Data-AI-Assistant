import pytest
from pydantic import ValidationError

from src.finops_query.query_catalog import (
    PhysicalColumn,
    PhysicalTable,
    QueryCatalogError,
    QuerySchemaCatalog,
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
                        name="ProviderName",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=2,
                    ),
                ],
            )
        ]
    )


def test_catalog_finds_table_and_column():
    catalog = make_catalog()

    table = catalog.get_table(
        FULL_TABLE_ID
    )

    assert (
        table.get_column("billedcost").name
        == "BilledCost"
    )


def test_column_normalizes_bigquery_aliases():
    column = PhysicalColumn(
        name="BilledCost",
        data_type="FLOAT",
        is_nullable=True,
        ordinal_position=1,
    )

    assert column.data_type == "FLOAT64"


def test_table_rejects_duplicate_columns():
    with pytest.raises(ValidationError):
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
                    name="billedcost",
                    data_type="FLOAT64",
                    is_nullable=True,
                    ordinal_position=2,
                ),
            ],
        )


def test_catalog_rejects_empty_tables():
    with pytest.raises(ValidationError):
        QuerySchemaCatalog(tables=[])


def test_missing_column_raises_clear_error():
    catalog = make_catalog()
    table = catalog.get_table(
        FULL_TABLE_ID
    )

    with pytest.raises(
        QueryCatalogError,
        match="not allowed",
    ):
        table.get_column(
            "InventedColumn"
        )