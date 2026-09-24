"""ينسق توليد Query Plan وSQL Proposal مع التحقق بين المرحلتين من دون تنفيذ الاستعلام."""

from pydantic import BaseModel

from src.finops_query.query_catalog import (
    QuerySchemaCatalog,
)
from src.finops_query.query_generation_prompt import (
    build_query_plan_prompt,
    build_sql_generation_prompt,
)
from src.finops_query.query_plan import (
    FinOpsQueryPlan,
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
    GeneratedSqlProposal,
    QueryGenerationResult,
)
# يتحقق من أمان SQL ومن مطابقتها الدلالية قبل إعادة النتيجة.
from .query_sql_safety_validator import (
    validate_sql_safety,
)
from .query_sql_semantic_validator import (
    validate_sql_semantics,
)

DEFAULT_QUERY_MODEL = "gemini-3.6-flash"

# يحول Pydantic Model إلى Response Format تطلب JSON منظمة من Gemini.
def build_structured_response_format(
    response_model: type[BaseModel],
) -> dict:
    """بناء عقد Structured Output لـGemini."""

    return {
        "type": "text",
        "mime_type": "application/json",
        "schema": (
            response_model.model_json_schema()
        ),
    }

# يبدأ الرحلة بفحص Schema Mapping محليًا ثم يبني السياق الآمن قبل استدعاء Gemini.
def generate_finops_query(
    client,
    user_question: str,
    catalog: QuerySchemaCatalog,
    full_table_id: str,
    model_name: str = DEFAULT_QUERY_MODEL,
) -> QueryGenerationResult:
    """توليد Query Plan ثم SQL Proposal منظمة."""

    validate_query_schema_mapping(
        catalog=catalog,
        full_table_id=full_table_id,
    )

    schema_context = build_query_schema_context(
        catalog=catalog,
        full_table_id=full_table_id,
    )

    plan_prompt = build_query_plan_prompt(
        user_question=user_question,
        schema_context=schema_context,
    )

    # يطلب Query Plan منظمة ويتحقق من JSON المعادة باستخدام Pydantic.
    plan_interaction = (
        client.interactions.create(
            model=model_name,
            input=plan_prompt,
            response_format=(
                build_structured_response_format(
                    FinOpsQueryPlan
                )
            ),
        )
    )

    plan = FinOpsQueryPlan.model_validate_json(
        plan_interaction.output_text
    )
    # يوقف الرحلة بعد استدعاء واحد إذا احتاج السؤال توضيحًا أو كان غير مدعوم.
    if plan.status is not QueryStatus.READY:
        return QueryGenerationResult(
            plan=plan,
            sql_proposal=None,
        )

    # يتحقق من قابلية تنفيذ الخطة قبل السماح بالانتقال إلى SQL Generator.
    validate_query_plan_against_schema(
        plan=plan,
        catalog=catalog,
        full_table_id=full_table_id,
    )

    sql_prompt = build_sql_generation_prompt(
        plan=plan,
        schema_context=schema_context,
    )

    # يطلب SQL Proposal منظمة ويتحقق من شكلها دون السماح بتنفيذها.
    sql_interaction = (
        client.interactions.create(
            model=model_name,
            input=sql_prompt,
            response_format=(
                build_structured_response_format(
                    GeneratedSqlProposal
                )
            ),
        )
    )

    sql_proposal = (
        GeneratedSqlProposal.model_validate_json(
            sql_interaction.output_text
        )
    )

    # البوابة الأولى: التحقق البنيوي والأمني من SQL.
    sql_statement = validate_sql_safety(
        proposal=sql_proposal,
        schema_context=schema_context,
    )

    # البوابة الثانية: التأكد أن SQL تطبق معنى Query Plan نفسها.
    validate_sql_semantics(
        plan=plan,
        proposal=sql_proposal,
        schema_context=schema_context,
        statement=sql_statement,
    )

    return QueryGenerationResult(
        plan=plan,
        sql_proposal=sql_proposal,
    )