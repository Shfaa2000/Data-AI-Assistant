"""ينفذ SQL المقترحة على BigQuery بعد Dry Run وحدود التكلفة والصفوف."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Any

from google.cloud import bigquery
from pydantic import BaseModel, ConfigDict, Field

from .query_sql_proposal import GeneratedSqlProposal

class QueryExecutionError(ValueError):
    """الخطأ الأساسي لمرحلة تنفيذ استعلام BigQuery."""


class QueryParameterBindingError(QueryExecutionError):
    """يظهر عندما يتعذر تحويل Parameter إلى نوع تفهمه BigQuery."""


class QueryCostLimitError(QueryExecutionError):
    """يظهر عندما تتجاوز القراءة المتوقعة الحد المالي المسموح."""


class QueryResultLimitError(QueryExecutionError):
    """يظهر عندما يتجاوز عدد الصفوف الحد المسموح."""


class BigQueryExecutionPolicy(BaseModel):
    """يحدد الحدود التي يجب احترامها في Dry Run والتنفيذ الحقيقي."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    location: str = Field(min_length=1)
    maximum_bytes_billed: int = Field(
        default=100 * 1024 * 1024,
        gt=0,
    )
    max_result_rows: int = Field(default=100, ge=1, le=1000)
    timeout_seconds: int = Field(default=60, ge=1, le=300)


class QueryDryRunReport(BaseModel):
    """يحفظ نتيجة فحص BigQuery قبل التنفيذ الحقيقي."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sql_sha256: str
    location: str
    total_bytes_processed: int = Field(ge=0)
    maximum_bytes_billed: int = Field(gt=0)
    job_id: str | None = None


class QueryExecutionResult(BaseModel):
    """يحفظ الصفوف وبيانات التنفيذ التي أعادتها BigQuery."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int = Field(ge=0)
    total_bytes_processed: int = Field(ge=0)
    job_id: str
    location: str

# يحول Enum أو النص العادي إلى قيمة نصية موحدة.
def _text(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return str(value)


# يوحد أسماء أنواع GoogleSQL المدعومة داخل المشروع.
def _normalize_parameter_type(data_type: Any) -> str:
    normalized = _text(data_type).strip().upper()

    aliases = {
        "INTEGER": "INT64",
        "FLOAT": "FLOAT64",
        "BOOLEAN": "BOOL",
    }

    normalized = aliases.get(normalized, normalized)

    allowed_types = {
        "STRING",
        "INT64",
        "FLOAT64",
        "BOOL",
        "DATE",
        "TIMESTAMP",
        "NUMERIC",
    }

    if normalized not in allowed_types:
        raise QueryParameterBindingError(
            f"Unsupported BigQuery parameter type: {normalized}"
        )

    return normalized

# يحول قيمة Parameter إلى نوع Python المناسب قبل إرسالها إلى BigQuery.
def _coerce_parameter_value(data_type: str, value: Any) -> Any:
    if value is None:
        return None

    if data_type == "STRING":
        return str(value)

    if data_type == "INT64":
        if isinstance(value, bool):
            raise QueryParameterBindingError(
                "BOOL cannot be used as an INT64 parameter."
            )
        return int(value)

    if data_type == "FLOAT64":
        return float(value)

    if data_type == "NUMERIC":
        return Decimal(str(value))

    if data_type == "BOOL":
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized == "true":
                return True

            if normalized == "false":
                return False

        raise QueryParameterBindingError(
            f"Invalid BOOL parameter value: {value!r}"
        )

    if data_type == "DATE":
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        return date.fromisoformat(str(value))

    if data_type == "TIMESTAMP":
        if isinstance(value, datetime):
            parsed_value = value
        else:
            parsed_value = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )

        if parsed_value.tzinfo is None:
            parsed_value = parsed_value.replace(tzinfo=timezone.utc)

        return parsed_value

    raise QueryParameterBindingError(
        f"Cannot bind parameter type: {data_type}"
    )

# يحول Parameters الموجودة في SQL Proposal إلى ScalarQueryParameter.
def build_bigquery_parameters(
    proposal: GeneratedSqlProposal,
) -> list[bigquery.ScalarQueryParameter]:
    query_parameters: list[bigquery.ScalarQueryParameter] = []

    for parameter in proposal.parameters:
        data_type = _normalize_parameter_type(parameter.data_type)
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

# ينشئ بصمة ثابتة لنتأكد أن SQL المنفذة هي نفسها التي اجتازت Dry Run.
def _sql_fingerprint(sql: str) -> str:
    return sha256(sql.encode("utf-8")).hexdigest()

# يفحص SQL في BigQuery ويقيس القراءة المتوقعة دون تنفيذ الاستعلام الحقيقي.
def dry_run_query(
    client: bigquery.Client,
    proposal: GeneratedSqlProposal,
    policy: BigQueryExecutionPolicy,
) -> QueryDryRunReport:
    job_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
        use_legacy_sql=False,
        query_parameters=build_bigquery_parameters(proposal),
    )

    query_job = client.query(
        proposal.sql,
        job_config=job_config,
        location=policy.location,
    )

    total_bytes = int(query_job.total_bytes_processed or 0)

    if total_bytes > policy.maximum_bytes_billed:
        raise QueryCostLimitError(
            "Dry Run rejected the query because it would process "
            f"{total_bytes} bytes, while the allowed maximum is "
            f"{policy.maximum_bytes_billed} bytes."
        )

    return QueryDryRunReport(
        sql_sha256=_sql_fingerprint(proposal.sql),
        location=policy.location,
        total_bytes_processed=total_bytes,
        maximum_bytes_billed=policy.maximum_bytes_billed,
        job_id=query_job.job_id,
    )

# ينفذ SQL بعد مطابقة بصمتها مع Dry Run ويعيد الصفوف بعقد منظم.
def execute_read_only_query(
    client: bigquery.Client,
    proposal: GeneratedSqlProposal,
    policy: BigQueryExecutionPolicy,
    dry_run_report: QueryDryRunReport,
) -> QueryExecutionResult:
    current_fingerprint = _sql_fingerprint(proposal.sql)

    if current_fingerprint != dry_run_report.sql_sha256:
        raise QueryExecutionError(
            "The SQL changed after Dry Run and must be checked again."
        )

    if dry_run_report.location != policy.location:
        raise QueryExecutionError(
            "Dry Run and execution locations do not match."
        )

    job_config = bigquery.QueryJobConfig(
        use_legacy_sql=False,
        use_query_cache=True,
        maximum_bytes_billed=policy.maximum_bytes_billed,
        query_parameters=build_bigquery_parameters(proposal),
        labels={
            "component": "finops-query",
            "mode": "read-only",
        },
    )

    query_job = client.query(
        proposal.sql,
        job_config=job_config,
        location=policy.location,
    )

    row_iterator = query_job.result(
        timeout=policy.timeout_seconds,
        max_results=policy.max_result_rows + 1,
    )

    total_rows = int(row_iterator.total_rows or 0)

    if total_rows > policy.max_result_rows:
        raise QueryResultLimitError(
            f"BigQuery returned {total_rows} rows, while only "
            f"{policy.max_result_rows} rows are allowed."
        )

    rows = [dict(row.items()) for row in row_iterator]
    columns = [field.name for field in row_iterator.schema]

    return QueryExecutionResult(
        columns=columns,
        rows=rows,
        total_rows=total_rows,
        total_bytes_processed=int(
            query_job.total_bytes_processed or 0
        ),
        job_id=str(query_job.job_id),
        location=policy.location,
    )

