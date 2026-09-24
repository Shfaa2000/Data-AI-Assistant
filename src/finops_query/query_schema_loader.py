"""يقرأ Metadata الجداول المسموحة من BigQuery ويحولها إلى Query Schema Catalog موثقة وقابلة للاختبار."""
from collections.abc import Iterable
from typing import Any

from google.cloud import bigquery

from src.finops_query.query_catalog import (
    PhysicalColumn,
    PhysicalTable,
    QueryCatalogError,
    QuerySchemaCatalog,
)

# يبني استعلامًا يقرأ حقول Metadata المطلوبة فقط من INFORMATION_SCHEMA.
def build_information_schema_query(
    project_id: str,
    dataset_id: str,
) -> str:
    """بناء استعلام Metadata لبيئة موثوقة."""

    return f"""
        SELECT
            table_catalog,
            table_schema,
            table_name,
            column_name,
            ordinal_position,
            is_nullable,
            data_type
        FROM
            `{project_id}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
        WHERE
            table_name IN UNNEST(@table_names)
        ORDER BY
            table_name,
            ordinal_position
    """.strip()

# يسمح لنفس منطق التحويل بقراءة BigQuery Rows الحقيقية وقواميس الاختبار الوهمية.
def _read_row_value(
    row: Any,
    field_name: str,
) -> Any:
    """قراءة قيمة من BigQuery Row أو قاموس اختبار."""

    if isinstance(row, dict):
        return row[field_name]

    return getattr(row, field_name)

# يحول صفوف INFORMATION_SCHEMA إلى أعمدة وجداول مرتبة ويرفض أي جدول غير مسموح.
def build_catalog_from_rows(
    rows: Iterable[Any],
    project_id: str,
    dataset_id: str,
    allowed_table_ids: tuple[str, ...],
) -> QuerySchemaCatalog:
    """تحويل صفوف Metadata إلى كتالوج موثوق."""

    allowed = set(allowed_table_ids)

    grouped_columns: dict[
        str,
        list[PhysicalColumn],
    ] = {
        table_id: []
        for table_id in allowed_table_ids
    }

    for row in rows:
        table_name = str(
            _read_row_value(
                row,
                "table_name",
            )
        )

        if table_name not in allowed:
            raise QueryCatalogError(
                "Metadata returned a non-allowed table: "
                f"{table_name}"
            )

        grouped_columns[table_name].append(
            PhysicalColumn(
                name=str(
                    _read_row_value(
                        row,
                        "column_name",
                    )
                ),
                data_type=str(
                    _read_row_value(
                        row,
                        "data_type",
                    )
                ),
                is_nullable=(
                    str(
                        _read_row_value(
                            row,
                            "is_nullable",
                        )
                    ).upper()
                    == "YES"
                ),
                ordinal_position=_read_row_value(
                    row,
                    "ordinal_position",
                ),
            )
        )

    missing_tables = [
        table_id
        for table_id, columns
        in grouped_columns.items()
        if not columns
    ]

    if missing_tables:
        raise QueryCatalogError(
            "No metadata returned for allowed tables: "
            + ", ".join(
                sorted(missing_tables)
            )
        )

    tables = [
        PhysicalTable(
            project_id=project_id,
            dataset_id=dataset_id,
            table_id=table_id,
            columns=sorted(
                columns,
                key=lambda column: (
                    column.ordinal_position or 0
                ),
            ),
        )
        for table_id, columns
        in grouped_columns.items()
    ]

    return QuerySchemaCatalog(
        tables=tables,
    )

# ينفذ استعلام Metadata بمعامل آمن ثم يحول النتيجة إلى QuerySchemaCatalog.
def load_query_schema_catalog(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str,
    allowed_table_ids: tuple[str, ...],
    location: str,
) -> QuerySchemaCatalog:
    """تحميل Physical Schema الفعلية من BigQuery."""

    sql = build_information_schema_query(
        project_id=project_id,
        dataset_id=dataset_id,
    )

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "table_names",
                "STRING",
                list(allowed_table_ids),
            )
        ]
    )

    rows = client.query(
        sql,
        job_config=job_config,
        location=location,
    ).result()

    return build_catalog_from_rows(
        rows=rows,
        project_id=project_id,
        dataset_id=dataset_id,
        allowed_table_ids=allowed_table_ids,
    )

