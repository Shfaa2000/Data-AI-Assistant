"""
ينفذ SQL مرجعية مستقلة على BigQuery للتحقق اليدوي من نتائج المسار.
"""

import json
import os

from dotenv import load_dotenv
from google.cloud import bigquery


DEFAULT_PROJECT_ID = "data-ai-assistant-training"
DEFAULT_LOCATION = "US"
DEFAULT_MAXIMUM_BYTES_BILLED = 100 * 1024 * 1024


REFERENCE_SQL = """
SELECT SUM(BilledCost) AS billed_cost
FROM `data-ai-assistant-training.cloud_finops.billing_pipeline_day2`
WHERE BillingCurrency = 'USD';
""".strip()


def _validate_reference_sql(sql: str) -> None:
    normalized = sql.strip().upper()

    if not normalized:
        raise ValueError("REFERENCE_SQL is empty.")

    if not normalized.startswith(("SELECT", "WITH")):
        raise ValueError(
            "Only a SELECT or WITH query is allowed."
        )


def main() -> int:
    load_dotenv()

    project_id = os.getenv(
        "GOOGLE_CLOUD_PROJECT",
        DEFAULT_PROJECT_ID,
    ).strip()

    location = os.getenv(
        "BIGQUERY_LOCATION",
        DEFAULT_LOCATION,
    ).strip()

    maximum_bytes_billed = int(
        os.getenv(
            "FINOPS_MAXIMUM_BYTES_BILLED",
            str(DEFAULT_MAXIMUM_BYTES_BILLED),
        )
    )

    _validate_reference_sql(REFERENCE_SQL)

    client = bigquery.Client(project=project_id)

    try:
        # يفحص صلاحية الاستعلام وتكلفته من دون قراءة النتائج.
        dry_run_config = bigquery.QueryJobConfig(
            dry_run=True,
            use_query_cache=False,
        )

        dry_run_job = client.query(
            REFERENCE_SQL,
            job_config=dry_run_config,
            location=location,
        )

        estimated_bytes = (
            dry_run_job.total_bytes_processed or 0
        )

        print("Reference SQL Dry Run: PASS")
        print(f"Estimated bytes: {estimated_bytes}")

        if estimated_bytes > maximum_bytes_billed:
            raise RuntimeError(
                "Reference SQL exceeds "
                "FINOPS_MAXIMUM_BYTES_BILLED."
            )

        execution_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=maximum_bytes_billed,
            use_legacy_sql=False,
        )

        query_job = client.query(
            REFERENCE_SQL,
            job_config=execution_config,
            location=location,
        )

        rows = [
            dict(row.items())
            for row in query_job.result()
        ]

        print("Reference SQL Execution: PASS")
        print(f"Row count: {len(rows)}")
        print("Result:")
        print(
            json.dumps(
                rows,
                indent=2,
                default=str,
            )
        )

        return 0

    finally:
        client.close()


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)