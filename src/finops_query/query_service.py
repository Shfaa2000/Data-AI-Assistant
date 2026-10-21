"""
ينفذ استدعاء Gemini الأول لإنشاء Query Plan وSQL Proposal،
ثم يتحقق من أن SQL آمنة وتطبق الخطة نفسها.
"""

import json
from collections import Counter
from decimal import (
    Decimal,
    InvalidOperation,
)
from typing import Any

import sqlglot
from pydantic import BaseModel
from sqlglot import exp
from sqlglot.errors import (
    ParseError,
    TokenError,
)

from src.finops_query.models import (
    GeneratedSqlProposal,
    QueryGenerationResult,
    QueryStatus,
)
from src.finops_query.schema import (
    get_field_map,
    validate_query_plan,
)


class SqlValidationError(ValueError):
    """يظهر عندما تكون SQL غير آمنة أو لا تطابق الخطة."""


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


# ينظف سؤال المستخدم ويرفض السؤال الفارغ أو الطويل.
def normalize_user_question(
    user_question: str,
) -> str:
    question = user_question.strip()

    if not question:
        raise ValueError(
            "User question cannot be empty."
        )

    if len(question) > 1000:
        raise ValueError(
            "User question exceeds "
            "the 1000-character limit."
        )

    return question


# يبني Prompt واحدًا يعيد Query Plan وSQL Proposal.
def build_query_generation_prompt(
    user_question: str,
    schema_context: dict,
) -> str:
    question = normalize_user_question(
        user_question
    )

    schema_json = json.dumps(
        schema_context,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    return f"""
ROLE:
You are a FinOps query planner and GoogleSQL generator
for a read-only analytics backend.

TASK:
Analyze USER_QUESTION and return one structured result
containing:
1. A semantic Query Plan.
2. An SQL Proposal when the plan status is "ready".

STATUS POLICY:
- Use "ready" only when the question can be answered
  from SAFE_SCHEMA_CONTEXT.
- A ready plan must include an SQL Proposal.
- Use "needs_clarification" when an essential detail
  is ambiguous or missing.
- Use "unsupported" when the required information is
  unavailable in SAFE_SCHEMA_CONTEXT.
- For needs_clarification or unsupported, return
  sql_proposal as null.

QUERY PLAN RULES:
- Use only semantic fields from SAFE_SCHEMA_CONTEXT.
- Do not invent metrics, dimensions, filters, or dates.
- Use only the listed aggregations and filter operators.
- Keep user-provided filter values grounded in the question.
- Every provider, service, or currency explicitly named in
  USER_QUESTION must appear as a Query Plan filter.
- Build the complete Query Plan first, then generate SQL only
  from that same plan.

SQL SAFETY RULES:
- Generate exactly one GoogleSQL SELECT statement.
- Use only the allowed table and physical columns.
- Never generate INSERT, UPDATE, DELETE, MERGE, CREATE,
  ALTER, DROP, TRUNCATE, CALL, EXPORT, or scripting.
- Do not use joins, subqueries, CTEs, UNNEST, window
  functions, HAVING, QUALIFY, OFFSET, SELECT *, or COUNT(*).
- Do not add SQL comments.
- Do not execute the SQL.

PARAMETER RULES:
- Use named parameters for user-provided filter values
  and time boundaries.
- Store parameter names without @ in the parameters list.
- Reference the same parameter with @ inside SQL.
- Do not add unused or undeclared parameters.
- Use a numeric literal for LIMIT.
- The literal 0 may be used for negative_values scope.

TIME RANGE RULES:
- Treat time_range start and end as inclusive calendar dates.
- Implement time_range using exactly two direct comparisons:
  physical_time_column >= @start_date and
  physical_time_column <= @end_date.
- Set each time parameter data_type to match the physical
  time column type from SAFE_SCHEMA_CONTEXT.
- Use TIMESTAMP parameters for a TIMESTAMP column,
  DATE parameters for a DATE column, and DATETIME
  parameters for a DATETIME column.
- Compare the physical column directly with the named
  parameter.
- Never wrap time parameters in TIMESTAMP(), DATE(),
  DATETIME(), CAST(), or any other function.
- Do not use BETWEEN.
- Do not add a time condition when time_range is null.
- TIMESTAMP parameter values must use strict
  ISO-8601 format, for example:
  2024-09-01T00:00:00Z.

SQL SEMANTIC RULES:
- SQL must implement the returned Query Plan exactly.
- Use physical columns in SELECT, WHERE, and GROUP BY.
- Use semantic names only as SELECT aliases.
- GROUP BY physical dimension columns.
- SELECT aliases may be used in ORDER BY only.
- Implement every metric, aggregation, dimension, filter,
  time range, sort, value scope, and limit in the plan.
- Do not add behavior absent from the plan.
- A scalar aggregate with no dimensions may omit LIMIT.
- If dimensions is not empty, SQL must include
  LIMIT equal to plan.limit, even when the user
  did not explicitly request a limit.

FINAL CONSISTENCY CHECK:
- Before returning, compare the Query Plan and SQL Proposal.
- If status is "ready", sql_proposal must be a JSON object,
  never null.
- Every ordinary WHERE comparison must correspond one-to-one
  with a filter in the Query Plan.
- Do not add default filters such as cost > 0, cost >= 0,
  IS NOT NULL, currency, provider, service, or date conditions
  unless the Query Plan explicitly requires them.
- The only condition allowed without a plan filter is the
  physical metric column < 0 required by negative_values scope.
- If you cannot produce matching SQL, do not use "ready";
  return "unsupported" with sql_proposal set to null.
- Never place a provider, service, or currency constraint only
  in SQL; it must exist in the Query Plan filters as well.

OUTPUT CONTRACT:
- Return only JSON matching the required response schema.
- Do not wrap the JSON in Markdown code fences.
- The backend will validate the plan and SQL before execution.

SAFE_SCHEMA_CONTEXT:
{schema_json}

USER_QUESTION:
{question}
""".strip()


# يحول عقد Pydantic إلى Schema يطلبها Gemini.
def _structured_response_format(
    response_model: type[BaseModel],
) -> dict:
    return {
        "type": "text",
        "mime_type": "application/json",
        "schema": (
            response_model.model_json_schema()
        ),
    }


# يحلل GoogleSQL ويسمح بجملة SELECT واحدة فقط.
def _parse_single_select(
    sql: str,
) -> exp.Select:
    if (
        "--" in sql
        or "/*" in sql
    ):
        raise SqlValidationError(
            "SQL comments are not allowed."
        )

    try:
        statements = [
            statement
            # هو يفكك النص إلى شجرة Python تمثل مكونات الاستعلام.
            for statement in sqlglot.parse(
                sql,
                read="bigquery",
            )
            if statement is not None
        ]

    except (
        ParseError,
        TokenError,
    ) as exc:
        raise SqlValidationError(
            f"Invalid GoogleSQL: {exc}"
        ) from exc

    if (
        len(statements) != 1
        or not isinstance(
            statements[0],
            exp.Select,
        )
    ):
        raise SqlValidationError(
            "Exactly one SELECT "
            "statement is required."
        )

    return statements[0]


# يعيد اسم جدول BigQuery الكامل.
def _full_table_name(
    table: exp.Table,
) -> str:
    return ".".join(
        part
        for part in (
            table.catalog,
            table.db,
            table.name,
        )
        if part
    )


# يسمح باستخدام Alias داخل ORDER BY فقط.
def _is_order_alias(
    column: exp.Column,
    aliases: set[str],
) -> bool:
    if (
        column.name.casefold()
        not in aliases
    ):
        return False

    current = column.parent

    while current is not None:
        if isinstance(
            current,
            exp.Order,
        ):
            return True

        if isinstance(
            current,
            (
                exp.Where,
                exp.Group,
                exp.Having,
            ),
        ):
            return False

        current = current.parent

    return False


# يفرض شكل SQL الآمن والجداول والأعمدة والـParameters.
def validate_sql_safety(
    proposal: GeneratedSqlProposal,
    schema_context: dict,
) -> exp.Select:
    statement = _parse_single_select(
        proposal.sql
    )

    if (
        statement.args.get("with_")
        is not None
    ):
        raise SqlValidationError(
            "CTEs are not allowed."
        )

    forbidden_nodes = (
        exp.Join,
        exp.Subquery,
        exp.Union,
        exp.Intersect,
        exp.Except,
        exp.Unnest,
        exp.Window,
    )

    if any(
        statement.find(node) is not None
        for node in forbidden_nodes
    ):
        raise SqlValidationError(
            "Joins, subqueries, set operations, "
            "UNNEST, and windows are not allowed."
        )

    for clause in (
        "having",
        "qualify",
        "offset",
    ):
        if (
            statement.args.get(clause)
            is not None
        ):
            raise SqlValidationError(
                f"{clause.upper()} is not allowed."
            )

    if (
        statement.find(exp.Star)
        is not None
    ):
        raise SqlValidationError(
            "SELECT * and COUNT(*) "
            "are not allowed."
        )

    tables = list(
        statement.find_all(
            exp.Table
        )
    )

    if len(tables) != 1:
        raise SqlValidationError(
            "Exactly one table "
            "must be referenced."
        )

    actual_table = _full_table_name(
        tables[0]
    )

    allowed_table = str(
        schema_context["allowed_table"]
    )

    if (
        actual_table.casefold()
        != allowed_table.casefold()
    ):
        raise SqlValidationError(
            f"Table is not allowed: "
            f"{actual_table}"
        )

    allowed_columns = {
        field[
            "physical_column"
        ].casefold()
        for field in schema_context[
            "fields"
        ]
    }

    aliases = {
        item.alias.casefold()
        for item in statement.expressions
        if item.alias
    }

    for column in statement.find_all(
        exp.Column
    ):
        if (
            column.name.casefold()
            in allowed_columns
        ):
            continue

        if _is_order_alias(
            column,
            aliases,
        ):
            continue

        raise SqlValidationError(
            "Column is not allowed: "
            f"{column.name}"
        )

    allowed_functions = {
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "COUNT",
    }

    for function in statement.find_all(
        exp.Func
    ):
        if isinstance(
            function,
            exp.And,
        ):
            continue

        function_name = (
            function.sql_name().upper()
        )

        if (
            function_name
            not in allowed_functions
        ):
            raise SqlValidationError(
                "Function is not allowed: "
                f"{function_name}"
            )

    sql_parameters = {
        parameter.name.casefold()
        for parameter
        in statement.find_all(
            exp.Parameter
        )
    }

    proposal_parameters = {
        parameter.name.casefold()
        for parameter
        in proposal.parameters
    }

    if (
        sql_parameters
        != proposal_parameters
    ):
        raise SqlValidationError(
            "SQL parameter names must exactly "
            "match proposal parameters."
        )

    return statement


# يستخرج التجميع والعمود والـAlias لكل Metric.
def _metric_signatures(
    # هو شجرة SQL فسرها SQLGlot وتأكدنا أنها جملة SELECT
    statement: exp.Select,
) -> Counter:
    # قاموس يحفظ كل بصمة وعدد مرات ظهورها.
    signatures = Counter()

    for item in statement.expressions:
        target = (
            item.this
            if isinstance(
                item,
                exp.Alias,
            )
            else item
        )

        if not isinstance(
            target,
            exp.AggFunc,
        ):
            continue

        columns = list(
            target.find_all(
                exp.Column
            )
        )
        # فرض عمود واحد وAlias
        if (
            len(columns) != 1
            or not item.alias
        ):
            raise SqlValidationError(
                "Each metric must aggregate "
                "one column and use "
                "a semantic alias."
            )
        # بناء البصمة
        signature = (
            # casefold() تمنع اختلاف حالة الأحرف من إفساد المقارنة
            target.key.casefold(), # عملية التجميع: sum
            columns[0].name.casefold(), # العمود الحقيقي: billedcost
            item.alias.casefold(), # الاسم الدلالي: billed_cost
        )

        signatures[signature] += 1

    return signatures


# يبني شكل Metrics المتوقع من Query Plan.
def _expected_metric_signatures(
    plan,
    fields: dict,
) -> Counter:
    return Counter(
        (
            _text(
                metric.aggregation
            ).casefold(),
            fields[
                _text(metric.name)
            ][
                "physical_column"
            ].casefold(),
            _text(
                metric.name
            ).casefold(),
        )
        for metric in plan.metrics
    )


# يستخرج Dimensions الموجودة داخل SELECT.
def _dimension_signatures(
    statement: exp.Select,
) -> Counter:
    signatures = Counter()

    for item in statement.expressions:
        target = (
            item.this
            if isinstance(
                item,
                exp.Alias,
            )
            else item
        )

        if isinstance(
            target,
            exp.Column,
        ):
            alias = (
                item.alias
                or target.name
            )

            signatures[
                (
                    target.name.casefold(),
                    alias.casefold(),
                )
            ] += 1

    return signatures


# يبني شكل Dimensions المتوقع من Query Plan.
def _expected_dimension_signatures(
    plan,
    fields: dict,
) -> Counter:
    return Counter(
        (
            fields[
                _text(dimension)
            ][
                "physical_column"
            ].casefold(),
            _text(
                dimension
            ).casefold(),
        )
        for dimension in plan.dimensions
    )


# يستخرج المقارنات البسيطة من WHERE.
def _where_comparisons(
    statement: exp.Select,
) -> list[exp.Expression]:
    where = statement.args.get(
        "where"
    )

    if where is None:
        return []

    comparison_types = (
        exp.EQ,
        exp.NEQ,
        exp.GT,
        exp.GTE,
        exp.LT,
        exp.LTE,
    )

    return [
        node
        for node in where.walk()
        if isinstance(
            node,
            comparison_types,
        )
    ]


# يقارن قيمة Parameter بالقيمة الموجودة في Query Plan.
def _values_equal(
    actual: Any,
    expected: Any,
    date_only: bool = False,
) -> bool:
    if date_only:
        return (
            str(actual)[:10]
            == str(expected)[:10]
        )

    return (
        actual == expected
        or str(actual) == str(expected)
    )


# يبحث داخل WHERE عن شرط Parameter واحد مطابق للشرط
# المتوقع من Query Plan، ثم يسجل المقارنة كمستهلكة
# حتى لا تُستخدم مرة ثانية أو تبقى شروط SQL إضافية.
def _consume_parameter_comparison(
    comparisons: list[exp.Expression],
    consumed: set[int],
    parameter_values: dict[str, Any],
    column_name: str,
    operator_type: type[exp.Expression],
    expected_value: Any,
    date_only: bool = False,
) -> None:

    # يمشي على شروط WHERE مع الاحتفاظ برقم كل شرط.
    for (
        index,
        comparison,
    ) in enumerate(comparisons):

        # يتجاوز الشرط إذا استُخدم سابقًا أو كانت
        # عمليته مختلفة عن العملية المطلوبة.
        if (
            index in consumed
            or not isinstance(
                comparison,
                operator_type,
            )
        ):
            continue

        # يشترط أن يكون الطرف الأيسر عمودًا.
        # مثال: ProviderName = @p_provider
        if not isinstance(
            comparison.left,
            exp.Column,
        ):
            continue

        # يتأكد أن SQL تستخدم العمود الحقيقي المتوقع.
        if (
            comparison.left.name.casefold()
            != column_name.casefold()
        ):
            continue

        # يشترط أن تكون القيمة Parameter آمنة،
        # وليست قيمة مكتوبة مباشرة داخل SQL.
        if not isinstance(
            comparison.right,
            exp.Parameter,
        ):
            continue

        # يستخرج اسم Parameter من الطرف الأيمن.
        # مثال: @p_provider يصبح p_provider.
        parameter_name = (
            comparison.right.name.casefold()
        )

        # يتأكد أن Parameter المستخدمة في SQL
        # موجودة فعلًا في SQL Proposal.
        if (
            parameter_name
            not in parameter_values
        ):
            continue

        # يأخذ القيمة الحقيقية للـParameter.
        # مثال: p_provider تعطي القيمة AWS.
        actual_value = parameter_values[
            parameter_name
        ]

        # يقارن قيمة Parameter بالقيمة التي طلبتها الخطة.
        if _values_equal(
            actual_value,
            expected_value,
            date_only,
        ):
            # يسجل رقم المقارنة حتى لا تستخدم مرة ثانية.
            consumed.add(index)
            return

    # إذا انتهى البحث دون تطابق، فهذا يعني أن SQL
    # لم تنفذ شرطًا مطلوبًا من Query Plan.
    raise SqlValidationError(
        "SQL does not implement "
        "the planned condition on "
        f"{column_name}."
    )


# يفرض شرط القيمة السالبة للمقياس السلبي.
def _consume_negative_scope(
    comparisons: list[exp.Expression],
    consumed: set[int],
    column_name: str,
) -> None:
    for (
        index,
        comparison,
    ) in enumerate(comparisons):
        if (
            index in consumed
            or not isinstance(
                comparison,
                exp.LT,
            )
        ):
            continue

        if not isinstance(
            comparison.left,
            exp.Column,
        ):
            continue

        if (
            comparison.left.name.casefold()
            != column_name.casefold()
        ):
            continue

        if (
            not isinstance(
                comparison.right,
                exp.Literal,
            )
            or comparison.right.is_string
        ):
            continue

        try:
            is_zero = (
                Decimal(
                    comparison.right.this
                )
                == 0
            )

        except InvalidOperation:
            is_zero = False

        if is_zero:
            consumed.add(index)
            return

    raise SqlValidationError(
        "Negative metric requires "
        f"{column_name} < 0."
    )


# يطابق ORDER BY وLIMIT مع Query Plan.
def _validate_sort_and_limit(
    plan,
    statement: exp.Select,
    fields: dict,
) -> None:
    order = statement.args.get(
        "order"
    )

    if plan.sort_by is None:
        if order is not None:
            raise SqlValidationError(
                "SQL adds ORDER BY "
                "not requested by the plan."
            )

    else:
        if (
            order is None
            or len(order.expressions) != 1
        ):
            raise SqlValidationError(
                "SQL must contain one "
                "planned ORDER BY field."
            )

        ordered = order.expressions[0]

        if not isinstance(
            ordered.this,
            exp.Column,
        ):
            raise SqlValidationError(
                "ORDER BY must reference "
                "a permitted field."
            )

        semantic_name = _text(
            plan.sort_by
        )

        allowed_names = {
            semantic_name.casefold(),
            fields[
                semantic_name
            ][
                "physical_column"
            ].casefold(),
        }

        if (
            ordered.this.name.casefold()
            not in allowed_names
        ):
            raise SqlValidationError(
                "ORDER BY does not "
                "match Query Plan."
            )

        direction = (
            "desc"
            if ordered.args.get("desc")
            else "asc"
        )

        if (
            direction
            != _text(plan.sort_direction)
        ):
            raise SqlValidationError(
                "ORDER BY direction does not "
                "match Query Plan."
            )

    limit = statement.args.get(
        "limit"
    )

    if (
        plan.dimensions
        and limit is None
    ):
        raise SqlValidationError(
            "Grouped queries must "
            "include LIMIT."
        )

    if limit is not None:
        expression = limit.expression

        if (
            not isinstance(
                expression,
                exp.Literal,
            )
            or expression.is_string
        ):
            raise SqlValidationError(
                "LIMIT must be "
                "a numeric literal."
            )

        if (
            int(expression.this)
            != plan.limit
        ):
            raise SqlValidationError(
                "SQL LIMIT does not "
                "match Query Plan."
            )


# يقارن Metrics وDimensions وFilters والوقت والترتيب.
def validate_sql_semantics(
    result: QueryGenerationResult,
    schema_context: dict,
    statement: exp.Select,
) -> None:
    plan = result.plan
    proposal = result.sql_proposal

    if proposal is None:
        raise SqlValidationError(
            "A ready plan requires SQL."
        )

    fields = get_field_map(
        schema_context
    )

    actual_metrics = _metric_signatures(
        statement
    )

    expected_metrics = (
        _expected_metric_signatures(
            plan,
            fields,
        )
    )

    if actual_metrics != expected_metrics:
        raise SqlValidationError(
            "SQL metrics do not "
            "match Query Plan."
        )

    actual_dimensions = (
        _dimension_signatures(
            statement
        )
    )

    expected_dimensions = (
        _expected_dimension_signatures(
            plan,
            fields,
        )
    )

    if (
        actual_dimensions
        != expected_dimensions
    ):
        raise SqlValidationError(
            "SQL dimensions do not "
            "match Query Plan."
        )

    group = statement.args.get(
        "group"
    )

    actual_groups = Counter()

    if group is not None:
        actual_groups = Counter(
            item.name.casefold()
            for item in group.expressions
            if isinstance(
                item,
                exp.Column,
            )
        )

    expected_groups = Counter(
        fields[
            _text(dimension)
        ][
            "physical_column"
        ].casefold()
        for dimension in plan.dimensions
    )

    if actual_groups != expected_groups:
        raise SqlValidationError(
            "GROUP BY does not "
            "match Query Plan."
        )

    parameter_values = {
        parameter.name.casefold(): (
            parameter.value
        )
        for parameter
        in proposal.parameters
    }

    comparisons = _where_comparisons(
        statement
    )

    consumed: set[int] = set()

    operator_types = {
        "eq": exp.EQ,
        "ne": exp.NEQ,
        "gt": exp.GT,
        "gte": exp.GTE,
        "lt": exp.LT,
        "lte": exp.LTE,
    }

    for query_filter in plan.filters:
        filter_name = _text(
            query_filter.column
        )

        _consume_parameter_comparison(
            comparisons=comparisons,
            consumed=consumed,
            parameter_values=parameter_values,
            column_name=fields[
                filter_name
            ][
                "physical_column"
            ],
            operator_type=operator_types[
                _text(
                    query_filter.operator
                )
            ],
            expected_value=(
                query_filter.value
            ),
        )

    if plan.time_range is not None:
        time_column = fields[
            "time_range"
        ][
            "physical_column"
        ]

        _consume_parameter_comparison(
            comparisons=comparisons,
            consumed=consumed,
            parameter_values=parameter_values,
            column_name=time_column,
            operator_type=exp.GTE,
            expected_value=(
                plan.time_range.start
            ),
            date_only=True,
        )

        _consume_parameter_comparison(
            comparisons=comparisons,
            consumed=consumed,
            parameter_values=parameter_values,
            column_name=time_column,
            operator_type=exp.LTE,
            expected_value=(
                plan.time_range.end
            ),
            date_only=True,
        )

    for metric in plan.metrics:
        metric_field = fields[
            _text(metric.name)
        ]

        if (
            metric_field["value_scope"]
            == "negative_values"
        ):
            _consume_negative_scope(
                comparisons=comparisons,
                consumed=consumed,
                column_name=metric_field[
                    "physical_column"
                ],
            )

    if (
        len(consumed)
        != len(comparisons)
    ):
        extra_conditions = [
            comparison.sql(
                dialect="bigquery"
            )
            for (
                index,
                comparison,
            ) in enumerate(comparisons)
            if index not in consumed
        ]

        raise SqlValidationError(
            "SQL contains filters not "
            "requested by Query Plan: "
            f"{extra_conditions}"
        )

    _validate_sort_and_limit(
        plan,
        statement,
        fields,
    )


# ينفذ الاستدعاء الأول ويمرر النتيجة على الفحوص المحلية.
def generate_finops_query(
    client,
    user_question: str,
    schema_context: dict,
    model_name: str,
) -> QueryGenerationResult:
    prompt = build_query_generation_prompt(
        user_question=user_question,
        schema_context=schema_context,
    )

    interaction = (
        client.interactions.create(
            model=model_name,
            input=prompt,
            # عقد النتيجة المطلوبة.
            response_format=(
                _structured_response_format(
                    QueryGenerationResult
                )
            ),
        )
    )

    output_text = (
        interaction.output_text
        or ""
    ).strip()

    if not output_text:
        raise RuntimeError(
            "Gemini returned an empty "
            "query generation result."
        )

    result = (
        QueryGenerationResult
        .model_validate_json(
            output_text
        )
    )

    if (
        result.plan.status
        is not QueryStatus.READY
    ):
        return result

    validate_query_plan(
        plan=result.plan,
        schema_context=schema_context,
    )

    statement = validate_sql_safety(
        proposal=result.sql_proposal,
        schema_context=schema_context,
    )

    validate_sql_semantics(
        result=result,
        schema_context=schema_context,
        statement=statement,
    )

    return result