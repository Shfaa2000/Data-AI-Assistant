"""
يحول SQL Parameters، وينفذ Dry Run والاستعلام الحقيقي،
ويتحقق من النتيجة ثم يبني Dynamic Evidence الموثقة.
"""

import json
import math

from datetime import (
    date,
    datetime,
    timezone,
)
from decimal import Decimal
from hashlib import sha256
from typing import Any

from google.cloud import bigquery

from src.finops_query.models import (
    BigQueryExecutionPolicy,
    DynamicQueryEvidence,
    FinOpsQueryPlan,
    GeneratedSqlProposal,
    QueryDryRunReport,
    QueryExecutionResult,
    QueryStatus,
)


class BigQueryServiceError(ValueError):
    """يظهر عند فشل الربط أو التكلفة أو التنفيذ أو النتيجة."""


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

# يحول قيمة Parameter النصية إلى نوع Python
# المناسب الذي تستطيع BigQuery استخدامه.
def _coerce_parameter_value(
    data_type: str,
    value: Any,
) -> Any:
    if data_type == "STRING":
        return str(value)

    if data_type == "INT64":
        if isinstance(
            value,
            bool,
        ):
            raise BigQueryServiceError(
                "BOOL cannot be used "
                "as INT64."
            )

        return int(value)

    if data_type == "FLOAT64":
        return float(value)

    if data_type == "BOOL":
        if isinstance(
            value,
            bool,
        ):
            return value

        raise BigQueryServiceError(
            "BOOL parameter requires "
            "a boolean value."
        )

    if data_type == "DATE":
        if isinstance(
            value,
            datetime,
        ):
            return value.date()

        if isinstance(
            value,
            date,
        ):
            return value

        try:
            return date.fromisoformat(
                str(value).strip()
            )

        except ValueError as exc:
            raise BigQueryServiceError(
                "Invalid DATE parameter "
                f"value: {value!r}."
            ) from exc

    if data_type == "TIMESTAMP":
        if isinstance(
            value,
            datetime,
        ):
            parsed_value = value

        else:
            timestamp_text = str(
                value
            ).strip()

            # يحول صيغة مثل:
            # 2024-09-01 00:00:00 UTC
            # إلى صيغة ISO تقبلها Python.
            if timestamp_text.upper().endswith(
                " UTC"
            ):
                timestamp_text = (
                    timestamp_text[:-4]
                    + "+00:00"
                )

            # يحول صيغة ISO التي تنتهي بـ Z
            # إلى UTC Offset تقبله Python 3.10.
            elif timestamp_text.endswith(
                "Z"
            ):
                timestamp_text = (
                    timestamp_text[:-1]
                    + "+00:00"
                )

            try:
                parsed_value = (
                    datetime.fromisoformat(
                        timestamp_text
                    )
                )

            except ValueError as exc:
                raise BigQueryServiceError(
                    "Invalid TIMESTAMP "
                    "parameter value: "
                    f"{value!r}."
                ) from exc

        # إذا لم تحتوِ القيمة على Timezone،
        # نعاملها كتوقيت UTC.
        if parsed_value.tzinfo is None:
            parsed_value = (
                parsed_value.replace(
                    tzinfo=timezone.utc
                )
            )

        return parsed_value

    raise BigQueryServiceError(
        "Unsupported parameter type: "
        f"{data_type}"
    )

# يحول Parameters المقترحة إلى قيم typed ويربطها بأسماء
# يمكن لـBigQuery استخدامها بأمان عند تنفيذ SQL.
def build_bigquery_parameters(
    proposal: GeneratedSqlProposal,
) -> list[
    bigquery.ScalarQueryParameter # الخرج قائمة من كائنات يفهمها BigQuery
]:
    query_parameters = []

    for parameter in proposal.parameters:
        data_type = _text(
            parameter.data_type
        ).upper()

        # تحوّل القيمة إلى نوع Python الصحيح
        value = _coerce_parameter_value(
            data_type=data_type,
            value=parameter.value,
        )

        query_parameters.append(
            bigquery.ScalarQueryParameter(
                parameter.name,
                data_type,
                value,
            )
        )

    return query_parameters


