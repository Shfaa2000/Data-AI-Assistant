"""يأخذ Query Plan الموثقة وSQL الآمنة، ثم يقارن معناهما. إذا طلبت الخطة شيئًا وكتبت SQL شيئًا مختلفًا، يوقف الرحلة."""

from collections import Counter
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlglot import exp

from .query_plan import FinOpsQueryPlan
from .query_sql_proposal import (
    GeneratedSqlProposal,
)


class SqlSemanticValidationError(ValueError):
    """يُرفع عندما لا تطابق SQL معنى Query Plan."""


OPERATOR_TYPES = {
    "eq": exp.EQ,
    "ne": exp.NEQ,
    "gt": exp.GT,
    "gte": exp.GTE,
    "lt": exp.LT,
    "lte": exp.LTE,
}

# توحد قراءة Dictionary وPydantic Models وEnums.
def _read_value(
    item: Any,
    name: str,
) -> Any:
    if isinstance(item, Mapping):
        return item[name]

    return getattr(item, name)


def _text(value: Any) -> str:
    return str(
        getattr(value, "value", value)
    )


def _field_index(
    schema_context: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        str(
            _read_value(
                field,
                "semantic_name",
            )
        ): field
        for field in schema_context["fields"]
    }


def _parameter_values(
    proposal: GeneratedSqlProposal,
) -> dict[str, Any]:
    return {
        parameter.name: parameter.value
        for parameter in proposal.parameters
    }


def _values_equal(
    left: Any,
    right: Any,
) -> bool:
    if left == right:
        return True

    return str(left) == str(right)

# تستخرج التجميع والعمود والـAlias من SQL الفعلية.
def _actual_metric_signatures(
    statement: exp.Select,
) -> Counter:
    signatures = Counter()

    for item in statement.expressions:
        target = (
            item.this
            if isinstance(item, exp.Alias)
            else item
        )

        if not isinstance(
            target,
            exp.AggFunc,
        ):
            continue

        columns = list(
            target.find_all(exp.Column)
        )

        if len(columns) != 1:
            raise SqlSemanticValidationError(
                "Each metric aggregation must "
                "use exactly one column."
            )

        if not item.alias:
            raise SqlSemanticValidationError(
                "Each metric must use its "
                "semantic name as an alias."
            )

        signature = (
            target.key.casefold(),
            columns[0].name.casefold(),
            item.alias.casefold(),
        )

        signatures[signature] += 1

    return signatures


# تحول Metrics الموجودة في Query Plan إلى الشكل المتوقع داخل SQL.
def _expected_metric_signatures(
    plan: FinOpsQueryPlan,
    fields: Mapping[str, Any],
) -> Counter:
    signatures = Counter()

    for metric in plan.metrics:
        semantic_name = _text(metric.name)

        mapping = fields.get(
            semantic_name
        )

        if mapping is None:
            raise SqlSemanticValidationError(
                "Metric is not present in "
                f"schema context: {semantic_name}"
            )

        signature = (
            _text(
                metric.aggregation
            ).casefold(),
            str(
                _read_value(
                    mapping,
                    "physical_column",
                )
            ).casefold(),
            semantic_name.casefold(),
        )

        signatures[signature] += 1

    return signatures

# تستخرج Dimensions المباشرة الموجودة داخل SELECT.
def _actual_dimension_signatures(
    statement: exp.Select,
) -> Counter:
    signatures = Counter()

    for item in statement.expressions:
        target = (
            item.this
            if isinstance(item, exp.Alias)
            else item
        )

        if not isinstance(
            target,
            exp.Column,
        ):
            continue

        alias = item.alias or target.name

        signatures[
            (
                target.name.casefold(),
                alias.casefold(),
            )
        ] += 1

    return signatures


# تبني Dimensions المتوقعة من Query Plan وMapping.
def _expected_dimension_signatures(
    plan: FinOpsQueryPlan,
    fields: Mapping[str, Any],
) -> Counter:
    signatures = Counter()

    for dimension in plan.dimensions:
        semantic_name = _text(dimension)

        mapping = fields.get(
            semantic_name
        )

        if mapping is None:
            raise SqlSemanticValidationError(
                "Dimension is not present in "
                f"schema context: {semantic_name}"
            )

        physical_column = str(
            _read_value(
                mapping,
                "physical_column",
            )
        )

        signatures[
            (
                physical_column.casefold(),
                semantic_name.casefold(),
            )
        ] += 1

    return signatures


