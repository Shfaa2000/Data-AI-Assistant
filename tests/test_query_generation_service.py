import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.finops_query.query_catalog import (
    PhysicalColumn,
    PhysicalTable,
    QuerySchemaCatalog,
)

from src.finops_query.query_generation_service import (
    generate_finops_query,
)

from src.finops_query.query_plan_validator import (
    QueryPlanValidationError,
)


PROJECT_ID = (
    "data-ai-assistant-training"
)

DATASET_ID = (
    "cloud_finops"
)

TABLE_ID = (
    "billing_pipeline_day2"
)

FULL_TABLE_ID = (
    f"{PROJECT_ID}."
    f"{DATASET_ID}."
    f"{TABLE_ID}"
)


class FakeInteractions:
    """يعيد استجابات محلية مرتبة دون استدعاء Gemini."""

    def __init__(
        self,
        output_texts: list[str],
    ):
        self.output_texts = list(
            output_texts
        )

        self.requests = []

    def create(
        self,
        **kwargs,
    ):
        # حفظ بيانات الاستدعاء حتى نستطيع
        # التأكد من عدد الاستدعاءات في الاختبار.
        self.requests.append(
            kwargs
        )

        if not self.output_texts:
            raise AssertionError(
                "No fake interaction output remains."
            )

        return SimpleNamespace(
            id=(
                "fake-interaction-"
                f"{len(self.requests)}"
            ),
            output_text=(
                self.output_texts.pop(0)
            ),
        )


class FakeGeminiClient:
    """Client وهمية لا تتصل بخدمة Gemini."""

    def __init__(
        self,
        output_texts: list[str],
    ):
        self.interactions = (
            FakeInteractions(
                output_texts
            )
        )


def make_catalog() -> QuerySchemaCatalog:
    """إنشاء Catalog تجريبي تستخدمه الاختبارات."""

    return QuerySchemaCatalog(
        tables=[
            PhysicalTable(
                project_id=PROJECT_ID,
                dataset_id=DATASET_ID,
                table_id=TABLE_ID,
                columns=[
                    PhysicalColumn(
                        name="BilledCost",
                        data_type="FLOAT64",
                        is_nullable=True,
                        ordinal_position=1,
                    ),
                    PhysicalColumn(
                        name="EffectiveCost",
                        data_type="FLOAT64",
                        is_nullable=True,
                        ordinal_position=2,
                    ),
                    PhysicalColumn(
                        name="ProviderName",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=3,
                    ),
                    PhysicalColumn(
                        name="ServiceName",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=4,
                    ),
                    PhysicalColumn(
                        name="BillingCurrency",
                        data_type="STRING",
                        is_nullable=True,
                        ordinal_position=5,
                    ),
                    PhysicalColumn(
                        name="BillingPeriodStart",
                        data_type="TIMESTAMP",
                        is_nullable=True,
                        ordinal_position=6,
                    ),
                ],
            )
        ]
    )


def ready_plan_json() -> str:
    """إعادة Query Plan جاهزة بصيغة JSON."""

    return json.dumps(
        {
            "status": "ready",
            "intent": (
                "Calculate total billed cost "
                "for AWS."
            ),
            "metrics": [
                {
                    "name": "billed_cost",
                    "aggregation": "sum",
                }
            ],
            "dimensions": [],
            "filters": [
                {
                    "column": "provider",
                    "operator": "eq",
                    "value": "AWS",
                }
            ],
            "time_range": None,
            "sort_by": None,
            "sort_direction": None,
            "limit": 100,
            "clarification_question": None,
            "unsupported_reason": None,
        }
    )


def sql_proposal_json() -> str:
    """إعادة SQL Proposal صالحة بصيغة JSON."""

    return json.dumps(
        {
            "sql": (
                "SELECT "
                "SUM(BilledCost) AS billed_cost "
                "FROM "
                "`data-ai-assistant-training."
                "cloud_finops."
                "billing_pipeline_day2` "
                "WHERE ProviderName = @provider"
            ),
            "parameters": [
                {
                    "name": "provider",
                    "data_type": "STRING",
                    "value": "AWS",
                }
            ],
        }
    )


def clarification_plan_json() -> str:
    """إعادة خطة تحتاج توضيحًا من المستخدم."""

    return json.dumps(
        {
            "status": (
                "needs_clarification"
            ),
            "intent": (
                "Clarify the requested provider."
            ),
            "metrics": [],
            "dimensions": [],
            "filters": [],
            "time_range": None,
            "sort_by": None,
            "sort_direction": None,
            "limit": 100,
            "clarification_question": (
                "Which provider do you mean?"
            ),
            "unsupported_reason": None,
        }
    )


