from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.cloud import bigquery

from src.finops_query.query_bigquery_execution import (
    BigQueryExecutionPolicy,
    QueryCostLimitError,
    QueryExecutionError,
    QueryResultLimitError,
    build_bigquery_parameters,
    dry_run_query,
    execute_read_only_query,
)


def make_proposal():
    return SimpleNamespace(
        sql=(
            "SELECT SUM(BilledCost) AS billed_cost "
            "FROM `project.dataset.billing_table` "
            "WHERE ProviderName = @provider"
        ),
        parameters=[
            SimpleNamespace(
                name="provider",
                data_type="STRING",
                value="AWS",
            )
        ],
    )


def make_policy():
    return BigQueryExecutionPolicy(
        location="US",
        maximum_bytes_billed=100_000_000,
        max_result_rows=100,
        timeout_seconds=30,
    )


def test_build_bigquery_parameters():
    parameters = build_bigquery_parameters(make_proposal())

    assert len(parameters) == 1
    assert isinstance(parameters[0], bigquery.ScalarQueryParameter)
    assert parameters[0].name == "provider"
    assert parameters[0].type_ == "STRING"
    assert parameters[0].value == "AWS"


def test_dry_run_returns_report():
    client = MagicMock()
    dry_job = MagicMock()
    dry_job.total_bytes_processed = 2_000_000
    dry_job.job_id = "dry-job-1"
    client.query.return_value = dry_job

    report = dry_run_query(
        client=client,
        proposal=make_proposal(),
        policy=make_policy(),
    )

    assert report.total_bytes_processed == 2_000_000
    assert report.job_id == "dry-job-1"
    assert len(report.sql_sha256) == 64

    job_config = client.query.call_args.kwargs["job_config"]
    assert job_config.dry_run is True
    assert job_config.use_query_cache is False


def test_dry_run_rejects_expensive_query():
    client = MagicMock()
    dry_job = MagicMock()
    dry_job.total_bytes_processed = 200_000_000
    dry_job.job_id = "dry-job-expensive"
    client.query.return_value = dry_job

    with pytest.raises(QueryCostLimitError):
        dry_run_query(
            client=client,
            proposal=make_proposal(),
            policy=make_policy(),
        )


def test_execution_rejects_sql_changed_after_dry_run():
    client = MagicMock()
    proposal = make_proposal()

    dry_job = MagicMock()
    dry_job.total_bytes_processed = 1_000_000
    dry_job.job_id = "dry-job"
    client.query.return_value = dry_job

    report = dry_run_query(client, proposal, make_policy())

    proposal.sql += " LIMIT 1"

    with pytest.raises(QueryExecutionError):
        execute_read_only_query(
            client=client,
            proposal=proposal,
            policy=make_policy(),
            dry_run_report=report,
        )


def test_execution_returns_rows():
    client = MagicMock()
    proposal = make_proposal()
    policy = make_policy()

    dry_job = MagicMock()
    dry_job.total_bytes_processed = 1_000_000
    dry_job.job_id = "dry-job"

    execution_job = MagicMock()
    execution_job.total_bytes_processed = 1_000_000
    execution_job.job_id = "execution-job"

    row_iterator = MagicMock()
    row_iterator.total_rows = 1
    row_iterator.schema = [
        SimpleNamespace(name="billed_cost")
    ]
    row_iterator.__iter__.return_value = iter(
        [{"billed_cost": 125.50}]
    )
    execution_job.result.return_value = row_iterator

    client.query.side_effect = [dry_job, execution_job]

    report = dry_run_query(client, proposal, policy)

    result = execute_read_only_query(
        client=client,
        proposal=proposal,
        policy=policy,
        dry_run_report=report,
    )

    assert result.total_rows == 1
    assert result.columns == ["billed_cost"]
    assert result.rows == [{"billed_cost": 125.50}]
    assert result.job_id == "execution-job"


def test_execution_rejects_too_many_rows():
    client = MagicMock()
    proposal = make_proposal()
    policy = BigQueryExecutionPolicy(
        location="US",
        maximum_bytes_billed=100_000_000,
        max_result_rows=5,
    )

    dry_job = MagicMock()
    dry_job.total_bytes_processed = 1_000_000
    dry_job.job_id = "dry-job"

    execution_job = MagicMock()
    execution_job.total_bytes_processed = 1_000_000
    execution_job.job_id = "execution-job"

    row_iterator = MagicMock()
    row_iterator.total_rows = 6
    execution_job.result.return_value = row_iterator

    client.query.side_effect = [dry_job, execution_job]

    report = dry_run_query(client, proposal, policy)

    with pytest.raises(QueryResultLimitError):
        execute_read_only_query(
            client=client,
            proposal=proposal,
            policy=policy,
            dry_run_report=report,
        )