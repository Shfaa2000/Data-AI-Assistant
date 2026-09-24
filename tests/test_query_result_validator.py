from types import SimpleNamespace

import pytest

from src.finops_query.query_bigquery_execution import (
    QueryExecutionResult,
)
from src.finops_query.query_result_validator import (
    QueryResultValidationError,
    validate_query_result,
)


def make_plan(
    dimensions=None,
    limit=100,
):
    return SimpleNamespace(
        status="ready",
        metrics=[
            SimpleNamespace(
                name="billed_cost",
                aggregation="sum",
            )
        ],
        dimensions=dimensions or [],
        limit=limit,
    )


def make_result(
    columns=None,
    rows=None,
):
    result_rows = rows or [{"billed_cost": 125.50}]

    return QueryExecutionResult(
        columns=columns or ["billed_cost"],
        rows=result_rows,
        total_rows=len(result_rows),
        total_bytes_processed=1_000_000,
        job_id="job-1",
        location="US",
    )


def test_accepts_valid_scalar_result():
    validate_query_result(
        query_plan=make_plan(),
        result=make_result(),
    )


def test_rejects_missing_expected_column():
    result = make_result(
        columns=["total_cost"],
        rows=[{"total_cost": 125.50}],
    )

    with pytest.raises(QueryResultValidationError):
        validate_query_result(make_plan(), result)


def test_rejects_non_numeric_metric():
    result = make_result(
        rows=[{"billed_cost": "not-a-number"}],
    )

    with pytest.raises(QueryResultValidationError):
        validate_query_result(make_plan(), result)


def test_rejects_nan_metric():
    result = make_result(
        rows=[{"billed_cost": float("nan")}],
    )

    with pytest.raises(QueryResultValidationError):
        validate_query_result(make_plan(), result)


def test_rejects_more_than_one_scalar_row():
    result = make_result(
        rows=[
            {"billed_cost": 10.0},
            {"billed_cost": 20.0},
        ],
    )

    with pytest.raises(QueryResultValidationError):
        validate_query_result(make_plan(), result)


def test_accepts_grouped_result():
    plan = make_plan(
        dimensions=["service"],
        limit=5,
    )

    result = QueryExecutionResult(
        columns=["service", "billed_cost"],
        rows=[
            {
                "service": "EC2",
                "billed_cost": 80.0,
            },
            {
                "service": "S3",
                "billed_cost": 45.0,
            },
        ],
        total_rows=2,
        total_bytes_processed=1_000_000,
        job_id="job-2",
        location="US",
    )

    validate_query_result(plan, result)


def test_rejects_result_above_plan_limit():
    plan = make_plan(
        dimensions=["service"],
        limit=1,
    )

    result = QueryExecutionResult(
        columns=["service", "billed_cost"],
        rows=[
            {"service": "EC2", "billed_cost": 80.0},
            {"service": "S3", "billed_cost": 45.0},
        ],
        total_rows=2,
        total_bytes_processed=1_000_000,
        job_id="job-3",
        location="US",
    )

    with pytest.raises(QueryResultValidationError):
        validate_query_result(plan, result)