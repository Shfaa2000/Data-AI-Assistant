# هو مدير بناء الدليل: يجمع آخر Manifest ناجح، ومؤشرات Published، وأعلى خدمة، وتفصيلها، ثم يبني Evidence JSON موثوقًا ويحفظه.
import argparse
from pathlib import Path

from google.cloud import bigquery

from run_finops_analytics import read_service_costs
from src.config import (
    BQ_DATASET_ID,
    BQ_PIPELINE_TABLE_ID,
    GCP_PROJECT_ID,
    PIPELINE_MANIFESTS_DIR,
)
from src.evidence import (
    build_evidence,
    load_latest_successful_manifest,
    read_published_metrics,
    write_evidence,
)
from src.service_breakdown import read_service_breakdown


def main() -> int:
    """Build and save the latest deterministic FinOps evidence."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help=(
            "Optional manifest file used for a controlled "
            "reconciliation test."
        ),
    )
    args = parser.parse_args()
    client = None

    try:
        manifest = load_latest_successful_manifest(
            PIPELINE_MANIFESTS_DIR,
            manifest_path=args.manifest_path,
        )
        published_table = (
            f"{GCP_PROJECT_ID}."
            f"{BQ_DATASET_ID}."
            f"{BQ_PIPELINE_TABLE_ID}"
        )

        if manifest["published_table"] != published_table:
            raise ValueError(
                "Manifest published_table does not match config: "
                f"{manifest['published_table']} != {published_table}"
            )

        client = bigquery.Client(project=GCP_PROJECT_ID)
        dataset = client.get_dataset(
            f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"
        )

        published_metrics, metrics_job_id = (
            read_published_metrics(
                client=client,
                location=dataset.location,
                table_id=published_table,
            )
        )

        ranking = read_service_costs(
            client=client,
            location=dataset.location,
            currency="USD",
            provider="",
            top_n=1,
        )
        services = ranking.get("services", [])

        if not services:
            raise ValueError(
                "Service ranking returned no data."
            )

        top_service = services[0]
        breakdown = read_service_breakdown(
            client=client,
            location=dataset.location,
            provider=top_service["ProviderName"],
            service=top_service["ServiceName"],
            currency=top_service["BillingCurrency"],
        )

        query_job_ids = [
            metrics_job_id,
            ranking.get("query_job_id"),
            breakdown.get("query_job_id"),
        ]
        evidence = build_evidence(
            manifest=manifest,
            published_metrics=published_metrics,
            query_job_ids=query_job_ids,
            top_service=top_service,
            service_breakdown=breakdown,
        )
        evidence_path = write_evidence(evidence)

        passed_checks = sum(
            check.status == "PASS"
            for check in evidence.reconciliation_checks
        )
        total_checks = len(evidence.reconciliation_checks)

        print(f"EVIDENCE_STATUS: {evidence.status}")
        print(f"EVIDENCE_ID: {evidence.evidence_id}")
        print(f"PIPELINE_RUN_ID: {evidence.pipeline_run_id}")
        print(
            "RECONCILIATION_CHECKS: "
            f"{passed_checks}/{total_checks} PASS"
        )
        print(f"EVIDENCE_FILE: {evidence_path}")

        return 0 if evidence.status == "VERIFIED" else 1

    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
