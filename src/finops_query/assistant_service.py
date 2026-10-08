"""
يقود رحلة FinOps Query الكاملة ويعيد نتيجة مشتركة
تستخدمها واجهتا CLI وFastAPI دون تكرار المنطق.
"""

import os

from dotenv import load_dotenv
from google import genai
from google.cloud import bigquery

from src.finops_query.answer_service import (
    generate_finops_answer,
)
from src.finops_query.bigquery_service import (
    build_dynamic_evidence,
    dry_run_query,
    execute_query,
    validate_query_result,
)
from src.finops_query.models import (
    BigQueryExecutionPolicy,
    FinOpsAssistantResult,
    QueryGenerationResult,
)
from src.finops_query.query_service import (
    generate_finops_query,
)
from src.finops_query.schema import (
    load_schema_context,
)


DEFAULT_PROJECT_ID = (
    "data-ai-assistant-training"
)

DEFAULT_DATASET_ID = (
    "cloud_finops"
)

DEFAULT_TABLE_ID = (
    "billing_pipeline_day2"
)

DEFAULT_GEMINI_MODEL = (
    "gemini-3.5-flash-lite"
)


# يقرأ متغيرًا إلزاميًا ويرفض التشغيل عندما يكون مفقودًا.
def _require_environment_variable(
    variable_name: str,
) -> str:
    value = os.getenv(
        variable_name,
        "",
    ).strip()

    if not value:
        raise RuntimeError(
            f"{variable_name} is missing."
        )

    return value


# يحول قيمة بيئة نصية إلى True أو False.
def _read_boolean_environment_variable(
    variable_name: str,
    default: bool,
) -> bool:
    default_text = (
        "true"
        if default
        else "false"
    )

    value = os.getenv(
        variable_name,
        default_text,
    ).strip().lower()

    if value not in {
        "true",
        "false",
    }:
        raise ValueError(
            f"{variable_name} must be "
            "either true or false."
        )

    return value == "true"


# يستخدم الموقع المحدد أو يقرأ موقع Dataset.
def _resolve_bigquery_location(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str,
) -> str:
    configured_location = os.getenv(
        "BIGQUERY_LOCATION",
        "",
    ).strip()

    if configured_location:
        return configured_location

    dataset = client.get_dataset(
        f"{project_id}.{dataset_id}"
    )

    location = (
        dataset.location
        or ""
    ).strip()

    if not location:
        raise RuntimeError(
            "BigQuery dataset location "
            "could not be determined."
        )

    return location


# يحول الخطة غير الجاهزة إلى جواب دون تنفيذ BigQuery.
def _build_non_ready_result(
    user_question: str,
    model_name: str,
    location: str,
    full_table_id: str,
    query_generation: QueryGenerationResult,
) -> FinOpsAssistantResult:
    plan = query_generation.plan

    if (
        plan.status.value
        == "needs_clarification"
    ):
        result_status = (
            "needs_clarification"
        )

        message = (
            plan.clarification_question
            or (
                "The question needs "
                "clarification."
            )
        )

    else:
        result_status = "unsupported"

        message = (
            plan.unsupported_reason
            or (
                "The question "
                "is not supported."
            )
        )

    return FinOpsAssistantResult(
        status=result_status,
        message=message,
        user_question=user_question,
        model_name=model_name,
        location=location,
        allowed_table=full_table_id,
        query_generation=(
            query_generation
        ),
    )


# يشغل الرحلة الكاملة ويعيد عقدًا واحدًا للـCLI والـAPI.
def answer_finops_question(
    user_question: str,
) -> FinOpsAssistantResult:
    load_dotenv()

    question = user_question.strip()

    if not question:
        raise ValueError(
            "The user question is required."
        )

    gemini_api_key = (
        _require_environment_variable(
            "GEMINI_API_KEY"
        )
    )

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

    full_table_id = (
        f"{project_id}."
        f"{dataset_id}."
        f"{table_id}"
    )

    bigquery_client = bigquery.Client(
        project=project_id
    )

    gemini_client = genai.Client(
        api_key=gemini_api_key
    )

    try:
        location = (
            _resolve_bigquery_location(
                client=bigquery_client,
                project_id=project_id,
                dataset_id=dataset_id,
            )
        )

        schema_context = (
            load_schema_context(
                client=bigquery_client,
                full_table_id=(
                    full_table_id
                ),
            )
        )

        # الاستدعاء الأول: Query Plan وSQL Proposal.
        query_generation = (
            generate_finops_query(
                client=gemini_client,
                user_question=question,
                schema_context=(
                    schema_context
                ),
                model_name=model_name,
            )
        )

        sql_proposal = (
            query_generation.sql_proposal
        )

        if sql_proposal is None:
            return _build_non_ready_result(
                user_question=question,
                model_name=model_name,
                location=location,
                full_table_id=(
                    full_table_id
                ),
                query_generation=(
                    query_generation
                ),
            )

        execution_policy = (
            BigQueryExecutionPolicy(
                location=location,
                maximum_bytes_billed=int(
                    os.getenv(
                        (
                            "FINOPS_"
                            "MAXIMUM_BYTES_BILLED"
                        ),
                        str(
                            100
                            * 1024
                            * 1024
                        ),
                    )
                ),
                max_result_rows=int(
                    os.getenv(
                        "FINOPS_MAX_RESULT_ROWS",
                        "100",
                    )
                ),
                timeout_seconds=int(
                    os.getenv(
                        (
                            "FINOPS_QUERY_"
                            "TIMEOUT_SECONDS"
                        ),
                        "60",
                    )
                ),
            )
        )

        dry_run_report = dry_run_query(
            client=bigquery_client,
            proposal=sql_proposal,
            policy=execution_policy,
        )

        execute_queries = (
            _read_boolean_environment_variable(
                "FINOPS_EXECUTE_QUERIES",
                default=False,
            )
        )

        if not execute_queries:
            return FinOpsAssistantResult(
                status="dry_run_only",
                message=(
                    "The query passed validation "
                    "and BigQuery Dry Run, but "
                    "execution is disabled."
                ),
                user_question=question,
                model_name=model_name,
                location=location,
                allowed_table=(
                    full_table_id
                ),
                query_generation=(
                    query_generation
                ),
                dry_run_report=(
                    dry_run_report
                ),
            )

        execution_result = (
            execute_query(
                client=bigquery_client,
                proposal=sql_proposal,
                policy=execution_policy,
                dry_run_report=(
                    dry_run_report
                ),
            )
        )

        validate_query_result(
            query_plan=(
                query_generation.plan
            ),
            result=execution_result,
        )

        dynamic_evidence = (
            build_dynamic_evidence(
                user_question=question,
                query_plan=(
                    query_generation.plan
                ),
                source_table=(
                    full_table_id
                ),
                result=execution_result,
            )
        )

        # الاستدعاء الثاني: الجواب من Evidence فقط.
        final_answer = (
            generate_finops_answer(
                client=gemini_client,
                evidence=(
                    dynamic_evidence
                ),
                model_name=model_name,
            )
        )

        return FinOpsAssistantResult(
            status=(
                final_answer.status.value
            ),
            message=(
                final_answer.answer
            ),
            user_question=question,
            model_name=model_name,
            location=location,
            allowed_table=(
                full_table_id
            ),
            query_generation=(
                query_generation
            ),
            dry_run_report=(
                dry_run_report
            ),
            dynamic_evidence=(
                dynamic_evidence
            ),
            final_answer=(
                final_answer
            ),
        )

    finally:
        bigquery_client.close()