"""
يرسل Prompt والعقد إلى Gemini،
  ثم يحول JSON إلى Query Answer."""

from typing import Any

from pydantic import ValidationError

from .query_answer import (
    FinOpsQueryAnswer,
)
from .query_answer_prompt import (
    build_finops_answer_prompt,
)
from .query_answer_validator import (
    validate_finops_answer,
)
from .query_dynamic_evidence import (
    DynamicQueryEvidence,
)


class QueryAnswerGenerationError(
    ValueError
):
    """يظهر إذا لم تعد Gemini جوابًا منظمًا صالحًا."""


# ينفذ الاستدعاء الثالث ويتحقق من JSON ومن Grounding.
def generate_finops_answer(
    client: Any,
    evidence: DynamicQueryEvidence,
    model_name: str,
) -> FinOpsQueryAnswer:
    prompt = build_finops_answer_prompt(
        evidence
    )

    interaction = (
        client.interactions.create(
            model=model_name,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": (
                    FinOpsQueryAnswer
                    .model_json_schema()
                ),
            },
        )
    )

    output_text = (
        interaction.output_text
        or ""
    ).strip()

    if not output_text:
        raise QueryAnswerGenerationError(
            "Gemini returned an empty final answer."
        )

    try:
        answer = (
            FinOpsQueryAnswer
            .model_validate_json(
                output_text
            )
        )
    except ValidationError as exc:
        raise QueryAnswerGenerationError(
            "Gemini returned an invalid "
            "answer contract."
        ) from exc

    validate_finops_answer(
        answer=answer,
        evidence=evidence,
    )

    return answer