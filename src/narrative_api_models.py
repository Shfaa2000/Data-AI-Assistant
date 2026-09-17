"""تعريف عقود البيانات الخاصة بواجهة Narrative HTTP.

يعرّف هذا الملف شكل السؤال الذي يستقبله FastAPI من HTTP Client،
وشكل Backend Envelope التي يعيدها إلى العميل بعد توليد السرد المالي.

تستخدم هذه النماذج Pydantic للتحقق من أسماء الحقول وأنواعها وحدودها，
ولمنع استقبال أو إعادة حقول غير معروفة.
"""
from pydantic import BaseModel, ConfigDict, Field
from src.narrative_response import NarrativeResponse

class NarrativeRequest(BaseModel):
    model_config = ConfigDict(
    extra="forbid",
    str_strip_whitespace=True,
)
    question: str = Field(
    ...,
    min_length=1,
    max_length=1000,
)
    
class NarrativeProvenance(BaseModel): 
    model_config = ConfigDict(
    extra="forbid",
    str_strip_whitespace=True,
)
    evidence_id: str
    pipeline_run_id: str
    source_table: str
    object_uri: str

class NarrativeExecution(BaseModel):
    model_config = ConfigDict(
    extra="forbid",
    str_strip_whitespace=True,
)
    interaction_id: str
    model_name: str
    interaction_status: str
    generated_at_utc: str

class NarrativeEnvelopeResponse(BaseModel):
    model_config = ConfigDict(
    extra="forbid",
    str_strip_whitespace=True,
)
    provenance: NarrativeProvenance
    execution: NarrativeExecution
    narrative: NarrativeResponse