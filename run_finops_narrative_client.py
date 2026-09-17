# إرسال سؤال إلى FastAPI عبر HTTP، واستلام Envelope وعرض أهم حقولها.
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# يرسل سؤالًا إلى Narrative API عبر HTTP،
# ثم يستقبل Envelope ويعرض المصدر والتنفيذ والجواب المالي.

API_URL = "http://127.0.0.1:8000/v1/narratives"

request_body = {
    "question": (
        "اذكر قيمة Billed Cost وقيمة Effective Cost للخدمة، "
        "وحدد أيهما أقل باستخدام البيانات المرسلة فقط."
    )
}

def main() -> int:
    request = Request(
    API_URL,
    data=json.dumps(
        request_body,
        ensure_ascii=False,
    ).encode("utf-8"),
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
    },
    method="POST",
)

    try:
        with urlopen(request, timeout=30) as response:
            http_status = response.status
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

    try:
        provenance = payload["provenance"]
        execution = payload["execution"]
        narrative = payload["narrative"]

    except (KeyError, TypeError) as error:
        print(
            "API response does not match "
            f"Narrative Envelope contract: {error}"
        )
        return 1

    print(f"HTTP status: {http_status}")

    print("\nProvenance:")
    print(f"Evidence ID: {provenance['evidence_id']}")
    print(
        "Pipeline run ID: "
        f"{provenance['pipeline_run_id']}"
    )
    print(f"Source table: {provenance['source_table']}")
    print(f"Object URI: {provenance['object_uri']}")

    print("\nExecution:")
    print(
        "Interaction ID: "
        f"{execution['interaction_id']}"
    )
    print(f"Model: {execution['model_name']}")
    print(
        "Interaction status: "
        f"{execution['interaction_status']}"
    )
    print(
        "Generated at: "
        f"{execution['generated_at_utc']}"
    )

    print("\nNarrative:")
    print(f"Status: {narrative['status']}")
    print(f"Answer: {narrative['answer']}")

    used_metrics = narrative["used_metrics"]
    print(
        "Used metrics: "
        + (", ".join(used_metrics) or "None")
    )

    print("Limitations:")
    for limitation in narrative["limitations"]:
        print(f"- {limitation}")

    unsupported_reason = narrative.get(
        "unsupported_reason"
    )

    if unsupported_reason:
        print(
            "Unsupported reason: "
            f"{unsupported_reason}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

