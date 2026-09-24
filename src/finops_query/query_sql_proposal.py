"""يعرّف العقد المنظم لـGoogleSQL والـParameters التي تقترحها Gemini بعد قبول Query Plan."""

from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from src.finops_query.query_plan import (
    FinOpsQueryPlan,
    QueryStatus,
)


class StrictGeneratedQueryModel(BaseModel):
    """قاعدة مشتركة تمنع الحقول غير المعروفة."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

# يحصر أنواع Parameters ضمن أنواع GoogleSQL التي ندعمها في النسخة الأولى.
class QueryParameterType(str, Enum):
    """أنواع Query Parameters المسموحة في MVP."""

    STRING = "STRING"
    INT64 = "INT64"
    FLOAT64 = "FLOAT64"
    BOOL = "BOOL"
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP"

# يمثل Parameter واحدة دون رمز @ ويحفظ اسمها ونوعها وقيمتها المنظمة.
class GeneratedQueryParameter(
    StrictGeneratedQueryModel
):
    """يمثل Named Parameter مقترحة لـBigQuery."""

    name: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    )

    data_type: QueryParameterType

    value: str | int | float | bool

    @model_validator(mode="after")
    def validate_parameter_value(
        self,
    ) -> "GeneratedQueryParameter":
        """التحقق من توافق قيمة Parameter مع نوعها."""

        if self.data_type in {
            QueryParameterType.STRING,
            QueryParameterType.DATE,
            QueryParameterType.TIMESTAMP,
        }:
            if not isinstance(self.value, str):
                raise ValueError(
                    "String, DATE, and TIMESTAMP "
                    "parameters require a string value."
                )

        elif self.data_type is QueryParameterType.INT64:
            if (
                not isinstance(self.value, int)
                or isinstance(self.value, bool)
            ):
                raise ValueError(
                    "INT64 parameter requires an integer."
                )

        elif self.data_type is QueryParameterType.FLOAT64:
            if (
                not isinstance(
                    self.value,
                    (int, float),
                )
                or isinstance(self.value, bool)
            ):
                raise ValueError(
                    "FLOAT64 parameter requires "
                    "a numeric value."
                )

        elif self.data_type is QueryParameterType.BOOL:
            if not isinstance(self.value, bool):
                raise ValueError(
                    "BOOL parameter requires "
                    "a boolean value."
                )

        return self

# يمثل SQL المقترحة وقائمة Named Parameters ويرفض أسماء Parameters المكررة.
class GeneratedSqlProposal(
    StrictGeneratedQueryModel
):
    """اقتراح GoogleSQL منظم لم يُسمح بتنفيذه بعد."""

    sql: str = Field(
        min_length=1,
        max_length=20_000,
    )

    parameters: list[
        GeneratedQueryParameter
    ] = Field(default_factory=list)

    @field_validator("sql")
    @classmethod
    def normalize_sql(
        cls,
        value: str,
    ) -> str:
        """تنظيف بداية SQL ونهايتها."""

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Generated SQL cannot be empty."
            )

        return normalized

    @model_validator(mode="after")
    def reject_duplicate_parameters(
        self,
    ) -> "GeneratedSqlProposal":
        """رفض تكرار اسم Parameter."""

        normalized_names = [
            parameter.name.casefold()
            for parameter in self.parameters
        ]

        if len(normalized_names) != len(
            set(normalized_names)
        ):
            raise ValueError(
                "Generated query contains "
                "duplicate parameter names."
            )

        return self

# يجمع Query Plan مع SQL Proposal ويمنع وجود SQL عندما لا تكون الخطة ready.
class QueryGenerationResult(
    StrictGeneratedQueryModel
):
    """النتيجة الداخلية لرحلة Query Generation."""

    plan: FinOpsQueryPlan

    sql_proposal: (
        GeneratedSqlProposal | None
    ) = None

    @model_validator(mode="after")
    def validate_result_consistency(
        self,
    ) -> "QueryGenerationResult":
        """ربط وجود SQL بحالة Query Plan."""

        if (
            self.plan.status
            is QueryStatus.READY
            and self.sql_proposal is None
        ):
            raise ValueError(
                "A ready query plan requires "
                "an SQL proposal."
            )

        if (
            self.plan.status
            is not QueryStatus.READY
            and self.sql_proposal is not None
        ):
            raise ValueError(
                "A non-ready query plan "
                "must not contain SQL."
            )

        return self