from types import SimpleNamespace

import pytest

from src.finops_query.query_catalog import (
    QueryCatalogError,
)
from src.finops_query.query_schema_loader import (
    build_catalog_from_rows,
    build_information_schema_query,
)


PROJECT_ID = "data-ai-assistant-training"
DATASET_ID = "cloud_finops"
TABLE_ID = "billing_pipeline_day2"

FULL_TABLE_ID = (
    f"{PROJECT_ID}."
    f"{DATASET_ID}."
    f"{TABLE_ID}"
)


def make_row(
    column_name: str,
    data_type: str,
    position: int,
    table_name: str = TABLE_ID,
):
    return SimpleNamespace(
        table_name=table_name,
        column_name=column_name,
        data_type=data_type,
        is_nullable="YES",
        ordinal_position=position,
    )


def test_builds_catalog_from_fake_rows():
    catalog = build_catalog_from_rows(
        rows=[
            make_row(
                "ProviderName",
                "STRING",
                2,
            ),
            make_row(
                "BilledCost",
                "FLOAT64",
                1,
            ),
        ],
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        allowed_table_ids=(TABLE_ID,),
    )

    table = catalog.get_table(
        FULL_TABLE_ID
    )

    assert [
        column.name
        for column in table.columns
    ] == [
        "BilledCost",
        "ProviderName",
    ]


def test_rejects_missing_allowed_table():
    with pytest.raises(
        QueryCatalogError,
        match="No metadata",
    ):
        build_catalog_from_rows(
            rows=[],
            project_id=PROJECT_ID,
            dataset_id=DATASET_ID,
            allowed_table_ids=(TABLE_ID,),
        )


def test_rejects_non_allowed_table():
    with pytest.raises(
        QueryCatalogError,
        match="non-allowed",
    ):
        build_catalog_from_rows(
            rows=[
                make_row(
                    "BilledCost",
                    "FLOAT64",
                    1,
                    table_name="secret_table",
                )
            ],
            project_id=PROJECT_ID,
            dataset_id=DATASET_ID,
            allowed_table_ids=(TABLE_ID,),
        )


def test_information_schema_query_is_narrow():
    sql = build_information_schema_query(
        PROJECT_ID,
        DATASET_ID,
    )

    assert "INFORMATION_SCHEMA.COLUMNS" in sql
    assert "@table_names" in sql
    assert "SELECT *" not in sql.upper()
    assert (
        "ORDER BY\n"
        "            table_name,\n"
        "            ordinal_position"
        in sql
    )