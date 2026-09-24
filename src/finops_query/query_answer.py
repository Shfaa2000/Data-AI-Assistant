"""
العقد الذي يحدد شكل جواب Gemini النهائي.
يحتوي الجواب الإنجليزي وحالته ومراجع الصفوف
والأعمدة التي استُخدمت من Dynamic Evidence.
"""

from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

# يحدد هل توجد نتيجة مالية أم لا توجد بيانات مطابقة.
class QueryAnswerStatus(
    str,
    Enum,
):
    ANSWERED = "answered"
    NO_DATA = "no_data"

# يربط جزءًا من الجواب بصف وأعمدة حقيقية داخل Evidence.
class EvidenceReference(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    row_index: int = Field(
        ge=0,
    )

    columns: list[str] = Field(
        min_length=1,
    )

    @field_validator("columns")
    @classmethod
    def validate_columns(
        cls,
        columns: list[str],
    ) -> list[str]:
        cleaned_columns = [
            column.strip()
            for column in columns
        ]

        if any(
            not column
            for column in cleaned_columns
        ):
            raise ValueError(
                "Evidence column names cannot be empty."
            )

        if len(cleaned_columns) != len(
            set(cleaned_columns)
        ):
            raise ValueError(
                "Evidence column names cannot be duplicated."
            )

        return cleaned_columns


# يمثل الجواب الإنجليزي الذي تعيده Gemini للمستخدم.
class FinOpsQueryAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    status: QueryAnswerStatus

    answer: str = Field(
        min_length=1,
        max_length=2000,
    )

    evidence_references: list[
        EvidenceReference
    ]

    @field_validator("answer")
    @classmethod
    def clean_answer(
        cls,
        answer: str,
    ) -> str:
        cleaned_answer = answer.strip()

        if not cleaned_answer:
            raise ValueError(
                "The final answer cannot be empty."
            )

        return cleaned_answer