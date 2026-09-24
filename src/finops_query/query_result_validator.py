"""يتحقق من أن نتيجة BigQuery تطابق Query Plan وحدود التطبيق."""

from __future__ import annotations

import math
from decimal import Decimal
from enum import Enum
from typing import Any

from .query_bigquery_execution import QueryExecutionResult


class QueryResultValidationError(ValueError):
    """يظهر عندما لا تطابق نتيجة BigQuery الخطة الموثقة."""


def _read(value: Any, field_name: str) -> Any:
    if isinstance(value, dict):
        return value[field_name]

    return getattr(value, field_name)


def _text(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return str(value)

# يستخرج أسماء Dimensions وMetrics الدلالية التي يجب أن تعيدها SQL.
def _expected_result_columns(query_plan: Any) -> list[str]:
    dimensions = [
        _text(dimension)
        for dimension in query_plan.dimensions
    ]

    metrics = [
        _text(_read(metric, "name"))
        for metric in query_plan.metrics
    ]

    return dimensions + metrics

# يتحقق من أن Metric رقم صالح أو NULL عند عدم وجود بيانات مطابقة.
def _validate_metric_value(
    metric_name: str,
    value: Any,
) -> None:
    if value is None:
        return

    if isinstance(value, bool):
        raise QueryResultValidationError(
            f"Metric {metric_name!r} returned a boolean value."
        )

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise QueryResultValidationError(
                f"Metric {metric_name!r} is not finite."
            )
        return

    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise QueryResultValidationError(
                f"Metric {metric_name!r} is not finite."
            )
        return

    raise QueryResultValidationError(
        f"Metric {metric_name!r} returned a non-numeric value: "
        f"{value!r}"
    )

# يقارن أعمدة وصفوف نتيجة BigQuery بما تتوقعه Query Plan.
def validate_query_result(
    query_plan: Any,
    result: QueryExecutionResult,
) -> None:
    status = _text(query_plan.status).strip().lower()

    if status != "ready":
        raise QueryResultValidationError(
            "Only a ready Query Plan may have an execution result."
        )

    expected_columns = _expected_result_columns(query_plan)

    if len(expected_columns) != len(set(expected_columns)):
        raise QueryResultValidationError(
            "The Query Plan contains duplicate output columns."
        )

    if set(result.columns) != set(expected_columns):
        raise QueryResultValidationError(
            "BigQuery result columns do not match the Query Plan. "
            f"Expected {expected_columns}, received {result.columns}."
        )

    if result.total_rows != len(result.rows):
        raise QueryResultValidationError(
            "The result was truncated or its row count is inconsistent."
        )

    plan_limit = query_plan.limit

    if plan_limit is not None and result.total_rows > plan_limit:
        raise QueryResultValidationError(
            f"The result exceeded the Query Plan limit: {plan_limit}."
        )

    if not query_plan.dimensions and query_plan.metrics:
        if result.total_rows != 1:
            raise QueryResultValidationError(
                "A scalar aggregate query must return exactly one row."
            )

    metric_names = [
        _text(_read(metric, "name"))
        for metric in query_plan.metrics
    ]

    for row in result.rows:
        if set(row.keys()) != set(expected_columns):
            raise QueryResultValidationError(
                "A result row contains missing or unexpected columns."
            )

        for metric_name in metric_names:
            _validate_metric_value(
                metric_name=metric_name,
                value=row[metric_name],
            )