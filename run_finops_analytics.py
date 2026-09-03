# ينشئ View تحليلية لتكاليف الخدمات في BigQuery أو يقرأ منها ترتيب الخدمات حسب التكلفة الموجبة.

import argparse
import json

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from src.config import (
    BASE_DIR,
    GCP_PROJECT_ID,
    BQ_DATASET_ID,
    BQ_PIPELINE_TABLE_ID,
    BQ_SERVICE_COST_VIEW_ID,
)

#     مسؤول عن إنشاء الـ View بأمان أو التأكد أن النسخة الموجودة هي نفسها المطلوبة.
def create_service_view(client):
    dataset_id = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"
    source_id = f"{dataset_id}.{BQ_PIPELINE_TABLE_ID}"
    view_id = f"{dataset_id}.{BQ_SERVICE_COST_VIEW_ID}"
    if source_id == view_id:
        raise ValueError("View and source table must differ.")

    source = client.get_table(source_id)
    required = {
        "BillingCurrency", "ProviderName", "ServiceName",
        "ServiceCategory", "BilledCost", "EffectiveCost",
    }
    missing = required - {field.name for field in source.schema}
    if missing:
        raise ValueError(f"Missing source columns: {sorted(missing)}")

#     فصل الاستعلام الطويل عن Python. Python يدير التنفيذ، وSQL يحتوي منطق التجميع المالي.
    sql_path = BASE_DIR / "queries" / "bigquery" / "v_service_costs.sql"
    sql = sql_path.read_text(encoding="utf-8").format(source_table=source_id)

    try:
        existing = client.get_table(view_id)
    except NotFound:
        view = bigquery.Table(view_id)
        view.view_query = sql
        view.view_use_legacy_sql = False
        view.description = (
            "Service costs by provider and billing currency; "
            "all loaded periods; published data only."
        )
        client.create_table(view)
        print(f"VIEW_CREATED: {view_id}")
    else:
        if existing.table_type != "VIEW":
            raise ValueError("The view name belongs to a non-view resource.")
        if existing.view_query.strip() != sql.strip():
            raise ValueError(
                "An existing view has a different definition. "
                "Review it before updating."
            )
        print(f"VIEW_ALREADY_CONFIGURED: {view_id}")

#     تابع منطق قراءة التحليل. يُستخدم من Terminal ويستدعيه finops_api.py أيضًا.
def read_service_costs(client, location, currency, provider, top_n):
    view_id = (
        f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_SERVICE_COST_VIEW_ID}"
    )
    sql = f"""
    SELECT
        BillingCurrency,
        ProviderName,
        ServiceName,
        service_categories,
        charge_line_count,
        ROUND(billed_cost, 6) AS billed_cost,
        ROUND(positive_billed_cost, 6) AS positive_billed_cost,
        ROUND(negative_billed_cost, 6) AS negative_billed_cost,
        ROUND(effective_cost, 6) AS effective_cost,
        ROUND(billed_effective_gap, 6) AS billed_effective_gap,
        negative_line_count,
        zero_billed_line_count,
        ROUND(positive_share_of_currency_pct, 2)
            AS positive_share_of_currency_pct,
        ROUND(positive_share_of_provider_pct, 2)
            AS positive_share_of_provider_pct
    FROM `{view_id}` AS costs
    WHERE BillingCurrency = @currency
    #     العملة إلزامية حتى لا نجمع أرقام عملات مختلفة.
      AND (@provider = '' OR ProviderName = @provider)
    ORDER BY costs.positive_billed_cost DESC, ProviderName, ServiceName
    LIMIT @top_n
    """
    job = client.query(
        sql,
        location=location,
        #هي كائن يجمع إعدادات تنفيذ استعلام BigQuery.
        job_config=bigquery.QueryJobConfig(
            #     حد حماية للتكلفة؛ يمنع الاستعلام من معالجة حجم أكبر من المسموح.
            maximum_bytes_billed=10 * 1024 * 1024,
            query_parameters=[
                #     يرسل القيم كمعاملات بدل دمجها داخل نص SQL. هذا أكثر أمانًا وأوضح للأنواع.
                bigquery.ScalarQueryParameter("currency", "STRING", currency),
                bigquery.ScalarQueryParameter("provider", "STRING", provider),
                bigquery.ScalarQueryParameter("top_n", "INT64", top_n),
            ],
        ),
    )
    rows = [dict(row) for row in job.result()]
    return {
        "source_view": view_id,
        "period_scope": "all_loaded_periods",
        "currency": currency,
        "provider_filter": provider or "ALL",
        "ranking": "positive_billed_cost_desc",
        "returned_services": len(rows),
        "query_job_id": job.job_id,
        "bytes_processed": job.total_bytes_processed,
        "services": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--create-view", action="store_true")
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--provider", default="")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.top <= 50:
        parser.error("--top must be between 1 and 50.")

    client = bigquery.Client(project=GCP_PROJECT_ID)
    try:
        if args.create_view:
            create_service_view(client)
            return
        dataset = client.get_dataset(f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}")
        result = read_service_costs(
            client,
            dataset.location,
            args.currency.strip().upper(),
            args.provider.strip(),
            args.top,
        )
        # تحوّل كائن Python إلى نص JSON.
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    finally:
        client.close()


if __name__ == "__main__":
    main()