# ينشئ بصمة تثبت أن SQL لم تتغير بعد Dry Run.
def _sql_fingerprint(
    sql: str,
) -> str:
    return sha256(
        sql.encode("utf-8")
    ).hexdigest()


# يفحص SQL ويقدر حجم القراءة دون تنفيذها.
def dry_run_query(
    client: bigquery.Client,
    proposal: GeneratedSqlProposal,
    policy: BigQueryExecutionPolicy,
) -> QueryDryRunReport:
    #  تعليمات نرسلها إلى BigQuery مع المهمة.
    job_config = (
        bigquery.QueryJobConfig(
            # افحص SQL وقدّر القراءة، لكن لا ترجع نتائج فعلية.
            dry_run=True,
            # لا تعتمد على نتيجة قديمة مخزنة في Cache، لأننا نريد تقديرًا حقيقيًا لحجم البيانات التي سيقرأها الاستعلام.
            use_query_cache=False,
            # استخدم GoogleSQL الحديث، وليس صيغة BigQuery القديمة Legacy SQL.
            use_legacy_sql=False,
            # اربط أسماء الـparameters بقيمها وأنواعها أثناء فحص SQL.
            query_parameters=(
                build_bigquery_parameters(
                    proposal
                )
            ),
        )
    )
    # هو كائن يمثل مهمة Dry Run التي أرسلناها إلى BigQuery.
    query_job = client.query(
        proposal.sql,
        job_config=job_config,
        location=policy.location,
    )

    total_bytes = int(
        query_job.total_bytes_processed
        or 0
    )

    if (
        total_bytes
        > policy.maximum_bytes_billed
    ):
        raise BigQueryServiceError(
            "Dry Run would process "
            f"{total_bytes} bytes; "
            "the maximum is "
            f"{policy.maximum_bytes_billed}."
        )

    return QueryDryRunReport(
        sql_sha256=_sql_fingerprint(
            proposal.sql
        ),
        location=policy.location,
        total_bytes_processed=(
            total_bytes
        ),
        maximum_bytes_billed=(
            policy.maximum_bytes_billed
        ),
        job_id=query_job.job_id,
    )


# ينفذ SQL نفسها التي اجتازت Dry Run.
def execute_query(
    client: bigquery.Client,
    proposal: GeneratedSqlProposal,
    policy: BigQueryExecutionPolicy,
    dry_run_report: QueryDryRunReport,
) -> QueryExecutionResult:
    current_fingerprint = (
        _sql_fingerprint(
            proposal.sql
        )
    )

    if (
        current_fingerprint
        != dry_run_report.sql_sha256
    ):
        raise BigQueryServiceError(
            "SQL changed after Dry Run."
        )

    if (
        policy.location
        != dry_run_report.location
    ):
        raise BigQueryServiceError(
            "Dry Run and execution "
            "locations do not match."
        )

    job_config = (
        bigquery.QueryJobConfig(
            # استخدام GoogleSQL.
            use_legacy_sql=False,
            use_query_cache=True,
            maximum_bytes_billed=(
                policy.maximum_bytes_billed
            ),
            query_parameters=(
                build_bigquery_parameters(
                    proposal
                )
            ),
            labels={
                "component": "finops-query",
                "mode": "read-only",
            },
        )
    )

    query_job = client.query(
        proposal.sql,
        job_config=job_config,
        location=policy.location,
    )

    iterator = query_job.result(
        timeout=policy.timeout_seconds,
        max_results=(
            policy.max_result_rows + 1
        ),
    )

    total_rows = int(
        iterator.total_rows
        or 0
    )

    if (
        total_rows
        > policy.max_result_rows
    ):
        raise BigQueryServiceError(
            "BigQuery returned "
            f"{total_rows} rows; "
            "the maximum is "
            f"{policy.max_result_rows}."
        )

    rows = [
        dict(row.items())
        for row in iterator
    ]

    columns = [
        field.name
        for field in iterator.schema
    ]

    return QueryExecutionResult(
        columns=columns,
        rows=rows,
        total_rows=total_rows,
        total_bytes_processed=int(
            query_job.total_bytes_processed
            or 0
        ),
        job_id=str(
            query_job.job_id
        ),
        location=policy.location,
    )


