"""إنشاء سجل تشخيصي آمن لحالة التفاعل واستهلاك التوكنات."""
# يستخرج حالة Gemini واستهلاك التوكنات وأنواع الخطوات من دون كشف أسرار أو محتوى التفكير.

from src.narrative_response import NarrativeResponse


def build_narrative_trace(
    interaction,
    narrative: NarrativeResponse,
) -> dict:
    """استخراج معلومات التتبع الآمنة فقط."""

    usage = interaction.usage

    interaction_status = getattr(
        interaction.status,
        "value",
        interaction.status,
    )

    return {
        "interaction_id": interaction.id,
        "model": interaction.model,
        "interaction_status": str(
            interaction_status
        ),
        "narrative_status": narrative.status,
        "input_tokens": usage.total_input_tokens,
        "output_tokens": usage.total_output_tokens,
        "thought_tokens": (
            usage.total_thought_tokens
        ),
        "tool_use_tokens": (
            usage.total_tool_use_tokens
        ),
        "total_tokens": usage.total_tokens,
        "step_types": [
            step.type
            for step in (interaction.steps or [])
        ],
    }