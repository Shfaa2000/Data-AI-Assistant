"""بناء Prompt ثابت يجمع قواعد السرد المالي،
والـpayload الموثقة، وسؤال المستخدم."""

import json

def build_narrative_prompt(
    payload: dict,
    user_question: str,
) -> str:
    """Build one grounded FinOps narrative prompt."""

    # تنظيف السؤال ورفضه محليًا إذا كان فارغًا،
    # حتى لا نستهلك استدعاء Gemini بلا فائدة.
    normalized_question = user_question.strip()

    if not normalized_question:
        raise ValueError(
            "user_question must not be empty."
        )

    # نرفض الـpayload الفارغة قبل إرسال الطلب للنموذج.
    if not payload:
        raise ValueError(
            "payload must not be empty."
        )

    # تحويل Dictionary إلى JSON نصي قياسي حتى ندخله
    # داخل الـPrompt بصورة واضحة ومنظمة.
    payload_json = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )

    # بناء Prompt يفصل التعليمات عن البيانات
    # وعن سؤال المستخدم.
    prompt = f"""
    <role>
    You are a FinOps narrative assistant.
    - Every metric listed in used_metrics must appear in answer using its supplied numeric value.
    - Do not include any numeric value that is not present in data_json.
    - When status is unsupported, used_metrics must be empty and answer must not contain unsupported numeric claims.
    </role>

    <source_policy>
    Use only the information inside data_json.
    Do not use external knowledge for financial claims.
    </source_policy>

    <rules>
    - Copy all financial values exactly as supplied.
    - Do not calculate new financial values.
    - Do not invent discounts, causes, savings, or utilization claims.
    - If the supplied data cannot support the question, use status "unsupported".
    - used_metrics must contain only metric names found in data_json.
    - Write the answer in clear Arabic.
    - Follow the required response schema.
    </rules>

    <data_json>
    {payload_json}
    </data_json>

    <user_question>
    {normalized_question}
    </user_question>
    """

    return prompt.strip()