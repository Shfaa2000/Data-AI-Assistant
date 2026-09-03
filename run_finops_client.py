# عميل محلي يرسل طلب HTTP إلى endpoint تفصيل الخدمة ويحوّل JSON المستلمة إلى عرض مختصر في Terminal.

#    أدوات قياسية لبناء طلب HTTP، قراءة JSON، والتعامل مع خيارات Terminal.
import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

#    منطق بسيط مهم: يحسب نسبة القيمة الموجبة للمجموعة إلى مجموع التكاليف الموجبة للخدمة.
def positive_share(value, total):
    if value is None or total is None:
        return None

    if total == 0:
        return None

    return 100 * value / total


def main():
    parser = argparse.ArgumentParser()
    #    يحدد القيم التي يمكن تغييرها من Terminal مع defaults مناسبة لاختبار EC2.
    parser.add_argument(
        "--provider",
        default="AWS",
    )

    parser.add_argument(
        "--service",
        default="Amazon Elastic Compute Cloud",
    )

    parser.add_argument(
        "--currency",
        default="USD",
    )

    args = parser.parse_args()

    params = urlencode(vars(args))

    #    يشير إلى API المحلية، وليس BigQuery. يجب أن يكون Uvicorn شغالًا قبل تشغيل هذا الملف.
    url = (
        "http://127.0.0.1:8000/finops/service-breakdown"
        f"?{params}"
    )

    try:
        with urlopen(url, timeout=60) as response:
            payload = json.load(response)

    except HTTPError as exc:
        message = exc.read().decode("utf-8")

        print(
            f"API returned HTTP {exc.code}: "
            f"{message}"
        )

        raise SystemExit(1) from exc

    except (URLError, TimeoutError) as exc:
        print(
            f"Could not reach the local API: {exc}"
        )

        raise SystemExit(1) from exc

    if payload["status"] == "no_data":
        print(
            "No matching data. "
            "This is not evidence of zero cost."
        )
        return

    totals = payload["totals"]

    print(
        f"Service: {payload['service']} | "
        f"Currency: {payload['currency']}"
    )

    print(
        f"Scope: {payload['period_scope']}"
    )

    print(
        f"Charge lines: "
        f"{totals['charge_line_count']}"
    )

    for field in (
        "positive_billed_cost",
        "negative_billed_cost",
        "billed_cost",
        "effective_cost",
    ):
        value = totals[field]

        if value is None:
            print(f"{field}: unavailable")
        else:
            print(f"{field}: {value:.9f}")

    positive_total = totals["positive_billed_cost"]

    print("Breakdown:")

    for group in payload["groups"]:
        share = positive_share(
            group["positive_billed_cost"],
            positive_total,
        )

        if share is None:
            share_text = "unavailable"
        else:
            share_text = f"{share:.2f}%"

        print(
            f"{group['service_category']} / "
            f"{group['charge_category']} | "
            f"rows={group['charge_line_count']} | "
            f"billed={group['billed_cost']} | "
            f"positive_share={share_text}"
        )


if __name__ == "__main__":
    main()