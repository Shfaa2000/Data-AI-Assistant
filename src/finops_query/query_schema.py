"""تعريف الـSemantic Schema المسموحة لطبقة FinOps Query.

هذا الملف يحدد الجداول والمقاييس والأبعاد والعمليات التي
يسمح للنموذج باقتراحها، قبل ربطها بأسماء أعمدة BigQuery الفعلية.
"""

from enum import Enum

# الجدول الوحيد المسموح بالوصول إليه في Query V1.
ALLOWED_TABLES = frozenset(
    {
        (
            "data-ai-assistant-training."
            "cloud_finops.billing_pipeline_day2"
        ),
    }
)

# المقاييس المالية الدلالية التي يدعمها الإصدار الأول.
class MetricName(str, Enum):
    BILLED_COST = "billed_cost"
    EFFECTIVE_COST = "effective_cost"
    NEGATIVE_BILLED_COST = "negative_billed_cost"

# الأبعاد التي يمكن استخدامها في التجميع والفلترة.
class DimensionName(str, Enum):
    PROVIDER = "provider"
    SERVICE = "service"
    CURRENCY = "currency"

# العمليات التجميعية المسموحة للمقاييس المالية.
class AggregationName(str, Enum):
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"

# معاملات الفلترة الدلالية التي سيحولها الـBackend إلى GoogleSQL.
class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"

# اتجاهات الترتيب التي يسمح بها Query Plan.
class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"