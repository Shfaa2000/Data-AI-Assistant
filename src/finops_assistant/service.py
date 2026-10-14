"""
يربط Router بمساري Query وRAG،
ويعيد نتيجة موحدة لجميع الواجهات.
"""

import logging
import os
from enum import Enum
from time import perf_counter

from dotenv import load_dotenv
from google import genai

from src.finops_assistant.router import (
    route_question,
)

from src.finops_query.assistant_service import (
    answer_finops_question,
)

from src.finops_rag.assistant_service import (
    answer_finops_rag_question,
)

# يحدد مستوى Logging وشكل الرسائل التي تظهر في Terminal.
logging.basicConfig(
    level=logging.INFO,
    format=(
        # وقت ظهور الرسالة
        "%(asctime)s "
        # مستوى الرسالة، مثل INFO
        "%(levelname)s "
        # اسم الـLogger، وهو finops_assistant
        "%(name)s: "
        "%(message)s"
    ),
)
# ينشئ Logger خاصًا بالخدمة الموحدة.
logger = logging.getLogger(
    "finops_assistant"
)

# يحول Enum أو النص إلى قيمة نصية
# مناسبة للعقد الموحد.
def _text(value) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return str(value)


# يبني الشكل المشترك الذي تستلمه
# CLI وFastAPI وReact.
def build_unified_result(
    status: str,
    route: str,
    answer: str,
    sources: list[dict] | None = None,
) -> dict:
    allowed_routes = {
        "query",
        "rag",
        "needs_clarification",
        "unsupported",
    }

    if route not in allowed_routes:
        raise ValueError(
            f"Unsupported route: {route}"
        )

    return {
        "status": status,
        "route": route,
        "answer": answer,
        "sources": sources or [],
    }


# يشغل رحلة Query الموجودة ثم يحول
# نتيجتها إلى الشكل المشترك.
def run_query_tool(
    question: str,
) -> dict:
    result = answer_finops_question(
        question
    )

    result_status = _text(
        result.status
    ).strip().lower()

    sources = []
    # يضيف جدول BigQuery وموقعه كمصدر للجواب المالي.
    if result.allowed_table:
        sources.append(
            {
                "source_type": "bigquery",
                "source_name": (
                    result.allowed_table
                ),
                "location": (
                    result.location
                ),
            }
        )

    return build_unified_result(
        status=result_status,
        route="query",
        answer=result.message,
        sources=sources,
    )


# يشغل رحلة RAG الموجودة ثم يحول
# نتيجتها إلى الشكل المشترك.
def run_rag_tool(
    question: str,
) -> dict:
    result = answer_finops_rag_question(
        question
    )
    # يحول مصادر RAG المسترجعة إلى شكل المصادر المشترك.
    sources = [
        {
            "source_type": "document",
            "source_name": source[
                "source_name"
            ],
            "page_number": source.get(
                "page_number"
            ),
            "chunk_id": source.get(
                "chunk_id"
            ),
            "source_url": source.get(
                "source_url"
            ),
        }
        for source in result["sources"]
    ]

    return build_unified_result(
        status=result["status"],
        route="rag",
        answer=result["answer"],
        sources=sources,
    )


# يجهز اتصال Gemini الذي يستخدمه
# الـRouter فقط لتصنيف السؤال.
def create_router_client():
    load_dotenv()

    api_key = os.getenv(
        "GEMINI_API_KEY",
        "",
    ).strip()

    model_name = os.getenv(
        "GEMINI_MODEL",
        "",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

    if not model_name:
        raise RuntimeError(
            "GEMINI_MODEL is missing."
        )

    client = genai.Client(
        api_key=api_key
    )

    return client, model_name


# يشغل Router ثم يستدعي Tool المناسبة
# ويعيد جوابًا موحدًا.
def answer_finops_assistant(
    question: str,
) -> dict:
    normalized_question = (
        question.strip()
    )

    if not normalized_question:
        raise ValueError(
            "The question is required."
        )
    # يحفظ لحظة بدء الرحلة لحساب مدة تنفيذها لاحقًا.
    started_at = perf_counter()

    client, model_name = (
        create_router_client()
    )

    decision = route_question(
        client=client,
        question=normalized_question,
        model_name=model_name,
    )
    # يسجل المسار الذي اختاره Router للسؤال.
    logger.info(
    "Router selected route=%s",
    decision.route,
    )

    if decision.route == "query":
        result = run_query_tool(
            normalized_question
        )

    elif decision.route == "rag":
        result = run_rag_tool(
            normalized_question
        )

    elif (
        decision.route
        == "needs_clarification"
    ):
        clarification = (
            decision.clarification_question
            or decision.reason
        )

        result = build_unified_result(
            status="needs_clarification",
            route="needs_clarification",
            answer=clarification,
        )

    else:
        result = build_unified_result(
            status="unsupported",
            route="unsupported",
            answer=decision.reason,
        )
    # يحسب مدة الرحلة كاملة ثم يحولها من الثواني إلى milliseconds.
    duration_ms = (
        perf_counter() - started_at
    ) * 1000
    # يسجل المسار والحالة والمدة وعدد المصادر في النتيجة النهائية.
    logger.info(
        (
            "FinOps request completed "
            "route=%s status=%s "
            "duration_ms=%.2f sources=%d"
        ),
        result["route"],
        result["status"],
        duration_ms,
        len(result["sources"]),
    )

    return result