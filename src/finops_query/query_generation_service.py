"""ينسق استدعاء Gemini الأول والتحقق المحلي من الخطة وSQL."""

from pydantic import BaseModel

from src.finops_query.query_catalog import (
    QuerySchemaCatalog,
)

from src.finops_query.query_generation_prompt import (
    build_query_generation_prompt,
)

from src.finops_query.query_plan import (
    QueryStatus,
)

from src.finops_query.query_plan_validator import (
    validate_query_plan_against_schema,
)

from src.finops_query.query_schema_context import (
    build_query_schema_context,
)

from src.finops_query.query_schema_validator import (
    validate_query_schema_mapping,
)

from src.finops_query.query_sql_proposal import (
    QueryGenerationResult,
)

from .query_sql_safety_validator import (
    validate_sql_safety,
)

from .query_sql_semantic_validator import (
    validate_sql_semantics,
)


DEFAULT_QUERY_MODEL = (
    "gemini-3.5-flash-lite"
)


def build_structured_response_format(
    response_model: type[BaseModel],
) -> dict:
    """تحويل Pydantic Model إلى عقد JSON تطلبه Gemini."""

    return {
        "type": "text",
        "mime_type": "application/json",
        "schema": (
            response_model.model_json_schema()
        ),
    }


def generate_finops_query(
    client,
    user_question: str,
    catalog: QuerySchemaCatalog,
    full_table_id: str,
    model_name: str = DEFAULT_QUERY_MODEL,
) -> QueryGenerationResult:
    """توليد Query Plan وSQL Proposal في استدعاء واحد."""

    # التأكد محليًا أن Mapping متوافق مع BigQuery Catalog.
    validate_query_schema_mapping(
        catalog=catalog,
        full_table_id=full_table_id,
    )

    # بناء النسخة الآمنة من Schema المرسلة إلى Gemini.
    schema_context = (
        build_query_schema_context(
            catalog=catalog,
            full_table_id=full_table_id,
        )
    )

    # بناء Prompt واحد للخطة وSQL معًا.
    prompt = (
        build_query_generation_prompt(
            user_question=user_question,
            schema_context=schema_context,
        )
    )

    # الاستدعاء الأول:
    interaction = (
        client.interactions.create(
            model=model_name,
            input=prompt,
            response_format=(
                build_structured_response_format(
                    QueryGenerationResult
                )
            ),
        )
    )

    # التحقق من شكل JSON والعلاقة بين الخطة وSQL.
    result = (
        QueryGenerationResult
        .model_validate_json(
            interaction.output_text
        )
    )

    # السؤال غير الجاهز يتوقف دون SQL أو BigQuery.
    if (
        result.plan.status
        is not QueryStatus.READY
    ):
        return result

    # التحقق من أن الخطة تستخدم Schema المسموحة.
    validate_query_plan_against_schema(
        plan=result.plan,
        catalog=catalog,
        full_table_id=full_table_id,
    )

    sql_proposal = (
        result.sql_proposal
    )

    # التحقق من أن SQL آمنة.
    sql_statement = validate_sql_safety(
        proposal=sql_proposal,
        schema_context=schema_context,
    )

    # التحقق من أن SQL تطبق معنى الخطة نفسها.
    validate_sql_semantics(
        plan=result.plan,
        proposal=sql_proposal,
        schema_context=schema_context,
        statement=sql_statement,
    )

    return result