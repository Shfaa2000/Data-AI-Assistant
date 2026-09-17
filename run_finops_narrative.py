# قائد تشغيل Narrative V1: يجهز Gemini Client،
# ويستدعي Narrative Service، ويعرض Envelope وTrace.

import json
import os

from dotenv import load_dotenv
from google import genai

from src.narrative_service import (
    generate_finops_narrative,
)


def main() -> int:
    """تشغيل Narrative V1 وعرض النتيجة والتتبع."""

    # تحميل متغيرات البيئة من ملف .env.
    load_dotenv()

    # قراءة المفتاح من البيئة وعدم وضعه داخل الكود.
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY was not found."
        )

    # إنشاء Client التي ستتواصل مع Gemini.
    client = genai.Client(
        api_key=api_key,
    )

    # سؤال تجريبي مدعوم بالبيانات الموجودة.
    user_question = (
        "اذكر قيمة Billed Cost وقيمة Effective Cost "
        "للخدمة، وحدد أيهما أقل باستخدام "
        "البيانات المرسلة فقط."
    )

    # استدعاء Service الداخلية التي تنفذ الرحلة كاملة.
    envelope, trace = generate_finops_narrative(
        client=client,
        user_question=user_question,
    )

    # عرض النتيجة الموثقة.
    print("Envelope:")
    print(
        json.dumps(
            envelope,
            ensure_ascii=False,
            indent=2,
        )
    )

    # عرض سجل التشخيص الآمن.
    print("\nTrace:")
    print(
        json.dumps(
            trace,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())