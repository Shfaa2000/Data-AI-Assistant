"""يبني Evidence مالية صغيرة من نتيجة BigQuery الموثقة."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .query_bigquery_execution import QueryExecutionResult


class DynamicQueryEvidence(BaseModel):
    """يمثل البيانات الحقيقية المسموح باستخدامها لصياغة الجواب."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_type: Literal["bigquery_query_result"] = (
        "bigquery_query_result"
    )
    user_question: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    query_plan: dict[str, Any]
    source_table: str = Field(min_length=1)
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int = Field(ge=0)
    total_bytes_processed: int = Field(ge=0)
    job_id: str
    location: str

# يحول Pydantic Model إلى dict يمكن إدخاله بأمان في Evidence.
def _model_to_json_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump_json"):
        return json.loads(model.model_dump_json())

    if isinstance(model, dict):
        return json.loads(json.dumps(model, default=str))

    raise TypeError(
        "The Query Plan must be a Pydantic model or dictionary."
    )

# يبني النسخة الصغيرة والموثقة التي ستُستخدم لصياغة الإجابة.
def build_dynamic_query_evidence(
    user_question: str,
    query_plan: Any,
    source_table: str,
    result: QueryExecutionResult,
) -> DynamicQueryEvidence:
    plan_dict = _model_to_json_dict(query_plan)

    return DynamicQueryEvidence(
        user_question=user_question.strip(),
        intent=str(plan_dict["intent"]),
        query_plan=plan_dict,
        source_table=source_table,
        columns=result.columns,
        rows=result.rows,
        row_count=result.total_rows,
        total_bytes_processed=result.total_bytes_processed,
        job_id=result.job_id,
        location=result.location,
    )

