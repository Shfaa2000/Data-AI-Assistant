"""دمج مصدر الحقيقة وبيانات التنفيذ مع السرد الذي تم التحقق منه."""
# يدمج هوية Evidence ومعلومات تشغيل Gemini مع الجواب المنظم الذي تم التحقق منه.

from datetime import datetime

from src.evidence import EvidenceBundle
from src.narrative_response import NarrativeResponse


def value_as_text(value) -> str:
    """تحويل Enum أو datetime أو قيمة عادية إلى نص."""

    if isinstance(value, datetime):
        return value.isoformat()

    if hasattr(value, "value"):
        return str(value.value)

    return str(value)


def build_narrative_envelope(
    evidence: EvidenceBundle,
    interaction,
    narrative: NarrativeResponse,
) -> dict:
    """بناء النتيجة الموثقة التي يملكها الـBackend."""

    return {
        "provenance": {
            "evidence_id": evidence.evidence_id,
            "pipeline_run_id": (
                evidence.pipeline_run_id
            ),
            "source_table": evidence.source_table,
            "object_uri": evidence.object_uri,
        },
        "execution": {
            "interaction_id": interaction.id,
            "model_name": interaction.model,
            "interaction_status": value_as_text(
                interaction.status
            ),
            "generated_at_utc": value_as_text(
                interaction.created
            ),
        },
        "narrative": narrative.model_dump(),
    }