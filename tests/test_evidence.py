import json

from src.evidence import (
    DatasetMetrics,
    build_evidence,
    write_evidence,
)


def make_manifest(row_count: int = 1000) -> dict:
    return {
        "run_id": "pipeline-run-test",
        "status": "SUCCESS",
        "phase": "COMPLETED",
        "finished_at_utc": "2026-09-03T10:00:00+00:00",
        "published_table": (
            "data-ai-assistant-training."
            "cloud_finops.billing_pipeline_day2"
        ),
        "object_storage": {
            "uri": "local://finops-landing/test.csv",
        },
        "local_metrics": {
            "row_count": row_count,
            "billed_cost": 20.52022672899,
            "effective_cost": 14.97651418586,
            "negative_rows": 13,
            "zero_rows": 329,
        },
    }


def make_published_metrics() -> DatasetMetrics:
    return DatasetMetrics(
        row_count=1000,
        billed_cost=20.52022672899,
        effective_cost=14.97651418586,
        positive_billed_cost=24.0,
        negative_billed_cost=-3.47977327101,
        negative_line_count=13,
        zero_billed_line_count=329,
        provider_count=3,
        service_count=33,
        currency_count=1,
    )


def make_evidence(row_count: int = 1000):
    return build_evidence(
        manifest=make_manifest(row_count=row_count),
        published_metrics=make_published_metrics(),
        query_job_ids=["metrics-job", "ranking-job"],
        top_service={
            "ProviderName": "AWS",
            "ServiceName": "Amazon Elastic Compute Cloud",
            "BillingCurrency": "USD",
        },
        service_breakdown={
            "status": "ok",
            "returned_groups": 3,
        },
    )


def test_matching_metrics_create_verified_evidence(tmp_path):
    evidence = make_evidence()
    latest_file = tmp_path / "latest.json"

    evidence_path = write_evidence(
        evidence,
        evidence_dir=tmp_path,
        latest_evidence_file=latest_file,
    )

    assert evidence.status == "VERIFIED"
    assert all(
        check.status == "PASS"
        for check in evidence.reconciliation_checks
    )
    assert evidence_path.is_file()
    assert latest_file.is_file()

    latest_payload = json.loads(
        latest_file.read_text(encoding="utf-8")
    )
    assert latest_payload["evidence_id"] == evidence.evidence_id


def test_failed_evidence_does_not_replace_latest(tmp_path):
    latest_file = tmp_path / "latest.json"

    verified = make_evidence()
    write_evidence(
        verified,
        evidence_dir=tmp_path,
        latest_evidence_file=latest_file,
    )
    latest_before_failure = latest_file.read_text(
        encoding="utf-8"
    )

    failed = make_evidence(row_count=999)
    failed_path = write_evidence(
        failed,
        evidence_dir=tmp_path,
        latest_evidence_file=latest_file,
    )

    assert failed.status == "FAILED"
    assert any(
        check.metric == "row_count"
        and check.status == "FAIL"
        for check in failed.reconciliation_checks
    )
    assert failed_path.is_file()
    assert (
        latest_file.read_text(encoding="utf-8")
        == latest_before_failure
    )

