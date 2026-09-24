"""يتحقق من أن Query Plan جاهزة ومتوافقة مع Schema Catalog قبل السماح بانتقالها إلى SQL Generator."""
from enum import Enum

from src.finops_query.query_catalog import (
    QuerySchemaCatalog,
)
from src.finops_query.query_mapping import (
    QUERY_FIELD_MAPPINGS,
    QueryFieldKind,
    QueryFieldMapping,
)
from src.finops_query.query_plan import (
    FinOpsQueryPlan,
    QueryStatus,
)
from src.finops_query.query_schema_validator import (
    validate_query_schema_mapping,
)


class QueryPlanValidationError(ValueError):
    """يُرفع عندما لا يمكن تنفيذ Query Plan."""

# يحول Enum أو النص العادي إلى قيمة نصية موحدة لاستخدامها كمفتاح داخل Mapping.
def _value(
    value: object,
) -> str:
    """استخراج القيمة النصية من Enum."""

    if isinstance(value, Enum):
        return str(value.value)

    return str(value)

# يمنع الخطط غير الجاهزة ويتحقق من Metrics وDimensions وFilters والترتيب والوقت.
def validate_query_plan_against_schema(
    plan: FinOpsQueryPlan,
    catalog: QuerySchemaCatalog,
    full_table_id: str,
    mappings: dict[
        str,
        QueryFieldMapping,
    ] = QUERY_FIELD_MAPPINGS,
) -> None:
    """التحقق من قابلية تنفيذ Query Plan."""

    if plan.status is not QueryStatus.READY:
        raise QueryPlanValidationError(
            "Only ready plans can generate SQL; "
            f"got {plan.status.value}."
        )

    validate_query_schema_mapping(
        catalog=catalog,
        full_table_id=full_table_id,
        mappings=mappings,
    )

    for metric in plan.metrics:
        metric_name = _value(
            metric.name
        )

        mapping = mappings.get(
            metric_name
        )

        if (
            mapping is None
            or mapping.kind
            is not QueryFieldKind.METRIC
        ):
            raise QueryPlanValidationError(
                "Metric is not executable: "
                f"{metric_name}"
            )

        if (
            metric.aggregation
            not in mapping.allowed_aggregations
        ):
            raise QueryPlanValidationError(
                f"Aggregation "
                f"{metric.aggregation.value!r} "
                f"is not allowed for metric "
                f"{metric_name!r}."
            )

    for dimension in plan.dimensions:
        dimension_name = _value(
            dimension
        )

        mapping = mappings.get(
            dimension_name
        )

        if (
            mapping is None
            or mapping.kind
            is not QueryFieldKind.DIMENSION
        ):
            raise QueryPlanValidationError(
                "Dimension is not executable: "
                f"{dimension_name}"
            )

    for query_filter in plan.filters:
        dimension_name = _value(
            query_filter.column
        )

        mapping = mappings.get(
            dimension_name
        )

        if (
            mapping is None
            or mapping.kind
            is not QueryFieldKind.DIMENSION
        ):
            raise QueryPlanValidationError(
                "Filter column is not executable: "
                f"{dimension_name}"
            )

    if plan.time_range is not None:
        time_mapping = mappings.get(
            "time_range"
        )

        if (
            time_mapping is None
            or time_mapping.kind
            is not QueryFieldKind.TIME
        ):
            raise QueryPlanValidationError(
                "Time range has no executable "
                "physical mapping."
            )

    if plan.sort_by is not None:
        sort_name = _value(
            plan.sort_by
        )

        if sort_name not in mappings:
            raise QueryPlanValidationError(
                "Sort field is not executable: "
                f"{sort_name}"
            )

