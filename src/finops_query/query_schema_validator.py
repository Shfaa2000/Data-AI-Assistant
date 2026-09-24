"""يتحقق من أن Semantic-to-Physical Mapping مكتملة وتستخدم أعمدة موجودة وأنواعًا متوافقة مع BigQuery Catalog."""
from src.finops_query.query_catalog import (
    QuerySchemaCatalog,
)
from src.finops_query.query_mapping import (
    QUERY_FIELD_MAPPINGS,
    QueryFieldKind,
    QueryFieldMapping,
)
from src.finops_query.query_schema import (
    DimensionName,
    MetricName,
)


class QuerySchemaValidationError(ValueError):
    """يُرفع عندما لا يطابق الربط مخطط BigQuery."""

# يتأكد من اكتمال Mapping ووجود أعمدتها وتوافق أنواعها مع Physical Schema.
def validate_query_schema_mapping(
    catalog: QuerySchemaCatalog,
    full_table_id: str,
    mappings: dict[
        str,
        QueryFieldMapping,
    ] = QUERY_FIELD_MAPPINGS,
) -> None:
    """التحقق من الربط بين Semantic وPhysical Schema."""

    table = catalog.get_table(
        full_table_id
    )

    required_semantic_names = {
        *(
            metric.value
            for metric in MetricName
        ),
        *(
            dimension.value
            for dimension in DimensionName
        ),
        "time_range",
    }

    missing_mappings = (
        required_semantic_names
        - mappings.keys()
    )

    if missing_mappings:
        raise QuerySchemaValidationError(
            "Missing semantic mappings: "
            + ", ".join(
                sorted(missing_mappings)
            )
        )

    for semantic_name, mapping in mappings.items():
        try:
            column = table.get_column(
                mapping.physical_column
            )
        except ValueError as exc:
            raise QuerySchemaValidationError(
                f"Mapping {semantic_name!r} uses "
                "a missing column: "
                f"{mapping.physical_column}"
            ) from exc

        if (
            column.data_type
            not in mapping.expected_data_types
        ):
            raise QuerySchemaValidationError(
                f"Mapping {semantic_name!r} expects "
                f"{mapping.expected_data_types}, "
                f"but column {column.name!r} is "
                f"{column.data_type}."
            )

        if (
            mapping.kind
            is QueryFieldKind.METRIC
            and not mapping.allowed_aggregations
        ):
            raise QuerySchemaValidationError(
                "Metric mapping has no aggregation: "
                f"{semantic_name}"
            )