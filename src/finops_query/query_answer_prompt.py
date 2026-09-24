"""
يجهز السؤال وEvidence والقواعد."""

import json
from typing import Any

from .query_dynamic_evidence import (
    DynamicQueryEvidence,
)

# يحذف Metadata التشغيلية التي لا تحتاجها Gemini لصياغة الجواب.
def build_narrative_evidence_payload(
    evidence: DynamicQueryEvidence,
) -> dict[str, Any]:
    return evidence.model_dump(
        mode="json",
        exclude={
            "job_id",
            "location",
            "total_bytes_processed",
        },
    )

# يبني تعليمات تمنع Gemini من اختراع أرقام أو معلومات مالية.
def build_finops_answer_prompt(
    evidence: DynamicQueryEvidence,
) -> str:
    evidence_payload = (
        build_narrative_evidence_payload(
            evidence
        )
    )

    evidence_json = json.dumps(
        evidence_payload,
        ensure_ascii=False,
        indent=2,
    )

    return f"""
ROLE:
You are a FinOps answer writer.

TASK:
Answer the user's financial question in clear English
using only the supplied DYNAMIC_EVIDENCE.

GROUNDING RULES:
- Use only facts and values present in DYNAMIC_EVIDENCE.
- Never invent, estimate, infer, or recalculate a number.
- Do not create percentages unless they already exist in the evidence.
- Preserve the exact meaning of the user's question.
- Do not claim a currency unless the evidence includes one.
- Do not mention SQL, prompts, validators, schemas, credentials,
  job IDs, locations, byte counts, or internal implementation details.
- Keep the answer concise and understandable.
- The answer field must be written in English.
- If the evidence contains no usable metric value, return
  status "no_data" and explain that no matching data was found.
- If data exists, return status "answered".
- For every fact used, provide its zero-based row index
  and the exact evidence columns used.
- Do not mention row indices in the answer text.
- Return only JSON matching the required response schema.
- Monetary metric values may be rounded to exactly two
  decimal places using standard financial rounding.
- Do not round row counts, limits, dates, or identifiers.
- Do not otherwise transform or recalculate values.

DYNAMIC_EVIDENCE:
{evidence_json}
""".strip()