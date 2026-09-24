"""
يتحقق من أن جواب Gemini مؤسس على Dynamic Evidence فقط.
"""

import re
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)
from typing import Any

from .query_answer import (
    FinOpsQueryAnswer,
    QueryAnswerStatus,
)
from .query_dynamic_evidence import (
    DynamicQueryEvidence,
)


class QueryAnswerValidationError(
    ValueError
):
    """يظهر عندما يحتوي الجواب على معلومة غير موثقة."""

# يحدد عدد المنازل المستخدمة في عرض القيم المالية.
ANSWER_DECIMAL_PLACES = 2

ARABIC_PATTERN = re.compile(
    r"[\u0600-\u06FF]"
)

# يستخرج الأرقام المستقلة ويتجنب الأرقام داخل أسماء مثل EC2.
NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"[-+]?\d[\d,]*(?:\.\d+)?"
    r"(?![A-Za-z0-9_])"
)

# يحول تمثيلات الأرقام المختلفة إلى Decimal قابلة للمقارنة.
def _normalize_number(
    value: str,
) -> Decimal:
    return Decimal(
        value.replace(",", "")
    ).normalize()

# يقرب القيمة المالية بطريقة ثابتة إلى منزلتين عشريتين.
def _round_for_answer(
    value: Decimal,
) -> Decimal:
    quantum = Decimal("0.01")

    return value.quantize(
        quantum,
        rounding=ROUND_HALF_UP,
    ).normalize()

# يستخرج الأرقام الموجودة داخل نص.
def _numbers_from_text(
    text: str,
) -> set[Decimal]:
    numbers: set[Decimal] = set()

    for match in NUMBER_PATTERN.findall(
        text
    ):
        numbers.add(
            _normalize_number(match)
        )

    return numbers


# يستخرج الأرقام من قيمة Evidence مهما كان نوعها.
def _numbers_from_value(
    value: Any,
) -> set[Decimal]:
    if value is None or isinstance(
        value,
        bool,
    ):
        return set()

    if isinstance(
        value,
        (int, float, Decimal),
    ):
        return {
            Decimal(str(value)).normalize()
        }

    if isinstance(value, str):
        return _numbers_from_text(value)

    return set()

# يتحقق من وجود Metric فعلية غير NULL في صفوف Evidence.
def _has_metric_data(
    evidence: DynamicQueryEvidence,
) -> bool:
    query_plan = evidence.query_plan

    metric_names = [
        str(metric["name"])
        for metric in query_plan.get(
            "metrics",
            [],
        )
    ]

    if not evidence.rows:
        return False

    if not metric_names:
        return True

    return any(
        row.get(metric_name) is not None
        for row in evidence.rows
        for metric_name in metric_names
    )

# يجمع أرقام السؤال والقيم المشار إليها في Evidence
# مع نسخها المقربة إلى منزلتين عشريتين.
def _allowed_numbers(
    evidence: DynamicQueryEvidence,
    answer: FinOpsQueryAnswer,
) -> set[Decimal]:
    allowed_numbers = _numbers_from_text(
        evidence.user_question
    )

    for reference in (
        answer.evidence_references
    ):
        if reference.row_index >= len(
            evidence.rows
        ):
            continue

        referenced_row = evidence.rows[
            reference.row_index
        ]

        for column in reference.columns:
            if column not in referenced_row:
                continue

            value_numbers = (
                _numbers_from_value(
                    referenced_row[column]
                )
            )

            allowed_numbers.update(
                value_numbers
            )

            allowed_numbers.update(
                _round_for_answer(number)
                for number in value_numbers
            )

    return allowed_numbers

# يتحقق من الحالة والمراجع واللغة والأرقام.
def validate_finops_answer(
    answer: FinOpsQueryAnswer,
    evidence: DynamicQueryEvidence,
) -> None:
    has_data = _has_metric_data(
        evidence
    )

    if has_data:
        if (
            answer.status
            != QueryAnswerStatus.ANSWERED
        ):
            raise QueryAnswerValidationError(
                "Evidence contains data, so status "
                "must be answered."
            )

        if not answer.evidence_references:
            raise QueryAnswerValidationError(
                "An answered response must contain "
                "at least one evidence reference."
            )

    else:
        if (
            answer.status
            != QueryAnswerStatus.NO_DATA
        ):
            raise QueryAnswerValidationError(
                "Evidence contains no usable metric "
                "value, so status must be no_data."
            )

        if answer.evidence_references:
            raise QueryAnswerValidationError(
                "A no_data response must not contain "
                "evidence references."
            )

    if ARABIC_PATTERN.search(
        answer.answer
    ):
        raise QueryAnswerValidationError(
            "The final answer must be written in English."
        )

    for reference in (
        answer.evidence_references
    ):
        if reference.row_index >= len(
            evidence.rows
        ):
            raise QueryAnswerValidationError(
                "The answer references a row "
                "that does not exist."
            )

        referenced_row = evidence.rows[
            reference.row_index
        ]

        missing_columns = [
            column
            for column in reference.columns
            if column not in referenced_row
        ]

        if missing_columns:
            raise QueryAnswerValidationError(
                "The answer references unknown "
                f"evidence columns: {missing_columns}."
            )

    answer_numbers = _numbers_from_text(
        answer.answer
    )

    allowed_numbers = _allowed_numbers(
    evidence=evidence,
    answer=answer,
)

    invented_numbers = (
        answer_numbers
        - allowed_numbers
    )

    if invented_numbers:
        formatted_numbers = sorted(
            str(number)
            for number in invented_numbers
        )

        raise QueryAnswerValidationError(
            "The answer contains numbers that are "
            "not present in the evidence or question: "
            f"{formatted_numbers}."
        )