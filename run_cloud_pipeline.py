"""تشغيل مسار البيانات محليًا ونشر البيانات اختياريًا إلى BigQuery."""

import argparse
import math
import sqlite3
from contextlib import closing

import pandas as pd
from google.cloud import bigquery

from main import run_data_pipeline

from src.config import (
    BQ_DATASET_ID,
    BQ_PIPELINE_TABLE_ID,
    BQ_SCHEMA_TABLE_ID,
    BQ_STAGING_TABLE_ID,
    CLEANED_BILLING_FILE,
    DATABASE_FILE,
    GCP_PROJECT_ID,
    PIPELINE_REPORT_FILE,
)

from src.database import (
    save_cleaned_data_to_sqlite,
)

from src.pipeline_manifest import (
    utc_now,
    write_pipeline_manifest,
)


# استعلام مشترك لحساب المؤشرات التي سنستخدمها
# عند مقارنة CSV وSQLite وBigQuery.
METRICS_SQL = """
SELECT
    COUNT(*) AS row_count,
    COALESCE(SUM(BilledCost), 0) AS billed_cost,
    COALESCE(SUM(EffectiveCost), 0) AS effective_cost,
    COALESCE(
        SUM(
            CASE
                WHEN BilledCost < 0 THEN 1
                ELSE 0
            END
        ),
        0
    ) AS negative_rows,
    COALESCE(
        SUM(
            CASE
                WHEN BilledCost = 0 THEN 1
                ELSE 0
            END
        ),
        0
    ) AS zero_rows
FROM {table}
"""


def frame_metrics(
    data: pd.DataFrame,
) -> dict:

    required_columns = {
        "BilledCost",
        "EffectiveCost",
    }

    missing_columns = (
        required_columns
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing columns: "
            f"{sorted(missing_columns)}"
        )

    if data.empty:
        raise ValueError(
            "The cleaned data contains no rows."
        )

    # تحويل أعمدة التكلفة إلى أرقام.
    costs = data[
        [
            "BilledCost",
            "EffectiveCost",
        ]
    ].apply(
        pd.to_numeric,
        errors="raise",
    )

    if costs.isna().any().any():
        raise ValueError(
            "Financial columns contain missing values."
        )

    for column in costs.columns:
        valid_values = costs[column].map(
            math.isfinite
        )

        if not valid_values.all():
            raise ValueError(
                f"{column} contains non-finite values."
            )

    return {
        "row_count": len(data),
        "billed_cost": float(
            costs["BilledCost"].sum()
        ),
        "effective_cost": float(
            costs["EffectiveCost"].sum()
        ),
        "negative_rows": int(
            (
                costs["BilledCost"] < 0
            ).sum()
        ),
        "zero_rows": int(
            (
                costs["BilledCost"] == 0
            ).sum()
        ),
    }


