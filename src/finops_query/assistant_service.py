"""
يشغّل رحلة FinOps الكاملة ويعيد نتيجة منظمة قابلة للاستخدام
من واجهة الأوامر CLI أو من FastAPI دون تكرار منطق المشروع.

تتكون الرحلة من استدعاءين إلى Gemini:
1. إنشاء Query Plan وSQL Proposal معًا والتحقق منهما محليًا.
2. صياغة الجواب النهائي من Dynamic Evidence الموثقة.
"""

import os
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.cloud import bigquery
from pydantic import BaseModel, ConfigDict, Field

from src.finops_query.query_answer import FinOpsQueryAnswer
from src.finops_query.query_answer_service import generate_finops_answer
from src.finops_query.query_bigquery_execution import (
    BigQueryExecutionPolicy,
    QueryDryRunReport,
    dry_run_query,
    execute_read_only_query,
)
from src.finops_query.query_dynamic_evidence import (
    DynamicQueryEvidence,
    build_dynamic_query_evidence,
)
from src.finops_query.query_generation_service import generate_finops_query
from src.finops_query.query_result_validator import validate_query_result
from src.finops_query.query_schema_loader import load_query_schema_catalog
from src.finops_query.query_sql_proposal import QueryGenerationResult


# القيم الافتراضية المعروفة لبيئة المشروع الحالية.
DEFAULT_PROJECT_ID = "data-ai-assistant-training"
DEFAULT_DATASET_ID = "cloud_finops"
DEFAULT_TABLE_ID = "billing_pipeline_day2"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


