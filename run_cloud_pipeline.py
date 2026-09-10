# يشغّل المعالجة المحلية، يصالح النتائج، ثم يرفع البيانات وينشرها بأمان
# يستدعي أجزاء المشروع بالترتيب، ويتأكد أن البيانات المحلية والسحابية متطابقة قبل أن يسمح باستبدال الجدول النهائي.

import argparse
import math
import sqlite3
import subprocess
import sys
# الاغلاق وظيفتها ضمان استدعاء:
from contextlib import closing
from uuid import uuid4
from pathlib import Path
import pandas as pd
from google.cloud import bigquery

from src.config import (
    BASE_DIR,
    CLEANED_BILLING_FILE,
    DATABASE_FILE,
    GCP_PROJECT_ID,
    BQ_DATASET_ID,
    BQ_SCHEMA_TABLE_ID,
    BQ_PIPELINE_TABLE_ID,
    BQ_STAGING_TABLE_ID,
    LOCAL_OBJECT_STORAGE_ROOT,
    LOCAL_OBJECT_STORAGE_BUCKET,
    LOCAL_OBJECT_STORAGE_PREFIX,
    PIPELINE_MANIFESTS_DIR,
)
from src.pipeline_manifest import (
    utc_now,
    write_pipeline_manifest,
)

from src.object_storage import (
    build_object_name,
    calculate_file_sha256,
    store_or_reuse_local_object,
)

# حساب مؤشرات المصالحة المالية المشتركة بين SQLite وBigQuery
METRICS_SQL = """
SELECT
    COUNT(*) AS row_count,
    COALESCE(SUM(BilledCost), 0) AS billed_cost,
    COALESCE(SUM(EffectiveCost), 0) AS effective_cost,
    COALESCE(SUM(CASE WHEN BilledCost < 0 THEN 1 ELSE 0 END), 0)
        AS negative_rows,
    COALESCE(SUM(CASE WHEN BilledCost = 0 THEN 1 ELSE 0 END), 0)
        AS zero_rows
FROM {table}
"""

# التحقق من أعمدة التكلفة واستخراج مؤشرات المصالحة من DataFrame
def frame_metrics(data):
    required = {"BilledCost", "EffectiveCost"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if data.empty:
        raise ValueError("CSV is empty.")

    costs = data[list(required)].apply(pd.to_numeric, errors="raise")
    if costs.isna().any().any():
        raise ValueError("Missing financial values.")
    if not all(costs[column].map(math.isfinite).all() for column in costs):
        raise ValueError("Non-finite financial values.")

    return {
        "row_count": len(data),
        "billed_cost": float(costs["BilledCost"].sum()),
        "effective_cost": float(costs["EffectiveCost"].sum()),
        "negative_rows": int((costs["BilledCost"] < 0).sum()),
        "zero_rows": int((costs["BilledCost"] == 0).sum()),
    }

# مقارنة مؤشرات المصدر والهدف مع السماح بفروق عشرية ضئيلة
def compare_metrics(expected, actual, label):
    failed = []
    for name, value in expected.items():
        other = actual[name]
        if name in {"billed_cost", "effective_cost"}:
            # لأن العمليات العشرية في الحاسوب قد تنتج فروقًا صغيرة جدً
            matches = math.isclose(
                float(value), float(other), rel_tol=1e-9, abs_tol=1e-9
            )
        else:
            matches = value == other
        status = "PASS" if matches else "FAIL"
        print(f"{label} | {name}: {value} / {other} | {status}")
        if not matches:
            failed.append(name)

    if failed:
        raise ValueError(f"{label}: mismatched metrics: {failed}")

# مطابقة المؤشرات المالية بين CSV المنظف وقاعدة SQLite
def run_local():
    subprocess.run([sys.executable, "main.py"], cwd=BASE_DIR, check=True)
    subprocess.run(
        [sys.executable, "-m", "src.database"], cwd=BASE_DIR, check=True
    )

    if not CLEANED_BILLING_FILE.is_file():
        raise FileNotFoundError(CLEANED_BILLING_FILE)
    if not DATABASE_FILE.is_file():
        raise FileNotFoundError(DATABASE_FILE)

    data = pd.read_csv(CLEANED_BILLING_FILE)
    metrics = frame_metrics(data)
    uri = DATABASE_FILE.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            METRICS_SQL.format(table="billing")
        ).fetchone()

    compare_metrics(metrics, dict(row), "CSV vs SQLite")
    return data, metrics

# يأخذ ملف CSV المنظف الجاهز، يحسب بصمته، يبني له عنوانًا حسب محتواه، ثم يخزنه في Landing Zone أو يعيد استخدام النسخة الموجودة، ويعيد معلوماتها.
def store_cleaned_artifact():
    file_hash = calculate_file_sha256(
        CLEANED_BILLING_FILE
    )

    object_name = build_object_name(
        file_hash,
        LOCAL_OBJECT_STORAGE_PREFIX,
    )

    metadata = store_or_reuse_local_object(
        source_path=CLEANED_BILLING_FILE,
        storage_root=LOCAL_OBJECT_STORAGE_ROOT,
        bucket_name=LOCAL_OBJECT_STORAGE_BUCKET,
        object_name=object_name,
        expected_sha256=file_hash,
    )

    print(
        f"OBJECT_BACKEND: "
        f"{metadata['backend']}"
    )
    print(
        f"OBJECT_URI: "
        f"{metadata['uri']}"
    )
    print(
        f"OBJECT_SHA256: "
        f"{metadata['sha256']}"
    )
    print(
        f"OBJECT_SIZE_BYTES: "
        f"{metadata['size_bytes']}"
    )
    print(
        f"OBJECT_STORED: "
        f"{metadata['stored']}"
    )
    print(
        f"OBJECT_REUSED: "
        f"{metadata['reused']}"
    )

    return metadata

