"""
ينفذ استدعاء Gemini الثاني لصياغة الجواب من Dynamic Evidence،
ثم يتحقق من الحالة والمراجع والأرقام المستخدمة في الجواب.
"""

import json
import re

from decimal import (
    Decimal,
    ROUND_HALF_UP,
)
from typing import Any

from pydantic import ValidationError

from src.finops_query.models import (
    DynamicQueryEvidence,
    FinOpsQueryAnswer,
    QueryAnswerStatus,
)


class AnswerValidationError(ValueError):
    """يظهر عندما يكون جواب Gemini فارغًا أو غير موثق."""


ARABIC_PATTERN = re.compile(
    r"[\u0600-\u06FF]"
)

NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"[-+]?\d[\d,]*(?:\.\d+)?"
    r"(?![A-Za-z0-9_])"
)


# يبني Prompt يمنع استخدام معلومات خارج Evidence.
def build_answer_prompt(
    evidence: DynamicQueryEvidence,
) -> str:
    evidence_payload = (
        evidence.model_dump(
            mode="json",
            exclude={
                "job_id",
                "location",
                "total_bytes_processed",
            },
        )
    )

    evidence_json = json.dumps(
        evidence_payload,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
ROLE:
You are a FinOps answer writer.

TASK:
Answer the user's financial question in clear English
using only the supplied DYNAMIC_EVIDENCE.

GROUNDING RULES:
- Use only facts and values present in DYNAMIC_EVIDENCE.
- Never invent, estimate, infer, or recalculate a number.
- Do not create percentages unless they already exist in the evidence.
- Preserve the exact meaning of the user's question.
- Do not claim a currency unless the evidence includes one.
- Do not mention SQL, prompts, validators, schemas, credentials,
  job IDs, locations, byte counts, or internal implementation details.
- Keep the answer concise and understandable.
- The answer field must be written in English.
- If the evidence contains no usable metric value, return
  status "no_data" and explain that no matching data was found.
- If data exists, return status "answered".
- For every fact used, provide its zero-based row index
  and the exact evidence columns used.
- Do not mention row indices in the answer text.
- Return only JSON matching the required response schema.
- Monetary metric values may be rounded to exactly two
  decimal places using standard financial rounding.
- Do not round row counts, limits, dates, or identifiers.
- Do not otherwise transform or recalculate values.
- For multi-row results, do not number the rows and do not use
  numeric list labels such as 1, 2, or 3. Use plain sentences
  or unnumbered bullet text so no new numbers are introduced.

DYNAMIC_EVIDENCE:
{evidence_json}
""".strip()


# يستخرج الأرقام المستقلة من النص.
def _numbers_from_text(
    text: str,
) -> set[Decimal]:
    return {
        Decimal(
            value.replace(
                ",",
                "",
            )
        ).normalize()
        for value
        in NUMBER_PATTERN.findall(text)
    }


# يستخرج الأرقام من قيمة Evidence.
def _numbers_from_value(
    value: Any,
) -> set[Decimal]:
    if (
        value is None
        or isinstance(
            value,
            bool,
        )
    ):
        return set()

    if isinstance(
        value,
        (
            int,
            float,
            Decimal,
        ),
    ):
        return {
            Decimal(
                str(value)
            ).normalize()
        }

    if isinstance(
        value,
        str,
    ):
        return _numbers_from_text(
            value
        )

    return set()


# يتحقق من وجود قيمة فعلية لأحد Metrics.
def _has_metric_data(
    evidence: DynamicQueryEvidence,
) -> bool:
    metric_names = [
        str(metric["name"])
        for metric
        in evidence.query_plan.get(
            "metrics",
            [],
        )
    ]

    if not evidence.rows:
        return False

    if not metric_names:
        return True

    return any(
        row.get(metric_name)
        is not None
        for row in evidence.rows
        for metric_name in metric_names
    )


# يتحقق من الحالة واللغة والمراجع والأرقام.
def validate_answer(
    answer: FinOpsQueryAnswer,
    evidence: DynamicQueryEvidence,
) -> None:
    has_data = _has_metric_data(
        evidence
    )

    if has_data:
        if (
            answer.status
            is not QueryAnswerStatus.ANSWERED
        ):
            raise AnswerValidationError(
                "Evidence contains data; "
                "status must be answered."
            )

        if not answer.evidence_references:
            raise AnswerValidationError(
                "An answered result requires "
                "evidence references."
            )

    else:
        if (
            answer.status
            is not QueryAnswerStatus.NO_DATA
        ):
            raise AnswerValidationError(
                "Evidence has no data; "
                "status must be no_data."
            )

        if answer.evidence_references:
            raise AnswerValidationError(
                "A no_data result cannot "
                "contain references."
            )

    if ARABIC_PATTERN.search(
        answer.answer
    ):
        raise AnswerValidationError(
            "The final answer must "
            "be written in English."
        )

    allowed_numbers = (
        _numbers_from_text(
            evidence.user_question
        )
    )

    for reference in (
        answer.evidence_references
    ):
        if (
            reference.row_index
            >= len(evidence.rows)
        ):
            raise AnswerValidationError(
                "The answer references "
                "a missing row."
            )

        referenced_row = evidence.rows[
            reference.row_index
        ]

        missing_columns = [
            column
            for column
            in reference.columns
            if column
            not in referenced_row
        ]

        if missing_columns:
            raise AnswerValidationError(
                "The answer references "
                "unknown columns: "
                f"{missing_columns}."
            )

        for column in reference.columns:
            numbers = (
                _numbers_from_value(
                    referenced_row[column]
                )
            )

            allowed_numbers.update(
                numbers
            )

            allowed_numbers.update(
                number.quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                ).normalize()
                for number in numbers
            )

    answer_numbers = (
        _numbers_from_text(
            answer.answer
        )
    )

    invented_numbers = (
        answer_numbers
        - allowed_numbers
    )

    if invented_numbers:
        formatted_numbers = sorted(
            str(number)
            for number
            in invented_numbers
        )

        raise AnswerValidationError(
            "The answer contains numbers "
            "not present in Evidence: "
            f"{formatted_numbers}"
        )


# ينفذ الاستدعاء الثاني ويعيد جوابًا موثقًا.
def generate_finops_answer(
    client,
    evidence: DynamicQueryEvidence,
    model_name: str,
) -> FinOpsQueryAnswer:
    prompt = build_answer_prompt(
        evidence
    )

    interaction = (
        client.interactions.create(
            model=model_name,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": (
                    "application/json"
                ),
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
        raise AnswerValidationError(
            "Gemini returned an empty "
            "final answer."
        )

    try:
        answer = (
            FinOpsQueryAnswer
            .model_validate_json(
                output_text
            )
        )

    except ValidationError as exc:
        raise AnswerValidationError(
            "Gemini returned an invalid "
            "answer contract."
        ) from exc

    validate_answer(
        answer=answer,
        evidence=evidence,
    )

    return answer