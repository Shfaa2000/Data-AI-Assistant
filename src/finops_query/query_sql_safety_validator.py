"""يستقبل SQL Proposal، ويحلل SQL كشجرة، ثم يرفض أي شكل خارج مجموعة الاستعلامات الآمنة التي يدعمها الـMVP."""

from collections.abc import Mapping
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError

from .query_sql_proposal import GeneratedSqlProposal


class SqlSafetyValidationError(ValueError):
    """يُرفع عندما تكون SQL المقترحة غير آمنة أو خارج نطاق الـMVP."""

# تقرأ قيمة من Dictionary أو Pydantic Model بالطريقة نفسها.
def _read_value(item: Any, name: str) -> Any:
    if isinstance(item, Mapping):
        return item[name]

    return getattr(item, name)


# تستخرج قائمة الأعمدة الحقيقية التي يسمح التطبيق باستخدامها.
def _allowed_columns(
    schema_context: Mapping[str, Any],
) -> set[str]:
    return {
        str(
            _read_value(field, "physical_column")
        ).casefold()
        for field in schema_context["fields"]
    }


# تعيد هوية جدول BigQuery كاملة من عقدة SQLGlot.
def _full_table_name(table: exp.Table) -> str:
    parts = (
        table.catalog,
        table.db,
        table.name,
    )

    return ".".join(
        part
        for part in parts
        if part
    )

# يسمح باسم Alias داخل ORDER BY، لكنه لا يعامله كعمود حقيقي في WHERE.
def _is_order_by_alias(
    column: exp.Column,
    aliases: set[str],
) -> bool:
    if column.name.casefold() not in aliases:
        return False

    current = column.parent

    while current is not None:
        if isinstance(current, exp.Order):
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

# يحلل SQL باستخدام BigQuery Dialect، ثم يسمح باستعلام SELECT واحد فقط.
def _parse_single_select(
    sql: str,
) -> exp.Select:
    if "--" in sql or "/*" in sql:
        raise SqlSafetyValidationError(
            "SQL comments are not allowed."
        )

    try:
        statements = [
            statement
            for statement in sqlglot.parse(
                sql,
                read="bigquery",
            )
            if statement is not None
        ]
    except (ParseError, TokenError) as exc:
        raise SqlSafetyValidationError(
            f"Invalid GoogleSQL: {exc}"
        ) from exc

    if len(statements) != 1:
        raise SqlSafetyValidationError(
            "Exactly one SQL statement is required."
        )

    statement = statements[0]

    if not isinstance(statement, exp.Select):
        raise SqlSafetyValidationError(
            "Only a SELECT statement is allowed."
        )

    return statement

# يجعل نطاق الـMVP صارمًا: لا Joins ولا Subqueries ولا CTEs ولا Window Functions.
def _validate_query_shape(
    statement: exp.Select,
) -> None:
    if statement.args.get("with_") is not None:
        raise SqlSafetyValidationError(
            "CTEs are not allowed in the MVP."
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

    for node_type in forbidden_nodes:
        if statement.find(node_type) is not None:
            raise SqlSafetyValidationError(
                "Joins, subqueries, set operations, "
                "UNNEST, and windows are not allowed."
            )

    forbidden_clauses = (
        "having",
        "qualify",
        "offset",
    )

    for clause_name in forbidden_clauses:
        if statement.args.get(clause_name) is not None:
            raise SqlSafetyValidationError(
                f"{clause_name.upper()} is not allowed."
            )

    if statement.find(exp.Star) is not None:
        raise SqlSafetyValidationError(
            "SELECT * and COUNT(*) are not allowed."
        )

# يتأكد أن SQL تستخدم جدولًا واحدًا فقط، وهو الجدول الموجود في Allowlist.
def _validate_table(
    statement: exp.Select,
    schema_context: Mapping[str, Any],
) -> None:
    tables = list(
        statement.find_all(exp.Table)
    )

    if len(tables) != 1:
        raise SqlSafetyValidationError(
            "Exactly one table must be referenced."
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
        raise SqlSafetyValidationError(
            f"Table is not allowed: {actual_table}"
        )


# يتأكد أن كل اسم عمود موجود في Physical Schema المسموحة.
def _validate_columns(
    statement: exp.Select,
    schema_context: Mapping[str, Any],
) -> None:
    allowed_columns = _allowed_columns(
        schema_context
    )

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

        if _is_order_by_alias(
            column,
            aliases,
        ):
            continue

        raise SqlSafetyValidationError(
            f"Column is not allowed: "
            f"{column.name}"
        )

# يسمح فقط بالتجميعات المطلوبة في النسخة الحالية.
def _validate_functions(
    statement: exp.Select,
) -> None:
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
        function_name = (
            function.sql_name().upper()
        )

        if function_name not in allowed_functions:
            raise SqlSafetyValidationError(
                "Function is not allowed: "
                f"{function_name}"
            )


# يطابق Parameters المكتوبة داخل SQL مع القائمة المنظمة في Proposal.
def _validate_parameters(
    statement: exp.Select,
    proposal: GeneratedSqlProposal,
) -> None:
    sql_parameter_names = {
        parameter.name
        for parameter
        in statement.find_all(exp.Parameter)
    }

    proposal_parameter_names = {
        parameter.name
        for parameter
        in proposal.parameters
    }

    if (
        sql_parameter_names
        != proposal_parameter_names
    ):
        raise SqlSafetyValidationError(
            "SQL parameter names must exactly "
            "match proposal parameters. "
            f"SQL={sorted(sql_parameter_names)}, "
            "proposal="
            f"{sorted(proposal_parameter_names)}"
        )

# ينفذ جميع فحوص الأمان ويعيد AST لتستخدمها طبقة Semantic Validation.
def validate_sql_safety(
    proposal: GeneratedSqlProposal,
    schema_context: Mapping[str, Any],
) -> exp.Select:
    sql = proposal.sql.strip()

    statement = _parse_single_select(sql)

    _validate_query_shape(statement)

    _validate_table(
        statement,
        schema_context,
    )

    _validate_columns(
        statement,
        schema_context,
    )

    _validate_functions(statement)

    _validate_parameters(
        statement,
        proposal,
    )

    return statement