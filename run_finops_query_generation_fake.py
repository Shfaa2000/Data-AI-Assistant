"""يشغّل رحلة Query Generation باستخدام BigQuery Schema حقيقية واستجابات Gemini وهمية دون تنفيذ SQL."""

import json
from types import SimpleNamespace

from google.cloud import bigquery

from src.config import (
    BQ_DATASET_ID,
    GCP_PROJECT_ID,
)
from src.finops_query.query_generation_service import (
    generate_finops_query,
)
from src.finops_query.query_schema_loader import (
    load_query_schema_catalog,
)


TABLE_ID = "billing_pipeline_day2"

FULL_TABLE_ID = (
    f"{GCP_PROJECT_ID}."
    f"{BQ_DATASET_ID}."
    f"{TABLE_ID}"
)

# يحاكي استدعاءين متتاليين: الأول يعيد Query Plan والثاني يعيد SQL Proposal.
class FakeInteractions:
    """بديل محلي عن Gemini Interactions."""

    def __init__(
        self,
        output_texts: list[str],
    ):
        self.output_texts = list(
            output_texts
        )
        self.requests = []

    def create(
        self,
        **kwargs,
    ):
        self.requests.append(kwargs)

        if not self.output_texts:
            raise RuntimeError(
                "No fake response remains."
            )

        return SimpleNamespace(
            id=(
                "fake-interaction-"
                f"{len(self.requests)}"
            ),
            output_text=(
                self.output_texts.pop(0)
            ),
        )


class FakeGeminiClient:
    """Client وهمية لا تتصل بخدمة Gemini."""

    def __init__(
        self,
        output_texts: list[str],
    ):
        self.interactions = FakeInteractions(
            output_texts
        )

# ينشئ جواب التخطيط الوهمي لسؤال total billed cost for AWS.
def build_fake_plan_output() -> str:
    """إرجاع Query Plan تجريبية بصيغة JSON."""

    return json.dumps(
        {
            "status": "ready",
            "intent": (
                "Calculate total billed cost "
                "for AWS."
            ),
            "metrics": [
                {
                    "name": "billed_cost",
                    "aggregation": "sum",
                }
            ],
            "dimensions": [],
            "filters": [
                {
                    "column": "provider",
                    "operator": "eq",
                    "value": "AWS",
                }
            ],
            "time_range": None,
            "sort_by": None,
            "sort_direction": None,
            "limit": 100,
            "clarification_question": None,
            "unsupported_reason": None,
        }
    )

# ينشئ SQL Proposal تجريبية تستخدم الجدول والعمود وNamed Parameter المسموحة.
def build_fake_sql_output() -> str:
    """إرجاع SQL Proposal تجريبية بصيغة JSON."""

    return json.dumps(
        {
            "sql": (
                "SELECT "
                "SUM(BilledCost) AS billed_cost "
                "FROM "
                "`data-ai-assistant-training."
                "cloud_finops."
                "billing_pipeline_day2` "
                "WHERE ProviderName = @provider"
            ),
            "parameters": [
                {
                    "name": "provider",
                    "data_type": "STRING",
                    "value": "AWS",
                }
            ],
        }
    )

# يحمل Physical Schema الحقيقية ثم يمرر استجابات Fake عبر Query Generation Service.
def main() -> int:
    """تشغيل Query Generation من دون Gemini حقيقية."""

    bigquery_client = bigquery.Client(
        project=GCP_PROJECT_ID
    )

    try:
        dataset = bigquery_client.get_dataset(
            f"{GCP_PROJECT_ID}."
            f"{BQ_DATASET_ID}"
        )

        catalog = load_query_schema_catalog(
            client=bigquery_client,
            project_id=GCP_PROJECT_ID,
            dataset_id=BQ_DATASET_ID,
            allowed_table_ids=(TABLE_ID,),
            location=dataset.location,
        )

        fake_gemini_client = FakeGeminiClient(
            [
                build_fake_plan_output(),
                build_fake_sql_output(),
            ]
        )

        result = generate_finops_query(
            client=fake_gemini_client,
            user_question=(
                "What is the total billed cost "
                "for AWS?"
            ),
            catalog=catalog,
            full_table_id=FULL_TABLE_ID,
        )

        print(
            "Fake query generation: PASS"
        )
        print(
            result.model_dump_json(
                indent=2
            )
        )
        print(
            "Fake Gemini calls: "
            f"{len(fake_gemini_client.interactions.requests)}"
        )

        return 0

    finally:
        bigquery_client.close()

# يبدأ التشغيل عند تنفيذ الملف مباشرة من Terminal.
if __name__ == "__main__":
    raise SystemExit(main())