# يتأكد من أن قيمة Metric رقم صالح أو NULL.
def _validate_metric_value(
    metric_name: str,
    value: Any,
) -> None:
    if value is None:
        return

    if isinstance(
        value,
        bool,
    ):
        raise BigQueryServiceError(
            f"Metric {metric_name!r} "
            "returned BOOL."
        )

    if isinstance(
        value,
        Decimal,
    ):
        if value.is_finite():
            return

    elif isinstance(
        value,
        (int, float),
    ):
        if (
            not isinstance(
                value,
                float,
            )
            or math.isfinite(value)
        ):
            return

    raise BigQueryServiceError(
        f"Metric {metric_name!r} "
        "is not a finite number."
    )


# يقارن أعمدة وصفوف BigQuery بما تتوقعه Query Plan.
def validate_query_result(
    query_plan: FinOpsQueryPlan,
    result: QueryExecutionResult,
) -> None:
    if (
        query_plan.status
        is not QueryStatus.READY
    ):
        raise BigQueryServiceError(
            "Only a ready plan "
            "may have results."
        )

    dimensions = [
        _text(item)
        for item
        in query_plan.dimensions
    ]

    metrics = [
        _text(item.name)
        for item
        in query_plan.metrics
    ]

    expected_columns = (
        dimensions
        + metrics
    )

    if (
        len(expected_columns)
        != len(set(expected_columns))
    ):
        raise BigQueryServiceError(
            "Query Plan contains "
            "duplicate output columns."
        )

    if (
        set(result.columns)
        != set(expected_columns)
    ):
        raise BigQueryServiceError(
            "Unexpected result columns. "
            f"Expected {expected_columns}, "
            f"got {result.columns}."
        )

    if (
        result.total_rows
        != len(result.rows)
    ):
        raise BigQueryServiceError(
            "Result row count "
            "is inconsistent."
        )

    if (
        result.total_rows
        > query_plan.limit
    ):
        raise BigQueryServiceError(
            "Result exceeded "
            "the Query Plan limit."
        )

    if (
        not dimensions
        and metrics
        and result.total_rows != 1
    ):
        raise BigQueryServiceError(
            "A scalar aggregate must "
            "return exactly one row."
        )

    for row in result.rows:
        if (
            set(row)
            != set(expected_columns)
        ):
            raise BigQueryServiceError(
                "A result row has missing "
                "or unexpected columns."
            )

        for metric_name in metrics:
            _validate_metric_value(
                metric_name=metric_name,
                value=row[metric_name],
            )


# يحول النتيجة الموثقة إلى Evidence صغيرة.
def build_dynamic_evidence(
    user_question: str,
    query_plan: FinOpsQueryPlan,
    source_table: str,
    result: QueryExecutionResult,
) -> DynamicQueryEvidence:
    plan_dictionary = json.loads(
        query_plan.model_dump_json()
    )

    return DynamicQueryEvidence(
        user_question=(
            user_question.strip()
        ),
        intent=str(
            plan_dictionary["intent"]
        ),
        query_plan=plan_dictionary,
        source_table=source_table,
        columns=result.columns,
        rows=result.rows,
        row_count=result.total_rows,
        total_bytes_processed=(
            result.total_bytes_processed
        ),
        job_id=result.job_id,
        location=result.location,
    )