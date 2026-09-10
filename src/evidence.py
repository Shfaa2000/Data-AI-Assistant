# يعرّف عقد Evidence، يقرأ مقاييس الجدول المنشور، يطابقها مع Manifest، ويحفظ أحدث Evidence موثّق.
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from google.cloud import bigquery
from pydantic import BaseModel, Field

from src.config import EVIDENCE_DIR, LATEST_EVIDENCE_FILE


class DatasetMetrics(BaseModel):
    """عقد المقاييس المالية المحسوبة مباشرة من Published BigQuery Table.
    يتحقق النموذج من أسماء الحقول وأنواعها وبعض القيود،"""

    row_count: int = Field(ge=0)
    billed_cost: float
    effective_cost: float
    positive_billed_cost: float = Field(ge=0)
    negative_billed_cost: float = Field(le=0)
    negative_line_count: int = Field(ge=0)
    zero_billed_line_count: int = Field(ge=0)
    provider_count: int = Field(ge=0)
    service_count: int = Field(ge=0)
    currency_count: int = Field(ge=0)


class MetricCheck(BaseModel):
    """One reconciliation result between the pipeline and BigQuery."""

    metric: str
    expected: int | float
    actual: int | float
    status: Literal["PASS", "FAIL"]


class EvidenceBundle(BaseModel):
    """ العقد الكامل للـEvidence Snapshot. يربط حقيقة مالية منشورة بتشغيل Pipeline محدد، ويحفظ
    المقاييس، ونتائج المطابقة، وأعلى خدمة، وتفصيلها، ومعرفات استعلامات BigQuery، وحدود الاستنتاج."""

    schema_version: Literal["1.0"] = "1.0"
    evidence_id: str = Field(min_length=1)
    generated_at_utc: datetime
    pipeline_run_id: str = Field(min_length=1)
    status: Literal["VERIFIED", "FAILED"]
    source_table: str = Field(min_length=1)
    object_uri: str | None = None
    dataset_metrics: DatasetMetrics
    reconciliation_checks: list[MetricCheck]
    top_service: dict[str, Any] | None = None
    service_breakdown: dict[str, Any] | None = None
    query_job_ids: list[str]
    limitations: list[str]


PUBLISHED_METRICS_SQL = """
SELECT
    COUNT(*) AS row_count,
    SUM(BilledCost) AS billed_cost,
    SUM(EffectiveCost) AS effective_cost,
    SUM(IF(BilledCost > 0, BilledCost, 0))
        AS positive_billed_cost,
    SUM(IF(BilledCost < 0, BilledCost, 0))
        AS negative_billed_cost,
    COUNTIF(BilledCost < 0) AS negative_line_count,
    COUNTIF(BilledCost = 0) AS zero_billed_line_count,
    COUNT(DISTINCT ProviderName) AS provider_count,
    COUNT(DISTINCT ServiceName) AS service_count,
    COUNT(DISTINCT BillingCurrency) AS currency_count
FROM `{table_id}`
"""

# اربط أسماء المقاييس داخل Manifest بأسمائها داخل DatasetMetrics.
RECONCILIATION_FIELDS = {
    "row_count": "row_count",
    "billed_cost": "billed_cost",
    "effective_cost": "effective_cost",
    "negative_rows": "negative_line_count",
    "zero_rows": "zero_billed_line_count",
}


def read_published_metrics(
    client,
    location: str,
    table_id: str,
) -> tuple[DatasetMetrics, str]:
    """Read one deterministic metrics row from the published table."""

    sql = PUBLISHED_METRICS_SQL.format(table_id=table_id)
    query_job = client.query(
        sql,
        location=location,
        job_config=bigquery.QueryJobConfig(
            # يمنع الاستعلام من معالجة أكثر من 10 MiB.
            maximum_bytes_billed=10 * 1024 * 1024,
        ),
    )
    row = next(iter(query_job.result()))
    raw_metrics = dict(row.items())

    if raw_metrics["row_count"] == 0:
        raise ValueError(
            "Published table contains no financial rows."
        )

    metrics = DatasetMetrics.model_validate(raw_metrics)
    return metrics, query_job.job_id


