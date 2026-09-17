"""ينسّق رحلة السرد المالي من Evidence حتى Envelope وTrace."""

from pathlib import Path

from src.config import LATEST_EVIDENCE_FILE
from src.narrative_envelope import (
    build_narrative_envelope,
)
from src.narrative_payload import (
    build_service_narrative_payload,
    load_verified_evidence,
)
from src.narrative_prompt import (
    build_narrative_prompt,
)
from src.narrative_response import (
    NarrativeResponse,
)
from src.narrative_trace import (
    build_narrative_trace,
)
from src.narrative_grounding import (
    validate_narrative_grounding,
)


def generate_finops_narrative(
    client,
    user_question: str,
    evidence_path: Path = LATEST_EVIDENCE_FILE,
    model_name: str = "gemini-3.6-flash",
) -> tuple[dict, dict]:
    """توليد السرد المالي من Evidence إلى Envelope وTrace."""

    # تحميل أحدث Evidence والتحقق من حالتها.
    evidence = load_verified_evidence(
        evidence_path
    )

    # استخراج البيانات المالية اللازمة للسؤال فقط.
    payload = build_service_narrative_payload(
        evidence
    )

    # بناء Prompt من البيانات الموثقة وسؤال المستخدم.
    prompt = build_narrative_prompt(
        payload=payload,
        user_question=user_question,
    )

    # إرسال Prompt إلى Gemini وطلب استجابة JSON منظمة.
    interaction = client.interactions.create(
        model=model_name,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": (
                NarrativeResponse.model_json_schema()
            ),
        },
    )

    # تحليل الاستجابة والتحقق من شكلها وقواعدها.
    narrative = (
        NarrativeResponse.model_validate_json(
            interaction.output_text
        )
    )
    validate_narrative_grounding(
    payload=payload,
    narrative=narrative,
)

    # إضافة هوية المصدر والتنفيذ إلى الجواب.
    envelope = build_narrative_envelope(
        evidence=evidence,
        interaction=interaction,
        narrative=narrative,
    )

    # استخراج سجل تشخيصي آمن.
    trace = build_narrative_trace(
        interaction=interaction,
        narrative=narrative,
    )

    return envelope, trace