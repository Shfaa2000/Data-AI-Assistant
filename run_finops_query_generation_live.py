"""
يشغل رحلة FinOps Query باستخدام Gemini وBigQuery الحقيقيتين.

يحمل Physical Schema من BigQuery، ويطلب من Gemini إنشاء
Query Plan ثم SQL Proposal، ويمرر SQL على Safety وSemantic
Validators، ثم ينفذ BigQuery Dry Run، وعند السماح بالتنفيذ
يجلب النتائج ويتحقق منها ويبني Dynamic Evidence موثقة.
"""

import os

from dotenv import load_dotenv
from google import genai
from google.cloud import bigquery

# يشغل رحلة Gemini: Query Plan ثم SQL Proposal ثم الحارسين.
from src.finops_query.query_generation_service import (
    generate_finops_query,
)

# يحمل Physical Schema الحقيقية من BigQuery.
from src.finops_query.query_schema_loader import (
    load_query_schema_catalog,
)

# ينفذ Dry Run والتنفيذ الحقيقي ضمن حدود التكلفة والصفوف.
from src.finops_query.query_bigquery_execution import (
    BigQueryExecutionPolicy,
    QueryExecutionError,
    dry_run_query,
    execute_read_only_query,
)

# يتحقق من الصفوف والأعمدة التي أعادتها BigQuery.
from src.finops_query.query_result_validator import (
    QueryResultValidationError,
    validate_query_result,
)

# يحول نتيجة BigQuery إلى Evidence صغيرة وموثقة.
from src.finops_query.query_dynamic_evidence import (
    build_dynamic_query_evidence,
)
# يولد جوابًا  موثقًا من Dynamic Evidence.
from src.finops_query.query_answer_service import (
    generate_finops_answer,
)

# القيم المعروفة لبيئة BigQuery الحالية.
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

