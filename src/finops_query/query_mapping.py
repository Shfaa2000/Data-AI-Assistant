"""يربط الحقول الدلالية في Query Plan بأعمدة BigQuery الحقيقية ويحدد أنواعها وعملياتها المسموحة."""
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from src.finops_query.query_schema import (
    AggregationName,
    DimensionName,
    MetricName,
)


class QueryFieldKind(str, Enum):
    """يحدد دور الحقل الدلالي في الاستعلام."""

    METRIC = "metric"
    DIMENSION = "dimension"
    TIME = "time"


class MetricValueScope(str, Enum):
    """يحدد هل المقياس يستخدم كل القيم أم السالبة فقط."""

    ALL_VALUES = "all_values"
    NEGATIVE_VALUES = "negative_values"

# يمثل قاعدة ربط واحدة بين اسم يفهمه التطبيق وعمود موجود فعليًا في BigQuery.
class QueryFieldMapping(BaseModel):
    """يربط الاسم الدلالي بعمود BigQuery الحقيقي."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    semantic_name: str = Field(min_length=1)
    kind: QueryFieldKind
    physical_column: str = Field(min_length=1)

    expected_data_types: tuple[
        str,
        ...,
    ] = Field(min_length=1)

    allowed_aggregations: tuple[
        AggregationName,
        ...,
    ] = ()

    value_scope: MetricValueScope = (
        MetricValueScope.ALL_VALUES
    )

# يحدد الربط المسموح بين Metrics وDimensions الدلالية والأعمدة الحقيقية.
QUERY_FIELD_MAPPINGS: dict[
    str,
    QueryFieldMapping,
] = {
    MetricName.BILLED_COST.value: (
        QueryFieldMapping(
            semantic_name=(
                MetricName.BILLED_COST.value
            ),
            kind=QueryFieldKind.METRIC,
            physical_column="BilledCost",
            expected_data_types=(
                "FLOAT64",
                "NUMERIC",
                "BIGNUMERIC",
            ),
            allowed_aggregations=(
                AggregationName.SUM,
                AggregationName.AVG,
                AggregationName.MIN,
                AggregationName.MAX,
            ),
        )
    ),

    MetricName.EFFECTIVE_COST.value: (
        QueryFieldMapping(
            semantic_name=(
                MetricName.EFFECTIVE_COST.value
            ),
            kind=QueryFieldKind.METRIC,
            physical_column="EffectiveCost",
            expected_data_types=(
                "FLOAT64",
                "NUMERIC",
                "BIGNUMERIC",
            ),
            allowed_aggregations=(
                AggregationName.SUM,
                AggregationName.AVG,
                AggregationName.MIN,
                AggregationName.MAX,
            ),
        )
    ),

    MetricName.NEGATIVE_BILLED_COST.value: (
        QueryFieldMapping(
            semantic_name=(
                MetricName.NEGATIVE_BILLED_COST.value
            ),
            kind=QueryFieldKind.METRIC,
            physical_column="BilledCost",
            expected_data_types=(
                "FLOAT64",
                "NUMERIC",
                "BIGNUMERIC",
            ),
            allowed_aggregations=(
                AggregationName.SUM,
            ),
            value_scope=(
                MetricValueScope.NEGATIVE_VALUES
            ),
        )
    ),

    DimensionName.PROVIDER.value: (
        QueryFieldMapping(
            semantic_name=(
                DimensionName.PROVIDER.value
            ),
            kind=QueryFieldKind.DIMENSION,
            physical_column="ProviderName",
            expected_data_types=("STRING",),
        )
    ),

    DimensionName.SERVICE.value: (
        QueryFieldMapping(
            semantic_name=(
                DimensionName.SERVICE.value
            ),
            kind=QueryFieldKind.DIMENSION,
            physical_column="ServiceName",
            expected_data_types=("STRING",),
        )
    ),

    DimensionName.CURRENCY.value: (
        QueryFieldMapping(
            semantic_name=(
                DimensionName.CURRENCY.value
            ),
            kind=QueryFieldKind.DIMENSION,
            physical_column="BillingCurrency",
            expected_data_types=("STRING",),
        )
    ),

    "time_range": QueryFieldMapping(
        semantic_name="time_range",
        kind=QueryFieldKind.TIME,
        physical_column="BillingPeriodStart",
        expected_data_types=(
            "DATE",
            "DATETIME",
            "TIMESTAMP",
        ),
    ),
}