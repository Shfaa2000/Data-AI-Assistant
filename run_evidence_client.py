# يتصل بالـEvidence endpoint، يستقبل JSON الموثوق، ثم يعرض أهم النتائج بطريقة مقروءة.
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "http://127.0.0.1:8000/finops/evidence/latest"


def main() -> int:
    request = Request(
        API_URL,
        # أنا كعميل أفضّل أن يعيد الخادم الاستجابة بصيغة JSON.
        headers={"Accept": "application/json"},
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )
    # الخادم وصل إليه الطلب، لكنه أعاد حالة خطأ مثل 404 أو 422 أو 500.
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        print(f"API returned HTTP {error.code}: {body}")
        return 1
    # لم يتمكن العميل من الوصول إلى الخادم، مثل أن FastAPI غير مشغلة.
    except URLError as error:
        print(f"Could not reach the API: {error.reason}")
        return 1
    # وصلت استجابة، لكنها ليست JSON صالحاً.
    except json.JSONDecodeError as error:
        print(f"API returned invalid JSON: {error}")
        return 1

    metrics = payload["dataset_metrics"]
    checks = payload["reconciliation_checks"]
    passed_checks = sum(
        check["status"] == "PASS" for check in checks
    )
    top_service = payload.get("top_service") or {}
    # ادعم أكثر من تسمية محتملة للحقول، واستخدم N/A عند غياب القيمة.
    provider = (
        top_service.get("ProviderName")
        or top_service.get("provider")
        or "N/A"
    )
    service = (
        top_service.get("ServiceName")
        or top_service.get("service")
        or "N/A"
    )

    print(f"Evidence status: {payload['status']}")
    print(f"Evidence ID: {payload['evidence_id']}")
    print(f"Pipeline run ID: {payload['pipeline_run_id']}")
    print(f"Source table: {payload['source_table']}")
    print(f"Checks: {passed_checks}/{len(checks)} PASS")
    print(f"Rows: {metrics['row_count']}")
    print(f"Billed cost: {metrics['billed_cost']:.9f}")
    print(f"Effective cost: {metrics['effective_cost']:.9f}")
    print(
        "Positive billed cost: "
        f"{metrics['positive_billed_cost']:.9f}"
    )
    print(
        "Negative billed cost: "
        f"{metrics['negative_billed_cost']:.9f}"
    )
    print(f"Top service: {provider} | {service}")
    print("Limitations:")

    for limitation in payload["limitations"]:
        print(f"- {limitation}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

