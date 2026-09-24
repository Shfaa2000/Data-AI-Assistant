# يجهز تشغيلًا حيًا لتحميل BigQuery Schema والتحقق من Mapping وعرض السياق الآمن.
import json

from google.cloud import bigquery

from src.config import (
    BQ_DATASET_ID,
    GCP_PROJECT_ID,
)
from src.finops_query.query_schema_context import (
    build_query_schema_context,
)
from src.finops_query.query_schema_loader import (
    load_query_schema_catalog,
)
from src.finops_query.query_schema_validator import (
    validate_query_schema_mapping,
)


TABLE_ID = "billing_pipeline_day2"

FULL_TABLE_ID = (
    f"{GCP_PROJECT_ID}."
    f"{BQ_DATASET_ID}."
    f"{TABLE_ID}"
)

# ينشئ BigQuery Client ويحمّل Metadata الفعلية ثم يفحص Mapping مقابلها.
def main() -> int:
    """تشغيل فحص Query Schema الحقيقي."""

    client = bigquery.Client(
        project=GCP_PROJECT_ID
    )

    try:
        dataset = client.get_dataset(
            f"{GCP_PROJECT_ID}."
            f"{BQ_DATASET_ID}"
        )

        catalog = load_query_schema_catalog(
            client=client,
            project_id=GCP_PROJECT_ID,
            dataset_id=BQ_DATASET_ID,
            allowed_table_ids=(TABLE_ID,),
            location=dataset.location,
        )

        validate_query_schema_mapping(
            catalog=catalog,
            full_table_id=FULL_TABLE_ID,
        )

        context = build_query_schema_context(
            catalog=catalog,
            full_table_id=FULL_TABLE_ID,
        )

        print(
            "Query schema validation: PASS"
        )
        print(
            json.dumps(
                context,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    finally:
        client.close()

# يشغّل main عند تنفيذ الملف مباشرة من Terminal.
if __name__ == "__main__":
    raise SystemExit(main())