def invalid_aggregation_plan_json() -> str:
    """إعادة خطة تستخدم تجميعًا غير مسموح."""

    return json.dumps(
        {
            "status": "ready",
            "intent": (
                "Count negative billed cost."
            ),
            "metrics": [
                {
                    "name": (
                        "negative_billed_cost"
                    ),
                    "aggregation": "count",
                }
            ],
            "dimensions": [],
            "filters": [],
            "time_range": None,
            "sort_by": None,
            "sort_direction": None,
            "limit": 100,
            "clarification_question": None,
            "unsupported_reason": None,
        }
    )


def generation_result_json() -> str:
    """
    إعادة نتيجة الاستدعاء الأول الجديدة.

    تحتوي على Query Plan وSQL Proposal
    داخل العقد نفسه.
    """

    return json.dumps(
        {
            "plan": json.loads(
                ready_plan_json()
            ),
            "sql_proposal": json.loads(
                sql_proposal_json()
            ),
        }
    )


def clarification_result_json() -> str:
    """
    إعادة نتيجة تحتاج توضيحًا.

    لا يجوز أن تحتوي SQL Proposal.
    """

    return json.dumps(
        {
            "plan": json.loads(
                clarification_plan_json()
            ),
            "sql_proposal": None,
        }
    )


def invalid_aggregation_result_json() -> str:
    """
    إعادة عقد صحيح بنيويًا لكنه يحتوي
    على تجميع غير مسموح دلاليًا.
    """

    return json.dumps(
        {
            "plan": json.loads(
                invalid_aggregation_plan_json()
            ),
            "sql_proposal": json.loads(
                sql_proposal_json()
            ),
        }
    )


def test_ready_plan_generates_sql_proposal():
    """التأكد من إعادة الخطة وSQL باستدعاء واحد."""

    client = FakeGeminiClient(
        [
            generation_result_json()
        ]
    )

    result = generate_finops_query(
        client=client,
        user_question=(
            "What is the total billed cost "
            "for AWS?"
        ),
        catalog=make_catalog(),
        full_table_id=FULL_TABLE_ID,
    )

    assert (
        result.plan.status.value
        == "ready"
    )

    assert (
        result.sql_proposal
        is not None
    )

    assert (
        "@provider"
        in result.sql_proposal.sql
    )

    # الخطة وSQL أصبحتا في استدعاء واحد.
    assert (
        len(
            client.interactions.requests
        )
        == 1
    )

    request = (
        client.interactions.requests[0]
    )

    assert (
        request["response_format"][
            "mime_type"
        ]
        == "application/json"
    )


def test_clarification_stops_before_sql():
    """
    التأكد من توقف السؤال غير الواضح
    دون SQL Proposal.
    """

    client = FakeGeminiClient(
        [
            clarification_result_json()
        ]
    )

    result = generate_finops_query(
        client=client,
        user_question=(
            "What is the cost?"
        ),
        catalog=make_catalog(),
        full_table_id=FULL_TABLE_ID,
    )

    assert (
        result.plan.status.value
        == "needs_clarification"
    )

    assert (
        result.sql_proposal
        is None
    )

    assert (
        len(
            client.interactions.requests
        )
        == 1
    )


def test_invalid_plan_stops_before_sql():
    """
    التأكد من رفض الخطة إذا استخدمت
    عملية تجميع غير مسموحة.
    """

    client = FakeGeminiClient(
        [
            invalid_aggregation_result_json()
        ]
    )

    with pytest.raises(
        QueryPlanValidationError,
        match="not allowed",
    ):
        generate_finops_query(
            client=client,
            user_question=(
                "Count negative billed cost."
            ),
            catalog=make_catalog(),
            full_table_id=FULL_TABLE_ID,
        )

    assert (
        len(
            client.interactions.requests
        )
        == 1
    )


def test_invalid_plan_json_is_rejected():
    """التأكد من رفض نص لا يمثل JSON صالحًا."""

    client = FakeGeminiClient(
        [
            "This is not valid JSON."
        ]
    )

    with pytest.raises(
        ValidationError
    ):
        generate_finops_query(
            client=client,
            user_question=(
                "What is the billed cost?"
            ),
            catalog=make_catalog(),
            full_table_id=FULL_TABLE_ID,
        )