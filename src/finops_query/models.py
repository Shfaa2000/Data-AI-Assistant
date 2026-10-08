"""
يحتوي عقود البيانات المستخدمة في رحلة FinOps Query.

يحدد شكل Query Plan وSQL Proposal ونتائج BigQuery
وDynamic Evidence والجواب النهائي، دون تنفيذ أي منطق تشغيلي.
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# يمنع الحقول غير المعروفة وينظف النصوص في جميع العقود.
class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


# يحدد حالة فهم سؤال المستخدم.
class QueryStatus(str, Enum):
    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"


# يحدد المقاييس المالية المدعومة.
class MetricName(str, Enum):
    BILLED_COST = "billed_cost"
    EFFECTIVE_COST = "effective_cost"
    NEGATIVE_BILLED_COST = "negative_billed_cost"


# يحدد الأبعاد التي يمكن استخدامها في الفلترة والتجميع.
class DimensionName(str, Enum):
    PROVIDER = "provider"
    SERVICE = "service"
    CURRENCY = "currency"


# يحدد عمليات التجميع المسموحة.
class AggregationName(str, Enum):
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"


# يحدد معاملات الفلترة المسموحة.
class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


# يحدد اتجاه ترتيب النتيجة.
class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"

# يمثل مقياسًا ماليًا مع عملية التجميع المطلوبة.
class MetricSelection(StrictModel):
    name: MetricName
    aggregation: AggregationName


# يمثل فلترًا مطلوبًا بشكل صريح في سؤال المستخدم.
class QueryFilter(StrictModel):
    column: DimensionName
    operator: FilterOperator
    value: str | int | float | Decimal


# يمثل الفترة الزمنية المطلوبة ويتأكد من ترتيب تاريخيها.
class QueryTimeRange(StrictModel):
    start: date
    end: date

    @model_validator(mode="after")
    def validate_date_order(
        self,
    ) -> "QueryTimeRange":
        if self.start > self.end:
            raise ValueError(
                "Time range start must not be after end."
            )

        return self


# يمثل فهم Gemini المنظم لسؤال المستخدم قبل إنشاء SQL.
class FinOpsQueryPlan(StrictModel):
    status: QueryStatus

    intent: str = Field(
        min_length=1,
        max_length=200,
    )

    metrics: list[MetricSelection] = Field(
        default_factory=list,
        max_length=10,
    )

    dimensions: list[DimensionName] = Field(
        default_factory=list,
        max_length=10,
    )

    filters: list[QueryFilter] = Field(
        default_factory=list,
        max_length=20,
    )

    time_range: QueryTimeRange | None = None

    sort_by: MetricName | DimensionName | None = None
    sort_direction: SortDirection | None = None

    limit: int = Field(
        default=100,
        ge=1,
        le=100,
    )

    clarification_question: str | None = None
    unsupported_reason: str | None = None

    # يربط حالة الخطة بالحقول المطلوبة لكل حالة.
    @model_validator(mode="after")
    def validate_status(
        self,
    ) -> "FinOpsQueryPlan":
        if self.status is QueryStatus.READY:
            if not self.metrics:
                raise ValueError(
                    "A ready plan requires at least one metric."
                )

            if (
                self.clarification_question
                or self.unsupported_reason
            ):
                raise ValueError(
                    "A ready plan cannot contain "
                    "clarification or unsupported fields."
                )

        elif (
            self.status
            is QueryStatus.NEEDS_CLARIFICATION
        ):
            if not self.clarification_question:
                raise ValueError(
                    "A clarification question is required."
                )

            if self.unsupported_reason:
                raise ValueError(
                    "A clarification plan cannot contain "
                    "an unsupported reason."
                )

        elif self.status is QueryStatus.UNSUPPORTED:
            if not self.unsupported_reason:
                raise ValueError(
                    "An unsupported reason is required."
                )

            if self.clarification_question:
                raise ValueError(
                    "An unsupported plan cannot contain "
                    "a clarification question."
                )

        if (self.sort_by is None) != (
            self.sort_direction is None
        ):
            raise ValueError(
                "sort_by and sort_direction "
                "must be provided together."
            )

        return self

# يحصر أنواع Parameters ضمن الأنواع التي يدعمها المسار.
class QueryParameterType(str, Enum):
    STRING = "STRING"
    INT64 = "INT64"
    FLOAT64 = "FLOAT64"
    BOOL = "BOOL"
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP"


# يمثل Named Parameter دون رمز @.
class GeneratedQueryParameter(StrictModel):
    name: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*$",
    )

    data_type: QueryParameterType
    value: str | int | float | bool

    # يتحقق من توافق قيمة Parameter مع نوعها.
    @model_validator(mode="after")
    def validate_value(
        self,
    ) -> "GeneratedQueryParameter":
        if self.data_type in {
            QueryParameterType.STRING,
            QueryParameterType.DATE,
            QueryParameterType.TIMESTAMP,
        }:
            if not isinstance(self.value, str):
                raise ValueError(
                    "STRING, DATE, and TIMESTAMP "
                    "require a string value."
                )

        elif self.data_type is QueryParameterType.INT64:
            if (
                not isinstance(self.value, int)
                or isinstance(self.value, bool)
            ):
                raise ValueError(
                    "INT64 requires an integer value."
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
                    "FLOAT64 requires a numeric value."
                )

        elif self.data_type is QueryParameterType.BOOL:
            if not isinstance(self.value, bool):
                raise ValueError(
                    "BOOL requires a boolean value."
                )

        return self


# يمثل SQL المقترحة والـParameters التابعة لها.
class GeneratedSqlProposal(StrictModel):
    sql: str = Field(
        min_length=1,
        max_length=20_000,
    )

    parameters: list[
        GeneratedQueryParameter
    ] = Field(default_factory=list)

    # ينظف SQL ويرفض النص الفارغ.
    @field_validator("sql")
    @classmethod
    def clean_sql(
        cls,
        value: str,
    ) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                "Generated SQL cannot be empty."
            )

        return cleaned

    # يمنع تكرار اسم Parameter.
    @model_validator(mode="after")
    def reject_duplicate_parameters(
        self,
    ) -> "GeneratedSqlProposal":
        names = [
            parameter.name.casefold()
            for parameter in self.parameters
        ]

        if len(names) != len(set(names)):
            raise ValueError(
                "Generated query contains "
                "duplicate parameter names."
            )

        return self


# يجمع Query Plan وSQL Proposal في نتيجة الاستدعاء الأول.
class QueryGenerationResult(StrictModel):
    plan: FinOpsQueryPlan
    sql_proposal: GeneratedSqlProposal | None = None

    # يسمح بوجود SQL فقط عندما تكون الخطة جاهزة.
    @model_validator(mode="after")
    def validate_plan_and_sql(
        self,
    ) -> "QueryGenerationResult":
        if (
            self.plan.status is QueryStatus.READY
            and self.sql_proposal is None
        ):
            raise ValueError(
                "A ready query plan requires "
                "an SQL proposal."
            )

        if (
            self.plan.status is not QueryStatus.READY
            and self.sql_proposal is not None
        ):
            raise ValueError(
                "A non-ready query plan "
                "must not contain SQL."
            )

        return self

# يحدد حدود التكلفة والصفوف ووقت التنفيذ.
class BigQueryExecutionPolicy(StrictModel):
    location: str = Field(min_length=1)

    maximum_bytes_billed: int = Field(
        default=100 * 1024 * 1024,
        gt=0,
    )

    max_result_rows: int = Field(
        default=100,
        ge=1,
        le=1000,
    )

    timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=300,
    )


# يحفظ نتيجة Dry Run قبل التنفيذ الحقيقي.
class QueryDryRunReport(StrictModel):
    sql_sha256: str = Field(min_length=1)
    location: str = Field(min_length=1)
    total_bytes_processed: int = Field(ge=0)
    maximum_bytes_billed: int = Field(gt=0)
    job_id: str | None = None


# يحفظ الصفوف وMetadata التنفيذ التي أعادتها BigQuery.
class QueryExecutionResult(StrictModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int = Field(ge=0)
    total_bytes_processed: int = Field(ge=0)
    job_id: str = Field(min_length=1)
    location: str = Field(min_length=1)


# يمثل البيانات الحقيقية المسموح باستخدامها لصياغة الجواب.
class DynamicQueryEvidence(StrictModel):
    # Literal تعني أن هذا الحقل لا يقبل إلا قيمة واحدة حرفيًا
    evidence_type: Literal[
        "bigquery_query_result"
    ] = "bigquery_query_result"

    user_question: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    query_plan: dict[str, Any]
    source_table: str = Field(min_length=1)
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int = Field(ge=0)
    total_bytes_processed: int = Field(ge=0)
    job_id: str = Field(min_length=1)
    location: str = Field(min_length=1)


# يحدد هل توجد بيانات مالية أم لا.
class QueryAnswerStatus(str, Enum):
    ANSWERED = "answered"
    NO_DATA = "no_data"


# يربط معلومة في الجواب بصف وأعمدة داخل Evidence.
class EvidenceReference(StrictModel):
    row_index: int = Field(ge=0)
    columns: list[str] = Field(min_length=1)

    # ينظف أسماء الأعمدة ويمنع الفراغ والتكرار.
    @field_validator("columns")
    @classmethod
    def validate_columns(
        cls,
        columns: list[str],
    ) -> list[str]:
        cleaned = [
            column.strip()
            for column in columns
        ]

        if any(not column for column in cleaned):
            raise ValueError(
                "Evidence column names cannot be empty."
            )

        if len(cleaned) != len(set(cleaned)):
            raise ValueError(
                "Evidence column names cannot be duplicated."
            )

        return cleaned


# يمثل جواب Gemini النهائي المبني على Evidence.
class FinOpsQueryAnswer(StrictModel):
    status: QueryAnswerStatus

    answer: str = Field(
        min_length=1,
        max_length=2000,
    )

    evidence_references: list[
        EvidenceReference
    ]

    # ينظف الجواب ويرفض النص الفارغ.
    @field_validator("answer")
    @classmethod
    def clean_answer(
        cls,
        answer: str,
    ) -> str:
        cleaned = answer.strip()

        if not cleaned:
            raise ValueError(
                "The final answer cannot be empty."
            )

        return cleaned


# يمثل النتيجة المشتركة التي تستخدمها CLI وFastAPI.
class FinOpsAssistantResult(StrictModel):
    status: Literal[
        "answered",
        "no_data",
        "needs_clarification",
        "unsupported",
        "dry_run_only",
    ]

    message: str = Field(min_length=1)
    user_question: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    allowed_table: str = Field(min_length=1)

    query_generation: QueryGenerationResult

    dry_run_report: QueryDryRunReport | None = None
    dynamic_evidence: DynamicQueryEvidence | None = None
    final_answer: FinOpsQueryAnswer | None = None