def parse_manifest_time(manifest: dict) -> datetime:
    """Convert the manifest UTC timestamp text to datetime."""

    value = manifest["finished_at_utc"]
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def load_latest_successful_manifest(
    manifests_dir: Path,
    manifest_path: Path | None = None,
) -> dict:
    """Select the newest complete, successfully published run."""

    if manifest_path is not None:
        manifest_paths = [manifest_path]
    else:
        manifest_paths = list(manifests_dir.glob("*.json"))

    candidates = []

    for current_path in manifest_paths:
        manifest = json.loads(
            current_path.read_text(encoding="utf-8")
        )

        is_successful = (
            manifest.get("status") == "SUCCESS"
            and manifest.get("phase") == "COMPLETED"
            and manifest.get("finished_at_utc") is not None
            and manifest.get("published_table") is not None
        )

        if is_successful:
            candidates.append(manifest)

    if not candidates:
        raise FileNotFoundError(
            "No successful pipeline manifest was found. "
            "Run the full cloud pipeline after adding published_table."
        )

    latest_manifest = max(candidates, key=parse_manifest_time)
    required_fields = {
        "run_id",
        "status",
        "phase",
        "finished_at_utc",
        "local_metrics",
        "object_storage",
        "published_table",
    }
    missing_fields = required_fields - latest_manifest.keys()

    if missing_fields:
        raise ValueError(
            "Manifest is missing fields: "
            f"{sorted(missing_fields)}"
        )

    return latest_manifest

# قارن المقاييس الحرجة بين Manifest المحلي وPublished BigQuery Table.
def reconcile_metrics(
    local_metrics: dict,
    published_metrics: DatasetMetrics,
) -> list[MetricCheck]:
    checks = []

    for local_name, published_name in (
        RECONCILIATION_FIELDS.items()
    ):
        if local_name not in local_metrics:
            raise ValueError(
                f"Manifest local_metrics is missing: {local_name}"
            )

        expected = local_metrics[local_name]
        actual = getattr(published_metrics, published_name)

        if isinstance(expected, int) and isinstance(actual, int):
            passed = expected == actual
        else:
            passed = math.isclose(
                float(expected),
                float(actual),
                rel_tol=1e-9,
                abs_tol=1e-9,
            )

        checks.append(
            MetricCheck(
                metric=published_name,
                expected=expected,
                actual=actual,
                status="PASS" if passed else "FAIL",
            )
        )

    return checks

# ابنِ Evidence Snapshot من المصادر التي جُمعت مسبقاً.
def build_evidence(
    manifest: dict,
    published_metrics: DatasetMetrics,
    query_job_ids: list[str],
    top_service: dict,
    service_breakdown: dict,
) -> EvidenceBundle:

    checks = reconcile_metrics(
        manifest["local_metrics"],
        published_metrics,
    )
    all_checks_passed = all(
        check.status == "PASS" for check in checks
    )
    evidence_status = (
        "VERIFIED" if all_checks_passed else "FAILED"
    )
    object_metadata = manifest.get("object_storage", {})
    object_uri = (
        object_metadata.get("uri")
        or object_metadata.get("object_uri")
    )

    return EvidenceBundle(
        evidence_id=uuid4().hex,
        generated_at_utc=datetime.now(timezone.utc),
        pipeline_run_id=manifest["run_id"],
        status=evidence_status,
        source_table=manifest["published_table"],
        object_uri=object_uri,
        dataset_metrics=published_metrics,
        reconciliation_checks=checks,
        top_service=top_service,
        service_breakdown=service_breakdown,
        query_job_ids=[
            job_id for job_id in query_job_ids if job_id
        ],
        limitations=[
            "Evidence covers only loaded billing periods.",
            "No forecasting is included.",
            "No resource-level root cause is proven.",
            (
                "Recommendations require additional "
                "business context."
            ),
        ],
    )


def write_evidence(
    evidence: EvidenceBundle,
    evidence_dir: Path | None = None,
    latest_evidence_file: Path | None = None,
) -> Path:
    """Save history; update latest only for verified evidence."""

    target_dir = evidence_dir or EVIDENCE_DIR
    latest_file = latest_evidence_file or LATEST_EVIDENCE_FILE
    target_dir.mkdir(parents=True, exist_ok=True)

    evidence_path = target_dir / f"{evidence.evidence_id}.json"
    json_content = evidence.model_dump_json(indent=2)
    evidence_path.write_text(json_content, encoding="utf-8")

    if evidence.status == "VERIFIED":
        latest_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_latest = latest_file.with_name(
            "latest.tmp.json"
        )
        # يكتب ملفاً مؤقتاً أولاً ثم يستبدل latest. بذلك لا يترك latest.json ناقصاً إذا انقطع البرنامج أثناء الكتابة.
        temporary_latest.write_text(
            json_content,
            encoding="utf-8",
        )
        temporary_latest.replace(latest_file)

    return evidence_path