# تستخرج أعمدة GROUP BY للمقارنة مع Dimensions المطلوبة.
def _group_columns(
    statement: exp.Select,
) -> Counter:
    group = statement.args.get("group")

    if group is None:
        return Counter()

    return Counter(
        expression.name.casefold()
        for expression in group.expressions
        if isinstance(
            expression,
            exp.Column,
        )
    )

# تستخرج المقارنات الموجودة داخل WHERE.
def _comparisons(
    statement: exp.Select,
) -> list[exp.Expression]:
    where = statement.args.get("where")

    if where is None:
        return []

    comparison_types = tuple(
        OPERATOR_TYPES.values()
    )

    return [
        node
        for node in where.walk()
        if isinstance(
            node,
            comparison_types,
        )
    ]


# تقرأ قيمة Named Parameter المستخدمة في المقارنة.
def _parameter_value(
    expression: exp.Expression,
    parameter_values: Mapping[str, Any],
) -> tuple[bool, Any]:
    if not isinstance(
        expression,
        exp.Parameter,
    ):
        return False, None

    return (
        True,
        parameter_values[expression.name],
    )


# يبحث عن Filter يطابق الحقل والـOperator والقيمة الموجودة في Query Plan.
def _consume_plan_filter(
    query_filter: Any,
    comparisons: list[exp.Expression],
    consumed: set[int],
    fields: Mapping[str, Any],
    parameter_values: Mapping[str, Any],
) -> None:
    semantic_name = _text(
        query_filter.column
    )

    mapping = fields.get(
        semantic_name
    )

    if mapping is None:
        raise SqlSemanticValidationError(
            "Filter field is not present in "
            f"schema context: {semantic_name}"
        )

    physical_column = str(
        _read_value(
            mapping,
            "physical_column",
        )
    ).casefold()

    operator_name = _text(
        query_filter.operator
    )

    operator_type = OPERATOR_TYPES[
        operator_name
    ]

    for index, comparison in enumerate(
        comparisons
    ):
        if index in consumed:
            continue

        if not isinstance(
            comparison,
            operator_type,
        ):
            continue

        if not isinstance(
            comparison.left,
            exp.Column,
        ):
            continue

        if (
            comparison.left.name.casefold()
            != physical_column
        ):
            continue

        is_parameter, actual_value = (
            _parameter_value(
                comparison.right,
                parameter_values,
            )
        )

        if not is_parameter:
            continue

        if _values_equal(
            actual_value,
            query_filter.value,
        ):
            consumed.add(index)
            return

    raise SqlSemanticValidationError(
        "SQL does not implement filter: "
        f"{semantic_name} "
        f"{operator_name} "
        f"{query_filter.value}"
    )

# يتحقق أن القيمة الموجودة يمين المقارنة هي الصفر الرقمي.
def _is_numeric_zero(
    expression: exp.Expression,
) -> bool:
    if (
        not isinstance(
            expression,
            exp.Literal,
        )
        or expression.is_string
    ):
        return False

    try:
        return Decimal(
            expression.this
        ) == 0
    except InvalidOperation:
        return False


# يفرض BilledCost < 0 عند استخدام negative_billed_cost.
def _consume_negative_scope(
    physical_column: str,
    comparisons: list[exp.Expression],
    consumed: set[int],
) -> None:
    for index, comparison in enumerate(
        comparisons
    ):
        if index in consumed:
            continue

        if not isinstance(
            comparison,
            exp.LT,
        ):
            continue

        if not isinstance(
            comparison.left,
            exp.Column,
        ):
            continue

        if (
            comparison.left.name.casefold()
            != physical_column.casefold()
        ):
            continue

        if _is_numeric_zero(
            comparison.right
        ):
            consumed.add(index)
            return

    raise SqlSemanticValidationError(
        "Metric with negative_values scope "
        f"requires {physical_column} < 0."
    )

