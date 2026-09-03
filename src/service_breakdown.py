# ينفذ تحليلًا تفصيليًا لخدمة واحدة عند مزود وعملة محددين، ثم يجمع النتائج ويعيدها بصيغة مناسبة للـAPI.

# يجمع الأرقام العشرية بدقة أفضل من sum العادية عند العمل مع عدة float.
from math import fsum

from google.cloud import bigquery

from src.config import BASE_DIR, BQ_DATASET_ID, BQ_PIPELINE_TABLE_ID, GCP_PROJECT_ID

# وهو منطق أعمال مهم لأنه يحدد عقد النتيجة التي تتوقعها API والـClient.
def read_service_breakdown(client, location, provider, service, currency):
    source_table = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_PIPELINE_TABLE_ID}"
    sql_path = BASE_DIR / "queries" / "bigquery" / "service_breakdown.sql"
    sql = sql_path.read_text(encoding="utf-8").format(source_table=source_table)

    #    بلوك BigQuery قياسي. وظيفته منع Legacy SQL، حماية حد المعالجة، وإرسال المعاملات بأنواعها.
    job_config = bigquery.QueryJobConfig(
        use_legacy_sql=False,
        maximum_bytes_billed=10 * 1024 * 1024,
        query_parameters=[
            bigquery.ScalarQueryParameter("provider", "STRING", provider),
            bigquery.ScalarQueryParameter("service", "STRING", service),
            bigquery.ScalarQueryParameter("currency", "STRING", currency),
        ],
    )

    job = client.query(sql, location=location, job_config=job_config)
    groups = [dict(row) for row in job.result()]

    money_fields = (
        "billed_cost",
        "positive_billed_cost",
        "negative_billed_cost",
        "effective_cost",
    )

    for group in groups:
        for field in money_fields:
            if group[field] is not None:
                #    BigQuery قد يرجع أنواعًا رقمية لا تُحوّل إلى JSON بسهولة في كل السياقات، لذلك يوحدها الملف.
                group[field] = float(group[field])

    totals = None

    if groups:
        totals = {}

        for field in money_fields:
            values = [group[field] for group in groups]
            totals[field] = (
                None if any(value is None for value in values)
                # إذا كانت كل قيم الحقل متوفرة، يحسب مجموعها. إذا احتوت أي مجموعة على None، يجعل الإجمالي None بدل الادعاء أن الإجمالي معروف.
                else fsum(values)
            )

        for field in (
            "charge_line_count",
            "negative_line_count",
            "zero_billed_line_count",
        ):
            totals[field] = sum(group[field] for group in groups)

    return {
        "status": "ok" if groups else "no_data",
        "source_table": source_table,
        "period_scope": "all_loaded_periods",
        "provider": provider,
        "service": service,
        "currency": currency,
        "grouping": ["service_category", "charge_category"],
        "returned_groups": len(groups),
        "query_job_id": job.job_id,
        "totals": totals,
        "groups": groups,
    }