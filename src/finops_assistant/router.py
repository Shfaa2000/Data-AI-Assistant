"""
يصنف سؤال المستخدم ويحدد هل يحتاج
إلى Query أو RAG أو توضيح أو رفض.
"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

class RouterDecision(BaseModel):
    """شكل القرار المسموح للـRouter بإرجاعه."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    route: Literal[
        "query",
        "rag",
        "needs_clarification",
        "unsupported",
    ]

    reason: str = Field(
        min_length=1,
        max_length=500,
    )

    clarification_question: (
        str | None
    ) = None

# يبني تعليمات تصنيف السؤال فقط，
# من دون السماح للنموذج بالإجابة.
def build_router_prompt(
    question: str,
) -> str:
    return (
        "You route questions for a FinOps "
        "assistant.\n"
        "Do not answer the question.\n"
        "Choose exactly one route.\n\n"

        "Choose query for financial values, "
        "totals, averages, rankings, billing "
        "providers, services, currencies, "
        "filters, and date ranges.\n\n"

        "Choose rag for definitions, FOCUS, "
        "FinOps concepts, showback, chargeback, "
        "cost allocation, and documentation.\n\n"

        "Choose needs_clarification when the "
        "question is related to FinOps but is "
        "too ambiguous to route safely.\n\n"

        "Choose unsupported when the question "
        "is outside the project scope.\n\n"

        "Examples:\n"
        "What is the total AWS billed cost? "
        "-> query\n"
        "What are the top five services? "
        "-> query\n"
        "What is FOCUS? -> rag\n"
        "What is showback? -> rag\n"
        "What is the cost? "
        "-> needs_clarification\n"
        "Write a poem. -> unsupported\n\n"

        f"User question:\n{question}"
    )

# يرسل السؤال إلى Gemini ويعيد
# قرار Router منظمًا ومتحققًا منه.
def route_question(
    client,
    question: str,
    model_name: str,
) -> RouterDecision:
    normalized_question = (
        question.strip()
    )

    if not normalized_question:
        raise ValueError(
            "The question is required."
        )

    prompt = build_router_prompt(
        normalized_question
    )

    interaction = (
        client.interactions.create(
            model=model_name,
            input=prompt,
            # يطلب من Gemini إعادة القرار وفق عقد RouterDecision.
            response_format=(
                RouterDecision.model_json_schema()
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
            "router decision."
        )
    # يحول JSON الراجع إلى RouterDecision ويتحقق من الحقول والقيم.
    return (
        RouterDecision
        .model_validate_json(
            output_text
        )
    )