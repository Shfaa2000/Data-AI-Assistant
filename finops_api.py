"""
واجهة FastAPI لرحلة FinOps Assistant المشتركة.

تستقبل سؤالًا من Endpoint، وترسله إلى Assistant Service نفسها
التي يستخدمها CLI، ثم تعيد العقد المنظم بصيغة JSON.
"""

import logging

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from src.finops_query.assistant_service import (
    FinOpsAssistantResult,
    answer_finops_question,
)


app = FastAPI(
    title="Data-AI Assistant",
    version="0.1.0",
)

# يسجل أخطاء الخادم مع مصدرها دون طباعتها داخل منطق Assistant Core.
logger = logging.getLogger("uvicorn.error")


class FinOpsQueryRequest(BaseModel):
    """شكل طلب السؤال الذي تقبله واجهة FinOps."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(
        min_length=1,
        max_length=1000,
    )


@app.get("/health")
def health() -> dict[str, str]:

    return {
        "status": "ok",
        "scope": "api_process_only",
    }


@app.post(
    "/finops/query",
    response_model=FinOpsAssistantResult,
)
def query_answer(request: FinOpsQueryRequest) -> FinOpsAssistantResult:
    """يشغل الرحلة المشتركة ويعيد النتيجة نفسها التي يعرضها CLI."""

    try:
        return answer_finops_question(request.question)
    except Exception as exc:
        logger.exception("FinOps pipeline failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc
    except Exception as exc:
        logger.exception("FinOps request failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The FinOps query could not be completed.",
        ) from exc

