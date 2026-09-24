"""تعريف العقد المنظم لفهم سؤال FinOps قبل توليد SQL.

تحول هذه النماذج سؤال المستخدم إلى خطة دلالية تحتوي على
المقاييس والأبعاد والفلاتر والتجميع والترتيب المطلوب.
"""

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from src.finops_query.query_schema import (
    AggregationName,
    DimensionName,
    FilterOperator,
    MetricName,
    SortDirection,
)

# إعداد مشترك يجعل كل نماذج Query Plan صارمة.
class StrictQueryModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

# الحالة الدلالية لسؤال المستخدم قبل توليد أو تنفيذ SQL.
class QueryStatus(str, Enum):
    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"

# مقياس مالي واحد مع العملية التجميعية المطلوبة عليه.
class MetricSelection(StrictQueryModel):
    name: MetricName
    aggregation: AggregationName

# فلتر دلالي سيحوّله الـBackend لاحقًا إلى شرط SQL آمن.
class QueryFilter(StrictQueryModel):
    column: DimensionName
    operator: FilterOperator
    value: str | int | float | Decimal

# الفترة الزمنية المطلوبة في السؤال إن وجدت.
class QueryTimeRange(StrictQueryModel):
    start: date
    end: date

    # يتحقق من أن حالة Query Plan متوافقة مع بقية الحقول:
    # ready تحتاج Metric، وneeds_clarification تحتاج سؤالًا،
    # وunsupported تحتاج سببًا، كما يمنع إعداد ترتيب ناقص.
    @model_validator(mode="after")
    def validate_date_order(
        self,
    ) -> "QueryTimeRange":
        if self.start > self.end:
            raise ValueError(
                "Time range start must not be after end."
            )

        return self

# الخطة الدلالية الكاملة التي تسبق توليد SQL.
class FinOpsQueryPlan(StrictQueryModel):
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

    @model_validator(mode="after")
    def validate_status_consistency(
        self,
    ) -> "FinOpsQueryPlan":
        if self.status == QueryStatus.READY:
            if not self.metrics:
                raise ValueError(
                    "ready requires at least one metric."
                )

            if self.clarification_question:
                raise ValueError(
                    "ready must not include "
                    "clarification_question."
                )

            if self.unsupported_reason:
                raise ValueError(
                    "ready must not include "
                    "unsupported_reason."
                )

        if (
            self.status
            == QueryStatus.NEEDS_CLARIFICATION
        ):
            if not self.clarification_question:
                raise ValueError(
                    "needs_clarification requires "
                    "clarification_question."
                )

            if self.unsupported_reason:
                raise ValueError(
                    "needs_clarification must not include "
                    "unsupported_reason."
                )

        if self.status == QueryStatus.UNSUPPORTED:
            if not self.unsupported_reason:
                raise ValueError(
                    "unsupported requires "
                    "unsupported_reason."
                )

            if self.clarification_question:
                raise ValueError(
                    "unsupported must not include "
                    "clarification_question."
                )

        if (
            self.sort_by is None
            and self.sort_direction is not None
        ):
            raise ValueError(
                "sort_direction requires sort_by."
            )

        if (
            self.sort_by is not None
            and self.sort_direction is None
        ):
            raise ValueError(
                "sort_by requires sort_direction."
            )

        return self