class FinOpsAssistantResult(BaseModel):
    """العقد المشترك الذي تعيده الرحلة إلى CLI أو FastAPI."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal[
        "answered",
        "no_data",
        "needs_clarification",
        "unsupported",
        "dry_run_only",
    ]
    message: str = Field(min_length=1)
    user_question: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    allowed_table: str = Field(min_length=1)
    query_generation: QueryGenerationResult
    dry_run_report: QueryDryRunReport | None = None
    dynamic_evidence: DynamicQueryEvidence | None = None
    final_answer: FinOpsQueryAnswer | None = None


# يقرأ متغيرًا إلزاميًا من البيئة ويرفض التشغيل إن كان مفقودًا.
def _require_environment_variable(variable_name: str) -> str:
    value = os.getenv(variable_name, "").strip()

    if not value:
        raise RuntimeError(f"{variable_name} is missing.")

    return value


# يقرأ قيمة منطقية من ملف البيئة بصيغة true أو false فقط.
def _read_boolean_environment_variable(
    variable_name: str,
    default: bool,
) -> bool:
    default_text = "true" if default else "false"
    value = os.getenv(variable_name, default_text).strip().lower()

    if value not in {"true", "false"}:
        raise ValueError(
            f"{variable_name} must be either true or false."
        )

    return value == "true"

# يستخدم الموقع المحدد في البيئة أو يقرأ موقع Dataset الحقيقي.
def _resolve_bigquery_location(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str,
) -> str:
    configured_location = os.getenv("BIGQUERY_LOCATION", "").strip()

    if configured_location:
        return configured_location

    dataset = client.get_dataset(f"{project_id}.{dataset_id}")
    location = (dataset.location or "").strip()

    if not location:
        raise RuntimeError(
            "BigQuery dataset location could not be determined."
        )

    return location


# يحول الخطة غير الجاهزة إلى رسالة واضحة دون الوصول إلى BigQuery.
def _build_non_ready_result(
    *,
    user_question: str,
    model_name: str,
    location: str,
    full_table_id: str,
    query_generation: QueryGenerationResult,
) -> FinOpsAssistantResult:
    plan = query_generation.plan

    if plan.status.value == "needs_clarification":
        status = "needs_clarification"
        message = plan.clarification_question or (
            "The financial question needs clarification."
        )
    else:
        status = "unsupported"
        message = plan.unsupported_reason or (
            "The financial question is not supported."
        )

    return FinOpsAssistantResult(
        status=status,
        message=message,
        user_question=user_question,
        model_name=model_name,
        location=location,
        allowed_table=full_table_id,
        query_generation=query_generation,
    )

def answer_finops_question(user_question: str) -> FinOpsAssistantResult:
    """يشغّل الرحلة المشتركة ويعيد عقدًا واحدًا للـCLI والـAPI."""

    load_dotenv()

    cleaned_question = user_question.strip()
    if not cleaned_question:
        raise ValueError("The user question is required.")

    gemini_api_key = _require_environment_variable("GEMINI_API_KEY")
    project_id = os.getenv(
        "GOOGLE_CLOUD_PROJECT",
        DEFAULT_PROJECT_ID,
    ).strip()
    dataset_id = os.getenv(
        "FINOPS_DATASET_ID",
        DEFAULT_DATASET_ID,
    ).strip()
    table_id = os.getenv(
        "FINOPS_TABLE_ID",
        DEFAULT_TABLE_ID,
    ).strip()
    model_name = os.getenv(
        "GEMINI_MODEL",
        DEFAULT_GEMINI_MODEL,
    ).strip()

    full_table_id = f"{project_id}.{dataset_id}.{table_id}"

    # ينشئ العميلين الحقيقيين المستخدمين في الرحلة.
    bigquery_client = bigquery.Client(project=project_id)
    gemini_client = genai.Client(api_key=gemini_api_key)

    try:
        location = _resolve_bigquery_location(
            client=bigquery_client,
            project_id=project_id,
            dataset_id=dataset_id,
        )

        # يحمل Physical Schema الحقيقية من BigQuery.
        catalog = load_query_schema_catalog(
            client=bigquery_client,
            project_id=project_id,
            dataset_id=dataset_id,
            allowed_table_ids=(table_id,),
            location=location,
        )

        # الاستدعاء الأول: Query Plan وSQL Proposal ثم التحقق المحلي.
        query_generation = generate_finops_query(
            client=gemini_client,
            user_question=cleaned_question,
            catalog=catalog,
            full_table_id=full_table_id,
            model_name=model_name,
        )

        sql_proposal = query_generation.sql_proposal
        if sql_proposal is None:
            return _build_non_ready_result(
                user_question=cleaned_question,
                model_name=model_name,
                location=location,
                full_table_id=full_table_id,
                query_generation=query_generation,
            )

        # يحدد حدود التكلفة والصفوف ووقت الانتظار.
        execution_policy = BigQueryExecutionPolicy(
            location=location,
            maximum_bytes_billed=int(
                os.getenv(
                    "FINOPS_MAXIMUM_BYTES_BILLED",
                    str(100 * 1024 * 1024),
                )
            ),
            max_result_rows=int(
                os.getenv("FINOPS_MAX_RESULT_ROWS", "100")
            ),
            timeout_seconds=int(
                os.getenv("FINOPS_QUERY_TIMEOUT_SECONDS", "60")
            ),
        )

        # يفحص SQL ويقدّر Bytes دون تنفيذ الاستعلام الحقيقي.
        dry_run_report = dry_run_query(
            client=bigquery_client,
            proposal=sql_proposal,
            policy=execution_policy,
        )

        execute_queries = _read_boolean_environment_variable(
            "FINOPS_EXECUTE_QUERIES",
            default=False,
        )

        if not execute_queries:
            return FinOpsAssistantResult(
                status="dry_run_only",
                message=(
                    "The query passed validation and BigQuery Dry Run, "
                    "but execution is disabled."
                ),
                user_question=cleaned_question,
                model_name=model_name,
                location=location,
                allowed_table=full_table_id,
                query_generation=query_generation,
                dry_run_report=dry_run_report,
            )

        # ينفذ SQL نفسها التي اجتازت Dry Run ثم يتحقق من النتيجة.
        execution_result = execute_read_only_query(
            client=bigquery_client,
            proposal=sql_proposal,
            policy=execution_policy,
            dry_run_report=dry_run_report,
        )
        validate_query_result(
            query_plan=query_generation.plan,
            result=execution_result,
        )

        # يحول الصفوف الحقيقية إلى Evidence صغيرة وموثقة.
        dynamic_evidence = build_dynamic_query_evidence(
            user_question=cleaned_question,
            query_plan=query_generation.plan,
            source_table=full_table_id,
            result=execution_result,
        )

        # الاستدعاء الثاني: يصوغ الجواب من Evidence فقط ويتحقق منه.
        final_answer = generate_finops_answer(
            client=gemini_client,
            evidence=dynamic_evidence,
            model_name=model_name,
        )

        return FinOpsAssistantResult(
            status=final_answer.status.value,
            message=final_answer.answer,
            user_question=cleaned_question,
            model_name=model_name,
            location=location,
            allowed_table=full_table_id,
            query_generation=query_generation,
            dry_run_report=dry_run_report,
            dynamic_evidence=dynamic_evidence,
            final_answer=final_answer,
        )
    finally:
        # يغلق اتصال BigQuery الذي أنشأته هذه الرحلة.
        bigquery_client.close()