# مطابقة Staging مع البيانات المحلية قبل السماح بالنشر
def upload_and_check(data, local_metrics,object_metadata):
    dataset_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"
    schema_id = f"{dataset_id}.{BQ_SCHEMA_TABLE_ID}"
    staging_id = f"{dataset_id}.{BQ_STAGING_TABLE_ID}"
    target_id = f"{dataset_id}.{BQ_PIPELINE_TABLE_ID}"

    if len({schema_id, staging_id, target_id}) != 3:
        raise ValueError("Reference, staging, and published tables must differ.")

    client = bigquery.Client(project=GCP_PROJECT_ID)
    phase = "PREPARE"

    try:
        dataset = client.get_dataset(dataset_id)
        source = client.get_table(schema_id)
        client.get_table(target_id)

        schema_columns = [field.name for field in source.schema]
        if list(data.columns) != schema_columns:
            raise ValueError(
                f"CSV columns/order: {list(data.columns)}\n"
                f"Reference columns/order: {schema_columns}"
            )

        phase = "LOAD_STAGING"
        print(f"STAGING_TABLE: {staging_id}")

        load_config = bigquery.LoadJobConfig(
            schema=source.schema,
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=False,
            allow_quoted_newlines=True,
            max_bad_records=0,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        object_file = Path(
            object_metadata["local_path"]
        )
        with object_file.open("rb") as file:            
            load_job = client.load_table_from_file(
                file,
                staging_id,
                job_config=load_config,
                location=dataset.location,
            )

        print(f"LOAD_JOB_ID: {load_job.job_id}")
        load_job.result()

        phase = "VALIDATE_STAGING"
        query_job = client.query(
            METRICS_SQL.format(table=f"`{staging_id}`"),
            location=dataset.location,
            job_config=bigquery.QueryJobConfig(
                maximum_bytes_billed=10 * 1024 * 1024,
            ),
        )

        print(f"QUERY_JOB_ID: {query_job.job_id}")
        staging_metrics = dict(next(iter(query_job.result())))
        compare_metrics(local_metrics, staging_metrics, "CSV vs Staging")
        print(f"BYTES_PROCESSED: {query_job.total_bytes_processed}")
        print("STAGING_VALIDATED")

        phase = "PUBLISH"
        copy_job_id = f"finops_publish_{uuid4().hex}"
        print(f"PUBLISH_TARGET: {target_id}")
        print(f"COPY_JOB_ID: {copy_job_id}")

        copy_job = client.copy_table(
            staging_id,
            target_id,
            job_id=copy_job_id,
            location=dataset.location,
            job_config=bigquery.CopyJobConfig(
                create_disposition=bigquery.CreateDisposition.CREATE_NEVER,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            ),
        )
        copy_job.result()

        print("PUBLISH_SUCCESS")
        print(f"LOCATION: {dataset.location}")
        print("PIPELINE_SUCCESS")

        return {
        "staging_table": staging_id,
        "published_table": target_id,
        "load_job_id": load_job.job_id,
        "metrics_query_job_id": (
            query_job.job_id
        ),
        "copy_job_id": copy_job.job_id,
        "location": dataset.location,
    }

    except Exception:
        print(f"FAILED_PHASE: {phase}")
        if phase != "PUBLISH":
            print("PUBLISHED_TABLE_NOT_UPDATED_BY_THIS_RUN")
        else:
            print("CHECK_COPY_JOB_STATUS_BEFORE_RETRY")
        raise

    finally:
    #   إغلاق BigQuery Client بعد النجاح أو الفشل.
        client.close()

# تحديد نمط التشغيل المحلي أو السحابي وبدء الـPipeline
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--local-only",
        action="store_true",
    )

    args = parser.parse_args()

    run_id = uuid4().hex

    manifest = {
        "run_id": run_id,
        "status": "RUNNING",
        "phase": "START",
        "started_at_utc": utc_now(),
    }

    try:
        data, metrics = run_local()

        
        manifest["phase"] = "LOCAL_VALIDATED"
        manifest["local_metrics"] = metrics

        if args.local_only:
            manifest["status"] = (
                "LOCAL_ONLY_SUCCESS"
            )

            print("LOCAL_CHECK_SUCCESS")
            return
        # يستدعي تابع تخزين ملف CSV المنظف.
        object_metadata = (
            store_cleaned_artifact()
        )

        manifest["phase"] = "OBJECT_READY"
        # يحفظ Metadata داخل Manifest.
        manifest["object_storage"] = (
            object_metadata
        )

        cloud_publish = upload_and_check(
            data,
            metrics,
            object_metadata,
        )
        #تخزين نتيجة Cloud داخل Manifest
        manifest["cloud_publish"] = (cloud_publish)
        manifest["published_table"] = (cloud_publish["published_table"])

        manifest["phase"] = "COMPLETED"
        manifest["status"] = "SUCCESS"

    except Exception as error:
        manifest["status"] = "FAILED"
        manifest["error"] = str(error)
        raise

    finally:
        manifest["finished_at_utc"] = (
            utc_now()
        )

        manifest_path = (
            write_pipeline_manifest(
                PIPELINE_MANIFESTS_DIR,
                manifest,
            )
        )

        print(
            f"PIPELINE_MANIFEST: "
            f"{manifest_path}"
        )

if __name__ == "__main__":
    main()