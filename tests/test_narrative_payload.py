from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.evidence import EvidenceBundle
from src.narrative_payload import (
    build_service_narrative_payload,
    load_verified_evidence,
)


def make_evidence(
    status: str = "VERIFIED",
    breakdown_service: str = (
        "Amazon Elastic Compute Cloud"
    ),
) -> EvidenceBundle:
    """إنشاء Evidence تجريبية لاختبارات Payload."""

    return EvidenceBundle(
        schema_version="1.0",
        evidence_id="evidence-test",
        generated_at_utc=datetime(
            2026,
            9,
            14,
            tzinfo=timezone.utc,
        ),
        pipeline_run_id="pipeline-test",
        status=status,
        source_table=(
            "data-ai-assistant-training."
            "cloud_finops.billing_pipeline_day2"
        ),
        object_uri=(
            "local://finops-landing/test.csv"
        ),
        dataset_metrics={
            "row_count": 1000,
            "billed_cost": 999.0,
            "effective_cost": 888.0,
            "positive_billed_cost": 1000.0,
            "negative_billed_cost": -1.0,
            "negative_line_count": 1,
            "zero_billed_line_count": 10,
            "provider_count": 3,
            "service_count": 33,
            "currency_count": 1,
        },
        reconciliation_checks=[],
        top_service={
            "ProviderName": "AWS",
            "ServiceName": (
                "Amazon Elastic Compute Cloud"
            ),
            "BillingCurrency": "USD",
        },
        service_breakdown={
            "status": "ok",
            "provider": "AWS",
            "service": breakdown_service,
            "currency": "USD",
            "period_scope": "all_loaded_periods",
            "totals": {
                "billed_cost": 16.041693050500022,
                "effective_cost": 13.0,
                "negative_billed_cost": -2.6137,
            },
            "groups": [],
        },
        query_job_ids=["query-test"],
        limitations=[
            "Evidence covers only loaded billing periods.",
            "No utilization metrics are included.",
        ],
    )


def write_test_evidence(
    tmp_path,
    evidence: EvidenceBundle,
):
    evidence_path = tmp_path / "latest.json"

    evidence_path.write_text(
        evidence.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return evidence_path


def test_loads_verified_evidence(tmp_path):
    evidence_path = write_test_evidence(
        tmp_path,
        make_evidence(),
    )

    result = load_verified_evidence(
        evidence_path
    )

    assert result.status == "VERIFIED"
    assert result.evidence_id == "evidence-test"
    assert result.pipeline_run_id == "pipeline-test"


def test_rejects_missing_evidence_file(tmp_path):
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_verified_evidence(missing_path)


def test_rejects_invalid_evidence_json(tmp_path):
    evidence_path = tmp_path / "latest.json"

    evidence_path.write_text(
        "not valid JSON",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_verified_evidence(evidence_path)


def test_rejects_failed_evidence(tmp_path):
    evidence_path = write_test_evidence(
        tmp_path,
        make_evidence(status="FAILED"),
    )

    with pytest.raises(ValueError):
        load_verified_evidence(evidence_path)


def test_builds_payload_from_service_breakdown():
    evidence = make_evidence()

    payload = build_service_narrative_payload(
        evidence
    )

    assert payload["provider"] == "AWS"
    assert (
        payload["service"]
        == "Amazon Elastic Compute Cloud"
    )
    assert payload["currency"] == "USD"

    assert (
        payload["billed_cost"]
        == 16.041693050500022
    )
    assert payload["effective_cost"] == 13.0
    assert payload["negative_billed_cost"] == -2.6137

    # يثبت أننا لم نأخذ تكلفة Dataset الكاملة.
    assert (
        payload["billed_cost"]
        != evidence.dataset_metrics.billed_cost
    )


def test_rejects_missing_service_breakdown():
    evidence = make_evidence().model_copy(
        update={
            "service_breakdown": None,
        }
    )

    with pytest.raises(ValueError):
        build_service_narrative_payload(
            evidence
        )


def test_rejects_mismatched_service_identity():
    evidence = make_evidence(
        breakdown_service=(
            "Amazon Simple Storage Service"
        )
    )

    with pytest.raises(ValueError):
        build_service_narrative_payload(
            evidence
        )