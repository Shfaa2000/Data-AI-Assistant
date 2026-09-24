from datetime import date

import pytest
from pydantic import ValidationError

from src.finops_query.query_plan import (
    FinOpsQueryPlan,
    QueryStatus,
)


def make_ready_plan() -> dict:
    """إنشاء Query Plan صالحة للاختبارات."""

    return {
        "status": "ready",
        "intent": "find_top_service",
        "metrics": [
            {
                "name": "billed_cost",
                "aggregation": "sum",
            }
        ],
        "dimensions": [
            "service",
        ],
        "filters": [
            {
                "column": "provider",
                "operator": "eq",
                "value": "AWS",
            }
        ],
        "time_range": None,
        "sort_by": "billed_cost",
        "sort_direction": "desc",
        "limit": 1,
        "clarification_question": None,
        "unsupported_reason": None,
    }


def test_accepts_valid_ready_plan():
    plan = FinOpsQueryPlan.model_validate(
        make_ready_plan()
    )

    assert plan.status == QueryStatus.READY
    assert len(plan.metrics) == 1
    assert plan.limit == 1


def test_ready_requires_metric():
    data = make_ready_plan()
    data["metrics"] = []

    with pytest.raises(
        ValidationError,
        match="ready requires at least one metric",
    ):
        FinOpsQueryPlan.model_validate(data)


def test_rejects_unknown_metric():
    data = make_ready_plan()
    data["metrics"][0]["name"] = "invoice_cost"

    with pytest.raises(ValidationError):
        FinOpsQueryPlan.model_validate(data)


def test_accepts_clarification_plan():
    plan = FinOpsQueryPlan.model_validate(
        {
            "status": "needs_clarification",
            "intent": "clarify_cost_metric",
            "metrics": [],
            "dimensions": [],
            "filters": [],
            "limit": 100,
            "clarification_question": (
                "Do you mean billed cost "
                "or effective cost?"
            ),
            "unsupported_reason": None,
        }
    )

    assert (
        plan.status
        == QueryStatus.NEEDS_CLARIFICATION
    )
    assert plan.clarification_question is not None


def test_clarification_requires_question():
    with pytest.raises(
        ValidationError,
        match=(
            "needs_clarification requires "
            "clarification_question"
        ),
    ):
        FinOpsQueryPlan.model_validate(
            {
                "status": "needs_clarification",
                "intent": "clarify_cost_metric",
                "metrics": [],
                "dimensions": [],
                "filters": [],
                "limit": 100,
                "clarification_question": None,
                "unsupported_reason": None,
            }
        )


def test_accepts_unsupported_plan():
    plan = FinOpsQueryPlan.model_validate(
        {
            "status": "unsupported",
            "intent": "resource_utilization",
            "metrics": [],
            "dimensions": [],
            "filters": [],
            "limit": 100,
            "clarification_question": None,
            "unsupported_reason": (
                "The allowed schema does not "
                "contain utilization metrics."
            ),
        }
    )

    assert plan.status == QueryStatus.UNSUPPORTED
    assert plan.unsupported_reason is not None


def test_unsupported_requires_reason():
    with pytest.raises(
        ValidationError,
        match="unsupported requires unsupported_reason",
    ):
        FinOpsQueryPlan.model_validate(
            {
                "status": "unsupported",
                "intent": "resource_utilization",
                "metrics": [],
                "dimensions": [],
                "filters": [],
                "limit": 100,
                "clarification_question": None,
                "unsupported_reason": None,
            }
        )


def test_rejects_limit_above_maximum():
    data = make_ready_plan()
    data["limit"] = 101

    with pytest.raises(ValidationError):
        FinOpsQueryPlan.model_validate(data)


def test_rejects_unknown_sort_direction():
    data = make_ready_plan()
    data["sort_direction"] = "down"

    with pytest.raises(ValidationError):
        FinOpsQueryPlan.model_validate(data)


def test_sort_direction_requires_sort_by():
    data = make_ready_plan()
    data["sort_by"] = None
    data["sort_direction"] = "desc"

    with pytest.raises(
        ValidationError,
        match="sort_direction requires sort_by",
    ):
        FinOpsQueryPlan.model_validate(data)


def test_sort_by_requires_direction():
    data = make_ready_plan()
    data["sort_by"] = "billed_cost"
    data["sort_direction"] = None

    with pytest.raises(
        ValidationError,
        match="sort_by requires sort_direction",
    ):
        FinOpsQueryPlan.model_validate(data)


def test_rejects_reversed_time_range():
    data = make_ready_plan()
    data["time_range"] = {
        "start": date(2026, 9, 30),
        "end": date(2026, 9, 1),
    }

    with pytest.raises(
        ValidationError,
        match=(
            "Time range start must not "
            "be after end"
        ),
    ):
        FinOpsQueryPlan.model_validate(data)


def test_rejects_extra_field():
    data = make_ready_plan()
    data["unknown_field"] = "not allowed"

    with pytest.raises(ValidationError):
        FinOpsQueryPlan.model_validate(data)
        