def compare_metrics(
    expected: dict,
    actual: dict,
    label: str,
) -> None:

    failed_metrics = []

    for name, expected_value in expected.items():
        actual_value = actual[name]

        if name in {
            "billed_cost",
            "effective_cost",
        }:
            matches = math.isclose(
                float(expected_value),
                float(actual_value),
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
        else:
            matches = (
                expected_value
                == actual_value
            )

        status = (
            "PASS"
            if matches
            else "FAIL"
        )

        print(
            f"{label} | {name}: "
            f"{expected_value} / "
            f"{actual_value} | {status}"
        )

        if not matches:
            failed_metrics.append(name)

    if failed_metrics:
        raise ValueError(
            f"{label} mismatched metrics: "
            f"{failed_metrics}"
        )


def read_sqlite_metrics() -> dict:
    """قراءة المؤشرات المالية من قاعدة SQLite."""

    database_uri = (
        DATABASE_FILE.resolve().as_uri()
        + "?mode=ro"
    )

    with closing(
        sqlite3.connect(
            database_uri,
            uri=True,
        )
    ) as connection:

        connection.row_factory = (
            sqlite3.Row
        )

        row = connection.execute(
            METRICS_SQL.format(
                table="billing"
            )
        ).fetchone()

    return dict(row)


def run_local_pipeline():
    """
    تشغيل مسار البيانات المحلي.

    يشغل التنظيف والتحليل، ثم يحفظ البيانات
    في SQLite، وبعد ذلك يقارن CSV مع SQLite.
    """

    data = run_data_pipeline()

    save_cleaned_data_to_sqlite()

    # حساب المؤشرات من DataFrame المنظف.
    local_metrics = frame_metrics(
        data
    )

    # قراءة المؤشرات نفسها من SQLite.
    sqlite_metrics = (
        read_sqlite_metrics()
    )

    # التأكد أن SQLite تحتوي البيانات نفسها.
    compare_metrics(
        local_metrics,
        sqlite_metrics,
        "CSV vs SQLite",
    )

    print("LOCAL PIPELINE: PASS")

    return data, local_metrics


def publish_to_bigquery(
    data: pd.DataFrame,
    local_metrics: dict,
) -> dict:

    dataset_id = (
        f"{GCP_PROJECT_ID}."
        f"{BQ_DATASET_ID}"
    )

    schema_table = (
        f"{dataset_id}."
        f"{BQ_SCHEMA_TABLE_ID}"
    )

    staging_table = (
        f"{dataset_id}."
        f"{BQ_STAGING_TABLE_ID}"
    )

    published_table = (
        f"{dataset_id}."
        f"{BQ_PIPELINE_TABLE_ID}"
    )

    # التأكد أن الجداول الثلاثة مختلفة.
    table_ids = {
        schema_table,
        staging_table,
        published_table,
    }

    if len(table_ids) != 3:
        raise ValueError(
            "Reference, staging, and published "
            "tables must differ."
        )

    client = bigquery.Client(
        project=GCP_PROJECT_ID
    )

    # تساعدنا المرحلة في معرفة مكان الفشل.
    phase = "PREPARE"

    try:
        dataset = client.get_dataset(
            dataset_id
        )

        reference_table = client.get_table(
            schema_table
        )

        client.get_table(
            published_table
        )

        # استخراج ترتيب الأعمدة من جدول Schema المرجعي.
        schema_columns = [
            field.name
            for field
            in reference_table.schema
        ]

        # التأكد أن CSV يطابق أعمدة BigQuery.
        if list(data.columns) != schema_columns:
            raise ValueError(
                "Cleaned CSV columns do not match "
                "the BigQuery reference schema."
            )

        phase = "LOAD_STAGING"

        print(
            f"Staging table: {staging_table}"
        )

        # إعداد عملية رفع CSV إلى Staging.
        load_config = bigquery.LoadJobConfig(
            schema=reference_table.schema,
            source_format=(
                bigquery.SourceFormat.CSV
            ),
            skip_leading_rows=1,
            autodetect=False,
            allow_quoted_newlines=True,
            max_bad_records=0,
            write_disposition=(
                bigquery.WriteDisposition.WRITE_TRUNCATE
            ),
        )

        with CLEANED_BILLING_FILE.open(
            "rb"
        ) as csv_file:

            load_job = (
                client.load_table_from_file(
                    csv_file,
                    staging_table,
                    job_config=load_config,
                    location=dataset.location,
                )
            )

        print(
            f"Load job ID: {load_job.job_id}"
        )

        # انتظار انتهاء عملية الرفع.
        load_job.result()

        phase = "VALIDATE_STAGING"

        # حساب مؤشرات Staging للتحقق من البيانات.
        metrics_job = client.query(
            METRICS_SQL.format(
                table=f"`{staging_table}`"
            ),
            location=dataset.location,
            job_config=(
                bigquery.QueryJobConfig(
                    maximum_bytes_billed=(
                        10 * 1024 * 1024
                    ),
                )
            ),
        )

        staging_metrics = dict(
            next(
                iter(
                    metrics_job.result()
                )
            )
        )

        # مقارنة CSV المحلي مع BigQuery Staging.
        compare_metrics(
            local_metrics,
            staging_metrics,
            "CSV vs BigQuery Staging",
        )

        print(
            "Bytes processed: "
            f"{metrics_job.total_bytes_processed}"
        )

        phase = "PUBLISH"

        # نسخ Staging إلى الجدول النهائي بعد نجاح المقارنة.
        copy_job = client.copy_table(
            staging_table,
            published_table,
            location=dataset.location,
            job_config=(
                bigquery.CopyJobConfig(
                    create_disposition=(
                        bigquery.CreateDisposition.CREATE_NEVER
                    ),
                    write_disposition=(
                        bigquery.WriteDisposition.WRITE_TRUNCATE
                    ),
                )
            ),
        )

        copy_job.result()

        print(
            "BIGQUERY PUBLISH: PASS"
        )

        # إعادة معلومات التشغيل لإضافتها إلى التقرير.
        return {
            "staging_table": staging_table,
            "published_table": published_table,
            "load_job_id": load_job.job_id,
            "metrics_job_id": metrics_job.job_id,
            "copy_job_id": copy_job.job_id,
            "location": dataset.location,
        }

    except Exception:
        print(
            f"Failed BigQuery phase: {phase}"
        )
        raise

    finally:
        # إغلاق الاتصال سواء نجح التشغيل أو فشل.
        client.close()


def main() -> int:
    """اختيار التشغيل المحلي أو التشغيل السحابي الكامل."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--local-only",
        action="store_true",
        help=(
            "Run local validation without "
            "publishing to BigQuery."
        ),
    )

    args = parser.parse_args()

    report = {
        "status": "RUNNING",
        "phase": "START",
        "started_at_utc": utc_now(),
    }

    try:
        report["phase"] = (
            "LOCAL_PIPELINE"
        )

        # تشغيل المسار المحلي أولًا.
        data, local_metrics = (
            run_local_pipeline()
        )

        report["local_metrics"] = (
            local_metrics
        )

        # التوقف هنا عند طلب التشغيل المحلي فقط.
        if args.local_only:
            report["status"] = (
                "LOCAL_ONLY_SUCCESS"
            )

            report["phase"] = (
                "COMPLETED"
            )

            return 0

        report["phase"] = (
            "BIGQUERY_PIPELINE"
        )

        # رفع البيانات إلى BigQuery والتحقق منها.
        cloud_result = (
            publish_to_bigquery(
                data,
                local_metrics,
            )
        )

        report["cloud_result"] = (
            cloud_result
        )

        report["status"] = "SUCCESS"
        report["phase"] = "COMPLETED"

        return 0

    except Exception as error:
        # تسجيل الخطأ داخل التقرير ثم إظهاره للبرنامج.
        report["status"] = "FAILED"

        report["error_type"] = (
            type(error).__name__
        )

        report["error_message"] = (
            str(error)
        )

        raise

    finally:
        # يُنفذ هذا الجزء في النجاح والفشل.
        report["finished_at_utc"] = (
            utc_now()
        )

        report_path = (
            write_pipeline_manifest(
                PIPELINE_REPORT_FILE,
                report,
            )
        )

        print(
            f"Pipeline report: {report_path}"
        )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )