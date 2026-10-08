"""
يقرأ Schema الحقيقية من BigQuery، ويربط الأعمدة الفعلية
بالمقاييس والأبعاد التي يفهمها FinOps Assistant.
"""

from typing import Any

from src.finops_query.models import (
    FinOpsQueryPlan,
    QueryStatus,
)


class SchemaValidationError(ValueError):
    """يظهر عندما تكون Schema أو Query Plan غير متوافقة."""


# يربط أسماء FinOps بأعمدة BigQuery الحقيقية.
FIELD_MAPPINGS = {
    "billed_cost": {
        "kind": "metric",
        "physical_column": "BilledCost",
        "expected_types": (
            "FLOAT64",
            "NUMERIC",
            "BIGNUMERIC",
        ),
        "allowed_aggregations": (
            "sum",
            "avg",
            "min",
            "max",
        ),
        "value_scope": "all_values",
    },

    "effective_cost": {
        "kind": "metric",
        "physical_column": "EffectiveCost",
        "expected_types": (
            "FLOAT64",
            "NUMERIC",
            "BIGNUMERIC",
        ),
        "allowed_aggregations": (
            "sum",
            "avg",
            "min",
            "max",
        ),
        "value_scope": "all_values",
    },

    "negative_billed_cost": {
        "kind": "metric",
        "physical_column": "BilledCost",
        "expected_types": (
            "FLOAT64",
            "NUMERIC",
            "BIGNUMERIC",
        ),
        "allowed_aggregations": (
            "sum",
        ),
        "value_scope": "negative_values",
    },

    "provider": {
        "kind": "dimension",
        "physical_column": "ProviderName",
        "expected_types": (
            "STRING",
        ),
        "allowed_aggregations": (),
        "value_scope": "all_values",
    },

    "service": {
        "kind": "dimension",
        "physical_column": "ServiceName",
        "expected_types": (
            "STRING",
        ),
        "allowed_aggregations": (),
        "value_scope": "all_values",
    },

    "currency": {
        "kind": "dimension",
        "physical_column": "BillingCurrency",
        "expected_types": (
            "STRING",
        ),
        "allowed_aggregations": (),
        "value_scope": "all_values",
    },

    "time_range": {
        "kind": "time",
        "physical_column": "BillingPeriodStart",
        "expected_types": (
            "DATE",
            "DATETIME",
            "TIMESTAMP",
        ),
        "allowed_aggregations": (),
        "value_scope": "all_values",
    },
}


# يحول Enum أو النص العادي إلى قيمة نصية.
def _text(
    value: Any,
) -> str:
    return str(
        getattr(
            value,
            "value",
            value,
        )
    )


# يوحد أسماء أنواع BigQuery.
def _normalize_data_type(
    data_type: str,
) -> str:
    aliases = {
        "FLOAT": "FLOAT64",
        "INTEGER": "INT64",
        "BOOLEAN": "BOOL",
    }

    normalized = data_type.upper()

    return aliases.get(
        normalized,
        normalized,
    )


# يقرأ أعمدة الجدول ويبني سياقًا آمنًا ترسله الرحلة إلى Gemini.
def load_schema_context(
    client: Any,
    full_table_id: str,
) -> dict:
    table = client.get_table(
        full_table_id
    )

    physical_columns = {
        field.name: (
            _normalize_data_type(
                field.field_type
            )
        )
        for field in table.schema
    }
    # هذه القائمة سنضع فيها فقط الحقول الموجودة في FIELD_MAPPINGS.
    fields = []

    for (
        semantic_name,
        mapping,
    ) in FIELD_MAPPINGS.items():
        column_name = mapping[
            "physical_column"
        ]

        actual_type = physical_columns.get(
            column_name
        )

        if actual_type is None:
            raise SchemaValidationError(
                "Required BigQuery column "
                f"is missing: {column_name}"
            )

        if (
            actual_type
            not in mapping["expected_types"]
        ):
            raise SchemaValidationError(
                f"Column {column_name!r} "
                f"has type {actual_type!r}, "
                "expected one of "
                f"{mapping['expected_types']}."
            )

        fields.append(
            {
                "semantic_name": (
                    semantic_name
                ),
                "kind": mapping["kind"],
                "physical_column": (
                    column_name
                ),
                "data_type": actual_type,
                "allowed_aggregations": list(
                    mapping[
                        "allowed_aggregations"
                    ]
                ),
                "value_scope": mapping[
                    "value_scope"
                ],
            }
        )

    return {
        "allowed_table": full_table_id,
        "fields": fields,
    }


#  يحول قائمة الحقول إلى قاموس للبحث بالاسم الدلالي. مباشرة
def get_field_map(
    schema_context: dict,
) -> dict[str, dict]:
    return {
        field["semantic_name"]: field
        for field in schema_context[
            "fields"
        ]
    }


# يتحقق من أن Query Plan تستخدم حقولًا وعمليات مسموحة.
def validate_query_plan(
    plan: FinOpsQueryPlan,
    schema_context: dict,
) -> None:
    if plan.status is not QueryStatus.READY:
        raise SchemaValidationError(
            "Only a ready Query Plan "
            "can be validated."
        )

    fields = get_field_map(
        schema_context
    )

    for metric in plan.metrics:
        metric_name = _text(
            metric.name
        )

        aggregation = _text(
            metric.aggregation
        )

        field = fields.get(
            metric_name
        )

        if (
            field is None
            or field["kind"] != "metric"
        ):
            raise SchemaValidationError(
                "Metric is not supported: "
                f"{metric_name}"
            )

        if (
            aggregation
            not in field[
                "allowed_aggregations"
            ]
        ):
            raise SchemaValidationError(
                f"Aggregation {aggregation!r} "
                "is not allowed for "
                f"{metric_name!r}."
            )

    for dimension in plan.dimensions:
        dimension_name = _text(
            dimension
        )

        field = fields.get(
            dimension_name
        )

        if (
            field is None
            or field["kind"] != "dimension"
        ):
            raise SchemaValidationError(
                "Dimension is not supported: "
                f"{dimension_name}"
            )

    for query_filter in plan.filters:
        filter_name = _text(
            query_filter.column
        )

        field = fields.get(
            filter_name
        )

        if (
            field is None
            or field["kind"] != "dimension"
        ):
            raise SchemaValidationError(
                "Filter is not supported: "
                f"{filter_name}"
            )

    if plan.time_range is not None:
        time_field = fields.get(
            "time_range"
        )

        if (
            time_field is None
            or time_field["kind"] != "time"
        ):
            raise SchemaValidationError(
                "The time range field "
                "is not available."
            )

    if plan.sort_by is not None:
        sort_name = _text(
            plan.sort_by
        )

        if sort_name not in fields:
            raise SchemaValidationError(
                "Sort field is not supported: "
                f"{sort_name}"
            )