# يقرأ متغيرًا إلزاميًا من البيئة ويرفض التشغيل إن كان مفقودًا.
def require_environment_variable(
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

# يجهز الاتصالات والإعدادات ويشغل الرحلة الكاملة.
def main() -> int:
    load_dotenv()

    gemini_api_key = (
        require_environment_variable(
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

    # ينشئ BigQuery Client لتحميل Metadata ثم تنفيذ SQL بعد الموافقة.
    bigquery_client = bigquery.Client(
        project=project_id
    )

    # يستخدم الموقع المحدد في البيئة أو يقرأ موقع Dataset الحقيقي.
    configured_location = os.getenv(
        "BIGQUERY_LOCATION",
        "",
    ).strip()

    if configured_location:
        location = configured_location
    else:
        dataset_reference = (
            f"{project_id}.{dataset_id}"
        )

        dataset_metadata = (
            bigquery_client.get_dataset(
                dataset_reference
            )
        )

        location = (
            dataset_metadata.location
            or ""
        ).strip()

    if not location:
        raise RuntimeError(
            "BigQuery dataset location "
            "could not be determined."
        )

    print(
        f"BigQuery location: {location}"
    )

    # ينشئ Gemini Client المستخدم في الاستدعاءين الحقيقيين.
    gemini_client = genai.Client(
        api_key=gemini_api_key
    )

    # يحمل Metadata الفعلية من INFORMATION_SCHEMA.
    catalog = load_query_schema_catalog(
        client=bigquery_client,
        project_id=project_id,
        dataset_id=dataset_id,
        allowed_table_ids=[
            table_id
        ],
        location=location,
    )

    print(
        "BigQuery schema catalog: PASS"
    )

    print(
        f"Allowed table: {full_table_id}"
    )

    # يستقبل سؤالًا ماليًا باللغة الإنجليزية.
    user_question = input(
        "Enter an English financial question: "
    ).strip()

    if not user_question:
        raise ValueError(
            "The user question is required."
        )

    print(
        f"Gemini model: {model_name}"
    )

    print(
        f"User question: {user_question}"
    )

    # يطلب Query Plan ثم SQL Proposal ويمررهما على Validators المحلية.
    try:
        result = generate_finops_query(
            client=gemini_client,
            user_question=user_question,
            catalog=catalog,
            full_table_id=full_table_id,
            model_name=model_name,
        )

    except Exception as exc:
        print(
            "Real Gemini query generation: FAIL"
        )

        print(
            f"Error type: "
            f"{type(exc).__name__}"
        )

        print(
            f"Error message: {exc}"
        )

        print(
            "SQL was not executed."
        )

        return 1

    # لا تصل الرحلة إلى هنا إلا بعد نجاح استدعاء Gemini.
    print(
        "Real Gemini query generation: PASS"
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )

    query_plan = result.plan
    sql_proposal = result.sql_proposal

    # تتوقف بأمان إذا كانت الخطة تحتاج توضيحًا أو غير مدعومة.
    if sql_proposal is None:
        print(
            "BigQuery execution was skipped because "
            "no SQL proposal was generated."
        )

        return 0

    print(
        "Local SQL validation: PASS"
    )

    # يحدد الحد الأعلى للقراءة والصفوف ووقت الانتظار.
    execution_policy = BigQueryExecutionPolicy(
        location=location,
        maximum_bytes_billed=int(
            os.getenv(
                "FINOPS_MAXIMUM_BYTES_BILLED",
                str(100 * 1024 * 1024),
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
                "FINOPS_QUERY_TIMEOUT_SECONDS",
                "60",
            )
        ),
    )

    # يرسل SQL إلى BigQuery لفحصها وتقدير Bytes دون تنفيذها.
    try:
        dry_run_report = dry_run_query(
            client=bigquery_client,
            proposal=sql_proposal,
            policy=execution_policy,
        )

        print(
            "BigQuery Dry Run: PASS"
        )

        print(
            "Estimated bytes: "
            f"{dry_run_report.total_bytes_processed}"
        )

        # يتوقف بعد Dry Run افتراضيًا ما لم يُسمح بالتنفيذ صراحة.
        execute_queries = (
            os.getenv(
                "FINOPS_EXECUTE_QUERIES",
                "false",
            )
            .strip()
            .lower()
            == "true"
        )

        if not execute_queries:
            print(
                "Execution stopped safely after Dry Run."
            )

            print(
                "Set FINOPS_EXECUTE_QUERIES=true "
                "to execute the query."
            )

            return 0

        # ينفذ SQL نفسها التي اجتازت Dry Run.
        execution_result = (
            execute_read_only_query(
                client=bigquery_client,
                proposal=sql_proposal,
                policy=execution_policy,
                dry_run_report=dry_run_report,
            )
        )

        print(
            "BigQuery execution: PASS"
        )

        # يتحقق من أعمدة وصفوف وقيم نتيجة BigQuery.
        validate_query_result(
            query_plan=query_plan,
            result=execution_result,
        )

        print(
            "Query result validation: PASS"
        )

        # يحول الصفوف الحقيقية إلى Evidence صغيرة وموثقة.
        dynamic_evidence = (
            build_dynamic_query_evidence(
                user_question=user_question,
                query_plan=query_plan,
                source_table=full_table_id,
                result=execution_result,
            )
        )

        print(
            "Dynamic Evidence: PASS"
        )

        print(
            dynamic_evidence.model_dump_json(
                indent=2
            )
        )

        # يطلب من Gemini صياغة الجواب الإنجليزي من Evidence فقط.
        final_answer = generate_finops_answer(
            client=gemini_client,
            evidence=dynamic_evidence,
            model_name=model_name,
        )

        print(
            "Final answer generation: PASS"
        )

        print(
            "Final answer validation: PASS"
        )

        print()
        print("Final Answer:")
        print(final_answer.answer)

        print()
        print(
            "Final Answer Contract:"
        )

        print(
            final_answer.model_dump_json(
                indent=2
            )
        )

        return 0

    except (
        QueryExecutionError,
        QueryResultValidationError,
    ) as exc:
        print(
            "Protected BigQuery execution: FAIL"
        )

        print(
            f"Error type: "
            f"{type(exc).__name__}"
        )

        print(
            f"Error message: {exc}"
        )

        return 1

    except Exception as exc:
        print(
            "BigQuery request: FAIL"
        )

        print(
            f"Error type: "
            f"{type(exc).__name__}"
        )

        print(
            f"Error message: {exc}"
        )

        return 1

if __name__ == "__main__":
    raise SystemExit(main())