# يتحقق من أن ORDER BY يطابق الحقل والاتجاه الموجودين في الخطة.
def _validate_sort(
    plan: FinOpsQueryPlan,
    statement: exp.Select,
    fields: Mapping[str, Any],
) -> None:
    order = statement.args.get("order")

    if plan.sort_by is None:
        if order is not None:
            raise SqlSemanticValidationError(
                "SQL adds ORDER BY although "
                "the plan does not request it."
            )

        return

    if (
        order is None
        or len(order.expressions) != 1
    ):
        raise SqlSemanticValidationError(
            "SQL must implement exactly "
            "one planned sort field."
        )

    semantic_name = _text(
        plan.sort_by
    )

    mapping = fields.get(
        semantic_name
    )

    if mapping is None:
        raise SqlSemanticValidationError(
            "Sort field is not present in "
            f"schema context: {semantic_name}"
        )

    ordered = order.expressions[0]

    if not isinstance(
        ordered.this,
        exp.Column,
    ):
        raise SqlSemanticValidationError(
            "ORDER BY must reference a "
            "permitted field or output alias."
        )

    allowed_names = {
        semantic_name.casefold(),
        str(
            _read_value(
                mapping,
                "physical_column",
            )
        ).casefold(),
    }

    if (
        ordered.this.name.casefold()
        not in allowed_names
    ):
        raise SqlSemanticValidationError(
            "ORDER BY does not match "
            "the Query Plan."
        )

    actual_direction = (
        "desc"
        if ordered.args.get("desc")
        else "asc"
    )

    if (
        actual_direction
        != _text(plan.sort_direction)
    ):
        raise SqlSemanticValidationError(
            "ORDER BY direction does not "
            "match the Query Plan."
        )


# يفرض LIMIT على الاستعلامات المجمعة ويطابقه مع الخطة.
def _validate_limit(
    plan: FinOpsQueryPlan,
    statement: exp.Select,
) -> None:
    limit = statement.args.get("limit")

    if plan.dimensions and limit is None:
        raise SqlSemanticValidationError(
            "Grouped queries must include "
            "the planned LIMIT."
        )

    if limit is None:
        return

    expression = limit.expression

    if (
        not isinstance(
            expression,
            exp.Literal,
        )
        or expression.is_string
    ):
        raise SqlSemanticValidationError(
            "LIMIT must be a numeric literal."
        )

    actual_limit = int(
        expression.this
    )

    if actual_limit != plan.limit:
        raise SqlSemanticValidationError(
            f"SQL LIMIT {actual_limit} "
            "does not match planned limit "
            f"{plan.limit}."
        )

# يقارن Metrics وDimensions وFilters وScope والترتيب والحد مع الخطة.
def validate_sql_semantics(
    plan: FinOpsQueryPlan,
    proposal: GeneratedSqlProposal,
    schema_context: Mapping[str, Any],
    statement: exp.Select,
) -> None:
    if _text(plan.status) != "ready":
        raise SqlSemanticValidationError(
            "Only a ready Query Plan may "
            "have SQL."
        )

    fields = _field_index(
        schema_context
    )

    expected_metrics = (
        _expected_metric_signatures(
            plan,
            fields,
        )
    )

    actual_metrics = (
        _actual_metric_signatures(
            statement
        )
    )

    if actual_metrics != expected_metrics:
        raise SqlSemanticValidationError(
            "SQL metrics do not match "
            "the Query Plan. "
            f"expected={expected_metrics}, "
            f"actual={actual_metrics}"
        )

    expected_dimensions = (
        _expected_dimension_signatures(
            plan,
            fields,
        )
    )

    actual_dimensions = (
        _actual_dimension_signatures(
            statement
        )
    )

    if (
        actual_dimensions
        != expected_dimensions
    ):
        raise SqlSemanticValidationError(
            "SQL dimensions do not match "
            "the Query Plan."
        )

    expected_group_columns = Counter(
        str(
            _read_value(
                fields[_text(dimension)],
                "physical_column",
            )
        ).casefold()
        for dimension in plan.dimensions
    )

    if (
        _group_columns(statement)
        != expected_group_columns
    ):
        raise SqlSemanticValidationError(
            "GROUP BY columns do not match "
            "planned dimensions."
        )

    parameter_values = _parameter_values(
        proposal
    )

    comparisons = _comparisons(
        statement
    )

    consumed: set[int] = set()

    for query_filter in plan.filters:
        _consume_plan_filter(
            query_filter,
            comparisons,
            consumed,
            fields,
            parameter_values,
        )

    for metric in plan.metrics:
        semantic_name = _text(
            metric.name
        )

        mapping = fields[
            semantic_name
        ]

        value_scope = str(
            _read_value(
                mapping,
                "value_scope",
            )
        )

        if value_scope == "negative_values":
            _consume_negative_scope(
                str(
                    _read_value(
                        mapping,
                        "physical_column",
                    )
                ),
                comparisons,
                consumed,
            )

    if len(consumed) != len(comparisons):
        raise SqlSemanticValidationError(
            "SQL contains filters that were "
            "not requested by Query Plan."
        )

    _validate_sort(
        plan,
        statement,
        fields,
    )

    _validate_limit(
        plan,
        statement,
    )